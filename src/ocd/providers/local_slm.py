"""
Local Small Language Model Provider
===================================

Provider implementation for local SLMs (Small Language Models) using
transformers and local inference for privacy-focused processing.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
import structlog

from ocd.core.exceptions import OCDProviderError
from ocd.core.types import ProviderConfig, ProviderType, TaskRequest, TaskResponse
from ocd.providers.base import BaseProvider

logger = structlog.get_logger(__name__)


class LocalSLMProvider(BaseProvider):
    """
    Local Small Language Model provider.

    Uses lightweight transformer models for specific tasks:
    - File classification
    - Content extraction
    - Pattern recognition
    - Simple text generation
    """

    def __init__(self, config: ProviderConfig):
        """Initialize Local SLM provider."""
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._model_loaded = False

    async def initialize(self) -> None:
        """Initialize the local SLM models."""
        try:
            logger.info("Initializing Local SLM provider", provider_name=self.name)

            # Import transformers in initialize to avoid startup delays
            try:
                from transformers import pipeline, AutoTokenizer, AutoModel
                import torch

                self._transformers_available = True
            except ImportError as e:
                raise OCDProviderError(
                    "Transformers library not available. Install with: pip install transformers torch",
                    provider_name=self.name,
                    cause=e,
                )

            # Load model configuration
            model_name = self.config.model_name or "microsoft/DialoGPT-small"

            # Create pipeline based on task
            await self._load_models(model_name)

            self._initialized = True
            logger.info(
                "Local SLM provider initialized",
                provider_name=self.name,
                model=model_name,
            )

        except Exception as e:
            logger.error("Failed to initialize Local SLM provider", error=str(e))
            raise OCDProviderError(
                f"Local SLM initialization failed: {e}",
                provider_name=self.name,
                cause=e,
            )

    async def _load_models(self, model_name: str) -> None:
        """Load the transformer models."""
        try:
            from transformers import pipeline

            # Use text-generation pipeline for general tasks
            loop = asyncio.get_event_loop()

            # Load pipeline in thread pool to avoid blocking
            self.pipeline = await loop.run_in_executor(
                None,
                lambda: pipeline(
                    "text-generation",
                    model=model_name,
                    tokenizer=model_name,
                    device=-1,  # CPU
                    max_length=512,
                    do_sample=True,
                    temperature=0.7,
                ),
            )

            self._model_loaded = True
            logger.info("Model loaded successfully", model=model_name)

        except Exception as e:
            raise OCDProviderError(
                f"Failed to load model {model_name}: {e}",
                provider_name=self.name,
                cause=e,
            )

    def _check_availability(self) -> bool:
        """Check if the provider is available."""
        return self._initialized and self._model_loaded and self.pipeline is not None

    async def execute_task(self, request: TaskRequest) -> TaskResponse:
        """Execute a task using the local SLM."""
        if not self.is_available:
            raise OCDProviderError(
                "Local SLM provider not available", provider_name=self.name
            )

        self.validate_request(request)

        start_time = time.time()

        try:
            # Route to specific task handler
            task_handlers = {
                "analyze_directory": self._analyze_directory,
                "classify_files": self._classify_files,
                "extract_patterns": self._extract_patterns,
                "summarize_content": self._summarize_content,
                "generate_script": self._generate_script,
            }

            handler = task_handlers.get(request.task_type)
            if not handler:
                # Fallback to generic text generation
                handler = self._generate_text

            result = await handler(request)
            execution_time = time.time() - start_time

            return TaskResponse(
                task_type=request.task_type,
                success=True,
                result=result,
                provider_used=self.name,
                execution_time=execution_time,
                metadata={
                    "model_name": self.config.model_name,
                    "provider_type": "local_slm",
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Task execution failed", task_type=request.task_type, error=str(e)
            )

            return TaskResponse(
                task_type=request.task_type,
                success=False,
                result=None,
                provider_used=self.name,
                execution_time=execution_time,
                error_message=str(e),
            )

    async def _analyze_directory(self, request: TaskRequest) -> Dict[str, Any]:
        """Analyze directory structure and content."""
        analysis_result = request.analysis_result
        if not analysis_result:
            raise OCDProviderError("Analysis result required for directory analysis")

        # Create analysis prompt
        prompt = f"""
        Analyze this directory structure and provide insights:
        
        Directory: {analysis_result.directory_info.root_path}
        Total files: {analysis_result.directory_info.total_files}
        File types: {', '.join(set(f.file_type for f in analysis_result.directory_info.files[:10]))}
        
        Task: {request.prompt}
        
        Provide:
        1. Purpose of this directory
        2. Main file types and their roles
        3. Suggested organization improvements
        4. Potential automation opportunities
        """

        result = await self._generate_text_internal(prompt, max_length=300)

        return {
            "analysis": result,
            "directory_path": str(analysis_result.directory_info.root_path),
            "file_count": analysis_result.directory_info.total_files,
            "insights": self._extract_insights(result),
        }

    async def _classify_files(self, request: TaskRequest) -> Dict[str, Any]:
        """Classify files by type and purpose."""
        files_info = request.context.get("files", [])

        classifications = {}
        for file_info in files_info[:20]:  # Limit to avoid token limits
            prompt = f"""
            Classify this file:
            Name: {file_info.get('name', 'unknown')}
            Type: {file_info.get('file_type', 'unknown')}
            Size: {file_info.get('size', 0)} bytes
            
            Classification categories:
            - source_code
            - documentation
            - configuration
            - data
            - media
            - temporary
            - other
            
            Category:"""

            result = await self._generate_text_internal(prompt, max_length=50)
            category = result.strip().lower().split()[0] if result else "other"

            classifications[file_info.get("name", "unknown")] = category

        return {
            "classifications": classifications,
            "summary": self._summarize_classifications(classifications),
        }

    async def _extract_patterns(self, request: TaskRequest) -> Dict[str, Any]:
        """Extract patterns from directory content."""
        content = request.context.get("content", "")

        prompt = f"""
        Extract patterns from this content:
        
        {content[:2000]}  # Limit content length
        
        Find:
        1. Naming conventions
        2. Directory structures
        3. File organization patterns
        4. Common themes
        
        Patterns:"""

        result = await self._generate_text_internal(prompt, max_length=200)
        patterns = self._parse_patterns(result)

        return {"patterns": patterns, "analysis": result}

    async def _summarize_content(self, request: TaskRequest) -> Dict[str, Any]:
        """Summarize directory or file content."""
        content = request.context.get("content", request.prompt)

        prompt = f"""
        Summarize this content in 2-3 sentences:
        
        {content[:1500]}
        
        Summary:"""

        result = await self._generate_text_internal(prompt, max_length=150)

        return {
            "summary": result.strip(),
            "length": len(content),
            "key_points": self._extract_key_points(result),
        }

    async def _generate_script(self, request: TaskRequest) -> Dict[str, Any]:
        """Generate a simple script based on analysis."""
        analysis = request.context.get("analysis", {})

        prompt = f"""
        Generate a simple shell script for:
        {request.prompt}
        
        Context: {json.dumps(analysis, indent=2)[:500]}
        
        Script should be safe and simple.
        
        #!/bin/bash
        # {request.prompt}
        """

        result = await self._generate_text_internal(prompt, max_length=300)

        return {"script": result, "language": "bash", "description": request.prompt}

    async def _generate_text(self, request: TaskRequest) -> str:
        """Generic text generation for fallback."""
        return await self._generate_text_internal(request.prompt)

    async def _generate_text_internal(self, prompt: str, max_length: int = 200) -> str:
        """Internal text generation method."""
        try:
            loop = asyncio.get_event_loop()

            # Generate text in thread pool
            result = await loop.run_in_executor(
                None,
                lambda: self.pipeline(
                    prompt,
                    max_length=len(prompt) + max_length,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.pipeline.tokenizer.eos_token_id,
                ),
            )

            generated_text = result[0]["generated_text"]
            # Extract only the new generated part
            new_text = generated_text[len(prompt) :].strip()

            return new_text

        except Exception as e:
            logger.error("Text generation failed", error=str(e))
            raise OCDProviderError(
                f"Text generation failed: {e}", provider_name=self.name, cause=e
            )

    def _extract_insights(self, text: str) -> List[str]:
        """Extract insights from analysis text."""
        insights = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line and (
                line.startswith("-") or line.startswith("*") or line.startswith("1.")
            ):
                insights.append(line.lstrip("-*1234567890. "))
        return insights[:5]  # Limit insights

    def _summarize_classifications(
        self, classifications: Dict[str, str]
    ) -> Dict[str, int]:
        """Summarize file classifications."""
        summary = {}
        for category in classifications.values():
            summary[category] = summary.get(category, 0) + 1
        return summary

    def _parse_patterns(self, text: str) -> List[str]:
        """Parse patterns from generated text."""
        patterns = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:  # Reasonable pattern length
                patterns.append(line)
        return patterns[:10]  # Limit patterns

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from summary."""
        # Simple extraction based on sentence structure
        sentences = text.split(".")
        points = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Meaningful length
                points.append(sentence)
        return points[:3]  # Limit key points

    def get_supported_tasks(self) -> List[str]:
        """Get supported task types for Local SLM."""
        return [
            "analyze_directory",
            "classify_files",
            "extract_patterns",
            "summarize_content",
            "generate_script",
        ]

    async def cleanup(self) -> None:
        """Clean up model resources."""
        logger.info("Cleaning up Local SLM provider", provider_name=self.name)

        # Clear model references to free memory
        self.pipeline = None
        self.model = None
        self.tokenizer = None
        self._model_loaded = False

        # Force garbage collection
        import gc

        gc.collect()

        logger.info("Local SLM provider cleanup completed")

"""
Local Small Language Model Provider
===================================

Provider implementation for specialized local SLMs (Small Language Models) 
using individual task-specific models for privacy-focused processing.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
import structlog

from ocd.core.exceptions import OCDProviderError
from ocd.core.types import ProviderConfig, ProviderType, TaskRequest, TaskResponse
from ocd.providers.base import BaseProvider
from ocd.models.manager import SLMModelManager

logger = structlog.get_logger(__name__)


class LocalSLMProvider(BaseProvider):
    """
    Local Small Language Model provider using specialized models.

    Features individual specialized SLMs for:
    - File classification (DistilBERT, MobileBERT)
    - Content extraction (T5-small, BART-base)
    - File naming suggestions (GPT-2 small, fine-tuned)
    - Duplicate detection (SentenceTransformers)
    - Pattern recognition and analysis
    """

    def __init__(self, config: ProviderConfig):
        """Initialize Local SLM provider."""
        super().__init__(config)
        self.slm_manager = None
        self._model_loaded = False

    async def initialize(self) -> None:
        """Initialize the local SLM models."""
        try:
            logger.info("Initializing Local SLM provider", provider_name=self.name)

            # Check for required packages
            try:
                import transformers
                import torch
                import sentence_transformers

                self._dependencies_available = True
            except ImportError as e:
                raise OCDProviderError(
                    "Required packages not available. Install with: pip install transformers torch sentence-transformers",
                    provider_name=self.name,
                    cause=e,
                )

            # Initialize SLM Model Manager
            self.slm_manager = SLMModelManager(
                cache_dir=self.config.cache_dir,
                max_memory_usage=getattr(
                    self.config, "max_memory_usage", 2 * 1024 * 1024 * 1024
                ),
                idle_timeout=getattr(self.config, "idle_timeout", 300.0),
                auto_unload=getattr(self.config, "auto_unload", True),
            )

            await self.slm_manager.initialize()

            self._initialized = True
            self._model_loaded = True

            logger.info(
                "Local SLM provider initialized successfully",
                provider_name=self.name,
                supported_models=list(self.slm_manager.get_supported_models().keys()),
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
        return self._initialized and self._model_loaded and self.slm_manager is not None

    async def execute_task(self, request: TaskRequest) -> TaskResponse:
        """Execute a task using specialized SLM models."""
        if not self.is_available:
            raise OCDProviderError(
                "Local SLM provider not available", provider_name=self.name
            )

        self.validate_request(request)

        start_time = time.time()

        try:
            # Route to specialized SLM handlers
            task_handlers = {
                "analyze_directory": self._analyze_directory,
                "classify_files": self._classify_files,
                "find_similar_files": self._find_similar_files,
                "find_duplicates": self._find_duplicates,
                "extract_patterns": self._extract_patterns,
                "summarize_content": self._summarize_content,
                "generate_script": self._generate_script,
            }

            handler = task_handlers.get(request.task_type)
            if not handler:
                # Fallback to classification for unknown tasks
                handler = self._classify_files

            result = await handler(request)
            execution_time = time.time() - start_time

            # Get model status for metadata
            model_status = self.slm_manager.get_model_status()

            return TaskResponse(
                task_type=request.task_type,
                success=True,
                result=result,
                provider_used=self.name,
                execution_time=execution_time,
                metadata={
                    "provider_type": "local_slm",
                    "models_used": list(model_status["models"].keys()),
                    "total_memory_usage": model_status["total_memory_usage"],
                    "models_loaded": model_status["loaded_models"],
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
        """Classify files using specialized classifier SLM."""
        files_info = request.context.get("files", [])

        if not files_info:
            return {"classifications": {}, "summary": {}, "error": "No files provided"}

        # Use the specialized file classifier
        try:
            classifications = await self.slm_manager.batch_classify_files(
                files_info[:50], batch_size=16  # Process up to 50 files
            )

            # Convert results to expected format
            file_classifications = {}
            category_summary = {}

            for i, file_info in enumerate(files_info[: len(classifications)]):
                file_name = file_info.get("name", f"file_{i}")
                classification = classifications[i]

                category = classification.get("category", "unknown")
                confidence = classification.get("confidence", 0.0)

                file_classifications[file_name] = {
                    "category": category,
                    "confidence": confidence,
                    "subcategories": classification.get("subcategories", []),
                }

                # Update summary
                category_summary[category] = category_summary.get(category, 0) + 1

            return {
                "classifications": file_classifications,
                "summary": category_summary,
                "total_files": len(files_info),
                "processed_files": len(classifications),
                "model_info": "specialized_file_classifier_slm",
            }

        except Exception as e:
            logger.error("File classification failed", error=str(e))
            return {
                "classifications": {},
                "summary": {},
                "error": f"Classification failed: {e}",
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

    async def _find_similar_files(self, request: TaskRequest) -> Dict[str, Any]:
        """Find similar files using specialized similarity SLM."""
        target_file = request.context.get("target_file")
        compare_files = request.context.get("compare_files", [])

        if not target_file:
            return {"error": "No target file specified for similarity search"}

        try:
            # Use the specialized similarity detector
            result = await self.slm_manager.find_similar_files(
                target_file, compare_files=compare_files
            )

            return {**result, "model_info": "specialized_similarity_detector_slm"}

        except Exception as e:
            logger.error("Similarity detection failed", error=str(e))
            return {"error": f"Similarity detection failed: {e}"}

    async def _find_duplicates(self, request: TaskRequest) -> Dict[str, Any]:
        """Find duplicate files in directory using similarity SLM."""
        directory_path = request.context.get("directory_path")

        if not directory_path:
            analysis_result = request.analysis_result
            if analysis_result:
                directory_path = analysis_result.directory_info.root_path
            else:
                return {"error": "No directory specified for duplicate detection"}

        try:
            from pathlib import Path

            # Use the specialized duplicate detector
            result = await self.slm_manager.find_duplicates_in_directory(
                Path(directory_path)
            )

            return {**result, "model_info": "specialized_similarity_detector_slm"}

        except Exception as e:
            logger.error("Duplicate detection failed", error=str(e))
            return {"error": f"Duplicate detection failed: {e}"}

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

        # Clean up SLM model manager
        if self.slm_manager:
            await self.slm_manager.cleanup()
            self.slm_manager = None

        self._model_loaded = False

        # Force garbage collection
        import gc

        gc.collect()

        logger.info("Local SLM provider cleanup completed")

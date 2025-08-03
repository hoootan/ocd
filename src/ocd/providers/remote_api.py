"""
Remote API Provider
==================

Provider implementation for remote AI APIs (OpenAI, Anthropic, Google, etc.)
with proper rate limiting, error handling, and failover.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
import structlog
import httpx

from ocd.core.exceptions import OCDProviderError
from ocd.core.types import ProviderConfig, ProviderType, TaskRequest, TaskResponse
from ocd.providers.base import BaseProvider

logger = structlog.get_logger(__name__)


class RemoteAPIProvider(BaseProvider):
    """
    Remote API provider for cloud-based AI services.

    Supports:
    - OpenAI GPT models
    - Anthropic Claude models
    - Google Gemini models
    - Custom API endpoints
    """

    def __init__(self, config: ProviderConfig):
        """Initialize Remote API provider."""
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self.api_key: Optional[str] = None
        self.api_endpoint: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the remote API provider."""
        try:
            logger.info("Initializing Remote API provider", provider_name=self.name)

            # Get API key from environment or credential store
            await self._setup_credentials()

            # Set up API endpoint
            self._setup_endpoint()

            # Create HTTP client with proper settings
            timeout = httpx.Timeout(
                timeout=self.config.timeout_seconds or 30.0, connect=10.0
            )

            self.client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )

            # Verify API connectivity
            await self._verify_connection()

            self._initialized = True
            logger.info("Remote API provider initialized", provider_name=self.name)

        except Exception as e:
            logger.error("Failed to initialize Remote API provider", error=str(e))
            raise OCDProviderError(
                f"Remote API initialization failed: {e}",
                provider_name=self.name,
                cause=e,
            )

    async def _setup_credentials(self) -> None:
        """Set up API credentials."""
        if self.config.api_key_env_var:
            import os

            self.api_key = os.getenv(self.config.api_key_env_var)

            if not self.api_key:
                # Try to get from credential store
                try:
                    from ocd.credentials import get_credential

                    self.api_key = await get_credential(self.config.api_key_env_var)
                except ImportError:
                    pass  # Credential store not available yet

            if not self.api_key:
                raise OCDProviderError(
                    f"API key not found in environment variable: {self.config.api_key_env_var}",
                    provider_name=self.name,
                )

    def _setup_endpoint(self) -> None:
        """Set up API endpoint based on provider type."""
        if self.config.api_endpoint:
            self.api_endpoint = self.config.api_endpoint
        else:
            # Default endpoints for known providers
            endpoints = {
                "openai": "https://api.openai.com/v1/chat/completions",
                "anthropic": "https://api.anthropic.com/v1/messages",
                "google": "https://generativelanguage.googleapis.com/v1beta/models",
            }

            # Try to detect provider from name or model
            provider_name = self.name.lower()
            for key, endpoint in endpoints.items():
                if key in provider_name:
                    self.api_endpoint = endpoint
                    break

            if not self.api_endpoint:
                raise OCDProviderError(
                    f"API endpoint not configured for provider: {self.name}",
                    provider_name=self.name,
                )

    async def _verify_connection(self) -> None:
        """Verify API connectivity."""
        try:
            # Simple health check - adjust based on API
            headers = self._get_headers()

            # For OpenAI-style APIs, try a simple models list
            if "openai" in self.name.lower():
                response = await self.client.get(
                    "https://api.openai.com/v1/models", headers=headers
                )
                response.raise_for_status()

            logger.info("API connection verified", provider_name=self.name)

        except Exception as e:
            logger.warning(
                "API connection verification failed",
                provider_name=self.name,
                error=str(e),
            )
            # Don't fail initialization for connection issues

    def _check_availability(self) -> bool:
        """Check if the provider is available."""
        return (
            self._initialized
            and self.client is not None
            and self.api_key is not None
            and self.api_endpoint is not None
        )

    async def execute_task(self, request: TaskRequest) -> TaskResponse:
        """Execute a task using the remote API."""
        if not self.is_available:
            raise OCDProviderError(
                "Remote API provider not available", provider_name=self.name
            )

        self.validate_request(request)

        start_time = time.time()

        try:
            # Build API request based on task type
            api_request = await self._build_api_request(request)

            # Execute API call with retry logic
            response_data = await self._execute_api_call(api_request)

            # Parse response
            result = await self._parse_response(response_data, request.task_type)

            execution_time = time.time() - start_time

            return TaskResponse(
                task_type=request.task_type,
                success=True,
                result=result,
                provider_used=self.name,
                execution_time=execution_time,
                tokens_used=response_data.get("usage", {}).get("total_tokens"),
                metadata={
                    "model_name": self.config.model_name,
                    "provider_type": "remote_api",
                    "api_endpoint": self.api_endpoint,
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

    async def _build_api_request(self, request: TaskRequest) -> Dict[str, Any]:
        """Build API request payload."""
        # Create system prompt based on task type
        system_prompt = self._get_system_prompt(request.task_type)

        # Format user prompt with context
        user_prompt = self._format_user_prompt(request)

        # Build request based on API type
        if "openai" in self.name.lower():
            return {
                "model": self.config.model_name or "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": self.config.max_tokens or 1000,
                "temperature": self.config.temperature or 0.7,
            }
        elif "anthropic" in self.name.lower():
            return {
                "model": self.config.model_name or "claude-3-sonnet-20240229",
                "max_tokens": self.config.max_tokens or 1000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": self.config.temperature or 0.7,
            }
        else:
            # Generic format
            return {
                "model": self.config.model_name,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "max_tokens": self.config.max_tokens or 1000,
                "temperature": self.config.temperature or 0.7,
            }

    def _get_system_prompt(self, task_type: str) -> str:
        """Get system prompt for task type."""
        prompts = {
            "analyze_directory": """You are an expert file system analyzer. Analyze directory structures and provide insights about organization, patterns, and improvement opportunities. Be concise and practical.""",
            "generate_script": """You are an expert script generator. Create safe, well-commented scripts based on directory analysis. Focus on automation and organization tasks. Always prioritize safety.""",
            "summarize_content": """You are an expert content summarizer. Provide clear, concise summaries of file and directory content. Focus on key information and patterns.""",
            "extract_patterns": """You are an expert pattern recognition specialist. Identify naming conventions, organizational patterns, and structural insights from file systems.""",
            "classify_files": """You are an expert file classifier. Categorize files by type, purpose, and importance. Provide clear classification rationale.""",
        }

        return prompts.get(
            task_type,
            "You are a helpful AI assistant specializing in file system analysis and automation.",
        )

    def _format_user_prompt(self, request: TaskRequest) -> str:
        """Format user prompt with context."""
        prompt_parts = [request.prompt]

        # Add analysis context if available
        if request.analysis_result:
            analysis = request.analysis_result
            prompt_parts.append(
                f"""
            
Directory Analysis Context:
- Path: {analysis.directory_info.root_path}
- Files: {analysis.directory_info.total_files}
- Size: {analysis.directory_info.total_size} bytes
- File types: {', '.join(set(f.file_type for f in analysis.directory_info.files[:10]))}
"""
            )

        # Add additional context
        if request.context:
            context_str = json.dumps(request.context, indent=2, default=str)[
                :1000
            ]  # Limit context size
            prompt_parts.append(f"\nAdditional Context:\n{context_str}")

        return "\n".join(prompt_parts)

    async def _execute_api_call(self, api_request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call with retry logic."""
        headers = self._get_headers()
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                response = await self.client.post(
                    self.api_endpoint, json=api_request, headers=headers
                )

                if response.status_code == 429:  # Rate limit
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        "Rate limited, retrying", delay=delay, attempt=attempt
                    )
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise OCDProviderError("Invalid API key", provider_name=self.name)
                elif e.response.status_code == 403:
                    raise OCDProviderError(
                        "API access forbidden", provider_name=self.name
                    )
                elif attempt == max_retries - 1:
                    raise OCDProviderError(
                        f"API call failed: {e}", provider_name=self.name, cause=e
                    )
                else:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)

            except Exception as e:
                if attempt == max_retries - 1:
                    raise OCDProviderError(
                        f"API call failed: {e}", provider_name=self.name, cause=e
                    )
                else:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)

        raise OCDProviderError("Max retries exceeded", provider_name=self.name)

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"OCD-Client/0.1.0",
        }

        if "openai" in self.name.lower():
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif "anthropic" in self.name.lower():
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def _parse_response(
        self, response_data: Dict[str, Any], task_type: str
    ) -> Any:
        """Parse API response based on provider and task type."""
        try:
            # Parse based on API format
            if "openai" in self.name.lower():
                content = response_data["choices"][0]["message"]["content"]
            elif "anthropic" in self.name.lower():
                content = response_data["content"][0]["text"]
            else:
                # Try common response formats
                content = (
                    response_data.get("content")
                    or response_data.get("text")
                    or response_data.get("response")
                    or str(response_data)
                )

            # Parse content based on task type
            if task_type == "generate_script":
                return self._parse_script_response(content)
            elif task_type == "classify_files":
                return self._parse_classification_response(content)
            elif task_type == "extract_patterns":
                return self._parse_patterns_response(content)
            else:
                return content.strip()

        except (KeyError, IndexError, TypeError) as e:
            raise OCDProviderError(
                f"Failed to parse API response: {e}", provider_name=self.name, cause=e
            )

    def _parse_script_response(self, content: str) -> Dict[str, Any]:
        """Parse script generation response."""
        lines = content.split("\n")
        script_lines = []
        description = ""

        in_script = False
        for line in lines:
            if line.strip().startswith("#!/"):
                in_script = True

            if in_script:
                script_lines.append(line)
            elif not description and line.strip():
                description = line.strip()

        return {
            "script": "\n".join(script_lines) if script_lines else content,
            "description": description,
            "language": "bash",
        }

    def _parse_classification_response(self, content: str) -> Dict[str, Any]:
        """Parse file classification response."""
        # Try to extract structured data or return raw content
        try:
            # Look for JSON in response
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {"classification": content.strip()}

    def _parse_patterns_response(self, content: str) -> Dict[str, Any]:
        """Parse pattern extraction response."""
        lines = content.split("\n")
        patterns = []

        for line in lines:
            line = line.strip()
            if line and (
                line.startswith("-") or line.startswith("*") or line.startswith("1.")
            ):
                patterns.append(line.lstrip("-*1234567890. "))

        return {"patterns": patterns, "analysis": content.strip()}

    async def cleanup(self) -> None:
        """Clean up HTTP client resources."""
        logger.info("Cleaning up Remote API provider", provider_name=self.name)

        if self.client:
            await self.client.aclose()
            self.client = None

        logger.info("Remote API provider cleanup completed")

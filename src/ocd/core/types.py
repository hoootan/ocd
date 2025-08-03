"""
OCD Core Types
==============

Type definitions and data models for the OCD system using Pydantic for
validation and serialization.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, validator


class ProviderType(str, Enum):
    """AI provider types."""

    LOCAL_SLM = "local_slm"
    LOCAL_LLM = "local_llm"  # Ollama, GPT4All, etc.
    REMOTE_API = "remote_api"  # OpenAI, Anthropic, etc.


class ExecutionMode(str, Enum):
    """Script execution modes."""

    SAFE = "safe"  # Sandboxed execution
    RESTRICTED = "restricted"  # Limited system access
    FULL = "full"  # Full system access (dangerous)


class AnalysisType(str, Enum):
    """Types of directory analysis."""

    STRUCTURE = "structure"  # File/folder structure
    CONTENT = "content"  # File content analysis
    METADATA = "metadata"  # File metadata
    DEPENDENCY = "dependency"  # Code dependencies
    SEMANTIC = "semantic"  # Semantic analysis


class PromptType(str, Enum):
    """Types of prompts."""

    SYSTEM = "system"
    USER = "user"
    TEMPLATE = "template"
    CUSTOM = "custom"


class ScriptLanguage(str, Enum):
    """Supported script languages."""

    BASH = "bash"
    PYTHON = "python"
    POWERSHELL = "powershell"


class SafetyLevel(str, Enum):
    """Safety validation levels."""

    PERMISSIVE = "permissive"  # Minimal validation
    BALANCED = "balanced"  # Standard validation
    STRICT = "strict"  # High validation, block critical
    PARANOID = "paranoid"  # Maximum validation, block high+


class FileInfo(BaseModel):
    """Information about a file."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    name: str
    size: int
    modified: datetime
    file_type: str
    mime_type: Optional[str] = None
    encoding: Optional[str] = None
    permissions: Optional[str] = None

    @validator("path", pre=True)
    def convert_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v


class DirectoryInfo(BaseModel):
    """Information about a directory structure."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    root_path: Path
    total_files: int
    total_size: int
    files: List[FileInfo]
    subdirectories: List[str]
    depth: int
    analyzed_at: datetime = Field(default_factory=datetime.now)

    @validator("root_path", pre=True)
    def convert_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v


class AnalysisResult(BaseModel):
    """Result of directory analysis."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    directory_info: DirectoryInfo
    analysis_type: AnalysisType
    content_summary: Optional[str] = None
    extracted_patterns: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provider_used: Optional[str] = None
    analysis_duration: Optional[float] = None
    confidence_score: Optional[float] = None


class PromptTemplate(BaseModel):
    """Template for AI prompts."""

    name: str
    template: str
    prompt_type: PromptType
    variables: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class ExecutionContext(BaseModel):
    """Context for script execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    working_directory: Path
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: Optional[float] = None
    execution_mode: ExecutionMode = ExecutionMode.SAFE
    allowed_commands: Optional[List[str]] = None
    blocked_commands: Optional[List[str]] = None

    @validator("working_directory", pre=True)
    def convert_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v


class ExecutionConfig(BaseModel):
    """Configuration for script execution."""

    timeout: float = 300.0  # 5 minutes default
    use_sandbox: bool = True
    dry_run: bool = False
    verbose: bool = False
    allow_imports: bool = True
    environment_variables: Dict[str, str] = Field(default_factory=dict)


class SandboxConfig(BaseModel):
    """Configuration for execution sandbox."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_dir: Optional[Path] = None
    max_execution_time: float = 300.0  # 5 minutes
    max_disk_usage: int = 100 * 1024 * 1024  # 100MB
    max_files: int = 1000
    max_output_file_size: int = 10 * 1024 * 1024  # 10MB
    inherit_environment: bool = False
    environment_variables: Dict[str, str] = Field(default_factory=dict)

    @validator("base_dir", pre=True)
    def convert_path(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return Path(v)
        return v


class ExecutionResult(BaseModel):
    """Result of script execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    script_content: str
    language: ScriptLanguage
    config: ExecutionConfig
    output_files: Dict[str, str] = Field(default_factory=dict)
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    execution_id: Optional[str] = None


class ProviderConfig(BaseModel):
    """Configuration for an AI provider."""

    name: str
    provider_type: ProviderType
    model_name: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key_env_var: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout_seconds: Optional[float] = None
    rate_limit: Optional[int] = None
    enabled: bool = True
    fallback_providers: List[str] = Field(default_factory=list)
    custom_config: Dict[str, Any] = Field(default_factory=dict)


class OCDConfig(BaseModel):
    """Main OCD configuration."""

    default_provider: str
    providers: Dict[str, ProviderConfig]
    analysis_settings: Dict[str, Any] = Field(default_factory=dict)
    execution_settings: Dict[str, Any] = Field(default_factory=dict)
    security_settings: Dict[str, Any] = Field(default_factory=dict)
    logging_config: Dict[str, Any] = Field(default_factory=dict)
    cache_config: Dict[str, Any] = Field(default_factory=dict)


class TaskRequest(BaseModel):
    """Request for AI task execution."""

    task_type: str
    prompt: str
    context: Dict[str, Any] = Field(default_factory=dict)
    provider_preference: Optional[str] = None
    analysis_result: Optional[AnalysisResult] = None
    execution_context: Optional[ExecutionContext] = None


class TaskResponse(BaseModel):
    """Response from AI task execution."""

    task_type: str
    success: bool
    result: Any
    provider_used: str
    execution_time: float
    tokens_used: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class CredentialInfo(BaseModel):
    """Information about stored credentials."""

    key_name: str
    provider: str
    encrypted: bool
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None

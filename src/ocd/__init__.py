"""
OCD - Organized Content Directory
=================================

A cross-platform Python application that integrates both offline local SLMs 
and online LLMs to analyze directory structures and execute scripts based on 
intelligent prompts.

Core Features:
- Cross-platform compatibility (Windows, macOS, Linux)
- Multiple AI provider support (local SLMs, cloud APIs)
- Secure credential management
- Intelligent directory analysis
- Safe script execution
- Template-based prompt system
"""

__version__ = "0.1.0"
__author__ = "OCD Team"
__email__ = "ocd@example.com"

from ocd.core.exceptions import OCDError, OCDConfigError, OCDProviderError
from ocd.core.types import AnalysisResult, ExecutionResult, ProviderType

__all__ = [
    "__version__",
    "OCDError",
    "OCDConfigError",
    "OCDProviderError",
    "AnalysisResult",
    "ExecutionResult",
    "ProviderType",
]

"""
Prompt Engine
============

Dynamic prompt generation using Jinja2 templates with context injection
and template management.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import structlog

try:
    from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from ocd.core.exceptions import OCDError
from ocd.core.types import AnalysisResult, PromptTemplate, PromptType

logger = structlog.get_logger(__name__)


class PromptEngine:
    """
    Template-based prompt engine.

    Features:
    - Jinja2 template processing
    - Context injection
    - Template validation
    - Built-in template library
    - Custom template support
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize prompt engine.

        Args:
            templates_dir: Directory containing custom templates
        """
        if not JINJA2_AVAILABLE:
            raise OCDError(
                "Jinja2 is required for prompt engine. Install with: pip install jinja2"
            )

        self.templates_dir = templates_dir
        self.env = None
        self.built_in_templates: Dict[str, PromptTemplate] = {}
        self._initialize_environment()
        self._load_built_in_templates()

    def _initialize_environment(self) -> None:
        """Initialize Jinja2 environment."""
        loaders = []

        # Add file system loader if templates directory exists
        if self.templates_dir and self.templates_dir.exists():
            loaders.append(FileSystemLoader(str(self.templates_dir)))

        # Create environment
        if loaders:
            loader = loaders[0] if len(loaders) == 1 else loaders
            self.env = Environment(
                loader=loader,
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.env = Environment(
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )

        # Add custom filters
        self.env.filters["truncate_text"] = self._truncate_text
        self.env.filters["format_size"] = self._format_size
        self.env.filters["format_list"] = self._format_list

    def _load_built_in_templates(self) -> None:
        """Load built-in prompt templates."""
        self.built_in_templates = {
            "analyze_directory": PromptTemplate(
                name="analyze_directory",
                template="""You are an expert file system analyzer. Analyze the following directory structure and provide insights.

Directory Information:
- Path: {{ directory_info.root_path }}
- Total Files: {{ directory_info.total_files }}
- Total Size: {{ directory_info.total_size | format_size }}
- Subdirectories: {{ directory_info.subdirectories | length }}
- Analysis Date: {{ directory_info.analyzed_at }}

File Types Distribution:
{% for file_type, count in file_type_distribution.items() %}
- {{ file_type }}: {{ count }} files
{% endfor %}

Recent Files (Last 10):
{% for file in directory_info.files[:10] %}
- {{ file.name }} ({{ file.size | format_size }}, {{ file.modified }})
{% endfor %}

Task: {{ user_prompt }}

Please provide:
1. **Purpose Analysis**: What is this directory's main purpose?
2. **Organization Assessment**: How well organized is it currently?
3. **Improvement Suggestions**: What organizational improvements would you recommend?
4. **Automation Opportunities**: What tasks could be automated?

Focus on practical, actionable insights.""",
                prompt_type=PromptType.TEMPLATE,
                variables=["directory_info", "file_type_distribution", "user_prompt"],
                description="Template for directory analysis tasks",
            ),
            "generate_script": PromptTemplate(
                name="generate_script",
                template="""You are an expert script generator. Create a safe, well-documented script based on the analysis.

Directory Context:
- Path: {{ directory_info.root_path }}
- Files: {{ directory_info.total_files }}
- Key Patterns: {{ patterns | format_list }}

Analysis Summary:
{{ analysis_summary | truncate_text(500) }}

Task Request: {{ user_prompt }}

Requirements:
1. **Safety First**: Only include safe operations
2. **Clear Documentation**: Add comprehensive comments
3. **Error Handling**: Include proper error checking
4. **Cross-Platform**: Use cross-platform commands when possible
5. **Dry Run**: Include a dry-run option

Generate a {{ script_language | default('bash') }} script that accomplishes the requested task.
Include usage instructions and safety warnings.""",
                prompt_type=PromptType.TEMPLATE,
                variables=[
                    "directory_info",
                    "patterns",
                    "analysis_summary",
                    "user_prompt",
                    "script_language",
                ],
                description="Template for script generation tasks",
            ),
            "classify_files": PromptTemplate(
                name="classify_files",
                template="""You are an expert file classifier. Classify the following files by type and purpose.

Directory: {{ directory_info.root_path }}

Files to Classify:
{% for file in files_to_classify %}
- {{ file.name }} ({{ file.file_type }}, {{ file.size | format_size }})
{% endfor %}

Classification Categories:
- **source_code**: Programming source files
- **documentation**: README, docs, guides
- **configuration**: Config files, settings
- **data**: Datasets, databases, CSV files
- **media**: Images, videos, audio
- **build**: Build artifacts, compiled files
- **test**: Test files and test data
- **script**: Automation scripts
- **template**: Template files
- **temporary**: Temporary or cache files
- **other**: Files that don't fit other categories

For each file, provide:
1. Category classification
2. Brief reasoning
3. Confidence level (high/medium/low)

Task: {{ user_prompt }}

Provide structured classification results.""",
                prompt_type=PromptType.TEMPLATE,
                variables=["directory_info", "files_to_classify", "user_prompt"],
                description="Template for file classification tasks",
            ),
            "extract_patterns": PromptTemplate(
                name="extract_patterns",
                template="""You are an expert pattern recognition specialist. Extract meaningful patterns from the directory structure.

Directory Analysis:
- Path: {{ directory_info.root_path }}
- Structure Depth: {{ directory_info.depth }}
- File Count: {{ directory_info.total_files }}

Current Patterns Detected:
{% for pattern in current_patterns %}
- {{ pattern }}
{% endfor %}

File Sample:
{% for file in directory_info.files[:20] %}
- {{ file.path.name }}
{% endfor %}

Task: {{ user_prompt }}

Identify and extract:
1. **Naming Conventions**: File and directory naming patterns
2. **Organizational Structure**: How files are grouped and organized
3. **Version Patterns**: Version control or versioning schemes
4. **Temporal Patterns**: Creation or modification time patterns
5. **Size Patterns**: File size distributions and outliers
6. **Type Clustering**: How file types are grouped together

Provide actionable insights about the discovered patterns.""",
                prompt_type=PromptType.TEMPLATE,
                variables=["directory_info", "current_patterns", "user_prompt"],
                description="Template for pattern extraction tasks",
            ),
            "summarize_content": PromptTemplate(
                name="summarize_content",
                template="""You are an expert content summarizer. Provide a comprehensive summary of the directory contents.

Directory Overview:
- Location: {{ directory_info.root_path }}
- Files: {{ directory_info.total_files }}
- Size: {{ directory_info.total_size | format_size }}
- Last Modified: {{ directory_info.analyzed_at }}

Content Highlights:
{% if content_summary %}
{{ content_summary | truncate_text(1000) }}
{% else %}
No detailed content analysis available.
{% endif %}

Key Dependencies:
{% for dep in dependencies %}
- {{ dep }}
{% endfor %}

Recommendations:
{% for rec in recommendations %}
- {{ rec }}
{% endfor %}

Task: {{ user_prompt }}

Create a comprehensive summary including:
1. **Main Purpose**: What this directory/project is for
2. **Key Components**: Most important files and directories
3. **Technology Stack**: Languages, frameworks, tools used
4. **Current State**: Assessment of organization and completeness
5. **Next Steps**: Suggested actions or improvements

Keep the summary practical and actionable.""",
                prompt_type=PromptType.TEMPLATE,
                variables=[
                    "directory_info",
                    "content_summary",
                    "dependencies",
                    "recommendations",
                    "user_prompt",
                ],
                description="Template for content summarization tasks",
            ),
        }

    def render_template(
        self, template_name: str, context: Dict[str, Any], user_prompt: str = ""
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template to render
            context: Context variables for template
            user_prompt: User's prompt/request

        Returns:
            Rendered prompt string

        Raises:
            OCDError: If template rendering fails
        """
        try:
            # Add user prompt to context
            context = context.copy()
            context["user_prompt"] = user_prompt

            # Try built-in templates first
            if template_name in self.built_in_templates:
                template_obj = self.built_in_templates[template_name]
                template = self.env.from_string(template_obj.template)
                return template.render(**context)

            # Try file system templates
            elif self.env.loader:
                try:
                    template = self.env.get_template(f"{template_name}.jinja2")
                    return template.render(**context)
                except:
                    # Try without extension
                    template = self.env.get_template(template_name)
                    return template.render(**context)

            else:
                raise OCDError(f"Template '{template_name}' not found")

        except Exception as e:
            logger.error(
                "Template rendering failed", template=template_name, error=str(e)
            )
            raise OCDError(f"Template rendering failed: {e}", cause=e)

    def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Render a template string with the given context.

        Args:
            template_string: Template string to render
            context: Context variables for template

        Returns:
            Rendered string

        Raises:
            OCDError: If template rendering fails
        """
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)

        except Exception as e:
            logger.error("String template rendering failed", error=str(e))
            raise OCDError(f"String template rendering failed: {e}", cause=e)

    def build_context(
        self,
        analysis_result: Optional[AnalysisResult] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build template context from analysis result and additional data.

        Args:
            analysis_result: Directory analysis result
            additional_context: Additional context variables

        Returns:
            Template context dictionary
        """
        context = {}

        # Add analysis result data
        if analysis_result:
            context.update(
                {
                    "directory_info": analysis_result.directory_info,
                    "analysis_type": analysis_result.analysis_type.value,
                    "content_summary": analysis_result.content_summary,
                    "patterns": analysis_result.extracted_patterns,
                    "dependencies": analysis_result.dependencies,
                    "recommendations": analysis_result.recommendations,
                    "metadata": analysis_result.metadata,
                    "confidence_score": analysis_result.confidence_score,
                }
            )

            # Extract specific metadata for convenience
            if analysis_result.metadata:
                context.update(
                    {
                        "file_type_distribution": analysis_result.metadata.get(
                            "file_type_distribution", {}
                        ),
                        "current_patterns": analysis_result.extracted_patterns,
                    }
                )

        # Add additional context
        if additional_context:
            context.update(additional_context)

        return context

    def validate_template(self, template_string: str) -> List[str]:
        """
        Validate a template string and return any errors.

        Args:
            template_string: Template string to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        try:
            # Try to parse the template
            self.env.parse(template_string)

        except Exception as e:
            errors.append(f"Template syntax error: {e}")

        return errors

    def get_template_variables(self, template_name: str) -> List[str]:
        """
        Get list of variables used in a template.

        Args:
            template_name: Name of the template

        Returns:
            List of variable names
        """
        if template_name in self.built_in_templates:
            return self.built_in_templates[template_name].variables
        else:
            # For file templates, would need to parse AST
            return []

    def list_templates(self) -> List[str]:
        """Get list of available template names."""
        templates = list(self.built_in_templates.keys())

        # Add file system templates if available
        if self.env.loader:
            try:
                templates.extend(self.env.list_templates())
            except:
                pass

        return sorted(set(templates))

    # Custom Jinja2 filters
    def _truncate_text(self, text: str, length: int = 200) -> str:
        """Truncate text to specified length."""
        if not text:
            return ""
        if len(text) <= length:
            return text
        return text[:length] + "..."

    def _format_size(self, size_bytes: Union[int, float]) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"

        size_bytes = float(size_bytes)
        units = ["B", "KB", "MB", "GB", "TB"]

        for unit in units:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0

        return f"{size_bytes:.1f} PB"

    def _format_list(self, items: List[Any], separator: str = ", ") -> str:
        """Format list as string."""
        if not items:
            return "None"
        return separator.join(str(item) for item in items)

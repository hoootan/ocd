"""
Template Manager
===============

Manages prompt templates with CRUD operations, validation, and
template library management.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import structlog

from ocd.core.exceptions import OCDError
from ocd.core.types import PromptTemplate, PromptType

logger = structlog.get_logger(__name__)


class TemplateManager:
    """
    Manages prompt templates.

    Features:
    - Template CRUD operations
    - Template validation
    - Template library management
    - Import/export functionality
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize template manager.

        Args:
            templates_dir: Directory to store custom templates
        """
        self.templates_dir = templates_dir or Path.home() / ".ocd" / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        self.templates_file = self.templates_dir / "templates.json"
        self.custom_templates: Dict[str, PromptTemplate] = {}

        self._load_templates()

    def _load_templates(self) -> None:
        """Load custom templates from storage."""
        if not self.templates_file.exists():
            return

        try:
            with open(self.templates_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for template_data in data.get("templates", []):
                template = PromptTemplate(**template_data)
                self.custom_templates[template.name] = template

            logger.info("Loaded custom templates", count=len(self.custom_templates))

        except Exception as e:
            logger.error("Failed to load templates", error=str(e))

    def _save_templates(self) -> None:
        """Save custom templates to storage."""
        try:
            data = {
                "templates": [
                    template.dict() for template in self.custom_templates.values()
                ],
                "updated_at": datetime.now().isoformat(),
            }

            # Write atomically
            temp_file = self.templates_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            temp_file.replace(self.templates_file)

        except Exception as e:
            logger.error("Failed to save templates", error=str(e))
            raise OCDError(f"Failed to save templates: {e}", cause=e)

    def create_template(
        self,
        name: str,
        template: str,
        prompt_type: PromptType = PromptType.CUSTOM,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        variables: Optional[List[str]] = None,
    ) -> PromptTemplate:
        """
        Create a new template.

        Args:
            name: Template name
            template: Template content
            prompt_type: Type of template
            description: Template description
            tags: Template tags
            variables: Template variables

        Returns:
            Created template

        Raises:
            OCDError: If template creation fails
        """
        if name in self.custom_templates:
            raise OCDError(f"Template '{name}' already exists")

        # Validate template syntax
        errors = self._validate_template_syntax(template)
        if errors:
            raise OCDError(f"Template validation failed: {'; '.join(errors)}")

        # Extract variables if not provided
        if variables is None:
            variables = self._extract_variables(template)

        template_obj = PromptTemplate(
            name=name,
            template=template,
            prompt_type=prompt_type,
            description=description,
            tags=tags or [],
            variables=variables,
            created_at=datetime.now(),
        )

        self.custom_templates[name] = template_obj
        self._save_templates()

        logger.info("Created template", name=name)
        return template_obj

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get a template by name.

        Args:
            name: Template name

        Returns:
            Template or None if not found
        """
        return self.custom_templates.get(name)

    def update_template(
        self,
        name: str,
        template: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        variables: Optional[List[str]] = None,
    ) -> PromptTemplate:
        """
        Update an existing template.

        Args:
            name: Template name
            template: New template content
            description: New description
            tags: New tags
            variables: New variables

        Returns:
            Updated template

        Raises:
            OCDError: If template not found or update fails
        """
        if name not in self.custom_templates:
            raise OCDError(f"Template '{name}' not found")

        template_obj = self.custom_templates[name]

        # Update fields
        if template is not None:
            # Validate new template syntax
            errors = self._validate_template_syntax(template)
            if errors:
                raise OCDError(f"Template validation failed: {'; '.join(errors)}")

            template_obj.template = template

            # Update variables if not provided
            if variables is None:
                template_obj.variables = self._extract_variables(template)
            else:
                template_obj.variables = variables
        elif variables is not None:
            template_obj.variables = variables

        if description is not None:
            template_obj.description = description

        if tags is not None:
            template_obj.tags = tags

        self._save_templates()

        logger.info("Updated template", name=name)
        return template_obj

    def delete_template(self, name: str) -> bool:
        """
        Delete a template.

        Args:
            name: Template name

        Returns:
            True if deleted, False if not found
        """
        if name in self.custom_templates:
            del self.custom_templates[name]
            self._save_templates()
            logger.info("Deleted template", name=name)
            return True

        return False

    def list_templates(self, tag: Optional[str] = None) -> List[PromptTemplate]:
        """
        List all templates, optionally filtered by tag.

        Args:
            tag: Filter by tag

        Returns:
            List of templates
        """
        templates = list(self.custom_templates.values())

        if tag:
            templates = [t for t in templates if tag in t.tags]

        return sorted(templates, key=lambda t: t.name)

    def search_templates(self, query: str) -> List[PromptTemplate]:
        """
        Search templates by name, description, or content.

        Args:
            query: Search query

        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        matching_templates = []

        for template in self.custom_templates.values():
            if (
                query_lower in template.name.lower()
                or (
                    template.description and query_lower in template.description.lower()
                )
                or query_lower in template.template.lower()
            ):
                matching_templates.append(template)

        return sorted(matching_templates, key=lambda t: t.name)

    def export_templates(
        self, output_file: Path, template_names: Optional[List[str]] = None
    ) -> None:
        """
        Export templates to a file.

        Args:
            output_file: Output file path
            template_names: Specific templates to export (all if None)

        Raises:
            OCDError: If export fails
        """
        try:
            if template_names:
                templates_to_export = [
                    self.custom_templates[name]
                    for name in template_names
                    if name in self.custom_templates
                ]
            else:
                templates_to_export = list(self.custom_templates.values())

            data = {
                "templates": [template.dict() for template in templates_to_export],
                "exported_at": datetime.now().isoformat(),
                "version": "1.0",
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(
                "Exported templates", file=output_file, count=len(templates_to_export)
            )

        except Exception as e:
            raise OCDError(f"Failed to export templates: {e}", cause=e)

    def import_templates(self, input_file: Path, overwrite: bool = False) -> List[str]:
        """
        Import templates from a file.

        Args:
            input_file: Input file path
            overwrite: Whether to overwrite existing templates

        Returns:
            List of imported template names

        Raises:
            OCDError: If import fails
        """
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            imported_names = []

            for template_data in data.get("templates", []):
                template = PromptTemplate(**template_data)

                if template.name in self.custom_templates and not overwrite:
                    logger.warning(
                        "Template already exists, skipping", name=template.name
                    )
                    continue

                self.custom_templates[template.name] = template
                imported_names.append(template.name)

            if imported_names:
                self._save_templates()

            logger.info("Imported templates", count=len(imported_names))
            return imported_names

        except Exception as e:
            raise OCDError(f"Failed to import templates: {e}", cause=e)

    def _validate_template_syntax(self, template: str) -> List[str]:
        """
        Validate template syntax.

        Args:
            template: Template string to validate

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Try to import Jinja2 for validation
            from jinja2 import Environment

            env = Environment()
            env.parse(template)

        except ImportError:
            # Skip validation if Jinja2 not available
            pass
        except Exception as e:
            errors.append(str(e))

        # Basic validation
        if not template.strip():
            errors.append("Template cannot be empty")

        # Check for balanced braces
        open_braces = template.count("{{")
        close_braces = template.count("}}")
        if open_braces != close_braces:
            errors.append("Unbalanced template braces")

        return errors

    def _extract_variables(self, template: str) -> List[str]:
        """
        Extract variable names from template.

        Args:
            template: Template string

        Returns:
            List of variable names
        """
        import re

        # Simple regex to find Jinja2 variables
        variable_pattern = (
            r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)"
        )
        matches = re.findall(variable_pattern, template)

        # Extract base variable names (before dots)
        variables = set()
        for match in matches:
            base_var = match.split(".")[0]
            variables.add(base_var)

        return sorted(list(variables))

    def get_template_stats(self) -> Dict[str, int]:
        """
        Get statistics about templates.

        Returns:
            Template statistics
        """
        templates = list(self.custom_templates.values())

        stats = {
            "total_templates": len(templates),
            "by_type": {},
            "with_tags": len([t for t in templates if t.tags]),
            "with_description": len([t for t in templates if t.description]),
        }

        # Count by type
        for template in templates:
            template_type = template.prompt_type.value
            stats["by_type"][template_type] = stats["by_type"].get(template_type, 0) + 1

        return stats

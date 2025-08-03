"""
Prompt Engine
============

Template-based prompt system using Jinja2 for dynamic prompt generation
with context injection and template management.
"""

from ocd.prompts.engine import PromptEngine
from ocd.prompts.templates import TemplateManager

__all__ = [
    "PromptEngine",
    "TemplateManager",
]

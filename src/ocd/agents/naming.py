"""
Naming Agent
============

Intelligent agent specialized in generating meaningful, consistent file and folder names
based on content analysis, context, and naming conventions.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate

from ocd.agents.base import BaseAgent
from ocd.core.exceptions import OCDError

logger = structlog.get_logger(__name__)


class NamingAgent(BaseAgent):
    """
    AI agent specialized in intelligent file and folder naming.
    
    Capabilities:
    - Analyzes file content to generate descriptive names
    - Applies consistent naming conventions
    - Handles name conflicts intelligently
    - Supports various naming styles (camelCase, snake_case, kebab-case)
    - Learns from existing naming patterns
    - Generates batch renaming suggestions
    """
    
    def __init__(
        self,
        llm_provider,
        naming_style: str = "descriptive",  # descriptive, technical, minimal
        case_style: str = "snake_case",  # snake_case, camelCase, kebab-case, Title Case
        max_name_length: int = 100,
        **kwargs
    ):
        """
        Initialize Naming Agent.
        
        Args:
            llm_provider: LangChain LLM provider
            naming_style: Style of names to generate
            case_style: Case convention to follow
            max_name_length: Maximum length for generated names
        """
        super().__init__(llm_provider, **kwargs)
        
        self.naming_style = naming_style
        self.case_style = case_style
        self.max_name_length = max_name_length
        
        # Naming patterns and rules
        self.naming_rules = {
            "forbidden_chars": r'[<>:"/\\|?*]',
            "reserved_names": {
                "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
                "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
                "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
            },
            "common_abbreviations": {
                "document": "doc", "image": "img", "configuration": "config",
                "temporary": "tmp", "backup": "bak", "original": "orig",
                "specification": "spec", "requirements": "req"
            }
        }
        
        self.logger = logger.bind(agent_type="naming")
    
    async def _setup_agent_tools(self) -> List[Tool]:
        """Setup naming-specific tools."""
        return [
            Tool(
                name="generate_descriptive_name",
                func=self._generate_descriptive_name,
                description="Generate a descriptive name based on file content and context"
            ),
            Tool(
                name="apply_naming_convention",
                func=self._apply_naming_convention,
                description="Apply consistent naming convention to a file or folder name"
            ),
            Tool(
                name="batch_rename_suggestions",
                func=self._batch_rename_suggestions,
                description="Generate renaming suggestions for multiple files"
            ),
            Tool(
                name="detect_naming_pattern",
                func=self._detect_naming_pattern,
                description="Analyze existing names to detect patterns and conventions"
            ),
            Tool(
                name="resolve_name_conflict",
                func=self._resolve_name_conflict,
                description="Resolve naming conflicts when files have similar names"
            ),
            Tool(
                name="clean_filename",
                func=self._clean_filename,
                description="Clean and sanitize a filename to be filesystem-safe"
            ),
            Tool(
                name="suggest_folder_names",
                func=self._suggest_folder_names,
                description="Suggest appropriate folder names based on contained files"
            )
        ]
    
    async def _create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the naming agent's system prompt."""
        system_prompt = """You are an intelligent file naming agent. Your role is to generate meaningful, consistent, and appropriate names for files and folders.

Key Principles:
1. DESCRIPTIVE: Names should clearly indicate the file's purpose or content
2. CONSISTENT: Follow established naming conventions
3. FILESYSTEM-SAFE: Avoid special characters that cause problems
4. CONCISE: Keep names reasonably short while being descriptive
5. CONTEXTUAL: Consider the file's location and purpose

Naming Guidelines:
- Use {case_style} for consistency
- Maximum length: {max_name_length} characters
- Avoid forbidden characters: < > : " / \\ | ? *
- Don't use reserved system names
- Consider file content, not just extension
- Maintain readability and searchability

Current settings:
- Naming style: {naming_style}
- Case style: {case_style}
- Max length: {max_name_length}

You have tools to:
- Analyze file content for naming
- Apply naming conventions consistently
- Detect patterns in existing names
- Resolve naming conflicts
- Generate batch renaming suggestions
- Clean and sanitize filenames

Always explain your naming decisions and provide alternatives when possible.
"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
    
    # Naming tool implementations
    
    async def _generate_descriptive_name(self, file_path: str, context: str = "") -> str:
        """Generate a descriptive name based on file content and context."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"File does not exist: {file_path}"
            
            # Analyze file for content-based naming
            content_analysis = await self._analyze_file_content(path)
            
            # Generate name based on analysis
            if path.is_dir():
                suggested_name = await self._generate_folder_name(path, content_analysis, context)
            else:
                suggested_name = await self._generate_file_name(path, content_analysis, context)
            
            # Apply naming conventions
            clean_name = self._apply_case_style(suggested_name)
            clean_name = self._sanitize_filename(clean_name)
            
            return f"Suggested name: {clean_name} (based on: {content_analysis.get('basis', 'content analysis')})"
            
        except Exception as e:
            return f"Name generation failed: {e}"
    
    async def _apply_naming_convention(self, current_name: str, target_style: str = None) -> str:
        """Apply consistent naming convention to a name."""
        try:
            style = target_style or self.case_style
            
            # Clean the name first
            clean_name = self._sanitize_filename(current_name)
            
            # Apply case style
            styled_name = self._apply_case_style(clean_name, style)
            
            return f"Converted '{current_name}' to '{styled_name}' using {style} convention"
            
        except Exception as e:
            return f"Convention application failed: {e}"
    
    async def _batch_rename_suggestions(self, directory_path: str, pattern: str = "auto") -> str:
        """Generate renaming suggestions for multiple files."""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                return f"Directory does not exist: {directory_path}"
            
            suggestions = []
            files = list(directory.iterdir())
            
            # Detect existing pattern if auto
            if pattern == "auto":
                pattern = await self._detect_naming_pattern(directory_path)
            
            for file_path in files[:20]:  # Limit to first 20 files
                if file_path.is_file():
                    content_analysis = await self._analyze_file_content(file_path)
                    suggested = await self._generate_file_name(file_path, content_analysis)
                    clean_suggested = self._apply_case_style(suggested)
                    
                    if clean_suggested != file_path.name:
                        suggestions.append({
                            "current": file_path.name,
                            "suggested": clean_suggested,
                            "reason": content_analysis.get("basis", "content-based")
                        })
            
            if self.dry_run:
                summary = f"[DRY RUN] Would rename {len(suggestions)} files:\n"
                for s in suggestions[:5]:  # Show first 5
                    summary += f"- {s['current']} → {s['suggested']} ({s['reason']})\n"
                if len(suggestions) > 5:
                    summary += f"... and {len(suggestions) - 5} more"
                return summary
            else:
                return f"Generated {len(suggestions)} rename suggestions based on {pattern} pattern"
            
        except Exception as e:
            return f"Batch rename suggestion failed: {e}"
    
    async def _detect_naming_pattern(self, directory_path: str) -> str:
        """Analyze existing names to detect patterns and conventions."""
        try:
            directory = Path(directory_path)
            names = [f.name for f in directory.iterdir() if f.is_file()]
            
            if not names:
                return "No files to analyze"
            
            # Analyze patterns
            patterns = {
                "snake_case": sum(1 for name in names if "_" in name and name.islower()),
                "camelCase": sum(1 for name in names if any(c.isupper() for c in name[1:]) and not "_" in name),
                "kebab-case": sum(1 for name in names if "-" in name and name.islower()),
                "Title Case": sum(1 for name in names if " " in name and name.istitle()),
                "UPPERCASE": sum(1 for name in names if name.isupper()),
                "lowercase": sum(1 for name in names if name.islower() and not "_" in name and not "-" in name)
            }
            
            # Find dominant pattern
            dominant_pattern = max(patterns.items(), key=lambda x: x[1])
            
            # Additional analysis
            avg_length = sum(len(name) for name in names) / len(names)
            has_dates = sum(1 for name in names if re.search(r'\d{4}[-_]\d{2}[-_]\d{2}', name))
            has_numbers = sum(1 for name in names if re.search(r'\d+', name))
            
            analysis = {
                "dominant_case": dominant_pattern[0],
                "confidence": dominant_pattern[1] / len(names),
                "average_length": avg_length,
                "files_with_dates": has_dates,
                "files_with_numbers": has_numbers,
                "total_files": len(names)
            }
            
            return f"Detected pattern: {analysis['dominant_case']} ({analysis['confidence']:.1%} confidence), avg length: {analysis['average_length']:.1f}"
            
        except Exception as e:
            return f"Pattern detection failed: {e}"
    
    async def _resolve_name_conflict(self, proposed_name: str, existing_names: List[str]) -> str:
        """Resolve naming conflicts when files have similar names."""
        try:
            if proposed_name not in existing_names:
                return f"No conflict: {proposed_name}"
            
            # Generate alternatives
            base_name, extension = self._split_filename(proposed_name)
            alternatives = []
            
            # Try numbered variants
            for i in range(1, 100):
                candidate = f"{base_name}_{i:02d}{extension}"
                if candidate not in existing_names:
                    alternatives.append(candidate)
                    if len(alternatives) >= 3:
                        break
            
            # Try descriptive variants
            import time
            timestamp_variant = f"{base_name}_{int(time.time())}{extension}"
            if timestamp_variant not in existing_names:
                alternatives.append(timestamp_variant)
            
            return f"Conflict resolved. Alternatives: {', '.join(alternatives[:3])}"
            
        except Exception as e:
            return f"Conflict resolution failed: {e}"
    
    async def _clean_filename(self, filename: str) -> str:
        """Clean and sanitize a filename to be filesystem-safe."""
        try:
            # Remove forbidden characters
            clean_name = re.sub(self.naming_rules["forbidden_chars"], "_", filename)
            
            # Remove multiple spaces and underscores
            clean_name = re.sub(r'[_\s]+', '_', clean_name)
            
            # Remove leading/trailing underscores and dots
            clean_name = clean_name.strip('_.')
            
            # Check reserved names
            base_name = clean_name.split('.')[0].upper()
            if base_name in self.naming_rules["reserved_names"]:
                clean_name = f"file_{clean_name}"
            
            # Limit length
            if len(clean_name) > self.max_name_length:
                name_part, ext = self._split_filename(clean_name)
                available_length = self.max_name_length - len(ext)
                clean_name = name_part[:available_length] + ext
            
            return f"Cleaned filename: {clean_name}"
            
        except Exception as e:
            return f"Filename cleaning failed: {e}"
    
    async def _suggest_folder_names(self, directory_path: str) -> str:
        """Suggest appropriate folder names based on contained files."""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                return f"Directory does not exist: {directory_path}"
            
            # Analyze contained files
            file_types = {}
            content_themes = set()
            
            for file_path in directory.iterdir():
                if file_path.is_file():
                    # Count file types
                    ext = file_path.suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
                    
                    # Analyze content for themes
                    content_analysis = await self._analyze_file_content(file_path)
                    if content_analysis.get("theme"):
                        content_themes.add(content_analysis["theme"])
            
            # Generate suggestions
            suggestions = []
            
            # Based on file types
            if len(file_types) == 1:
                ext = list(file_types.keys())[0]
                suggestions.append(f"{ext.upper()}_Files")
            elif len(file_types) > 0:
                dominant_type = max(file_types.items(), key=lambda x: x[1])[0]
                suggestions.append(f"{dominant_type.upper()}_Collection")
            
            # Based on content themes
            if content_themes:
                theme_suggestion = "_".join(sorted(content_themes)[:2])
                suggestions.append(self._apply_case_style(theme_suggestion))
            
            # Generic suggestions
            suggestions.extend(["Mixed_Files", "Unsorted", "Archive"])
            
            return f"Folder name suggestions: {', '.join(suggestions[:3])}"
            
        except Exception as e:
            return f"Folder name suggestion failed: {e}"
    
    # Helper methods
    
    async def _analyze_file_content(self, file_path: Path) -> Dict[str, Any]:
        """Analyze file content for naming purposes."""
        try:
            analysis = {
                "basis": "extension",
                "theme": None,
                "keywords": [],
                "content_type": "unknown"
            }
            
            # Basic analysis based on extension
            ext = file_path.suffix.lower()
            if ext in ['.txt', '.md', '.doc', '.docx']:
                analysis["content_type"] = "document"
                analysis["theme"] = "documentation"
            elif ext in ['.py', '.js', '.html', '.css', '.java']:
                analysis["content_type"] = "code"
                analysis["theme"] = "source_code"
            elif ext in ['.jpg', '.png', '.gif', '.svg']:
                analysis["content_type"] = "image"
                analysis["theme"] = "graphics"
            elif ext in ['.mp4', '.avi', '.mov']:
                analysis["content_type"] = "video"
                analysis["theme"] = "media"
            elif ext in ['.mp3', '.wav', '.flac']:
                analysis["content_type"] = "audio"
                analysis["theme"] = "media"
            
            # Try to read small text files for keywords
            if ext in ['.txt', '.md', '.py', '.js', '.html'] and file_path.stat().st_size < 10000:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(500)  # First 500 chars
                        
                    # Extract potential keywords
                    words = re.findall(r'\b[A-Za-z]{3,}\b', content)
                    analysis["keywords"] = list(set(words[:10]))  # Top 10 unique words
                    analysis["basis"] = "content_analysis"
                    
                except (UnicodeDecodeError, PermissionError, OSError):
                    pass
            
            return analysis
            
        except Exception:
            return {"basis": "fallback", "theme": "unknown", "keywords": [], "content_type": "unknown"}
    
    async def _generate_file_name(self, file_path: Path, content_analysis: Dict[str, Any], context: str = "") -> str:
        """Generate a descriptive filename."""
        base_parts = []
        
        # Use context if provided
        if context:
            base_parts.append(context.lower().replace(" ", "_"))
        
        # Use content theme
        if content_analysis.get("theme"):
            base_parts.append(content_analysis["theme"])
        
        # Use keywords if available
        keywords = content_analysis.get("keywords", [])
        if keywords and self.naming_style == "descriptive":
            # Use most relevant keywords
            relevant_keywords = [kw for kw in keywords[:3] if len(kw) > 3]
            base_parts.extend(relevant_keywords)
        
        # Fallback to content type
        if not base_parts:
            content_type = content_analysis.get("content_type", "file")
            base_parts.append(content_type)
        
        # Combine parts
        base_name = "_".join(base_parts[:3])  # Limit to 3 parts
        
        # Add extension
        extension = file_path.suffix
        
        return f"{base_name}{extension}"
    
    async def _generate_folder_name(self, dir_path: Path, content_analysis: Dict[str, Any], context: str = "") -> str:
        """Generate a descriptive folder name."""
        if context:
            return context.lower().replace(" ", "_")
        
        theme = content_analysis.get("theme", "mixed")
        return f"{theme}_folder"
    
    def _apply_case_style(self, name: str, style: str = None) -> str:
        """Apply the specified case style to a name."""
        style = style or self.case_style
        
        # Split into words (by underscore, hyphen, or space)
        words = re.split(r'[_\s-]+', name)
        words = [w for w in words if w]  # Remove empty strings
        
        if style == "snake_case":
            return "_".join(w.lower() for w in words)
        elif style == "camelCase":
            if not words:
                return name
            return words[0].lower() + "".join(w.capitalize() for w in words[1:])
        elif style == "kebab-case":
            return "-".join(w.lower() for w in words)
        elif style == "Title Case":
            return " ".join(w.capitalize() for w in words)
        elif style == "UPPERCASE":
            return "_".join(w.upper() for w in words)
        else:
            return "_".join(w.lower() for w in words)  # Default to snake_case
    
    def _sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename."""
        # Remove forbidden characters
        sanitized = re.sub(self.naming_rules["forbidden_chars"], "_", filename)
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', "", sanitized)
        
        # Clean up multiple underscores/spaces
        sanitized = re.sub(r'[_\s]+', '_', sanitized)
        
        # Remove leading/trailing dots and underscores
        sanitized = sanitized.strip('._')
        
        return sanitized
    
    def _split_filename(self, filename: str) -> tuple:
        """Split filename into name and extension."""
        path = Path(filename)
        return str(path.stem), str(path.suffix)
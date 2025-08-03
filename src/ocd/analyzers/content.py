"""
Content Extractor
================

Extracts and analyzes content from various file types for AI processing.
"""

import asyncio
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union
import structlog

from ocd.core.exceptions import OCDAnalysisError

logger = structlog.get_logger(__name__)


class ContentExtractor:
    """
    Extracts content from various file types.

    Supports:
    - Text files (plain text, markdown, code)
    - Configuration files (JSON, YAML, TOML, INI)
    - Document files (basic text extraction)
    - Binary files (metadata only)
    """

    def __init__(self, max_content_size: int = 1024 * 1024):  # 1MB
        """
        Initialize content extractor.

        Args:
            max_content_size: Maximum content size to extract (bytes)
        """
        self.max_content_size = max_content_size

    async def extract_content(self, file_path: Path) -> Optional[str]:
        """
        Extract content from a file.

        Args:
            file_path: Path to file

        Returns:
            Extracted content or None if not extractable
        """
        try:
            # Check file size
            if file_path.stat().st_size > self.max_content_size:
                logger.debug("File too large for content extraction", file=file_path)
                return None

            # Determine extraction method based on file type
            mime_type, encoding = mimetypes.guess_type(str(file_path))
            file_extension = file_path.suffix.lower()

            # Text files
            if self._is_text_file(mime_type, file_extension):
                return await self._extract_text_content(file_path, encoding)

            # Configuration files
            elif self._is_config_file(file_extension):
                return await self._extract_config_content(file_path)

            # Binary files - extract metadata only
            elif self._is_binary_file(mime_type, file_extension):
                return await self._extract_binary_metadata(file_path)

            else:
                # Try as text file as fallback
                return await self._extract_text_content(file_path, encoding)

        except Exception as e:
            logger.debug("Content extraction failed", file=file_path, error=str(e))
            return None

    async def _extract_text_content(
        self, file_path: Path, encoding: Optional[str] = None
    ) -> Optional[str]:
        """Extract content from text files."""
        try:
            # Try different encodings
            encodings_to_try = [encoding, "utf-8", "utf-16", "latin-1", "cp1252"]
            encodings_to_try = [enc for enc in encodings_to_try if enc is not None]

            for enc in encodings_to_try:
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        content = f.read(self.max_content_size)

                    # Basic content validation
                    if self._is_valid_text_content(content):
                        return content

                except (UnicodeDecodeError, UnicodeError):
                    continue

            return None

        except Exception as e:
            logger.debug("Text content extraction failed", file=file_path, error=str(e))
            return None

    async def _extract_config_content(self, file_path: Path) -> Optional[str]:
        """Extract content from configuration files."""
        try:
            # Read as text first
            content = await self._extract_text_content(file_path)
            if not content:
                return None

            file_extension = file_path.suffix.lower()

            # Parse and format based on file type
            if file_extension == ".json":
                return await self._format_json_content(content)
            elif file_extension in [".yaml", ".yml"]:
                return await self._format_yaml_content(content)
            elif file_extension == ".toml":
                return await self._format_toml_content(content)
            elif file_extension in [".ini", ".cfg", ".conf"]:
                return await self._format_ini_content(content)
            else:
                return content

        except Exception as e:
            logger.debug(
                "Config content extraction failed", file=file_path, error=str(e)
            )
            return None

    async def _extract_binary_metadata(self, file_path: Path) -> Optional[str]:
        """Extract metadata from binary files."""
        try:
            stat = file_path.stat()
            mime_type, _ = mimetypes.guess_type(str(file_path))

            metadata = [
                f"Binary file: {file_path.name}",
                f"Size: {stat.st_size} bytes",
                f"Type: {mime_type or 'unknown'}",
                f"Extension: {file_path.suffix}",
            ]

            # Add specific metadata for known binary types
            if file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
                metadata.append("Type: Image file")
            elif file_path.suffix.lower() in [".mp3", ".wav", ".flac", ".ogg"]:
                metadata.append("Type: Audio file")
            elif file_path.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv"]:
                metadata.append("Type: Video file")
            elif file_path.suffix.lower() in [".pdf", ".doc", ".docx"]:
                metadata.append("Type: Document file")

            return "\n".join(metadata)

        except Exception as e:
            logger.debug(
                "Binary metadata extraction failed", file=file_path, error=str(e)
            )
            return None

    async def _format_json_content(self, content: str) -> str:
        """Format JSON content for better readability."""
        try:
            import json

            data = json.loads(content)

            # Create summary for large JSON files
            if len(content) > 2000:
                summary = []
                if isinstance(data, dict):
                    summary.append(f"JSON object with {len(data)} keys:")
                    for key in list(data.keys())[:10]:  # First 10 keys
                        value_type = type(data[key]).__name__
                        summary.append(f"  {key}: {value_type}")
                    if len(data) > 10:
                        summary.append(f"  ... and {len(data) - 10} more keys")
                elif isinstance(data, list):
                    summary.append(f"JSON array with {len(data)} items")

                return "\n".join(summary)
            else:
                return json.dumps(data, indent=2)[:2000]  # Limit size

        except json.JSONDecodeError:
            return content[:2000]  # Return raw content if JSON is invalid

    async def _format_yaml_content(self, content: str) -> str:
        """Format YAML content for better readability."""
        try:
            # Try to parse YAML for validation
            import yaml

            data = yaml.safe_load(content)

            if len(content) > 2000:
                # Create summary for large YAML files
                summary = []
                if isinstance(data, dict):
                    summary.append(f"YAML document with {len(data)} top-level keys:")
                    for key in list(data.keys())[:10]:
                        summary.append(f"  {key}")
                    if len(data) > 10:
                        summary.append(f"  ... and {len(data) - 10} more keys")
                else:
                    summary.append("YAML document")

                return "\n".join(summary)
            else:
                return content[:2000]

        except Exception:
            return content[:2000]  # Return raw content if YAML is invalid

    async def _format_toml_content(self, content: str) -> str:
        """Format TOML content for better readability."""
        try:
            import toml

            data = toml.loads(content)

            if len(content) > 2000:
                summary = []
                if isinstance(data, dict):
                    summary.append(f"TOML document with {len(data)} sections:")
                    for key in list(data.keys())[:10]:
                        summary.append(f"  [{key}]")
                    if len(data) > 10:
                        summary.append(f"  ... and {len(data) - 10} more sections")

                return "\n".join(summary)
            else:
                return content[:2000]

        except Exception:
            return content[:2000]  # Return raw content if TOML is invalid

    async def _format_ini_content(self, content: str) -> str:
        """Format INI content for better readability."""
        try:
            import configparser

            config = configparser.ConfigParser()
            config.read_string(content)

            if len(content) > 2000:
                summary = []
                sections = config.sections()
                summary.append(f"INI file with {len(sections)} sections:")
                for section in sections[:10]:
                    summary.append(f"  [{section}]")
                if len(sections) > 10:
                    summary.append(f"  ... and {len(sections) - 10} more sections")

                return "\n".join(summary)
            else:
                return content[:2000]

        except Exception:
            return content[:2000]  # Return raw content if INI is invalid

    def _is_text_file(self, mime_type: Optional[str], file_extension: str) -> bool:
        """Check if file is a text file."""
        text_extensions = {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".ts",
            ".html",
            ".css",
            ".scss",
            ".less",
            ".xml",
            ".svg",
            ".sql",
            ".sh",
            ".bat",
            ".ps1",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".java",
            ".go",
            ".rs",
            ".php",
            ".rb",
            ".pl",
            ".r",
            ".m",
            ".swift",
            ".kt",
            ".scala",
            ".clj",
            ".hs",
            ".elm",
            ".ex",
            ".exs",
            ".erl",
            ".vim",
            ".lua",
        }

        if file_extension in text_extensions:
            return True

        if mime_type and mime_type.startswith("text/"):
            return True

        return False

    def _is_config_file(self, file_extension: str) -> bool:
        """Check if file is a configuration file."""
        config_extensions = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
        return file_extension in config_extensions

    def _is_binary_file(self, mime_type: Optional[str], file_extension: str) -> bool:
        """Check if file is a binary file."""
        binary_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".ico",
            ".tiff",
            ".mp3",
            ".wav",
            ".flac",
            ".ogg",
            ".m4a",
            ".aac",
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".wmv",
            ".flv",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".7z",
            ".rar",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".bin",
        }

        if file_extension in binary_extensions:
            return True

        if mime_type and (
            mime_type.startswith("image/")
            or mime_type.startswith("audio/")
            or mime_type.startswith("video/")
            or mime_type.startswith("application/octet-stream")
        ):
            return True

        return False

    def _is_valid_text_content(self, content: str) -> bool:
        """Validate that content is readable text."""
        if not content:
            return False

        # Check for too many non-printable characters
        printable_chars = sum(
            1 for c in content[:1000] if c.isprintable() or c.isspace()
        )
        total_chars = len(content[:1000])

        if total_chars == 0:
            return False

        printable_ratio = printable_chars / total_chars
        return printable_ratio > 0.8  # At least 80% printable characters

    async def summarize_content(self, content: str, max_length: int = 500) -> str:
        """
        Create a summary of content.

        Args:
            content: Content to summarize
            max_length: Maximum summary length

        Returns:
            Content summary
        """
        if not content:
            return ""

        # Simple summarization - take first part and key lines
        lines = content.split("\n")

        # Remove empty lines and very short lines
        meaningful_lines = [line.strip() for line in lines if len(line.strip()) > 10]

        if not meaningful_lines:
            return content[:max_length]

        # Take first few meaningful lines
        summary_lines = meaningful_lines[:5]
        summary = "\n".join(summary_lines)

        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

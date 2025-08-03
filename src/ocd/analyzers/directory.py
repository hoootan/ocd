"""
Directory Analyzer
=================

Analyzes directory structures, extracts metadata, and builds
comprehensive context for AI processing.
"""

import asyncio
import mimetypes
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import structlog

from ocd.core.exceptions import OCDAnalysisError
from ocd.core.types import AnalysisResult, AnalysisType, DirectoryInfo, FileInfo
from ocd.analyzers.content import ContentExtractor
from ocd.analyzers.metadata import MetadataExtractor

logger = structlog.get_logger(__name__)


class DirectoryAnalyzer:
    """
    Comprehensive directory analyzer.

    Analyzes directory structures, file metadata, content patterns,
    and builds rich context for AI processing.
    """

    def __init__(
        self,
        max_files: int = 10000,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        max_depth: int = 10,
        excluded_dirs: Optional[Set[str]] = None,
        excluded_extensions: Optional[Set[str]] = None,
    ):
        """
        Initialize directory analyzer.

        Args:
            max_files: Maximum number of files to analyze
            max_file_size: Maximum file size to analyze (bytes)
            max_depth: Maximum directory depth to traverse
            excluded_dirs: Directory names to exclude
            excluded_extensions: File extensions to exclude
        """
        self.max_files = max_files
        self.max_file_size = max_file_size
        self.max_depth = max_depth

        self.excluded_dirs = excluded_dirs or {
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "env",
            ".env",
            "build",
            "dist",
            ".DS_Store",
            "Thumbs.db",
            ".tmp",
            "temp",
        }

        self.excluded_extensions = excluded_extensions or {
            ".pyc",
            ".pyo",
            ".pyd",
            ".so",
            ".dll",
            ".dylib",
            ".exe",
            ".bin",
            ".obj",
            ".o",
            ".class",
            ".jar",
            ".log",
            ".tmp",
            ".temp",
            ".cache",
            ".lock",
        }

        self.content_extractor = ContentExtractor()
        self.metadata_extractor = MetadataExtractor()

    async def analyze_directory(
        self,
        directory_path: Path,
        analysis_types: List[AnalysisType],
        include_content: bool = False,
    ) -> AnalysisResult:
        """
        Analyze a directory comprehensively.

        Args:
            directory_path: Path to directory to analyze
            analysis_types: Types of analysis to perform
            include_content: Whether to extract file content

        Returns:
            Comprehensive analysis result

        Raises:
            OCDAnalysisError: If analysis fails
        """
        start_time = time.time()

        try:
            logger.info(
                "Starting directory analysis", path=directory_path, types=analysis_types
            )

            # Validate directory
            if not directory_path.exists():
                raise OCDAnalysisError(f"Directory does not exist: {directory_path}")

            if not directory_path.is_dir():
                raise OCDAnalysisError(f"Path is not a directory: {directory_path}")

            # Build directory info
            directory_info = await self._build_directory_info(directory_path)

            # Initialize analysis result
            analysis_result = AnalysisResult(
                directory_info=directory_info,
                analysis_type=AnalysisType.STRUCTURE,  # Primary type
                analysis_duration=0.0,
            )

            # Perform requested analyses
            for analysis_type in analysis_types:
                await self._perform_analysis(
                    analysis_result, analysis_type, include_content
                )

            # Calculate duration
            analysis_result.analysis_duration = time.time() - start_time

            logger.info(
                "Directory analysis completed",
                path=directory_path,
                duration=analysis_result.analysis_duration,
                files_analyzed=len(directory_info.files),
            )

            return analysis_result

        except Exception as e:
            logger.error("Directory analysis failed", path=directory_path, error=str(e))
            raise OCDAnalysisError(
                f"Directory analysis failed: {e}",
                directory_path=str(directory_path),
                cause=e,
            )

    async def _build_directory_info(self, directory_path: Path) -> DirectoryInfo:
        """Build comprehensive directory information."""
        files = []
        subdirectories = []
        total_size = 0
        file_count = 0

        try:
            # Walk directory tree
            for root, dirs, file_names in os.walk(directory_path):
                root_path = Path(root)
                current_depth = len(root_path.relative_to(directory_path).parts)

                # Check depth limit
                if current_depth > self.max_depth:
                    dirs.clear()  # Don't recurse deeper
                    continue

                # Filter excluded directories
                dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

                # Add subdirectories
                for dir_name in dirs:
                    subdirectories.append(str(root_path / dir_name))

                # Process files
                for file_name in file_names:
                    if file_count >= self.max_files:
                        break

                    file_path = root_path / file_name

                    # Skip excluded extensions
                    if file_path.suffix.lower() in self.excluded_extensions:
                        continue

                    try:
                        file_info = await self._build_file_info(file_path)
                        if file_info:
                            files.append(file_info)
                            total_size += file_info.size
                            file_count += 1

                    except Exception as e:
                        logger.debug(
                            "Failed to analyze file", file=file_path, error=str(e)
                        )
                        continue

                if file_count >= self.max_files:
                    break

        except Exception as e:
            logger.warning("Error walking directory", path=directory_path, error=str(e))

        return DirectoryInfo(
            root_path=directory_path,
            total_files=len(files),
            total_size=total_size,
            files=files,
            subdirectories=subdirectories,
            depth=self._calculate_max_depth(files, directory_path),
            analyzed_at=datetime.now(),
        )

    async def _build_file_info(self, file_path: Path) -> Optional[FileInfo]:
        """Build information for a single file."""
        try:
            stat = file_path.stat()

            # Skip files that are too large
            if stat.st_size > self.max_file_size:
                logger.debug("Skipping large file", file=file_path, size=stat.st_size)
                return None

            # Get MIME type
            mime_type, encoding = mimetypes.guess_type(str(file_path))

            # Get file permissions
            permissions = oct(stat.st_mode)[-3:]

            return FileInfo(
                path=file_path,
                name=file_path.name,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                file_type=file_path.suffix.lower() or "no_extension",
                mime_type=mime_type,
                encoding=encoding,
                permissions=permissions,
            )

        except Exception as e:
            logger.debug("Failed to build file info", file=file_path, error=str(e))
            return None

    def _calculate_max_depth(self, files: List[FileInfo], root_path: Path) -> int:
        """Calculate maximum directory depth."""
        max_depth = 0
        for file_info in files:
            try:
                relative_path = file_info.path.relative_to(root_path)
                depth = len(relative_path.parts) - 1  # Subtract file name
                max_depth = max(max_depth, depth)
            except ValueError:
                continue
        return max_depth

    async def _perform_analysis(
        self,
        analysis_result: AnalysisResult,
        analysis_type: AnalysisType,
        include_content: bool,
    ) -> None:
        """Perform specific type of analysis."""

        if analysis_type == AnalysisType.STRUCTURE:
            await self._analyze_structure(analysis_result)
        elif analysis_type == AnalysisType.CONTENT:
            await self._analyze_content(analysis_result, include_content)
        elif analysis_type == AnalysisType.METADATA:
            await self._analyze_metadata(analysis_result)
        elif analysis_type == AnalysisType.DEPENDENCY:
            await self._analyze_dependencies(analysis_result)
        elif analysis_type == AnalysisType.SEMANTIC:
            await self._analyze_semantic(analysis_result)

    async def _analyze_structure(self, analysis_result: AnalysisResult) -> None:
        """Analyze directory structure patterns."""
        directory_info = analysis_result.directory_info

        # Analyze file type distribution
        file_types = {}
        for file_info in directory_info.files:
            file_type = file_info.file_type
            file_types[file_type] = file_types.get(file_type, 0) + 1

        # Analyze directory structure
        depth_distribution = {}
        for file_info in directory_info.files:
            try:
                relative_path = file_info.path.relative_to(directory_info.root_path)
                depth = len(relative_path.parts) - 1
                depth_distribution[depth] = depth_distribution.get(depth, 0) + 1
            except ValueError:
                continue

        # Extract patterns
        patterns = []

        # File naming patterns
        patterns.extend(self._extract_naming_patterns(directory_info.files))

        # Directory organization patterns
        patterns.extend(
            self._extract_organization_patterns(directory_info.subdirectories)
        )

        # Size distribution patterns
        patterns.extend(self._extract_size_patterns(directory_info.files))

        analysis_result.extracted_patterns = patterns
        analysis_result.metadata.update(
            {
                "file_type_distribution": file_types,
                "depth_distribution": depth_distribution,
                "total_subdirectories": len(directory_info.subdirectories),
            }
        )

    async def _analyze_content(
        self, analysis_result: AnalysisResult, include_content: bool
    ) -> None:
        """Analyze file content patterns."""
        if not include_content:
            return

        content_summary = []
        text_files = []

        # Filter text files for content analysis
        for file_info in analysis_result.directory_info.files[
            :50
        ]:  # Limit for performance
            if self._is_text_file(file_info):
                text_files.append(file_info)

        # Extract content from text files
        for file_info in text_files[:20]:  # Further limit
            try:
                content = await self.content_extractor.extract_content(file_info.path)
                if content:
                    summary = await self.content_extractor.summarize_content(content)
                    content_summary.append(
                        {
                            "file": file_info.name,
                            "summary": summary[:200],  # Limit summary length
                            "type": file_info.file_type,
                        }
                    )
            except Exception as e:
                logger.debug(
                    "Content extraction failed", file=file_info.path, error=str(e)
                )

        analysis_result.content_summary = "\n".join(
            [f"{item['file']}: {item['summary']}" for item in content_summary]
        )

        analysis_result.metadata["content_files_analyzed"] = len(content_summary)

    async def _analyze_metadata(self, analysis_result: AnalysisResult) -> None:
        """Analyze file metadata patterns."""
        directory_info = analysis_result.directory_info

        # Analyze modification times
        modification_times = [f.modified for f in directory_info.files]
        if modification_times:
            oldest = min(modification_times)
            newest = max(modification_times)

            analysis_result.metadata.update(
                {
                    "oldest_file": oldest.isoformat(),
                    "newest_file": newest.isoformat(),
                    "timespan_days": (newest - oldest).days,
                }
            )

        # Analyze file sizes
        sizes = [f.size for f in directory_info.files]
        if sizes:
            analysis_result.metadata.update(
                {
                    "average_file_size": sum(sizes) / len(sizes),
                    "largest_file_size": max(sizes),
                    "smallest_file_size": min(sizes),
                }
            )

    async def _analyze_dependencies(self, analysis_result: AnalysisResult) -> None:
        """Analyze code dependencies and relationships."""
        dependencies = []

        # Look for common dependency files
        dependency_files = [
            "requirements.txt",
            "package.json",
            "Pipfile",
            "pyproject.toml",
            "composer.json",
            "pom.xml",
            "build.gradle",
            "Cargo.toml",
        ]

        for file_info in analysis_result.directory_info.files:
            if file_info.name in dependency_files:
                try:
                    deps = await self.metadata_extractor.extract_dependencies(
                        file_info.path
                    )
                    dependencies.extend(deps)
                except Exception as e:
                    logger.debug(
                        "Dependency extraction failed",
                        file=file_info.path,
                        error=str(e),
                    )

        analysis_result.dependencies = dependencies

    async def _analyze_semantic(self, analysis_result: AnalysisResult) -> None:
        """Analyze semantic patterns and meaning."""
        # Extract semantic information from file names and paths
        semantic_patterns = []

        # Analyze file naming semantics
        for file_info in analysis_result.directory_info.files:
            semantic_info = self._extract_semantic_info(file_info.path)
            if semantic_info:
                semantic_patterns.append(semantic_info)

        # Generate recommendations based on analysis
        recommendations = self._generate_recommendations(analysis_result)
        analysis_result.recommendations = recommendations

        analysis_result.metadata["semantic_patterns"] = semantic_patterns[:10]  # Limit

    def _extract_naming_patterns(self, files: List[FileInfo]) -> List[str]:
        """Extract file naming patterns."""
        patterns = []

        # Common naming conventions
        if any("_test" in f.name or "test_" in f.name for f in files):
            patterns.append("Uses test prefix/suffix naming convention")

        if any("-" in f.name for f in files):
            patterns.append("Uses hyphen-separated naming")

        if any("_" in f.name for f in files):
            patterns.append("Uses underscore-separated naming")

        if any(f.name.isupper() for f in files):
            patterns.append("Contains uppercase file names")

        return patterns

    def _extract_organization_patterns(self, subdirectories: List[str]) -> List[str]:
        """Extract directory organization patterns."""
        patterns = []

        # Common directory patterns
        common_dirs = {
            "src",
            "lib",
            "test",
            "tests",
            "docs",
            "config",
            "scripts",
            "bin",
        }
        found_dirs = set()

        for subdir in subdirectories:
            dir_name = Path(subdir).name.lower()
            if dir_name in common_dirs:
                found_dirs.add(dir_name)

        if found_dirs:
            patterns.append(f"Standard project structure: {', '.join(found_dirs)}")

        return patterns

    def _extract_size_patterns(self, files: List[FileInfo]) -> List[str]:
        """Extract file size patterns."""
        patterns = []

        if not files:
            return patterns

        sizes = [f.size for f in files]
        avg_size = sum(sizes) / len(sizes)

        large_files = [f for f in files if f.size > avg_size * 10]
        if large_files:
            patterns.append(f"Contains {len(large_files)} unusually large files")

        small_files = [f for f in files if f.size < 100]  # Less than 100 bytes
        if len(small_files) > len(files) * 0.1:  # More than 10% are tiny
            patterns.append("Many very small files (possibly generated)")

        return patterns

    def _is_text_file(self, file_info: FileInfo) -> bool:
        """Check if file is likely a text file."""
        text_extensions = {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".xml",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".sh",
            ".bat",
        }

        if file_info.file_type in text_extensions:
            return True

        if file_info.mime_type and file_info.mime_type.startswith("text/"):
            return True

        return False

    def _extract_semantic_info(self, file_path: Path) -> Optional[str]:
        """Extract semantic information from file path."""
        # Simple semantic analysis based on path components
        path_parts = file_path.parts

        semantic_indicators = {
            "config": "configuration",
            "test": "testing",
            "src": "source code",
            "lib": "library",
            "util": "utility",
            "helper": "helper function",
            "model": "data model",
            "view": "user interface",
            "controller": "business logic",
        }

        for part in path_parts:
            for indicator, meaning in semantic_indicators.items():
                if indicator in part.lower():
                    return f"{file_path.name}: {meaning}"

        return None

    def _generate_recommendations(self, analysis_result: AnalysisResult) -> List[str]:
        """Generate organization recommendations."""
        recommendations = []

        directory_info = analysis_result.directory_info

        # Check for organization opportunities
        if directory_info.total_files > 100:
            recommendations.append("Consider organizing files into subdirectories")

        # Check file type distribution
        file_types = analysis_result.metadata.get("file_type_distribution", {})
        if len(file_types) > 5:
            recommendations.append(
                "Multiple file types - consider type-based organization"
            )

        # Check for naming consistency
        if (
            "Uses hyphen-separated naming" in analysis_result.extracted_patterns
            and "Uses underscore-separated naming" in analysis_result.extracted_patterns
        ):
            recommendations.append(
                "Inconsistent naming convention - standardize on one style"
            )

        # Check for large files
        avg_size = analysis_result.metadata.get("average_file_size", 0)
        if avg_size > 1024 * 1024:  # 1MB average
            recommendations.append(
                "Large average file size - consider file optimization"
            )

        return recommendations

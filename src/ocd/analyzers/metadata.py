"""
Metadata Extractor
==================

Extracts metadata from various file types and formats.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class MetadataExtractor:
    """
    Extracts metadata from files for analysis.

    Supports:
    - Dependency files (requirements.txt, package.json, etc.)
    - Project files (pyproject.toml, Cargo.toml, etc.)
    - Configuration metadata
    - Code analysis metadata
    """

    async def extract_dependencies(self, file_path: Path) -> List[str]:
        """
        Extract dependencies from dependency files.

        Args:
            file_path: Path to dependency file

        Returns:
            List of dependency names
        """
        try:
            file_name = file_path.name.lower()

            if file_name == "requirements.txt":
                return await self._extract_pip_dependencies(file_path)
            elif file_name == "package.json":
                return await self._extract_npm_dependencies(file_path)
            elif file_name == "pipfile":
                return await self._extract_pipfile_dependencies(file_path)
            elif file_name == "pyproject.toml":
                return await self._extract_pyproject_dependencies(file_path)
            elif file_name == "composer.json":
                return await self._extract_composer_dependencies(file_path)
            elif file_name == "pom.xml":
                return await self._extract_maven_dependencies(file_path)
            elif file_name == "build.gradle":
                return await self._extract_gradle_dependencies(file_path)
            elif file_name == "cargo.toml":
                return await self._extract_cargo_dependencies(file_path)
            else:
                return []

        except Exception as e:
            logger.debug("Dependency extraction failed", file=file_path, error=str(e))
            return []

    async def _extract_pip_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from requirements.txt."""
        dependencies = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue

                    # Skip -r includes and other pip options
                    if line.startswith("-"):
                        continue

                    # Extract package name (before version specifier)
                    package_match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                    if package_match:
                        dependencies.append(package_match.group(1))

        except Exception as e:
            logger.debug(
                "Failed to parse requirements.txt", file=file_path, error=str(e)
            )

        return dependencies

    async def _extract_npm_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from package.json."""
        dependencies = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract dependencies
            for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                if dep_type in data and isinstance(data[dep_type], dict):
                    dependencies.extend(data[dep_type].keys())

        except Exception as e:
            logger.debug("Failed to parse package.json", file=file_path, error=str(e))

        return dependencies

    async def _extract_pipfile_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from Pipfile."""
        dependencies = []

        try:
            import toml

            with open(file_path, "r", encoding="utf-8") as f:
                data = toml.load(f)

            # Extract dependencies
            for section in ["packages", "dev-packages"]:
                if section in data and isinstance(data[section], dict):
                    dependencies.extend(data[section].keys())

        except Exception as e:
            logger.debug("Failed to parse Pipfile", file=file_path, error=str(e))

        return dependencies

    async def _extract_pyproject_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from pyproject.toml."""
        dependencies = []

        try:
            import toml

            with open(file_path, "r", encoding="utf-8") as f:
                data = toml.load(f)

            # Extract dependencies from different sections
            project = data.get("project", {})
            if "dependencies" in project:
                for dep in project["dependencies"]:
                    # Extract package name from dependency string
                    package_match = re.match(r"^([a-zA-Z0-9_-]+)", dep)
                    if package_match:
                        dependencies.append(package_match.group(1))

            # Extract optional dependencies
            optional_deps = project.get("optional-dependencies", {})
            for group_deps in optional_deps.values():
                for dep in group_deps:
                    package_match = re.match(r"^([a-zA-Z0-9_-]+)", dep)
                    if package_match:
                        dependencies.append(package_match.group(1))

        except Exception as e:
            logger.debug("Failed to parse pyproject.toml", file=file_path, error=str(e))

        return dependencies

    async def _extract_composer_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from composer.json."""
        dependencies = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract dependencies
            for dep_type in ["require", "require-dev"]:
                if dep_type in data and isinstance(data[dep_type], dict):
                    dependencies.extend(data[dep_type].keys())

        except Exception as e:
            logger.debug("Failed to parse composer.json", file=file_path, error=str(e))

        return dependencies

    async def _extract_maven_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from pom.xml."""
        dependencies = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple regex extraction for Maven dependencies
            # This is a basic implementation - proper XML parsing would be better
            artifact_pattern = r"<artifactId>([^<]+)</artifactId>"
            matches = re.findall(artifact_pattern, content)
            dependencies.extend(matches)

        except Exception as e:
            logger.debug("Failed to parse pom.xml", file=file_path, error=str(e))

        return dependencies

    async def _extract_gradle_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from build.gradle."""
        dependencies = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract dependencies using regex
            # This handles common Gradle dependency patterns
            patterns = [
                r"implementation\s+['\"]([^'\"]+)['\"]",
                r"compile\s+['\"]([^'\"]+)['\"]",
                r"testImplementation\s+['\"]([^'\"]+)['\"]",
                r"api\s+['\"]([^'\"]+)['\"]",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Extract package name (group:artifact format)
                    if ":" in match:
                        parts = match.split(":")
                        if len(parts) >= 2:
                            dependencies.append(f"{parts[0]}:{parts[1]}")
                    else:
                        dependencies.append(match)

        except Exception as e:
            logger.debug("Failed to parse build.gradle", file=file_path, error=str(e))

        return dependencies

    async def _extract_cargo_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from Cargo.toml."""
        dependencies = []

        try:
            import toml

            with open(file_path, "r", encoding="utf-8") as f:
                data = toml.load(f)

            # Extract dependencies
            for section in ["dependencies", "dev-dependencies", "build-dependencies"]:
                if section in data and isinstance(data[section], dict):
                    dependencies.extend(data[section].keys())

        except Exception as e:
            logger.debug("Failed to parse Cargo.toml", file=file_path, error=str(e))

        return dependencies

    async def extract_project_metadata(self, file_path: Path) -> Dict[str, str]:
        """
        Extract project metadata from configuration files.

        Args:
            file_path: Path to project file

        Returns:
            Dictionary of metadata
        """
        try:
            file_name = file_path.name.lower()

            if file_name == "package.json":
                return await self._extract_npm_metadata(file_path)
            elif file_name == "pyproject.toml":
                return await self._extract_pyproject_metadata(file_path)
            elif file_name == "composer.json":
                return await self._extract_composer_metadata(file_path)
            elif file_name == "cargo.toml":
                return await self._extract_cargo_metadata(file_path)
            else:
                return {}

        except Exception as e:
            logger.debug("Metadata extraction failed", file=file_path, error=str(e))
            return {}

    async def _extract_npm_metadata(self, file_path: Path) -> Dict[str, str]:
        """Extract metadata from package.json."""
        metadata = {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract common metadata fields
            fields = ["name", "version", "description", "author", "license", "homepage"]
            for field in fields:
                if field in data:
                    metadata[field] = str(data[field])

        except Exception as e:
            logger.debug("Failed to extract npm metadata", error=str(e))

        return metadata

    async def _extract_pyproject_metadata(self, file_path: Path) -> Dict[str, str]:
        """Extract metadata from pyproject.toml."""
        metadata = {}

        try:
            import toml

            with open(file_path, "r", encoding="utf-8") as f:
                data = toml.load(f)

            project = data.get("project", {})

            # Extract common metadata fields
            fields = ["name", "version", "description", "license", "homepage"]
            for field in fields:
                if field in project:
                    value = project[field]
                    if isinstance(value, dict) and "text" in value:
                        metadata[field] = value["text"]
                    else:
                        metadata[field] = str(value)

            # Extract authors
            if "authors" in project:
                authors = project["authors"]
                if isinstance(authors, list) and authors:
                    metadata["author"] = str(authors[0].get("name", ""))

        except Exception as e:
            logger.debug("Failed to extract pyproject metadata", error=str(e))

        return metadata

    async def _extract_composer_metadata(self, file_path: Path) -> Dict[str, str]:
        """Extract metadata from composer.json."""
        metadata = {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract common metadata fields
            fields = ["name", "version", "description", "license", "homepage"]
            for field in fields:
                if field in data:
                    metadata[field] = str(data[field])

            # Extract authors
            if (
                "authors" in data
                and isinstance(data["authors"], list)
                and data["authors"]
            ):
                author = data["authors"][0]
                if isinstance(author, dict) and "name" in author:
                    metadata["author"] = author["name"]

        except Exception as e:
            logger.debug("Failed to extract composer metadata", error=str(e))

        return metadata

    async def _extract_cargo_metadata(self, file_path: Path) -> Dict[str, str]:
        """Extract metadata from Cargo.toml."""
        metadata = {}

        try:
            import toml

            with open(file_path, "r", encoding="utf-8") as f:
                data = toml.load(f)

            package = data.get("package", {})

            # Extract common metadata fields
            fields = ["name", "version", "description", "license", "homepage"]
            for field in fields:
                if field in package:
                    metadata[field] = str(package[field])

            # Extract authors
            if (
                "authors" in package
                and isinstance(package["authors"], list)
                and package["authors"]
            ):
                metadata["author"] = package["authors"][0]

        except Exception as e:
            logger.debug("Failed to extract cargo metadata", error=str(e))

        return metadata

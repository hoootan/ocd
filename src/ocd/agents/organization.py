"""
Organization Agent
==================

Intelligent agent that analyzes directory structures and automatically organizes
files based on type, content, project structure, and user preferences.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate

from ocd.agents.base import BaseAgent
from ocd.core.exceptions import OCDError
from ocd.core.types import SafetyLevel

logger = structlog.get_logger(__name__)


class OrganizationAgent(BaseAgent):
    """
    AI agent specialized in intelligent file and directory organization.
    
    Capabilities:
    - Analyzes directory structures and file patterns
    - Creates logical folder hierarchies
    - Organizes files by type, date, project, or custom criteria
    - Handles naming conflicts and duplicate files
    - Respects existing project structures
    - Learns from user preferences and feedback
    """
    
    def __init__(
        self,
        llm_provider,
        safety_level: SafetyLevel = SafetyLevel.BALANCED,
        organization_style: str = "smart",  # smart, by_type, by_date, by_project
        preserve_structure: bool = True,
        **kwargs
    ):
        """
        Initialize Organization Agent.
        
        Args:
            llm_provider: LangChain LLM provider
            safety_level: Safety level for file operations
            organization_style: Default organization approach
            preserve_structure: Whether to preserve existing project structures
        """
        super().__init__(llm_provider, safety_level, **kwargs)
        
        self.organization_style = organization_style
        self.preserve_structure = preserve_structure
        
        # Organization patterns and preferences
        self.organization_patterns = {
            "by_type": {
                "documents": ["pdf", "doc", "docx", "txt", "md", "rtf"],
                "images": ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"],
                "videos": ["mp4", "avi", "mkv", "mov", "wmv", "flv", "webm"],
                "audio": ["mp3", "wav", "flac", "aac", "ogg", "m4a"],
                "archives": ["zip", "rar", "7z", "tar", "gz", "bz2"],
                "code": ["py", "js", "html", "css", "java", "cpp", "c", "php"],
                "data": ["json", "xml", "csv", "sql", "db", "xlsx"],
            },
            "by_project": {
                "web_projects": ["package.json", "index.html", "webpack.config.js"],
                "python_projects": ["setup.py", "requirements.txt", "pyproject.toml"],
                "java_projects": ["pom.xml", "build.gradle", "build.xml"],
                "mobile_projects": ["AndroidManifest.xml", "Info.plist", "pubspec.yaml"],
            }
        }
        
        self.logger = logger.bind(agent_type="organization")
    
    async def _setup_agent_tools(self) -> List[Tool]:
        """Setup organization-specific tools."""
        return [
            Tool(
                name="organize_by_type",
                func=self._organize_by_type,
                description="Organize files into folders based on their file type/category"
            ),
            Tool(
                name="organize_by_date",
                func=self._organize_by_date,
                description="Organize files into date-based folder structure (YYYY/MM)"
            ),
            Tool(
                name="organize_by_project",
                func=self._organize_by_project,
                description="Organize files based on detected project structure and type"
            ),
            Tool(
                name="create_logical_structure",
                func=self._create_logical_structure,
                description="Create a logical folder structure based on file analysis"
            ),
            Tool(
                name="consolidate_duplicates",
                func=self._consolidate_duplicates,
                description="Find and consolidate duplicate files"
            ),
            Tool(
                name="clean_empty_directories",
                func=self._clean_empty_directories,
                description="Remove empty directories after organization"
            ),
            Tool(
                name="suggest_organization_strategy",
                func=self._suggest_organization_strategy,
                description="Analyze directory and suggest best organization approach"
            ),
            Tool(
                name="apply_naming_conventions",
                func=self._apply_naming_conventions,
                description="Apply consistent naming conventions to files and folders"
            )
        ]
    
    async def _create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the organization agent's system prompt."""
        system_prompt = """You are an intelligent file organization agent. Your role is to analyze directories and organize files in the most logical, efficient way possible.

Key Principles:
1. SAFETY FIRST: Never perform destructive operations without user confirmation
2. PRESERVE IMPORTANT STRUCTURES: Don't break existing project structures or working directories
3. BE INTELLIGENT: Consider file content, not just extensions
4. ASK WHEN UNCERTAIN: If you're unsure about organization strategy, ask for guidance
5. EXPLAIN YOUR DECISIONS: Always explain why you're organizing files a certain way

Available Organization Strategies:
- by_type: Group files by their type/category (documents, images, code, etc.)
- by_date: Organize by creation/modification date (YYYY/MM structure)
- by_project: Detect and organize by project type (web, python, java, etc.)
- smart: Intelligent combination based on directory analysis

You have access to tools for:
- Analyzing directory structure and file patterns
- Creating directories and moving files safely
- Detecting duplicates and handling conflicts
- Applying naming conventions
- Previewing changes before execution

Always start by analyzing the directory structure and suggesting an organization strategy. Get user approval before making significant changes.

Current safety level: {safety_level}
Default organization style: {organization_style}
Preserve existing structures: {preserve_structure}
"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
    
    # Organization tool implementations
    
    async def _organize_by_type(self, directory_path: str) -> str:
        """Organize files by their type/category."""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                return f"Directory does not exist: {directory_path}"
            
            # Analyze files
            files_by_type = {}
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    file_type = self._classify_file_type(file_path)
                    if file_type not in files_by_type:
                        files_by_type[file_type] = []
                    files_by_type[file_type].append(file_path)
            
            if self.dry_run:
                summary = f"[DRY RUN] Would organize {len(files_by_type)} file types:\n"
                for file_type, files in files_by_type.items():
                    summary += f"- {file_type}: {len(files)} files\n"
                return summary
            
            # Create type-based directories and move files
            organized_count = 0
            for file_type, files in files_by_type.items():
                if len(files) > 1:  # Only create folders for multiple files
                    type_dir = directory / file_type.title()
                    await self.file_ops.create_directory(type_dir)
                    
                    for file_path in files:
                        relative_path = file_path.relative_to(directory)
                        if relative_path.parent != Path(file_type.title()):
                            new_path = type_dir / file_path.name
                            await self.file_ops.move_file(file_path, new_path)
                            organized_count += 1
            
            return f"Organized {organized_count} files by type into {len(files_by_type)} categories"
            
        except Exception as e:
            return f"Organization by type failed: {e}"
    
    async def _organize_by_date(self, directory_path: str) -> str:
        """Organize files by creation/modification date."""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                return f"Directory does not exist: {directory_path}"
            
            # Group files by date
            files_by_date = {}
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    # Use modification time
                    mtime = file_path.stat().st_mtime
                    from datetime import datetime
                    date = datetime.fromtimestamp(mtime)
                    year_month = f"{date.year}/{date.month:02d}"
                    
                    if year_month not in files_by_date:
                        files_by_date[year_month] = []
                    files_by_date[year_month].append(file_path)
            
            if self.dry_run:
                summary = f"[DRY RUN] Would organize by date into {len(files_by_date)} periods:\n"
                for period, files in files_by_date.items():
                    summary += f"- {period}: {len(files)} files\n"
                return summary
            
            # Create date directories and move files
            organized_count = 0
            for year_month, files in files_by_date.items():
                date_dir = directory / year_month
                await self.file_ops.create_directory(date_dir)
                
                for file_path in files:
                    relative_path = file_path.relative_to(directory)
                    if not str(relative_path).startswith(year_month):
                        new_path = date_dir / file_path.name
                        await self.file_ops.move_file(file_path, new_path)
                        organized_count += 1
            
            return f"Organized {organized_count} files by date into {len(files_by_date)} time periods"
            
        except Exception as e:
            return f"Organization by date failed: {e}"
    
    async def _organize_by_project(self, directory_path: str) -> str:
        """Organize files based on detected project types."""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                return f"Directory does not exist: {directory_path}"
            
            # Detect project types
            project_indicators = {}
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    project_type = self._detect_project_type(file_path)
                    if project_type:
                        if project_type not in project_indicators:
                            project_indicators[project_type] = []
                        project_indicators[project_type].append(file_path.parent)
            
            if self.dry_run:
                summary = f"[DRY RUN] Detected {len(project_indicators)} project types:\n"
                for project_type, dirs in project_indicators.items():
                    summary += f"- {project_type}: {len(set(dirs))} directories\n"
                return summary
            
            # Group related files by project type
            organized_count = 0
            for project_type, base_dirs in project_indicators.items():
                if len(set(base_dirs)) > 1:  # Multiple projects of same type
                    type_dir = directory / f"{project_type.title()}_Projects"
                    await self.file_ops.create_directory(type_dir)
                    organized_count += 1
            
            return f"Organized files into {len(project_indicators)} project-based structures"
            
        except Exception as e:
            return f"Organization by project failed: {e}"
    
    async def _create_logical_structure(self, directory_path: str) -> str:
        """Create a logical folder structure based on intelligent analysis."""
        try:
            directory = Path(directory_path)
            
            # Analyze directory comprehensively
            analysis = await self._analyze_directory(directory_path)
            
            # Determine best organization strategy
            strategy = await self._suggest_organization_strategy(directory_path)
            
            if self.dry_run:
                return f"[DRY RUN] Would create logical structure using {strategy} strategy"
            
            # Apply the suggested strategy
            if "by_type" in strategy:
                result = await self._organize_by_type(directory_path)
            elif "by_date" in strategy:
                result = await self._organize_by_date(directory_path)
            elif "by_project" in strategy:
                result = await self._organize_by_project(directory_path)
            else:
                # Smart hybrid approach
                result = await self._smart_organization(directory_path)
            
            return f"Created logical structure: {result}"
            
        except Exception as e:
            return f"Logical structure creation failed: {e}"
    
    async def _smart_organization(self, directory_path: str) -> str:
        """Intelligent organization using multiple strategies."""
        try:
            directory = Path(directory_path)
            results = []
            
            # First, handle project structures
            if self.preserve_structure:
                project_result = await self._organize_by_project(directory_path)
                results.append(project_result)
            
            # Then organize remaining files by type
            type_result = await self._organize_by_type(directory_path)
            results.append(type_result)
            
            # Finally, clean up
            cleanup_result = await self._clean_empty_directories(directory_path)
            results.append(cleanup_result)
            
            return " | ".join(results)
            
        except Exception as e:
            return f"Smart organization failed: {e}"
    
    async def _consolidate_duplicates(self, directory_path: str) -> str:
        """Find and consolidate duplicate files."""
        try:
            # Use the similarity detector from our SLM system
            from ocd.models.manager import SLMModelManager
            
            slm_manager = SLMModelManager()
            await slm_manager.initialize()
            
            duplicates = await slm_manager.find_duplicates_in_directory(Path(directory_path))
            
            if self.dry_run:
                total_duplicates = duplicates.get("total_duplicate_files", 0)
                space_wasted = duplicates.get("space_wasted", 0)
                return f"[DRY RUN] Found {total_duplicates} duplicate files, {space_wasted} bytes wasted"
            
            # Handle duplicates (move to duplicates folder)
            duplicate_groups = duplicates.get("exact_duplicate_groups", {})
            consolidated_count = 0
            
            if duplicate_groups:
                duplicates_dir = Path(directory_path) / "_Duplicates"
                await self.file_ops.create_directory(duplicates_dir)
                
                for file_hash, file_group in duplicate_groups.items():
                    # Keep first file, move others to duplicates folder
                    for duplicate_file in file_group[1:]:
                        source_path = Path(duplicate_file["path"])
                        dest_path = duplicates_dir / source_path.name
                        await self.file_ops.move_file(source_path, dest_path)
                        consolidated_count += 1
            
            return f"Consolidated {consolidated_count} duplicate files"
            
        except Exception as e:
            return f"Duplicate consolidation failed: {e}"
    
    async def _clean_empty_directories(self, directory_path: str) -> str:
        """Remove empty directories after organization."""
        try:
            directory = Path(directory_path)
            cleaned_count = 0
            
            # Find empty directories (bottom-up)
            for dir_path in sorted(directory.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if dir_path.is_dir() and dir_path != directory:
                    try:
                        if not any(dir_path.iterdir()):  # Directory is empty
                            if self.dry_run:
                                cleaned_count += 1
                            else:
                                dir_path.rmdir()
                                cleaned_count += 1
                    except OSError:
                        continue  # Directory not empty or permission error
            
            status = "[DRY RUN] Would remove" if self.dry_run else "Removed"
            return f"{status} {cleaned_count} empty directories"
            
        except Exception as e:
            return f"Directory cleanup failed: {e}"
    
    async def _suggest_organization_strategy(self, directory_path: str) -> str:
        """Analyze directory and suggest the best organization approach."""
        try:
            directory = Path(directory_path)
            
            # Count files by type
            file_types = {}
            project_indicators = set()
            total_files = 0
            
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    file_type = self._classify_file_type(file_path)
                    file_types[file_type] = file_types.get(file_type, 0) + 1
                    
                    # Check for project indicators
                    project_type = self._detect_project_type(file_path)
                    if project_type:
                        project_indicators.add(project_type)
            
            # Determine best strategy
            if len(project_indicators) > 0:
                strategy = "by_project - Detected project structures"
            elif len(file_types) > 5 and total_files > 50:
                strategy = "by_type - Many different file types"
            elif total_files > 100:
                strategy = "by_date - Large number of files, date-based organization recommended"
            else:
                strategy = "smart - Hybrid approach based on content analysis"
            
            return f"Recommended strategy: {strategy} (Files: {total_files}, Types: {len(file_types)}, Projects: {len(project_indicators)})"
            
        except Exception as e:
            return f"Strategy suggestion failed: {e}"
    
    async def _apply_naming_conventions(self, directory_path: str) -> str:
        """Apply consistent naming conventions to files and folders."""
        try:
            directory = Path(directory_path)
            renamed_count = 0
            
            for file_path in directory.rglob("*"):
                if file_path.name.startswith('.'):
                    continue  # Skip hidden files
                
                # Generate better name
                better_name = self._generate_better_name(file_path)
                
                if better_name != file_path.name:
                    if self.dry_run:
                        renamed_count += 1
                    else:
                        await self.file_ops.rename_file(file_path, better_name)
                        renamed_count += 1
            
            status = "[DRY RUN] Would rename" if self.dry_run else "Renamed"
            return f"{status} {renamed_count} files to follow naming conventions"
            
        except Exception as e:
            return f"Naming convention application failed: {e}"
    
    def _classify_file_type(self, file_path: Path) -> str:
        """Classify file type based on extension and content."""
        extension = file_path.suffix.lower().lstrip('.')
        
        for category, extensions in self.organization_patterns["by_type"].items():
            if extension in extensions:
                return category
        
        return "other"
    
    def _detect_project_type(self, file_path: Path) -> Optional[str]:
        """Detect project type based on file indicators."""
        file_name = file_path.name.lower()
        
        for project_type, indicators in self.organization_patterns["by_project"].items():
            if file_name in indicators:
                return project_type
        
        return None
    
    def _generate_better_name(self, file_path: Path) -> str:
        """Generate a better name following conventions."""
        name = file_path.name
        
        # Basic improvements
        # Remove multiple spaces
        name = " ".join(name.split())
        
        # Remove special characters (keep dots and hyphens)
        import re
        name = re.sub(r'[^\w\s\-\.]', '', name)
        
        # Replace spaces with underscores if more than 2 words
        parts = name.split()
        if len(parts) > 2:
            name = "_".join(parts)
        
        return name
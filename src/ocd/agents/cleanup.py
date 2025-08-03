"""
Cleanup Agent
=============

Intelligent agent specialized in identifying and handling cleanup tasks like
duplicates, temporary files, empty directories, and disk space optimization.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate

from ocd.agents.base import BaseAgent
from ocd.core.exceptions import OCDError

logger = structlog.get_logger(__name__)


class CleanupAgent(BaseAgent):
    """
    AI agent specialized in intelligent cleanup operations.
    
    Capabilities:
    - Identifies and handles duplicate files
    - Removes temporary and cache files safely
    - Cleans up empty directories
    - Optimizes disk space usage
    - Identifies large files and space hogs
    - Handles old backups and logs
    - Provides disk usage analysis
    """
    
    def __init__(
        self,
        llm_provider,
        aggressive_cleanup: bool = False,
        preserve_recent: int = 30,  # days
        min_file_age: int = 1,  # days
        **kwargs
    ):
        """
        Initialize Cleanup Agent.
        
        Args:
            llm_provider: LangChain LLM provider
            aggressive_cleanup: Whether to perform more aggressive cleanup
            preserve_recent: Preserve files newer than this many days
            min_file_age: Minimum age for files to be considered for cleanup
        """
        super().__init__(llm_provider, **kwargs)
        
        self.aggressive_cleanup = aggressive_cleanup
        self.preserve_recent = preserve_recent
        self.min_file_age = min_file_age
        
        # Cleanup patterns
        self.cleanup_patterns = {
            "temporary_files": [
                "*.tmp", "*.temp", "*.cache", "*.log", "*.bak", "*.swp",
                "*~", ".DS_Store", "Thumbs.db", "*.pyc", "*.pyo"
            ],
            "cache_directories": [
                "__pycache__", ".cache", "node_modules/.cache", ".pytest_cache",
                ".mypy_cache", ".coverage", ".tox", "*.egg-info"
            ],
            "backup_patterns": [
                "*.backup", "*.old", "*.orig", "*_backup_*", "*_old_*"
            ],
            "large_file_threshold": 1024 * 1024 * 100,  # 100MB
        }
        
        self.logger = logger.bind(agent_type="cleanup")
    
    async def _setup_agent_tools(self) -> List[Tool]:
        """Setup cleanup-specific tools."""
        return [
            Tool(
                name="find_duplicates",
                func=self._find_duplicates,
                description="Find and handle duplicate files in directory"
            ),
            Tool(
                name="clean_temporary_files",
                func=self._clean_temporary_files,
                description="Remove temporary files and cache directories"
            ),
            Tool(
                name="remove_empty_directories",
                func=self._remove_empty_directories,
                description="Remove empty directories recursively"
            ),
            Tool(
                name="analyze_disk_usage",
                func=self._analyze_disk_usage,
                description="Analyze disk usage and identify space hogs"
            ),
            Tool(
                name="clean_old_backups",
                func=self._clean_old_backups,
                description="Clean up old backup files and directories"
            ),
            Tool(
                name="optimize_large_files",
                func=self._optimize_large_files,
                description="Identify and suggest optimization for large files"
            ),
            Tool(
                name="clean_logs",
                func=self._clean_logs,
                description="Clean up old log files"
            ),
            Tool(
                name="comprehensive_cleanup",
                func=self._comprehensive_cleanup,
                description="Perform comprehensive cleanup of directory"
            )
        ]
    
    async def _create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the cleanup agent's system prompt."""
        system_prompt = """You are an intelligent cleanup agent. Your role is to identify and safely remove unnecessary files, optimize disk usage, and maintain clean directory structures.

Key Principles:
1. SAFETY FIRST: Never delete important files or break working systems
2. PRESERVE RECENT: Don't touch files newer than {preserve_recent} days by default
3. ASK BEFORE MAJOR CLEANUP: Get confirmation for significant cleanup operations
4. EXPLAIN ACTIONS: Always explain what you're cleaning up and why
5. PROVIDE STATISTICS: Show before/after disk usage and cleanup summary

Cleanup Categories:
- Temporary files: .tmp, .cache, .log, .bak files
- Cache directories: __pycache__, node_modules/.cache, etc.
- Duplicate files: Identical files taking up extra space
- Empty directories: Folders with no content
- Old backups: Backup files older than retention period
- Large files: Files that may need compression or removal

Current Settings:
- Aggressive cleanup: {aggressive_cleanup}
- Preserve files newer than: {preserve_recent} days
- Minimum file age for cleanup: {min_file_age} days

You have tools to:
- Find and handle duplicates
- Clean temporary and cache files
- Remove empty directories
- Analyze disk usage patterns
- Clean old backups and logs
- Identify optimization opportunities

Always provide a summary of space saved and files processed.
"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
    
    # Cleanup tool implementations
    
    async def _find_duplicates(self, directory_path: str) -> str:
        """Find and handle duplicate files."""
        try:
            # Use our SLM similarity detector
            from ocd.models.manager import SLMModelManager
            
            slm_manager = SLMModelManager()
            await slm_manager.initialize()
            
            duplicates = await slm_manager.find_duplicates_in_directory(Path(directory_path))
            
            total_duplicates = duplicates.get("total_duplicate_files", 0)
            space_wasted = duplicates.get("space_wasted", 0)
            duplicate_groups = duplicates.get("exact_duplicate_groups", {})
            
            if total_duplicates == 0:
                return "No duplicate files found"
            
            if self.dry_run:
                return f"[DRY RUN] Found {total_duplicates} duplicate files wasting {space_wasted} bytes"
            
            # Handle duplicates - move to _Duplicates folder
            cleaned_count = 0
            duplicates_dir = Path(directory_path) / "_Duplicates"
            
            if duplicate_groups:
                await self.file_ops.create_directory(duplicates_dir)
                
                for file_hash, file_group in duplicate_groups.items():
                    # Keep the first file, move others
                    for duplicate_info in file_group[1:]:
                        source_path = Path(duplicate_info["path"])
                        dest_path = duplicates_dir / source_path.name
                        
                        # Handle naming conflicts in duplicates folder
                        counter = 1
                        while dest_path.exists():
                            stem = source_path.stem
                            suffix = source_path.suffix
                            dest_path = duplicates_dir / f"{stem}_{counter}{suffix}"
                            counter += 1
                        
                        await self.file_ops.move_file(source_path, dest_path)
                        cleaned_count += 1
            
            return f"Moved {cleaned_count} duplicate files to _Duplicates folder, saved {space_wasted} bytes"
            
        except Exception as e:
            return f"Duplicate cleanup failed: {e}"
    
    async def _clean_temporary_files(self, directory_path: str) -> str:
        """Remove temporary files and cache directories."""
        try:
            directory = Path(directory_path)
            cleaned_files = 0
            cleaned_size = 0
            
            # Find temporary files
            temp_files = []
            for pattern in self.cleanup_patterns["temporary_files"]:
                temp_files.extend(directory.rglob(pattern))
            
            # Find cache directories
            cache_dirs = []
            for pattern in self.cleanup_patterns["cache_directories"]:
                cache_dirs.extend(directory.rglob(pattern))
            
            if self.dry_run:
                total_temp = len(temp_files)
                total_cache = len(cache_dirs)
                return f"[DRY RUN] Would clean {total_temp} temporary files and {total_cache} cache directories"
            
            # Clean temporary files
            for temp_file in temp_files:
                if temp_file.exists() and self._is_safe_to_delete(temp_file):
                    try:
                        size = temp_file.stat().st_size
                        await self.file_ops.delete_file(temp_file)
                        cleaned_files += 1
                        cleaned_size += size
                    except Exception as e:
                        self.logger.warning("Failed to delete temp file", file=str(temp_file), error=str(e))
            
            # Clean cache directories
            for cache_dir in cache_dirs:
                if cache_dir.exists() and cache_dir.is_dir() and self._is_safe_to_delete(cache_dir):
                    try:
                        # Calculate size before deletion
                        dir_size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
                        await self.file_ops.delete_file(cache_dir, force=True)
                        cleaned_size += dir_size
                        cleaned_files += 1
                    except Exception as e:
                        self.logger.warning("Failed to delete cache dir", dir=str(cache_dir), error=str(e))
            
            return f"Cleaned {cleaned_files} temporary items, freed {cleaned_size} bytes"
            
        except Exception as e:
            return f"Temporary file cleanup failed: {e}"
    
    async def _remove_empty_directories(self, directory_path: str) -> str:
        """Remove empty directories recursively."""
        try:
            directory = Path(directory_path)
            removed_count = 0
            
            # Find empty directories (bottom-up traversal)
            empty_dirs = []
            for dir_path in sorted(directory.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if dir_path.is_dir() and dir_path != directory:
                    try:
                        # Check if directory is empty
                        if not any(dir_path.iterdir()):
                            empty_dirs.append(dir_path)
                    except PermissionError:
                        continue
            
            if self.dry_run:
                return f"[DRY RUN] Would remove {len(empty_dirs)} empty directories"
            
            # Remove empty directories
            for empty_dir in empty_dirs:
                try:
                    empty_dir.rmdir()
                    removed_count += 1
                except OSError as e:
                    self.logger.debug("Could not remove directory", dir=str(empty_dir), error=str(e))
            
            return f"Removed {removed_count} empty directories"
            
        except Exception as e:
            return f"Empty directory cleanup failed: {e}"
    
    async def _analyze_disk_usage(self, directory_path: str) -> str:
        """Analyze disk usage and identify space hogs."""
        try:
            directory = Path(directory_path)
            
            # Analyze files by size
            large_files = []
            total_size = 0
            file_count = 0
            
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    try:
                        size = file_path.stat().st_size
                        total_size += size
                        file_count += 1
                        
                        if size > self.cleanup_patterns["large_file_threshold"]:
                            large_files.append((file_path, size))
                    except (PermissionError, OSError):
                        continue
            
            # Sort by size
            large_files.sort(key=lambda x: x[1], reverse=True)
            
            # Analyze by file type
            file_types = {}
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    try:
                        size = file_path.stat().st_size
                        if ext not in file_types:
                            file_types[ext] = {"count": 0, "size": 0}
                        file_types[ext]["count"] += 1
                        file_types[ext]["size"] += size
                    except (PermissionError, OSError):
                        continue
            
            # Format results
            analysis = f"Disk Usage Analysis:\n"
            analysis += f"Total files: {file_count:,}\n"
            analysis += f"Total size: {total_size:,} bytes ({total_size / (1024*1024*1024):.2f} GB)\n"
            analysis += f"Large files (>100MB): {len(large_files)}\n"
            
            if large_files:
                analysis += "\nLargest files:\n"
                for file_path, size in large_files[:5]:
                    analysis += f"- {file_path.name}: {size:,} bytes\n"
            
            # Top file types by size
            sorted_types = sorted(file_types.items(), key=lambda x: x[1]["size"], reverse=True)
            analysis += "\nTop file types by size:\n"
            for ext, info in sorted_types[:5]:
                analysis += f"- {ext or 'no extension'}: {info['count']} files, {info['size']:,} bytes\n"
            
            return analysis
            
        except Exception as e:
            return f"Disk usage analysis failed: {e}"
    
    async def _clean_old_backups(self, directory_path: str) -> str:
        """Clean up old backup files."""
        try:
            directory = Path(directory_path)
            cleaned_count = 0
            cleaned_size = 0
            
            # Find backup files
            backup_files = []
            for pattern in self.cleanup_patterns["backup_patterns"]:
                backup_files.extend(directory.rglob(pattern))
            
            # Also find OCD backups older than retention period
            ocd_backup_dirs = list(directory.rglob(".ocd_backups"))
            
            if self.dry_run:
                return f"[DRY RUN] Would clean {len(backup_files)} backup files and {len(ocd_backup_dirs)} backup directories"
            
            # Clean old backup files
            import time
            current_time = time.time()
            max_age = self.preserve_recent * 24 * 60 * 60  # Convert days to seconds
            
            for backup_file in backup_files:
                if backup_file.exists() and self._is_safe_to_delete(backup_file):
                    try:
                        # Check age
                        file_age = current_time - backup_file.stat().st_mtime
                        if file_age > max_age:
                            size = backup_file.stat().st_size
                            await self.file_ops.delete_file(backup_file)
                            cleaned_count += 1
                            cleaned_size += size
                    except Exception as e:
                        self.logger.warning("Failed to delete backup", file=str(backup_file), error=str(e))
            
            # Clean old OCD backup directories
            for backup_dir in ocd_backup_dirs:
                if backup_dir.exists():
                    # Clean old files within backup directories
                    for backup_file in backup_dir.rglob("*"):
                        if backup_file.is_file():
                            try:
                                file_age = current_time - backup_file.stat().st_mtime
                                if file_age > max_age:
                                    size = backup_file.stat().st_size
                                    await self.file_ops.delete_file(backup_file)
                                    cleaned_size += size
                            except Exception:
                                continue
            
            return f"Cleaned {cleaned_count} old backup files, freed {cleaned_size} bytes"
            
        except Exception as e:
            return f"Backup cleanup failed: {e}"
    
    async def _optimize_large_files(self, directory_path: str) -> str:
        """Identify and suggest optimization for large files."""
        try:
            directory = Path(directory_path)
            large_files = []
            
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    try:
                        size = file_path.stat().st_size
                        if size > self.cleanup_patterns["large_file_threshold"]:
                            large_files.append((file_path, size))
                    except (PermissionError, OSError):
                        continue
            
            large_files.sort(key=lambda x: x[1], reverse=True)
            
            suggestions = []
            for file_path, size in large_files[:10]:  # Top 10 largest
                ext = file_path.suffix.lower()
                
                if ext in ['.log', '.txt']:
                    suggestions.append(f"{file_path.name}: Consider compressing (gzip) - {size:,} bytes")
                elif ext in ['.mp4', '.avi', '.mov']:
                    suggestions.append(f"{file_path.name}: Consider video compression - {size:,} bytes")
                elif ext in ['.jpg', '.png', '.bmp']:
                    suggestions.append(f"{file_path.name}: Consider image optimization - {size:,} bytes")
                elif ext in ['.zip', '.rar', '.tar']:
                    suggestions.append(f"{file_path.name}: Archive file, verify if needed - {size:,} bytes")
                else:
                    suggestions.append(f"{file_path.name}: Large file, review necessity - {size:,} bytes")
            
            if not suggestions:
                return "No large files found that need optimization"
            
            return f"Optimization suggestions for {len(suggestions)} large files:\n" + "\n".join(suggestions)
            
        except Exception as e:
            return f"Large file optimization failed: {e}"
    
    async def _clean_logs(self, directory_path: str) -> str:
        """Clean up old log files."""
        try:
            directory = Path(directory_path)
            cleaned_count = 0
            cleaned_size = 0
            
            # Find log files
            log_files = list(directory.rglob("*.log"))
            
            if self.dry_run:
                return f"[DRY RUN] Would process {len(log_files)} log files"
            
            # Clean logs older than retention period
            import time
            current_time = time.time()
            max_age = self.preserve_recent * 24 * 60 * 60
            
            for log_file in log_files:
                if log_file.exists() and self._is_safe_to_delete(log_file):
                    try:
                        file_age = current_time - log_file.stat().st_mtime
                        size = log_file.stat().st_size
                        
                        if file_age > max_age:
                            # Delete old logs
                            await self.file_ops.delete_file(log_file)
                            cleaned_count += 1
                            cleaned_size += size
                        elif size > 100 * 1024 * 1024:  # 100MB
                            # Truncate very large logs instead of deleting
                            with open(log_file, 'w') as f:
                                f.write(f"# Log truncated by OCD cleanup agent\n")
                            cleaned_size += size
                            
                    except Exception as e:
                        self.logger.warning("Failed to clean log", file=str(log_file), error=str(e))
            
            return f"Cleaned {cleaned_count} log files, freed {cleaned_size} bytes"
            
        except Exception as e:
            return f"Log cleanup failed: {e}"
    
    async def _comprehensive_cleanup(self, directory_path: str) -> str:
        """Perform comprehensive cleanup of directory."""
        try:
            results = []
            
            # Run all cleanup operations
            operations = [
                ("Duplicates", self._find_duplicates),
                ("Temporary files", self._clean_temporary_files),
                ("Old backups", self._clean_old_backups),
                ("Log files", self._clean_logs),
                ("Empty directories", self._remove_empty_directories),
            ]
            
            total_operations = len(operations)
            for i, (name, operation) in enumerate(operations):
                try:
                    result = await operation(directory_path)
                    results.append(f"{name}: {result}")
                    
                    # Progress update
                    progress = f"[{i+1}/{total_operations}]"
                    self.logger.info("Cleanup progress", operation=name, progress=progress)
                    
                except Exception as e:
                    results.append(f"{name}: Failed - {e}")
            
            # Final analysis
            disk_analysis = await self._analyze_disk_usage(directory_path)
            
            summary = f"Comprehensive cleanup completed:\n"
            summary += "\n".join(f"- {result}" for result in results)
            summary += f"\n\nFinal disk usage:\n{disk_analysis}"
            
            return summary
            
        except Exception as e:
            return f"Comprehensive cleanup failed: {e}"
    
    def _is_safe_to_delete(self, file_path: Path) -> bool:
        """Check if a file is safe to delete."""
        try:
            # Check file age
            import time
            current_time = time.time()
            file_age = current_time - file_path.stat().st_mtime
            min_age_seconds = self.min_file_age * 24 * 60 * 60
            
            if file_age < min_age_seconds:
                return False
            
            # Check if file is in use (basic check)
            if file_path.suffix.lower() in ['.exe', '.dll', '.so', '.dylib']:
                return False
            
            # Don't delete system files
            system_paths = ['/System', '/usr', '/bin', '/sbin', 'C:\\Windows', 'C:\\Program Files']
            file_str = str(file_path)
            if any(file_str.startswith(path) for path in system_paths):
                return False
            
            return True
            
        except Exception:
            return False
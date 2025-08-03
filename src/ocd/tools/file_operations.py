"""
File Operations Manager
======================

Safe, intelligent file system operations with validation, rollback,
and conflict resolution capabilities.
"""

import asyncio
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import structlog

from ocd.core.exceptions import OCDError, OCDPermissionError, OCDValidationError
from ocd.core.types import SafetyLevel

logger = structlog.get_logger(__name__)


@dataclass
class FileOperation:
    """Represents a file system operation that can be executed and rolled back."""
    
    operation_type: str  # move, copy, rename, delete, create_dir
    source_path: Optional[Path] = None
    destination_path: Optional[Path] = None
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    executed: bool = False
    rollback_info: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationResult:
    """Result of a file operation."""
    
    success: bool
    operation: FileOperation
    message: str
    source: Optional[Path] = None
    destination: Optional[Path] = None
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    conflicts_resolved: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class FileOperationManager:
    """
    Manages file system operations with safety, validation, and rollback capabilities.
    
    Features:
    - Comprehensive safety checks
    - Automatic conflict resolution
    - Operation rollback and undo
    - Batch operations with transactions
    - Detailed logging and audit trail
    """
    
    def __init__(
        self,
        safety_level: SafetyLevel = SafetyLevel.BALANCED,
        backup_enabled: bool = True,
        max_batch_size: int = 1000,
    ):
        """
        Initialize file operation manager.
        
        Args:
            safety_level: Level of safety checks to perform
            backup_enabled: Whether to create backups before destructive operations
            max_batch_size: Maximum number of operations in a batch
        """
        self.safety_level = safety_level
        self.backup_enabled = backup_enabled
        self.max_batch_size = max_batch_size
        
        # Operation tracking
        self.operation_history: List[FileOperation] = []
        self.active_transaction: Optional[List[FileOperation]] = None
        
        # Safety settings based on level
        self.safety_settings = self._configure_safety_settings()
        
        self.logger = logger.bind(component="file_operations")
    
    def _configure_safety_settings(self) -> Dict[str, Any]:
        """Configure safety settings based on safety level."""
        if self.safety_level == SafetyLevel.MAXIMUM:
            return {
                "require_backup": True,
                "validate_permissions": True,
                "check_system_files": True,
                "prevent_overwrite": True,
                "max_file_size": 100 * 1024 * 1024,  # 100MB
                "allowed_extensions": None,  # All allowed
                "forbidden_paths": {
                    "/System", "/usr", "/bin", "/sbin", "/etc",
                    "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"
                }
            }
        elif self.safety_level == SafetyLevel.BALANCED:
            return {
                "require_backup": True,
                "validate_permissions": True,
                "check_system_files": True,
                "prevent_overwrite": False,
                "max_file_size": 1024 * 1024 * 1024,  # 1GB
                "allowed_extensions": None,
                "forbidden_paths": {
                    "/System", "/usr/bin", "/usr/sbin", "/etc",
                    "C:\\Windows\\System32", "C:\\Windows\\SysWOW64"
                }
            }
        else:  # MINIMAL
            return {
                "require_backup": False,
                "validate_permissions": True,
                "check_system_files": False,
                "prevent_overwrite": False,
                "max_file_size": 10 * 1024 * 1024 * 1024,  # 10GB
                "allowed_extensions": None,
                "forbidden_paths": set()
            }
    
    async def validate_operation(self, operation: Union[str, FileOperation]) -> bool:
        """Validate if an operation is safe to perform."""
        try:
            if isinstance(operation, str):
                # Parse string operation (simplified)
                return await self._validate_string_operation(operation)
            
            # Validate FileOperation
            if operation.source_path:
                if not await self._is_path_safe(operation.source_path):
                    return False
            
            if operation.destination_path:
                if not await self._is_path_safe(operation.destination_path):
                    return False
            
            # Check operation-specific validations
            if operation.operation_type == "delete":
                return await self._validate_delete_operation(operation)
            elif operation.operation_type in ["move", "copy"]:
                return await self._validate_move_copy_operation(operation)
            elif operation.operation_type == "rename":
                return await self._validate_rename_operation(operation)
            
            return True
            
        except Exception as e:
            self.logger.error("Operation validation failed", error=str(e))
            return False
    
    async def _is_path_safe(self, path: Path) -> bool:
        """Check if a path is safe to operate on."""
        path_str = str(path.resolve())
        
        # Check forbidden paths
        for forbidden in self.safety_settings["forbidden_paths"]:
            if path_str.startswith(forbidden):
                self.logger.warning("Operation blocked on forbidden path", path=path_str)
                return False
        
        # Check if path exists and permissions
        if self.safety_settings["validate_permissions"]:
            try:
                if path.exists():
                    # Check read/write permissions
                    if not (path.is_file() and path.stat().st_mode & 0o200):  # Write permission
                        if not (path.is_dir() and path.stat().st_mode & 0o200):
                            return False
            except PermissionError:
                return False
        
        return True
    
    async def create_directory(
        self, 
        path: Path, 
        parents: bool = True,
        exist_ok: bool = True
    ) -> OperationResult:
        """Create a directory with safety checks."""
        operation = FileOperation(
            operation_type="create_dir",
            destination_path=path,
            metadata={"parents": parents, "exist_ok": exist_ok}
        )
        
        try:
            # Validation
            if not await self.validate_operation(operation):
                raise OCDValidationError(f"Directory creation not allowed: {path}")
            
            # Check if already exists
            if path.exists():
                if exist_ok and path.is_dir():
                    return OperationResult(
                        success=True,
                        operation=operation,
                        message=f"Directory already exists: {path}",
                        destination=path
                    )
                else:
                    raise OCDError(f"Path already exists: {path}")
            
            # Create directory
            path.mkdir(parents=parents, exist_ok=exist_ok)
            
            operation.executed = True
            operation.rollback_info = {"created": True}
            self.operation_history.append(operation)
            
            self.logger.info("Directory created", path=str(path))
            
            return OperationResult(
                success=True,
                operation=operation,
                message=f"Directory created: {path}",
                destination=path
            )
            
        except Exception as e:
            self.logger.error("Failed to create directory", path=str(path), error=str(e))
            raise OCDError(f"Directory creation failed: {e}")
    
    async def move_file(
        self, 
        source: Path, 
        destination: Path,
        resolve_conflicts: bool = True
    ) -> OperationResult:
        """Move a file with conflict resolution."""
        operation = FileOperation(
            operation_type="move",
            source_path=source,
            destination_path=destination
        )
        
        try:
            # Validation
            if not await self.validate_operation(operation):
                raise OCDValidationError(f"Move operation not allowed: {source} -> {destination}")
            
            if not source.exists():
                raise OCDError(f"Source file does not exist: {source}")
            
            # Handle conflicts
            conflicts_resolved = []
            final_destination = destination
            
            if destination.exists() and resolve_conflicts:
                final_destination = await self._resolve_naming_conflict(destination)
                conflicts_resolved.append(f"Renamed to {final_destination.name} to avoid conflict")
            
            # Create destination directory if needed
            final_destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup if required
            backup_path = None
            if self.backup_enabled and final_destination.exists():
                backup_path = await self._create_backup(final_destination)
            
            # Perform move
            shutil.move(str(source), str(final_destination))
            
            operation.destination_path = final_destination
            operation.executed = True
            operation.rollback_info = {
                "backup_path": str(backup_path) if backup_path else None,
                "original_existed": destination.exists()
            }
            self.operation_history.append(operation)
            
            self.logger.info("File moved", source=str(source), destination=str(final_destination))
            
            return OperationResult(
                success=True,
                operation=operation,
                message=f"File moved: {source.name} -> {final_destination}",
                source=source,
                destination=final_destination,
                conflicts_resolved=conflicts_resolved
            )
            
        except Exception as e:
            self.logger.error("Failed to move file", source=str(source), error=str(e))
            raise OCDError(f"File move failed: {e}")
    
    async def rename_file(self, current_path: Path, new_name: str) -> OperationResult:
        """Rename a file with intelligent conflict handling."""
        # Ensure new_name is just the filename, not a path
        new_name = Path(new_name).name
        new_path = current_path.parent / new_name
        
        operation = FileOperation(
            operation_type="rename",
            source_path=current_path,
            destination_path=new_path,
            old_name=current_path.name,
            new_name=new_name
        )
        
        try:
            # Use move_file for the actual operation
            result = await self.move_file(current_path, new_path)
            
            # Update operation type and info
            operation.executed = True
            result.operation = operation
            result.old_name = current_path.name
            result.new_name = new_path.name
            result.message = f"File renamed: {current_path.name} -> {new_path.name}"
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to rename file", current_path=str(current_path), error=str(e))
            raise OCDError(f"File rename failed: {e}")
    
    async def copy_file(
        self, 
        source: Path, 
        destination: Path,
        preserve_metadata: bool = True
    ) -> OperationResult:
        """Copy a file with metadata preservation."""
        operation = FileOperation(
            operation_type="copy",
            source_path=source,
            destination_path=destination,
            metadata={"preserve_metadata": preserve_metadata}
        )
        
        try:
            # Validation
            if not await self.validate_operation(operation):
                raise OCDValidationError(f"Copy operation not allowed: {source} -> {destination}")
            
            if not source.exists():
                raise OCDError(f"Source file does not exist: {source}")
            
            # Create destination directory if needed
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle conflicts
            final_destination = destination
            if destination.exists():
                final_destination = await self._resolve_naming_conflict(destination)
            
            # Perform copy
            if preserve_metadata:
                shutil.copy2(str(source), str(final_destination))
            else:
                shutil.copy(str(source), str(final_destination))
            
            operation.destination_path = final_destination
            operation.executed = True
            operation.rollback_info = {"created_copy": True}
            self.operation_history.append(operation)
            
            self.logger.info("File copied", source=str(source), destination=str(final_destination))
            
            return OperationResult(
                success=True,
                operation=operation,
                message=f"File copied: {source.name} -> {final_destination}",
                source=source,
                destination=final_destination
            )
            
        except Exception as e:
            self.logger.error("Failed to copy file", source=str(source), error=str(e))
            raise OCDError(f"File copy failed: {e}")
    
    async def delete_file(self, path: Path, force: bool = False) -> OperationResult:
        """Delete a file or directory with safety checks."""
        operation = FileOperation(
            operation_type="delete",
            source_path=path,
            metadata={"force": force}
        )
        
        try:
            # Validation
            if not await self.validate_operation(operation):
                raise OCDValidationError(f"Delete operation not allowed: {path}")
            
            if not path.exists():
                return OperationResult(
                    success=True,
                    operation=operation,
                    message=f"File does not exist: {path}",
                    source=path
                )
            
            # Backup if required
            backup_path = None
            if self.backup_enabled:
                backup_path = await self._create_backup(path)
            
            # Perform deletion
            if path.is_dir():
                shutil.rmtree(str(path))
            else:
                path.unlink()
            
            operation.executed = True
            operation.rollback_info = {
                "backup_path": str(backup_path) if backup_path else None,
                "was_directory": path.is_dir()
            }
            self.operation_history.append(operation)
            
            self.logger.info("File deleted", path=str(path))
            
            return OperationResult(
                success=True,
                operation=operation,
                message=f"File deleted: {path}",
                source=path
            )
            
        except Exception as e:
            self.logger.error("Failed to delete file", path=str(path), error=str(e))
            raise OCDError(f"File deletion failed: {e}")
    
    async def _resolve_naming_conflict(self, path: Path) -> Path:
        """Resolve naming conflicts by generating a unique name."""
        base_name = path.stem
        extension = path.suffix
        parent = path.parent
        counter = 1
        
        while True:
            new_name = f"{base_name} ({counter}){extension}"
            new_path = parent / new_name
            
            if not new_path.exists():
                return new_path
            
            counter += 1
            if counter > 1000:  # Prevent infinite loops
                timestamp = int(time.time())
                new_name = f"{base_name}_{timestamp}{extension}"
                return parent / new_name
    
    async def _create_backup(self, path: Path) -> Path:
        """Create a backup of a file or directory."""
        backup_dir = path.parent / ".ocd_backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.name}_{timestamp}"
        backup_path = backup_dir / backup_name
        
        if path.is_dir():
            shutil.copytree(str(path), str(backup_path))
        else:
            shutil.copy2(str(path), str(backup_path))
        
        return backup_path
    
    async def rollback_operations(self, operations: List[FileOperation]) -> List[OperationResult]:
        """Rollback a list of operations."""
        results = []
        
        # Rollback in reverse order
        for operation in reversed(operations):
            try:
                result = await self._rollback_single_operation(operation)
                results.append(result)
            except Exception as e:
                self.logger.error("Rollback failed for operation", operation=operation, error=str(e))
                results.append(OperationResult(
                    success=False,
                    operation=operation,
                    message=f"Rollback failed: {e}"
                ))
        
        return results
    
    async def _rollback_single_operation(self, operation: FileOperation) -> OperationResult:
        """Rollback a single operation."""
        if not operation.executed:
            return OperationResult(
                success=True,
                operation=operation,
                message="Operation was not executed, nothing to rollback"
            )
        
        try:
            if operation.operation_type == "move":
                # Move back to original location
                if operation.destination_path and operation.destination_path.exists():
                    await self.move_file(operation.destination_path, operation.source_path)
                
            elif operation.operation_type == "copy":
                # Delete the copy
                if operation.destination_path and operation.destination_path.exists():
                    await self.delete_file(operation.destination_path, force=True)
                
            elif operation.operation_type == "create_dir":
                # Remove created directory if empty
                if operation.destination_path and operation.destination_path.exists():
                    try:
                        operation.destination_path.rmdir()
                    except OSError:
                        # Directory not empty, don't remove
                        pass
                
            elif operation.operation_type == "delete":
                # Restore from backup if available
                backup_path = operation.rollback_info.get("backup_path")
                if backup_path and Path(backup_path).exists():
                    if operation.rollback_info.get("was_directory"):
                        shutil.copytree(backup_path, str(operation.source_path))
                    else:
                        shutil.copy2(backup_path, str(operation.source_path))
            
            return OperationResult(
                success=True,
                operation=operation,
                message=f"Operation rolled back successfully"
            )
            
        except Exception as e:
            raise OCDError(f"Rollback failed: {e}")
    
    async def preview_operations(self, operations: Union[str, List[FileOperation]]) -> Dict[str, Any]:
        """Preview what operations would be performed."""
        if isinstance(operations, str):
            # Parse string operations (simplified)
            return {"preview": f"Would execute: {operations}"}
        
        preview = {
            "total_operations": len(operations),
            "operations_by_type": {},
            "potential_conflicts": [],
            "safety_warnings": [],
            "estimated_changes": []
        }
        
        for op in operations:
            op_type = op.operation_type
            preview["operations_by_type"][op_type] = preview["operations_by_type"].get(op_type, 0) + 1
            
            # Check for potential issues
            if op.destination_path and op.destination_path.exists():
                preview["potential_conflicts"].append(f"File exists: {op.destination_path}")
            
            if not await self.validate_operation(op):
                preview["safety_warnings"].append(f"Unsafe operation: {op.operation_type} on {op.source_path}")
        
        return preview
    
    async def _validate_string_operation(self, operation: str) -> bool:
        """Validate a string operation description."""
        # This would parse natural language operations
        # For now, just basic validation
        dangerous_keywords = ["delete", "remove", "rm", "format"]
        return not any(keyword in operation.lower() for keyword in dangerous_keywords)
    
    async def _validate_delete_operation(self, operation: FileOperation) -> bool:
        """Validate delete operations."""
        if self.safety_level == SafetyLevel.MAXIMUM:
            # Very restrictive
            return False
        
        return await self._is_path_safe(operation.source_path)
    
    async def _validate_move_copy_operation(self, operation: FileOperation) -> bool:
        """Validate move/copy operations."""
        return (await self._is_path_safe(operation.source_path) and 
                await self._is_path_safe(operation.destination_path))
    
    async def _validate_rename_operation(self, operation: FileOperation) -> bool:
        """Validate rename operations."""
        return await self._is_path_safe(operation.source_path)
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get statistics about performed operations."""
        total_ops = len(self.operation_history)
        if total_ops == 0:
            return {"total_operations": 0}
        
        by_type = {}
        successful = 0
        
        for op in self.operation_history:
            by_type[op.operation_type] = by_type.get(op.operation_type, 0) + 1
            if op.executed:
                successful += 1
        
        return {
            "total_operations": total_ops,
            "successful_operations": successful,
            "success_rate": successful / total_ops,
            "operations_by_type": by_type,
            "recent_operations": len([op for op in self.operation_history if 
                                   (datetime.now() - op.timestamp).seconds < 3600])  # Last hour
        }
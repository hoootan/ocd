"""
Sandbox Manager
==============

Provides isolated execution environments for scripts with resource limits
and security constraints.
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, List, Any
import structlog

from ocd.core.exceptions import OCDExecutionError
from ocd.core.types import SandboxConfig

logger = structlog.get_logger(__name__)


class SandboxManager:
    """
    Manages sandboxed script execution environments.

    Features:
    - Isolated temporary directories
    - Resource limits (time, memory, disk)
    - Network isolation options
    - File system restrictions
    - Process monitoring
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Initialize sandbox manager.

        Args:
            config: Sandbox configuration
        """
        self.config = config or SandboxConfig()
        self.logger = logger.bind(sandbox_id=id(self))

        # Active sandboxes
        self.active_sandboxes: Dict[str, "Sandbox"] = {}

    def create_sandbox(self, sandbox_id: Optional[str] = None) -> "Sandbox":
        """
        Create a new sandbox environment.

        Args:
            sandbox_id: Optional sandbox identifier

        Returns:
            Sandbox instance
        """
        if not sandbox_id:
            sandbox_id = f"sandbox_{int(time.time())}_{os.getpid()}"

        if sandbox_id in self.active_sandboxes:
            raise OCDExecutionError(f"Sandbox {sandbox_id} already exists")

        sandbox = Sandbox(sandbox_id, self.config)
        self.active_sandboxes[sandbox_id] = sandbox

        self.logger.info("Created sandbox", sandbox_id=sandbox_id)
        return sandbox

    def get_sandbox(self, sandbox_id: str) -> Optional["Sandbox"]:
        """Get existing sandbox by ID."""
        return self.active_sandboxes.get(sandbox_id)

    def destroy_sandbox(self, sandbox_id: str) -> bool:
        """
        Destroy a sandbox and clean up resources.

        Args:
            sandbox_id: Sandbox identifier

        Returns:
            True if destroyed, False if not found
        """
        if sandbox_id not in self.active_sandboxes:
            return False

        sandbox = self.active_sandboxes[sandbox_id]
        sandbox.cleanup()
        del self.active_sandboxes[sandbox_id]

        self.logger.info("Destroyed sandbox", sandbox_id=sandbox_id)
        return True

    def list_sandboxes(self) -> List[str]:
        """List active sandbox IDs."""
        return list(self.active_sandboxes.keys())

    def cleanup_all(self) -> None:
        """Clean up all active sandboxes."""
        for sandbox_id in list(self.active_sandboxes.keys()):
            self.destroy_sandbox(sandbox_id)


class Sandbox:
    """
    Individual sandbox instance with isolated environment.
    """

    def __init__(self, sandbox_id: str, config: SandboxConfig):
        """
        Initialize sandbox.

        Args:
            sandbox_id: Unique sandbox identifier
            config: Sandbox configuration
        """
        self.sandbox_id = sandbox_id
        self.config = config
        self.logger = logger.bind(sandbox_id=sandbox_id)

        # Create isolated directory
        self.temp_dir = None
        self.working_dir = None
        self._setup_isolation()

        # Resource tracking
        self.start_time = time.time()
        self.resources_used = {
            "cpu_time": 0.0,
            "memory_peak": 0,
            "disk_usage": 0,
            "files_created": 0,
        }

    def _setup_isolation(self) -> None:
        """Set up isolated environment."""
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(
                prefix=f"ocd_sandbox_{self.sandbox_id}_", dir=self.config.base_dir
            )
            self.working_dir = Path(self.temp_dir)

            # Set permissions
            os.chmod(self.temp_dir, 0o755)

            # Create standard subdirectories
            (self.working_dir / "input").mkdir(exist_ok=True)
            (self.working_dir / "output").mkdir(exist_ok=True)
            (self.working_dir / "temp").mkdir(exist_ok=True)

            self.logger.info(
                "Sandbox isolation setup complete", working_dir=self.working_dir
            )

        except Exception as e:
            raise OCDExecutionError(f"Failed to setup sandbox isolation: {e}")

    def get_environment(self) -> Dict[str, str]:
        """
        Get sandbox environment variables.

        Returns:
            Environment variables for sandbox
        """
        env = {}

        # Base environment
        if self.config.inherit_environment:
            env.update(os.environ)
        else:
            # Minimal environment
            env.update(
                {
                    "HOME": str(self.working_dir),
                    "TMPDIR": str(self.working_dir / "temp"),
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                    "PYTHONPATH": str(self.working_dir),
                    "PWD": str(self.working_dir),
                }
            )

        # Override with sandbox-specific values
        env.update(
            {
                "OCD_SANDBOX": self.sandbox_id,
                "OCD_SANDBOX_DIR": str(self.working_dir),
                "OCD_SANDBOX_INPUT": str(self.working_dir / "input"),
                "OCD_SANDBOX_OUTPUT": str(self.working_dir / "output"),
            }
        )

        # Add custom environment variables
        if self.config.environment_variables:
            env.update(self.config.environment_variables)

        # Remove dangerous variables
        dangerous_vars = [
            "LD_PRELOAD",
            "LD_LIBRARY_PATH",
            "DYLD_INSERT_LIBRARIES",
            "PYTHONSTARTUP",
            "BROWSER",
        ]
        for var in dangerous_vars:
            env.pop(var, None)

        return env

    def prepare_files(self, input_files: Dict[str, str]) -> None:
        """
        Prepare input files in sandbox.

        Args:
            input_files: Dictionary of filename -> content
        """
        input_dir = self.working_dir / "input"

        for filename, content in input_files.items():
            # Validate filename
            if not self._is_safe_filename(filename):
                raise OCDExecutionError(f"Unsafe filename: {filename}")

            file_path = input_dir / filename

            # Ensure file is within input directory
            if not self._is_path_safe(file_path, input_dir):
                raise OCDExecutionError(f"Path traversal detected: {filename}")

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.resources_used["files_created"] += 1

        self.logger.info("Prepared input files", count=len(input_files))

    def collect_outputs(self) -> Dict[str, str]:
        """
        Collect output files from sandbox.

        Returns:
            Dictionary of filename -> content
        """
        outputs = {}
        output_dir = self.working_dir / "output"

        if not output_dir.exists():
            return outputs

        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                # Check file size limits
                if file_path.stat().st_size > self.config.max_output_file_size:
                    self.logger.warning(
                        "Output file too large",
                        file=file_path,
                        size=file_path.stat().st_size,
                    )
                    continue

                try:
                    # Get relative path from output directory
                    rel_path = file_path.relative_to(output_dir)

                    # Read content (text files only for now)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        outputs[str(rel_path)] = f.read()

                except Exception as e:
                    self.logger.warning(
                        "Failed to read output file", file=file_path, error=str(e)
                    )

        self.logger.info("Collected outputs", count=len(outputs))
        return outputs

    def get_disk_usage(self) -> int:
        """
        Get current disk usage of sandbox.

        Returns:
            Disk usage in bytes
        """
        total_size = 0

        for file_path in self.working_dir.rglob("*"):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except (OSError, IOError):
                    pass  # File might have been deleted

        self.resources_used["disk_usage"] = total_size
        return total_size

    def check_resource_limits(self) -> List[str]:
        """
        Check if resource limits are exceeded.

        Returns:
            List of limit violations
        """
        violations = []

        # Check execution time
        elapsed_time = time.time() - self.start_time
        if elapsed_time > self.config.max_execution_time:
            violations.append(
                f"Execution time exceeded: {elapsed_time:.1f}s > {self.config.max_execution_time}s"
            )

        # Check disk usage
        disk_usage = self.get_disk_usage()
        if disk_usage > self.config.max_disk_usage:
            violations.append(
                f"Disk usage exceeded: {disk_usage} > {self.config.max_disk_usage} bytes"
            )

        # Check file count
        file_count = sum(1 for _ in self.working_dir.rglob("*") if _.is_file())
        if file_count > self.config.max_files:
            violations.append(
                f"File count exceeded: {file_count} > {self.config.max_files}"
            )

        return violations

    def cleanup(self) -> None:
        """Clean up sandbox resources."""
        if self.temp_dir and Path(self.temp_dir).exists():
            try:
                import shutil

                shutil.rmtree(self.temp_dir)
                self.logger.info("Sandbox cleanup complete")
            except Exception as e:
                self.logger.error("Sandbox cleanup failed", error=str(e))

    def _is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe."""
        # Disallow path traversal
        if ".." in filename or filename.startswith("/"):
            return False

        # Disallow dangerous characters
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]
        if any(char in filename for char in dangerous_chars):
            return False

        # Disallow hidden files and system files
        if filename.startswith(".") or filename.lower() in ["con", "prn", "aux", "nul"]:
            return False

        return True

    def _is_path_safe(self, target_path: Path, base_path: Path) -> bool:
        """Check if target path is within base path."""
        try:
            target_path.resolve().relative_to(base_path.resolve())
            return True
        except ValueError:
            return False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

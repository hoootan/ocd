"""
Script Execution Engine
======================

Main execution engine that coordinates safety validation, sandboxing,
and script execution with comprehensive monitoring and logging.
"""

import asyncio
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import structlog

from ocd.core.exceptions import OCDExecutionError, OCDError
from ocd.core.types import (
    ScriptLanguage,
    ExecutionResult,
    ExecutionConfig,
    SafetyLevel,
    SandboxConfig,
)
from ocd.executor.safety import SafetyValidator
from ocd.executor.sandbox import SandboxManager

logger = structlog.get_logger(__name__)


class ScriptExecutor:
    """
    Main script execution engine with safety and sandboxing.

    Features:
    - Multi-language script execution
    - Safety validation and pattern detection
    - Sandboxed execution environments
    - Resource monitoring and limits
    - Comprehensive logging and error handling
    - Async and sync execution modes
    """

    def __init__(
        self,
        safety_level: SafetyLevel = SafetyLevel.STRICT,
        sandbox_config: Optional[SandboxConfig] = None,
    ):
        """
        Initialize script executor.

        Args:
            safety_level: Safety validation level
            sandbox_config: Sandbox configuration
        """
        self.safety_validator = SafetyValidator(safety_level)
        self.sandbox_manager = SandboxManager(sandbox_config)
        self.logger = logger.bind(component="executor")

        # Execution tracking
        self.active_executions: Dict[str, subprocess.Popen] = {}

    async def execute_script(
        self,
        script_content: str,
        language: ScriptLanguage,
        config: Optional[ExecutionConfig] = None,
        input_files: Optional[Dict[str, str]] = None,
        working_directory: Optional[Path] = None,
    ) -> ExecutionResult:
        """
        Execute a script with safety validation and sandboxing.

        Args:
            script_content: Script content to execute
            language: Script programming language
            config: Execution configuration
            input_files: Input files for script (filename -> content)
            working_directory: Working directory for execution

        Returns:
            Execution result with outputs, logs, and metadata

        Raises:
            OCDExecutionError: If execution fails or safety violations
        """
        config = config or ExecutionConfig()
        execution_id = f"exec_{int(time.time())}_{id(script_content)}"

        self.logger.info(
            "Starting script execution",
            execution_id=execution_id,
            language=language.value,
            dry_run=config.dry_run,
        )

        start_time = time.time()

        try:
            # Step 1: Safety validation
            await self._validate_script_safety(
                script_content, language, working_directory
            )

            # Step 2: Syntax check
            syntax_error = self.safety_validator.check_syntax(script_content, language)
            if syntax_error:
                raise OCDExecutionError(f"Script syntax error: {syntax_error}")

            # Step 3: Create sandbox if enabled
            sandbox = None
            if config.use_sandbox:
                sandbox = self.sandbox_manager.create_sandbox(execution_id)
                if input_files:
                    sandbox.prepare_files(input_files)

            # Step 4: Execute script
            if config.dry_run:
                result = self._create_dry_run_result(script_content, language, config)
            else:
                result = await self._execute_in_environment(
                    script_content,
                    language,
                    config,
                    sandbox,
                    working_directory,
                    execution_id,
                )

            # Step 5: Collect outputs and cleanup
            if sandbox:
                result.output_files = sandbox.collect_outputs()
                result.resource_usage = sandbox.resources_used

                # Check resource violations
                violations = sandbox.check_resource_limits()
                if violations:
                    result.warnings.extend(violations)

            result.execution_time = time.time() - start_time
            result.execution_id = execution_id

            self.logger.info(
                "Script execution completed",
                execution_id=execution_id,
                success=result.success,
                execution_time=result.execution_time,
            )

            return result

        except Exception as e:
            self.logger.error(
                "Script execution failed", execution_id=execution_id, error=str(e)
            )

            # Clean up on error
            if execution_id in self.active_executions:
                await self._terminate_execution(execution_id)

            if config.use_sandbox:
                self.sandbox_manager.destroy_sandbox(execution_id)

            if isinstance(e, OCDError):
                raise
            else:
                raise OCDExecutionError(f"Script execution failed: {e}", cause=e)

        finally:
            # Always cleanup
            if config.use_sandbox:
                self.sandbox_manager.destroy_sandbox(execution_id)

    async def _validate_script_safety(
        self,
        script_content: str,
        language: ScriptLanguage,
        working_directory: Optional[Path],
    ) -> None:
        """Validate script for safety violations."""
        violations = self.safety_validator.validate_script(
            script_content, language, working_directory
        )

        # Log all violations
        for severity, violation_list in violations.items():
            if violation_list:
                self.logger.warning(
                    f"Safety violations ({severity})",
                    violations=violation_list,
                    count=len(violation_list),
                )

    def _create_dry_run_result(
        self, script_content: str, language: ScriptLanguage, config: ExecutionConfig
    ) -> ExecutionResult:
        """Create result for dry run mode."""
        return ExecutionResult(
            success=True,
            exit_code=0,
            stdout="[DRY RUN] Script would be executed",
            stderr="",
            execution_time=0.0,
            script_content=script_content,
            language=language,
            config=config,
            warnings=["Dry run mode - script not actually executed"],
        )

    async def _execute_in_environment(
        self,
        script_content: str,
        language: ScriptLanguage,
        config: ExecutionConfig,
        sandbox: Optional[Any],
        working_directory: Optional[Path],
        execution_id: str,
    ) -> ExecutionResult:
        """Execute script in the configured environment."""
        # Determine execution command
        command = self._build_execution_command(language, config)

        # Set up environment
        env = self._prepare_environment(sandbox, config)

        # Set working directory
        cwd = sandbox.working_dir if sandbox else working_directory

        # Execute script
        try:
            # Create process
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(cwd) if cwd else None,
            )

            self.active_executions[execution_id] = process

            # Execute with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=script_content.encode("utf-8")),
                    timeout=config.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise OCDExecutionError("Script execution timed out")

            # Clean up
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

            return ExecutionResult(
                success=process.returncode == 0,
                exit_code=process.returncode,
                stdout=stdout.decode("utf-8", errors="ignore"),
                stderr=stderr.decode("utf-8", errors="ignore"),
                execution_time=0.0,  # Will be set by calling function
                script_content=script_content,
                language=language,
                config=config,
            )

        except Exception as e:
            raise OCDExecutionError(f"Process execution failed: {e}")

    def _build_execution_command(
        self, language: ScriptLanguage, config: ExecutionConfig
    ) -> List[str]:
        """Build command for script execution."""
        commands = {
            ScriptLanguage.BASH: ["bash"],
            ScriptLanguage.PYTHON: ["python3"],
            ScriptLanguage.POWERSHELL: ["pwsh"]
            if sys.platform != "win32"
            else ["powershell"],
        }

        base_command = commands.get(language)
        if not base_command:
            raise OCDExecutionError(f"Unsupported language: {language}")

        command = base_command.copy()

        # Add language-specific options
        if language == ScriptLanguage.BASH:
            command.extend(["-e"])  # Exit on error
            if config.verbose:
                command.append("-x")  # Trace execution
        elif language == ScriptLanguage.PYTHON:
            command.extend(["-u"])  # Unbuffered output
            if not config.allow_imports:
                command.extend(["-I"])  # Isolated mode
        elif language == ScriptLanguage.POWERSHELL:
            command.extend(["-NoProfile", "-ExecutionPolicy", "Bypass"])

        return command

    def _prepare_environment(
        self, sandbox: Optional[Any], config: ExecutionConfig
    ) -> Dict[str, str]:
        """Prepare environment variables for execution."""
        if sandbox:
            env = sandbox.get_environment()
        else:
            env = self.safety_validator.create_safe_environment()

        # Add config-specific environment variables
        if config.environment_variables:
            env.update(config.environment_variables)

        return env

    async def _terminate_execution(self, execution_id: str) -> None:
        """Terminate a running execution."""
        if execution_id not in self.active_executions:
            return

        process = self.active_executions[execution_id]

        try:
            # Try graceful termination first
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            # Force kill if graceful termination fails
            process.kill()
            await process.wait()
        finally:
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

    def execute_script_sync(
        self,
        script_content: str,
        language: ScriptLanguage,
        config: Optional[ExecutionConfig] = None,
        input_files: Optional[Dict[str, str]] = None,
        working_directory: Optional[Path] = None,
    ) -> ExecutionResult:
        """
        Synchronous wrapper for script execution.

        Args:
            script_content: Script content to execute
            language: Script programming language
            config: Execution configuration
            input_files: Input files for script
            working_directory: Working directory for execution

        Returns:
            Execution result
        """
        return asyncio.run(
            self.execute_script(
                script_content, language, config, input_files, working_directory
            )
        )

    def validate_script_only(
        self,
        script_content: str,
        language: ScriptLanguage,
        working_directory: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Validate script without execution.

        Args:
            script_content: Script to validate
            language: Script language
            working_directory: Working directory context

        Returns:
            Validation result with violations and syntax check
        """
        result = {
            "syntax_valid": True,
            "syntax_error": None,
            "safety_violations": {},
            "recommendations": [],
        }

        # Syntax check
        syntax_error = self.safety_validator.check_syntax(script_content, language)
        if syntax_error:
            result["syntax_valid"] = False
            result["syntax_error"] = syntax_error

        # Safety validation
        try:
            violations = self.safety_validator.validate_script(
                script_content, language, working_directory
            )
            result["safety_violations"] = violations

            # Generate recommendations
            total_violations = sum(len(v) for v in violations.values())
            if total_violations > 0:
                result["recommendations"].append(
                    f"Consider reviewing {total_violations} safety violations before execution"
                )

            if violations.get("critical"):
                result["recommendations"].append(
                    "Critical safety violations detected - execution blocked in strict mode"
                )

        except OCDExecutionError as e:
            result["safety_violations"] = {"error": str(e)}

        return result

    def list_active_executions(self) -> List[str]:
        """List currently active execution IDs."""
        return list(self.active_executions.keys())

    async def terminate_all_executions(self) -> None:
        """Terminate all active executions."""
        execution_ids = list(self.active_executions.keys())
        for execution_id in execution_ids:
            await self._terminate_execution(execution_id)

    def cleanup(self) -> None:
        """Clean up all resources."""
        # This would be called synchronously, so we need to handle async cleanup
        try:
            asyncio.run(self.terminate_all_executions())
        except:
            pass  # Best effort cleanup

        self.sandbox_manager.cleanup_all()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

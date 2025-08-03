"""
Safety Validator
===============

Validates scripts for potentially dangerous operations before execution.
"""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set
import structlog

from ocd.core.exceptions import OCDExecutionError
from ocd.core.types import ScriptLanguage, SafetyLevel

logger = structlog.get_logger(__name__)


class SafetyValidator:
    """
    Validates scripts for dangerous operations and patterns.

    Features:
    - Pattern-based analysis for dangerous commands
    - File system operation validation
    - Network operation detection
    - System command analysis
    - Configurable safety levels
    """

    def __init__(self, safety_level: SafetyLevel = SafetyLevel.STRICT):
        """
        Initialize safety validator.

        Args:
            safety_level: Safety validation level
        """
        self.safety_level = safety_level
        self.logger = logger.bind(safety_level=safety_level.value)

        # Load danger patterns
        self._load_danger_patterns()

    def _load_danger_patterns(self) -> None:
        """Load dangerous command patterns by language."""
        self.danger_patterns = {
            ScriptLanguage.BASH: {
                "critical": [
                    r"\brm\s+-rf\s+/",  # Recursive delete from root
                    r"\bformat\s+[c-z]:",  # Format drive
                    r"\bdd\s+if=/dev/zero",  # Zero out disk
                    r"\bchmod\s+777\s+/",  # Dangerous permissions
                    r">\s*/dev/sd[a-z]",  # Write to block device
                    r"\bmkfs\b",  # Format filesystem
                    r"\bfdisk\b",  # Disk partitioning
                    r"\bcryptsetup\b",  # Disk encryption
                ],
                "high": [
                    r"\brm\s+-rf\b",  # Recursive delete
                    r"\bchmod\s+777\b",  # Dangerous permissions
                    r"\bsudo\s+rm\b",  # Sudo delete
                    r"\bkill\s+-9\s+1\b",  # Kill init
                    r"\breboot\b",  # System reboot
                    r"\bshutdown\b",  # System shutdown
                    r"\buseradd\b",  # Add user
                    r"\buserdel\b",  # Delete user
                    r"\bpasswd\b",  # Change password
                    r"curl\s+.*\|\s*bash",  # Pipe to bash
                    r"wget\s+.*\|\s*bash",  # Pipe to bash
                ],
                "medium": [
                    r"\bkill\b",  # Kill processes
                    r"\bpkill\b",  # Kill by name
                    r"\bkillall\b",  # Kill all processes
                    r"\bmount\b",  # Mount filesystems
                    r"\bumount\b",  # Unmount filesystems
                    r"\bchown\b",  # Change ownership
                    r"\bchgrp\b",  # Change group
                    r"\bcrontab\b",  # Cron jobs
                    r"\bservice\b",  # System services
                    r"\bsystemctl\b",  # Systemd control
                ],
            },
            ScriptLanguage.PYTHON: {
                "critical": [
                    r'os\.system\(["\']rm\s+-rf\s+/',  # System rm -rf /
                    r'shutil\.rmtree\(["\']/',  # Remove tree from root
                    r"subprocess\..*rm\s+-rf\s+/",  # Subprocess rm -rf /
                    r'os\.remove\(["\']/',  # Remove from root
                    r'pathlib\.Path\(["\'/"].*(\.unlink|\.rmdir)',  # Path operations
                    r'__import__\(["\']os["\'].*system',  # Dynamic os import
                ],
                "high": [
                    r"shutil\.rmtree\b",  # Remove directory tree
                    r"os\.system\b",  # System commands
                    r"subprocess\.call\b",  # Subprocess calls
                    r"subprocess\.run\b",  # Subprocess run
                    r"subprocess\.Popen\b",  # Process creation
                    r"eval\s*\(",  # Code evaluation
                    r"exec\s*\(",  # Code execution
                    r"compile\s*\(",  # Code compilation
                    r"__import__\b",  # Dynamic imports
                    r"getattr\s*\(.*[\"\']__",  # Dynamic attribute access
                ],
                "medium": [
                    r'open\s*\(.*["\']w["\']',  # File writing
                    r"socket\.socket\b",  # Network sockets
                    r"urllib\.request\b",  # HTTP requests
                    r"requests\.get\b",  # HTTP requests
                    r"requests\.post\b",  # HTTP requests
                    r"os\.environ\b",  # Environment variables
                    r"sys\.exit\b",  # System exit
                    r"quit\s*\(\)",  # Quit function
                    r"exit\s*\(\)",  # Exit function
                ],
            },
            ScriptLanguage.POWERSHELL: {
                "critical": [
                    r"Remove-Item\s+.*-Recurse.*-Force.*C:\\",  # Delete from C:
                    r"Format-Volume\b",  # Format drive
                    r"Clear-Disk\b",  # Clear disk
                    r"Remove-Partition\b",  # Remove partition
                    r"Initialize-Disk\b",  # Initialize disk
                ],
                "high": [
                    r"Remove-Item\s+.*-Recurse.*-Force",  # Recursive force delete
                    r"Set-ExecutionPolicy\s+Unrestricted",  # Execution policy
                    r"Invoke-Expression\b",  # Dynamic execution
                    r"Invoke-Command\b",  # Remote execution
                    r"Start-Process\b",  # Process creation
                    r"New-Object\s+.*ComObject",  # COM objects
                    r"Add-Type\b",  # Dynamic compilation
                    r"Stop-Computer\b",  # Shutdown
                    r"Restart-Computer\b",  # Restart
                ],
                "medium": [
                    r"Remove-Item\b",  # Delete items
                    r"New-Item\b",  # Create items
                    r"Set-Content\b",  # Write content
                    r"Out-File\b",  # Write to file
                    r"Invoke-WebRequest\b",  # HTTP requests
                    r"Download\b",  # Downloads
                    r"Set-Location\b",  # Change directory
                    r"Get-ChildItem\s+.*-Recurse",  # Recursive listing
                ],
            },
        }

    def validate_script(
        self,
        script_content: str,
        language: ScriptLanguage,
        working_dir: Optional[Path] = None,
    ) -> Dict[str, List[str]]:
        """
        Validate script for safety violations.

        Args:
            script_content: Script content to validate
            language: Script language
            working_dir: Working directory context

        Returns:
            Dictionary of violations by severity level

        Raises:
            OCDExecutionError: If critical violations found in strict mode
        """
        violations = {"critical": [], "high": [], "medium": [], "low": []}

        if language not in self.danger_patterns:
            self.logger.warning("No patterns for language", language=language.value)
            return violations

        patterns = self.danger_patterns[language]

        # Check each severity level
        for severity, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(
                    pattern, script_content, re.IGNORECASE | re.MULTILINE
                )
                for match in matches:
                    violation = {
                        "pattern": pattern,
                        "match": match.group(),
                        "line": self._get_line_number(script_content, match.start()),
                        "context": self._get_context(
                            script_content, match.start(), match.end()
                        ),
                    }
                    violations[severity].append(violation)

        # Additional validations
        self._validate_file_operations(
            script_content, language, violations, working_dir
        )
        self._validate_network_operations(script_content, language, violations)
        self._validate_system_operations(script_content, language, violations)

        # Log violations
        total_violations = sum(len(v) for v in violations.values())
        if total_violations > 0:
            self.logger.warning(
                "Script violations detected",
                violations=violations,
                total=total_violations,
            )

        # Enforce safety level
        if self.safety_level == SafetyLevel.STRICT and violations["critical"]:
            raise OCDExecutionError(
                f"Critical safety violations detected: {len(violations['critical'])} issues",
                violations=violations,
            )
        elif self.safety_level == SafetyLevel.PARANOID and (
            violations["critical"] or violations["high"]
        ):
            raise OCDExecutionError(
                f"High-risk safety violations detected", violations=violations
            )

        return violations

    def _validate_file_operations(
        self,
        script_content: str,
        language: ScriptLanguage,
        violations: Dict[str, List[str]],
        working_dir: Optional[Path],
    ) -> None:
        """Validate file system operations."""
        # Check for operations outside working directory
        if working_dir:
            dangerous_paths = [
                "/",
                "/etc",
                "/bin",
                "/usr",
                "/var",
                "/sys",
                "/proc",
                "C:\\",
                "C:\\Windows",
                "C:\\Program Files",
                "$env:SystemRoot",
                "$env:ProgramFiles",
            ]

            for path in dangerous_paths:
                if path in script_content:
                    violations["high"].append(
                        {
                            "type": "dangerous_path",
                            "path": path,
                            "description": f"Access to system path: {path}",
                        }
                    )

    def _validate_network_operations(
        self,
        script_content: str,
        language: ScriptLanguage,
        violations: Dict[str, List[str]],
    ) -> None:
        """Validate network operations."""
        network_patterns = {
            ScriptLanguage.BASH: [
                r"curl\s+.*",
                r"wget\s+.*",
                r"nc\s+.*",
                r"netcat\s+.*",
            ],
            ScriptLanguage.PYTHON: [r"urllib\.", r"requests\.", r"socket\.", r"http\."],
            ScriptLanguage.POWERSHELL: [
                r"Invoke-WebRequest",
                r"Invoke-RestMethod",
                r"Net\.",
                r"WebClient",
            ],
        }

        if language in network_patterns:
            for pattern in network_patterns[language]:
                if re.search(pattern, script_content, re.IGNORECASE):
                    violations["medium"].append(
                        {
                            "type": "network_operation",
                            "pattern": pattern,
                            "description": "Network operation detected",
                        }
                    )

    def _validate_system_operations(
        self,
        script_content: str,
        language: ScriptLanguage,
        violations: Dict[str, List[str]],
    ) -> None:
        """Validate system-level operations."""
        # Check for privilege escalation
        privilege_patterns = {
            ScriptLanguage.BASH: [r"\bsudo\b", r"\bsu\b"],
            ScriptLanguage.PYTHON: [r"os\.setuid", r"os\.setgid"],
            ScriptLanguage.POWERSHELL: [r"Start-Process.*-Verb\s+RunAs"],
        }

        if language in privilege_patterns:
            for pattern in privilege_patterns[language]:
                if re.search(pattern, script_content, re.IGNORECASE):
                    violations["high"].append(
                        {
                            "type": "privilege_escalation",
                            "pattern": pattern,
                            "description": "Privilege escalation detected",
                        }
                    )

    def _get_line_number(self, content: str, position: int) -> int:
        """Get line number for a position in the content."""
        return content[:position].count("\n") + 1

    def _get_context(
        self, content: str, start: int, end: int, context_lines: int = 2
    ) -> str:
        """Get context around a match."""
        lines = content.split("\n")
        line_num = self._get_line_number(content, start) - 1

        start_line = max(0, line_num - context_lines)
        end_line = min(len(lines), line_num + context_lines + 1)

        context = lines[start_line:end_line]
        return "\n".join(
            f"{i+start_line+1:4d}: {line}" for i, line in enumerate(context)
        )

    def check_syntax(
        self, script_content: str, language: ScriptLanguage
    ) -> Optional[str]:
        """
        Check script syntax without execution.

        Args:
            script_content: Script content
            language: Script language

        Returns:
            Error message if syntax invalid, None if valid
        """
        try:
            if language == ScriptLanguage.PYTHON:
                import ast

                ast.parse(script_content)
            elif language == ScriptLanguage.BASH:
                # Use bash -n for syntax check
                result = subprocess.run(
                    ["bash", "-n"],
                    input=script_content,
                    text=True,
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    return result.stderr
            elif language == ScriptLanguage.POWERSHELL:
                # Use PowerShell parser
                result = subprocess.run(
                    [
                        "pwsh",
                        "-Command",
                        "param($code) [System.Management.Automation.PSParser]::Tokenize($code, [ref]$null)",
                    ],
                    input=script_content,
                    text=True,
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    return result.stderr

        except Exception as e:
            return f"Syntax check failed: {e}"

        return None

    def create_safe_environment(self) -> Dict[str, str]:
        """
        Create safe environment variables for script execution.

        Returns:
            Dictionary of safe environment variables
        """
        import os

        # Start with minimal environment
        safe_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": str(Path.home()),
            "USER": os.environ.get("USER", "unknown"),
            "SHELL": "/bin/bash",
            "TERM": "xterm-256color",
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
        }

        # Add Python path if needed
        if "PYTHONPATH" in os.environ:
            safe_env["PYTHONPATH"] = os.environ["PYTHONPATH"]

        return safe_env

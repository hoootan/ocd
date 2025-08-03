#!/usr/bin/env python3
"""
OCD Bootstrap Installer
=======================

Single-file installer that sets up the OCD environment with all dependencies.
Handles cross-platform installation, virtual environments, and dependency management.

Usage:
    python install.py [--dev] [--local-only] [--no-venv]

Options:
    --dev         Install development dependencies
    --local-only  Install only local AI dependencies (no cloud APIs)
    --no-venv     Skip virtual environment creation
    --force       Force reinstallation even if already installed
"""

import argparse
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import List, Optional


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class OCDInstaller:
    """
    Bootstrap installer for OCD project.
    
    Handles dependency installation, virtual environment setup,
    and cross-platform compatibility.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.venv_path = project_root / ".venv"
        self.platform = platform.system().lower()
        self.python_executable = sys.executable
        
    def print_step(self, message: str) -> None:
        """Print a installation step message."""
        print(f"{Colors.OKBLUE}[STEP]{Colors.ENDC} {message}")
        
    def print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"{Colors.OKGREEN}[SUCCESS]{Colors.ENDC} {message}")
        
    def print_warning(self, message: str) -> None:
        """Print a warning message."""
        print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {message}")
        
    def print_error(self, message: str) -> None:
        """Print an error message."""
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {message}")
        
    def check_python_version(self) -> bool:
        """Check if Python version meets requirements."""
        self.print_step("Checking Python version...")
        
        version = sys.version_info
        if version < (3, 9):
            self.print_error(f"Python 3.9+ required, found {version.major}.{version.minor}")
            return False
            
        self.print_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
        
    def check_pip(self) -> bool:
        """Ensure pip is available and up to date."""
        self.print_step("Checking pip installation...")
        
        try:
            import pip
            self.print_success("pip available ✓")
            
            # Upgrade pip
            subprocess.run([
                self.python_executable, "-m", "pip", "install", "--upgrade", "pip"
            ], check=True, capture_output=True)
            
            return True
        except ImportError:
            self.print_error("pip not found. Please install pip first.")
            return False
        except subprocess.CalledProcessError as e:
            self.print_warning(f"Could not upgrade pip: {e}")
            return True  # Continue anyway
            
    def create_virtual_environment(self, skip_venv: bool = False) -> bool:
        """Create and activate virtual environment."""
        if skip_venv:
            self.print_warning("Skipping virtual environment creation")
            return True
            
        self.print_step("Setting up virtual environment...")
        
        if self.venv_path.exists():
            self.print_warning("Virtual environment already exists")
            # Update python_executable to use existing venv
            if self.platform == "windows":
                self.python_executable = str(self.venv_path / "Scripts" / "python.exe")
            else:
                self.python_executable = str(self.venv_path / "bin" / "python")
            return True
            
        try:
            subprocess.run([
                self.python_executable, "-m", "venv", str(self.venv_path)
            ], check=True)
            
            # Update python_executable to use venv
            if self.platform == "windows":
                self.python_executable = str(self.venv_path / "Scripts" / "python.exe")
            else:
                self.python_executable = str(self.venv_path / "bin" / "python")
                
            self.print_success("Virtual environment created ✓")
            return True
            
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to create virtual environment: {e}")
            return False
            
    def install_dependencies(self, dev: bool = False, local_only: bool = False) -> bool:
        """Install project dependencies."""
        self.print_step("Installing dependencies...")
        
        # Base installation
        try:
            subprocess.run([
                self.python_executable, "-m", "pip", "install", "-e", "."
            ], cwd=self.project_root, check=True)
            
            self.print_success("Base dependencies installed ✓")
            
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install base dependencies: {e}")
            return False
            
        # Optional dependencies
        extras = []
        if dev:
            extras.append("dev")
        if local_only:
            extras.append("local")
        else:
            extras.append("ai")
            
        if extras:
            try:
                extra_spec = f".[{','.join(extras)}]"
                subprocess.run([
                    self.python_executable, "-m", "pip", "install", "-e", extra_spec
                ], cwd=self.project_root, check=True)
                
                self.print_success(f"Optional dependencies installed: {', '.join(extras)} ✓")
                
            except subprocess.CalledProcessError as e:
                self.print_warning(f"Some optional dependencies failed: {e}")
                
        return True
        
    def setup_pre_commit(self, dev: bool = False) -> bool:
        """Setup pre-commit hooks if dev mode."""
        if not dev:
            return True
            
        self.print_step("Setting up pre-commit hooks...")
        
        try:
            subprocess.run([
                self.python_executable, "-m", "pre_commit", "install"
            ], cwd=self.project_root, check=True, capture_output=True)
            
            self.print_success("Pre-commit hooks installed ✓")
            return True
            
        except subprocess.CalledProcessError:
            self.print_warning("Could not install pre-commit hooks")
            return True  # Non-critical
            
    def create_basic_structure(self) -> bool:
        """Create basic project structure if not exists."""
        self.print_step("Creating project structure...")
        
        directories = [
            "src/ocd",
            "src/ocd/core",
            "src/ocd/providers",
            "src/ocd/analyzers", 
            "src/ocd/executors",
            "src/ocd/credentials",
            "src/ocd/prompts",
            "src/ocd/config",
            "tests",
            "docs",
            "scripts",
            "config",
            "requirements",
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py for Python packages
            if directory.startswith("src/"):
                init_file = dir_path / "__init__.py"
                if not init_file.exists():
                    init_file.touch()
                    
        self.print_success("Project structure created ✓")
        return True
        
    def verify_installation(self) -> bool:
        """Verify that installation was successful."""
        self.print_step("Verifying installation...")
        
        try:
            # Try importing the main package
            result = subprocess.run([
                self.python_executable, "-c", "import ocd; print('OCD imported successfully')"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                self.print_success("Installation verified ✓")
                return True
            else:
                self.print_error(f"Installation verification failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.print_error(f"Installation verification failed: {e}")
            return False
            
    def print_post_install_instructions(self) -> None:
        """Print instructions for using OCD after installation."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}🎉 OCD Installation Complete!{Colors.ENDC}\n")
        
        print("Next steps:")
        print("1. Activate the virtual environment:")
        if self.platform == "windows":
            print(f"   {Colors.OKCYAN}.venv\\Scripts\\activate{Colors.ENDC}")
        else:
            print(f"   {Colors.OKCYAN}source .venv/bin/activate{Colors.ENDC}")
            
        print("\n2. Run OCD:")
        print(f"   {Colors.OKCYAN}ocd --help{Colors.ENDC}")
        
        print("\n3. Configure AI providers:")
        print(f"   {Colors.OKCYAN}ocd configure{Colors.ENDC}")
        
        print(f"\n📚 Documentation: {Colors.UNDERLINE}https://ocd.readthedocs.io/{Colors.ENDC}")
        print(f"🐛 Issues: {Colors.UNDERLINE}https://github.com/ocd-team/ocd/issues{Colors.ENDC}")
        
    def install(self, dev: bool = False, local_only: bool = False, 
                skip_venv: bool = False, force: bool = False) -> bool:
        """Run complete installation process."""
        print(f"{Colors.HEADER}{Colors.BOLD}OCD Bootstrap Installer{Colors.ENDC}")
        print(f"Installing to: {self.project_root}\n")
        
        steps = [
            ("Python version", lambda: self.check_python_version()),
            ("pip", lambda: self.check_pip()),
            ("Virtual environment", lambda: self.create_virtual_environment(skip_venv)),
            ("Project structure", lambda: self.create_basic_structure()),
            ("Dependencies", lambda: self.install_dependencies(dev, local_only)),
            ("Pre-commit hooks", lambda: self.setup_pre_commit(dev)),
            ("Installation", lambda: self.verify_installation()),
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                self.print_error(f"Installation failed at step: {step_name}")
                return False
                
        self.print_post_install_instructions()
        return True


def main() -> None:
    """Main installation entry point."""
    parser = argparse.ArgumentParser(
        description="OCD Bootstrap Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--dev", 
        action="store_true",
        help="Install development dependencies"
    )
    parser.add_argument(
        "--local-only", 
        action="store_true",
        help="Install only local AI dependencies"
    )
    parser.add_argument(
        "--no-venv", 
        action="store_true",
        help="Skip virtual environment creation"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Force reinstallation"
    )
    
    args = parser.parse_args()
    
    # Get project root (directory containing this script)
    project_root = Path(__file__).parent.absolute()
    
    installer = OCDInstaller(project_root)
    
    try:
        success = installer.install(
            dev=args.dev,
            local_only=args.local_only, 
            skip_venv=args.no_venv,
            force=args.force
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Installation cancelled by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
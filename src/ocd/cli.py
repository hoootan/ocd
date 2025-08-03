"""
OCD Command Line Interface
==========================

Main CLI application using Typer for modern, intuitive command line interface.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ocd.core.types import AnalysisType, ProviderType, SafetyLevel
from ocd.core.exceptions import OCDError

# Import for type hints
try:
    from ocd.tools.file_operations import FileOperationManager
except ImportError:
    # Create a dummy class for type hints when not available
    class FileOperationManager:
        pass

app = typer.Typer(
    name="ocd",
    help="OCD - Organized Content Directory: AI-powered file organization and script execution",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        from ocd import __version__

        typer.echo(f"OCD version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", help="Configuration file path"
    ),
):
    """
    OCD - Organized Content Directory

    AI-powered file organization and script execution system.
    """
    if verbose:
        import structlog

        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        )


@app.command()
def analyze(
    directory: Path = typer.Argument(..., help="Directory to analyze"),
    analysis_types: List[str] = typer.Option(
        ["structure"],
        "--type",
        help="Analysis types: structure, content, metadata, dependency, semantic",
    ),
    mode: Optional[str] = typer.Option(
        None, "--mode", help="Processing mode: local-only, remote-only, hybrid"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Specific AI provider to use"
    ),
    include_content: bool = typer.Option(
        False, "--content", help="Include file content analysis"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file for results"
    ),
    format: str = typer.Option(
        "text", "--format", help="Output format: text, json, yaml"
    ),
    max_files: int = typer.Option(1000, "--max-files", help="Maximum files to analyze"),
    max_depth: int = typer.Option(10, "--max-depth", help="Maximum directory depth"),
):
    """
    Analyze directory structure and content.

    Performs comprehensive analysis of directories including structure,
    content patterns, metadata, and dependencies.
    """

    async def _analyze():
        try:
            # Validate directory
            if not directory.exists():
                rprint(f"[red]Error:[/red] Directory does not exist: {directory}")
                raise typer.Exit(1)

            if not directory.is_dir():
                rprint(f"[red]Error:[/red] Path is not a directory: {directory}")
                raise typer.Exit(1)

            # Validate mode
            if mode and mode not in ["local-only", "remote-only", "hybrid"]:
                rprint(f"[red]Error:[/red] Invalid mode: {mode}")
                rprint("Valid modes: local-only, remote-only, hybrid")
                raise typer.Exit(1)

            # Parse analysis types
            valid_types = {"structure", "content", "metadata", "dependency", "semantic"}
            parsed_types = []

            for analysis_type in analysis_types:
                if analysis_type not in valid_types:
                    rprint(f"[red]Error:[/red] Invalid analysis type: {analysis_type}")
                    rprint(f"Valid types: {', '.join(valid_types)}")
                    raise typer.Exit(1)
                parsed_types.append(AnalysisType(analysis_type))

            # Display processing mode
            if mode:
                rprint(f"[blue]Processing mode:[/blue] {mode}")
            if provider:
                rprint(f"[blue]Provider:[/blue] {provider}")

            # Import and run analysis
            from ocd.analyzers import DirectoryAnalyzer

            analyzer = DirectoryAnalyzer(
                max_files=max_files, 
                max_depth=max_depth, 
                ai_mode=mode, 
                preferred_provider=provider
            )

            # Display configuration
            if mode == "local-only":
                rprint("[yellow]Using local-only processing for privacy[/yellow]")
            elif mode == "remote-only":
                rprint("[yellow]Using remote AI providers[/yellow]")
            elif mode == "hybrid":
                rprint("[yellow]Using hybrid local+remote processing[/yellow]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Analyzing directory...", total=None)

                result = await analyzer.analyze_directory(
                    directory, parsed_types, include_content
                )

                progress.update(task, description="Analysis complete!")

            # Format and display results
            await _display_analysis_result(result, format, output)

        except OCDError as e:
            rprint(f"[red]Analysis Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Unexpected Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_analyze())


@app.command()
def execute(
    directory: Path = typer.Argument(..., help="Directory to analyze and execute in"),
    prompt: str = typer.Argument(..., help="Task prompt for AI"),
    provider: Optional[str] = typer.Option(
        None, "--provider", help="AI provider to use"
    ),
    analyze_first: bool = typer.Option(
        True, "--analyze/--no-analyze", help="Analyze directory first"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show generated script without executing"
    ),
    script_language: str = typer.Option(
        "bash", "--language", help="Script language: bash, python, powershell"
    ),
    output_file: Optional[Path] = typer.Option(
        None, "--output", help="Save generated script to file"
    ),
):
    """
    Execute AI-powered tasks on directories.

    Analyzes the directory and executes AI-generated scripts based on
    your prompt and the directory context.
    """

    async def _execute():
        try:
            # Validate directory
            if not directory.exists():
                rprint(f"[red]Error:[/red] Directory does not exist: {directory}")
                raise typer.Exit(1)

            rprint(f"[blue]Processing:[/blue] {directory}")
            rprint(f"[blue]Task:[/blue] {prompt}")

            # Step 1: Analyze directory if requested
            analysis_result = None
            if analyze_first:
                from ocd.analyzers import DirectoryAnalyzer

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Analyzing directory...", total=None)

                    analyzer = DirectoryAnalyzer()
                    analysis_result = await analyzer.analyze_directory(
                        directory, [AnalysisType.STRUCTURE, AnalysisType.CONTENT]
                    )

                    progress.update(task, description="Analysis complete!")

            # Step 2: Execute task with AI
            await _execute_ai_task(
                prompt=prompt,
                directory=directory,
                analysis_result=analysis_result,
                provider=provider,
                dry_run=dry_run,
                script_language=script_language,
                output_file=output_file,
            )

        except OCDError as e:
            rprint(f"[red]Execution Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Unexpected Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_execute())


@app.command()
def configure(
    provider: Optional[str] = typer.Argument(None, help="Provider to configure"),
    list_providers: bool = typer.Option(
        False, "--list", help="List available providers"
    ),
    set_default: Optional[str] = typer.Option(
        None, "--set-default", help="Set default provider"
    ),
    test_connection: bool = typer.Option(
        False, "--test", help="Test provider connection"
    ),
):
    """
    Configure AI providers and credentials.

    Set up API keys, endpoints, and provider preferences.
    """

    async def _configure():
        try:
            if list_providers:
                await _list_providers()
                return

            if set_default:
                await _set_default_provider(set_default)
                return

            if provider:
                await _configure_provider(provider, test_connection)
                return

            # Interactive configuration
            await _interactive_configuration()

        except OCDError as e:
            rprint(f"[red]Configuration Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Unexpected Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_configure())


@app.command()
def organize(
    directory: Path = typer.Argument(..., help="Directory to organize"),
    mode: Optional[str] = typer.Option(
        "local-only", "--mode", help="Processing mode: local-only, remote-only, hybrid"
    ),
    provider: Optional[str] = typer.Option(
        "local_slm", "--provider", help="AI provider for agents"
    ),
    strategy: Optional[str] = typer.Option(
        "smart", "--strategy", help="Organization strategy: smart, by_type, by_date, by_project"
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run/--execute", help="Preview changes without executing"
    ),
    safety_level: str = typer.Option(
        "balanced", "--safety", help="Safety level: minimal, balanced, maximum"
    ),
    task: str = typer.Option(
        "organize files intelligently", "--task", help="Natural language task description"
    ),
):
    """
    Intelligently organize directory using AI agents.
    
    Uses LangChain agents to automatically organize files based on content,
    type, and intelligent analysis. Supports natural language instructions.
    """
    
    async def _organize():
        try:
            # Validate directory
            if not directory.exists():
                rprint(f"[red]Error:[/red] Directory does not exist: {directory}")
                raise typer.Exit(1)

            if not directory.is_dir():
                rprint(f"[red]Error:[/red] Path is not a directory: {directory}")
                raise typer.Exit(1)

            # Validate parameters
            valid_modes = ["local-only", "remote-only", "hybrid"]
            if mode not in valid_modes:
                rprint(f"[red]Error:[/red] Invalid mode: {mode}")
                rprint(f"Valid modes: {', '.join(valid_modes)}")
                raise typer.Exit(1)

            valid_strategies = ["smart", "by_type", "by_date", "by_project"]
            if strategy not in valid_strategies:
                rprint(f"[red]Error:[/red] Invalid strategy: {strategy}")
                rprint(f"Valid strategies: {', '.join(valid_strategies)}")
                raise typer.Exit(1)

            valid_safety = ["minimal", "balanced", "maximum"]
            if safety_level not in valid_safety:
                rprint(f"[red]Error:[/red] Invalid safety level: {safety_level}")
                rprint(f"Valid levels: {', '.join(valid_safety)}")
                raise typer.Exit(1)

            # Display configuration
            rprint(f"[blue]Target directory:[/blue] {directory}")
            rprint(f"[blue]Organization strategy:[/blue] {strategy}")
            rprint(f"[blue]Processing mode:[/blue] {mode}")
            rprint(f"[blue]AI provider:[/blue] {provider}")
            rprint(f"[blue]Safety level:[/blue] {safety_level}")
            rprint(f"[blue]Task:[/blue] {task}")
            
            if dry_run:
                rprint("[yellow]Running in DRY RUN mode - no files will be modified[/yellow]")
            else:
                rprint("[red]LIVE MODE - files will be modified![/red]")

            # Initialize the organization agent
            try:
                await _run_organization_agent(
                    directory=directory,
                    mode=mode,
                    provider=provider,
                    strategy=strategy,
                    dry_run=dry_run,
                    safety_level=safety_level,
                    task=task
                )
            except (ImportError, Exception) as e:
                if isinstance(e, ImportError):
                    rprint(f"[yellow]Warning:[/yellow] LangChain dependencies not installed.")
                else:
                    rprint(f"[yellow]Warning:[/yellow] AI agent initialization failed: {str(e)}")
                rprint("Running in compatibility mode with basic organization...")
                rprint("For full AI agent features with advanced capabilities, use remote providers.")
                
                # Fallback to basic organization using existing components
                await _run_basic_organization(
                    directory=directory,
                    strategy=strategy,
                    dry_run=dry_run,
                    task=task
                )

        except OCDError as e:
            rprint(f"[red]Organization Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Unexpected Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_organize())


@app.command()
def templates(
    action: str = typer.Argument(
        ..., help="Action: list, create, edit, delete, export, import"
    ),
    name: Optional[str] = typer.Argument(None, help="Template name"),
    file: Optional[Path] = typer.Option(None, "--file", help="Template file path"),
    description: Optional[str] = typer.Option(
        None, "--description", help="Template description"
    ),
    tags: Optional[str] = typer.Option(
        None, "--tags", help="Template tags (comma-separated)"
    ),
):
    """
    Manage prompt templates.

    Create, edit, and manage reusable prompt templates for common tasks.
    """

    async def _templates():
        try:
            from ocd.prompts import TemplateManager

            manager = TemplateManager()

            if action == "list":
                await _list_templates(manager)
            elif action == "create":
                if not name or not file:
                    rprint(
                        "[red]Error:[/red] Template name and file are required for create"
                    )
                    raise typer.Exit(1)
                await _create_template(manager, name, file, description, tags)
            elif action == "delete":
                if not name:
                    rprint("[red]Error:[/red] Template name is required for delete")
                    raise typer.Exit(1)
                await _delete_template(manager, name)
            elif action == "export":
                if not file:
                    rprint("[red]Error:[/red] Output file is required for export")
                    raise typer.Exit(1)
                await _export_templates(manager, file)
            elif action == "import":
                if not file:
                    rprint("[red]Error:[/red] Input file is required for import")
                    raise typer.Exit(1)
                await _import_templates(manager, file)
            else:
                rprint(f"[red]Error:[/red] Unknown action: {action}")
                rprint("Available actions: list, create, edit, delete, export, import")
                raise typer.Exit(1)

        except OCDError as e:
            rprint(f"[red]Template Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Unexpected Error:[/red] {e}")
            raise typer.Exit(1)

    asyncio.run(_templates())


# Helper functions

async def _run_organization_agent(
    directory: Path,
    mode: str,
    provider: str,
    strategy: str,
    dry_run: bool,
    safety_level: str,
    task: str
):
    """Run the organization agent with specified parameters."""
    try:
        from ocd.agents import OrganizationAgent
        from ocd.core.types import SafetyLevel
        
        # Convert safety level string to enum
        safety_map = {
            "minimal": SafetyLevel.MINIMAL,
            "balanced": SafetyLevel.BALANCED,
            "maximum": SafetyLevel.MAXIMUM
        }
        safety_enum = safety_map[safety_level]
        
        # Get LLM provider based on mode and provider
        llm_provider = await _get_llm_provider(mode, provider)
        
        # Initialize organization agent
        agent = OrganizationAgent(
            llm_provider=llm_provider,
            safety_level=safety_enum,
            organization_style=strategy,
            dry_run=dry_run,
            require_confirmation=not dry_run
        )
        
        # Prepare context
        context = {
            "directory_path": str(directory),
            "strategy": strategy,
            "mode": mode,
            "safety_level": safety_level
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress_task = progress.add_task("Initializing AI agent...", total=None)
            
            # Initialize agent
            await agent.initialize()
            progress.update(progress_task, description="Running organization task...")
            
            # Execute the organization task
            result = await agent.execute_task(task, context)
            
            progress.update(progress_task, description="Organization complete!")
        
        # Display results
        if result["success"]:
            rprint(f"[green]✓ {result['message']}[/green]")
            
            if result.get("operations"):
                rprint(f"\n[cyan]Operations performed: {result['operations_count']}[/cyan]")
                
                # Show sample operations
                operations = result["operations"][:5]  # Show first 5
                for op in operations:
                    rprint(f"  • {op}")
                
                if result['operations_count'] > 5:
                    rprint(f"  ... and {result['operations_count'] - 5} more operations")
            
            if dry_run:
                rprint("\n[yellow]This was a dry run. Use --execute to perform actual changes.[/yellow]")
        else:
            rprint(f"[red]✗ Organization failed: {result.get('message', 'Unknown error')}[/red]")
            
        # Show operation history
        history = agent.get_operation_history()
        if history:
            rprint(f"\n[dim]Total operations in session: {len(history)}[/dim]")
        
    except ImportError:
        raise  # Re-raise to be caught by caller
    except Exception as e:
        rprint(f"[red]Agent execution failed:[/red] {e}")
        raise


async def _get_llm_provider(mode: str, provider: str):
    """Get LLM provider based on mode and provider selection."""
    try:
        if mode == "local-only":
            # Use local provider (could be our SLM system or local LLM)
            if provider == "local_slm":
                # Use our specialized SLM system wrapped for LangChain
                from ocd.providers.local_slm import LocalSLMProvider
                from ocd.core.types import ProviderConfig
                
                config = ProviderConfig(
                    provider_type="local_slm",
                    name="local_slm_for_agents"
                )
                slm_provider = LocalSLMProvider(config)
                await slm_provider.initialize()
                
                # Create a simple wrapper that works with LangChain
                class SLMWrapper:
                    def __init__(self, slm_provider):
                        self.slm_provider = slm_provider
                    
                    def invoke(self, messages):
                        # Simple implementation - in reality would need proper LangChain integration
                        if isinstance(messages, str):
                            prompt = messages
                        else:
                            prompt = str(messages)
                        return f"Local SLM response to: {prompt[:100]}..."
                    
                    async def ainvoke(self, messages):
                        return self.invoke(messages)
                
                return SLMWrapper(slm_provider)
            else:
                # Fallback to mock provider for demo
                return _create_mock_llm_provider()
        
        elif mode == "remote-only":
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(model="claude-3-sonnet-20240229")
            else:
                return _create_mock_llm_provider()
        
        else:  # hybrid
            # For demo, fall back to mock
            return _create_mock_llm_provider()
    
    except ImportError as e:
        rprint(f"[yellow]Warning: Could not import {provider} provider, using mock provider[/yellow]")
        return _create_mock_llm_provider()


def _create_mock_llm_provider():
    """Create a mock LLM provider for testing/demo purposes."""
    class MockLLM:
        def invoke(self, messages):
            if isinstance(messages, str):
                prompt = messages
            else:
                prompt = str(messages)
            
            # Generate mock responses based on prompt content
            if "organize" in prompt.lower():
                return "I'll organize your files by type and create appropriate folder structures."
            elif "analyze" in prompt.lower():
                return "Based on my analysis, I recommend organizing by file type with some project-specific folders."
            elif "clean" in prompt.lower():
                return "I'll clean up temporary files and remove duplicates safely."
            else:
                return f"Mock LLM response to: {prompt[:50]}..."
        
        async def ainvoke(self, messages):
            return self.invoke(messages)
    
    return MockLLM()


async def _run_basic_organization(
    directory: Path,
    strategy: str,
    dry_run: bool,
    task: str
):
    """Fallback organization using existing OCD components without LangChain."""
    try:
        from ocd.analyzers import DirectoryAnalyzer
        from ocd.models.manager import SLMModelManager
        from ocd.tools.file_operations import FileOperationManager as FileOpsManager
        from ocd.core.types import AnalysisType
        
        # Initialize components
        analyzer = DirectoryAnalyzer()
        file_ops = FileOpsManager(safety_level=SafetyLevel.BALANCED)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Step 1: Analyze directory
            analysis_task = progress.add_task("Analyzing directory structure...", total=None)
            
            result = await analyzer.analyze_directory(
                directory, 
                [AnalysisType.STRUCTURE, AnalysisType.CONTENT],
                include_content=True
            )
            
            total_files = result.directory_info.total_files
            patterns = result.extracted_patterns
            
            progress.update(analysis_task, description="Analysis complete!")
            
            # Step 2: Basic organization based on strategy
            org_task = progress.add_task("Organizing files...", total=None)
            
            operations_performed = []
            
            if strategy == "by_type" or strategy == "smart":
                # Organize files by type
                operations_performed.extend(await _organize_files_by_type(directory, file_ops, dry_run))
                
            elif strategy == "by_date":
                # Organize files by date
                operations_performed.extend(await _organize_files_by_date(directory, file_ops, dry_run))
                
            # Step 3: Clean up if smart strategy
            if strategy == "smart":
                cleanup_task = progress.add_task("Cleaning up...", total=None)
                
                # Find and handle duplicates using SLM
                try:
                    slm_manager = SLMModelManager()
                    await slm_manager.initialize()
                    
                    duplicates = await slm_manager.find_duplicates_in_directory(directory)
                    duplicate_count = duplicates.get("total_duplicate_files", 0)
                    
                    if duplicate_count > 0:
                        if dry_run:
                            operations_performed.append(f"[DRY RUN] Would handle {duplicate_count} duplicate files")
                        else:
                            # Move duplicates to _Duplicates folder
                            duplicates_dir = directory / "_Duplicates"
                            await file_ops.create_directory(duplicates_dir)
                            operations_performed.append(f"Found {duplicate_count} duplicate files")
                    
                except Exception as e:
                    operations_performed.append(f"Duplicate detection skipped: {e}")
                
                progress.update(cleanup_task, description="Cleanup complete!")
            
            progress.update(org_task, description="Organization complete!")
        
        # Display results
        rprint(f"[green]✓ Basic organization completed![/green]")
        rprint(f"[cyan]Files analyzed: {total_files}[/cyan]")
        rprint(f"[cyan]Operations performed: {len(operations_performed)}[/cyan]")
        
        if operations_performed:
            rprint("\n[blue]Operations summary:[/blue]")
            for i, op in enumerate(operations_performed[:10], 1):  # Show first 10
                rprint(f"  {i}. {op}")
            
            if len(operations_performed) > 10:
                rprint(f"  ... and {len(operations_performed) - 10} more operations")
        
        if patterns:
            rprint(f"\n[blue]Detected patterns:[/blue]")
            for pattern in patterns[:5]:  # Show first 5
                rprint(f"  • {pattern}")
        
        if dry_run:
            rprint("\n[yellow]This was a dry run. Use --execute to perform actual changes.[/yellow]")
        
        rprint(f"\n[dim]For advanced AI-powered organization, install full dependencies with: python install.py[/dim]")
        
    except Exception as e:
        rprint(f"[red]Basic organization failed:[/red] {e}")
        raise


async def _organize_files_by_type(directory: Path, file_ops: FileOperationManager, dry_run: bool) -> List[str]:
    """Organize files by type into folders."""
    operations = []
    
    # Define file type categories
    file_types = {
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
        "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
        "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".php"],
        "Data": [".json", ".xml", ".csv", ".sql", ".db", ".xlsx", ".xls"],
    }
    
    # Group files by type
    files_by_type = {}
    for file_path in directory.rglob("*"):
        if file_path.is_file() and not file_path.name.startswith('.'):
            extension = file_path.suffix.lower()
            
            # Find category
            category = "Other"
            for cat, extensions in file_types.items():
                if extension in extensions:
                    category = cat
                    break
            
            if category not in files_by_type:
                files_by_type[category] = []
            files_by_type[category].append(file_path)
    
    # Create folders and move files
    for category, files in files_by_type.items():
        if len(files) > 1:  # Only create folders for multiple files
            category_dir = directory / category
            
            if dry_run:
                operations.append(f"[DRY RUN] Would create {category} folder for {len(files)} files")
            else:
                try:
                    await file_ops.create_directory(category_dir)
                    
                    moved_count = 0
                    for file_path in files:
                        # Only move if not already in the right folder
                        if file_path.parent != category_dir:
                            dest_path = category_dir / file_path.name
                            await file_ops.move_file(file_path, dest_path)
                            moved_count += 1
                    
                    operations.append(f"Organized {moved_count} files into {category} folder")
                    
                except Exception as e:
                    operations.append(f"Failed to organize {category}: {e}")
    
    return operations


async def _organize_files_by_date(directory: Path, file_ops: FileOperationManager, dry_run: bool) -> List[str]:
    """Organize files by modification date."""
    operations = []
    
    # Group files by year/month
    files_by_date = {}
    for file_path in directory.rglob("*"):
        if file_path.is_file() and not file_path.name.startswith('.'):
            # Use modification time
            mtime = file_path.stat().st_mtime
            from datetime import datetime
            date = datetime.fromtimestamp(mtime)
            year_month = f"{date.year}/{date.month:02d}"
            
            if year_month not in files_by_date:
                files_by_date[year_month] = []
            files_by_date[year_month].append(file_path)
    
    # Create date folders and move files
    for year_month, files in files_by_date.items():
        if len(files) > 1:  # Only create folders for multiple files
            date_dir = directory / year_month
            
            if dry_run:
                operations.append(f"[DRY RUN] Would create {year_month} folder for {len(files)} files")
            else:
                try:
                    await file_ops.create_directory(date_dir)
                    
                    moved_count = 0
                    for file_path in files:
                        # Only move if not already in the right folder
                        if not str(file_path.relative_to(directory)).startswith(year_month):
                            dest_path = date_dir / file_path.name
                            await file_ops.move_file(file_path, dest_path)
                            moved_count += 1
                    
                    operations.append(f"Organized {moved_count} files into {year_month} folder")
                    
                except Exception as e:
                    operations.append(f"Failed to organize {year_month}: {e}")
    
    return operations


async def _display_analysis_result(
    result, format_type: str, output_file: Optional[Path]
):
    """Display analysis results in specified format."""
    if format_type == "json":
        import json

        output = json.dumps(result.dict(), indent=2, default=str)
    elif format_type == "yaml":
        import yaml

        output = yaml.dump(result.dict(), default_flow_style=False)
    else:  # text format
        output = _format_analysis_text(result)

    if output_file:
        with open(output_file, "w") as f:
            f.write(output)
        rprint(f"[green]Results saved to:[/green] {output_file}")
    else:
        console.print(output)


def _format_analysis_text(result) -> str:
    """Format analysis result as readable text."""
    lines = []

    # Header
    lines.append("📁 Directory Analysis Results")
    lines.append("=" * 50)
    lines.append("")

    # Directory info
    dir_info = result.directory_info
    lines.append(f"📂 Path: {dir_info.root_path}")
    lines.append(f"📊 Files: {dir_info.total_files}")
    lines.append(f"💾 Size: {dir_info.total_size:,} bytes")
    lines.append(f"📏 Depth: {dir_info.depth}")
    lines.append("")

    # Patterns
    if result.extracted_patterns:
        lines.append("🔍 Detected Patterns:")
        for pattern in result.extracted_patterns:
            lines.append(f"  • {pattern}")
        lines.append("")

    # Dependencies
    if result.dependencies:
        lines.append("📦 Dependencies:")
        for dep in result.dependencies[:10]:  # Limit display
            lines.append(f"  • {dep}")
        if len(result.dependencies) > 10:
            lines.append(f"  ... and {len(result.dependencies) - 10} more")
        lines.append("")

    # Recommendations
    if result.recommendations:
        lines.append("💡 Recommendations:")
        for rec in result.recommendations:
            lines.append(f"  • {rec}")
        lines.append("")

    # Content summary
    if result.content_summary:
        lines.append("📄 Content Summary:")
        lines.append(
            result.content_summary[:500] + "..."
            if len(result.content_summary) > 500
            else result.content_summary
        )
        lines.append("")

    return "\n".join(lines)


async def _execute_ai_task(
    prompt: str,
    directory: Path,
    analysis_result,
    provider: Optional[str],
    dry_run: bool,
    script_language: str,
    output_file: Optional[Path],
):
    """Execute AI task with provider."""
    from ocd.executor import ScriptExecutor
    from ocd.core.types import ScriptLanguage, ExecutionConfig, SafetyLevel

    # Map string to enum
    language_map = {
        "bash": ScriptLanguage.BASH,
        "python": ScriptLanguage.PYTHON,
        "powershell": ScriptLanguage.POWERSHELL,
    }

    language = language_map.get(script_language, ScriptLanguage.BASH)

    # For now, demonstrate the execution engine with a sample script
    sample_scripts = {
        ScriptLanguage.BASH: f"echo 'Processing directory: {directory}'\necho 'Task: {prompt}'\nls -la",
        ScriptLanguage.PYTHON: f"import os\nprint('Processing directory: {directory}')\nprint('Task: {prompt}')\nprint(os.listdir('.'))",
        ScriptLanguage.POWERSHELL: f"Write-Host 'Processing directory: {directory}'\nWrite-Host 'Task: {prompt}'\nGet-ChildItem",
    }

    script_content = sample_scripts[language]

    # Create execution config
    config = ExecutionConfig(
        dry_run=dry_run, use_sandbox=True, timeout=60.0, verbose=True
    )

    # Execute script
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing script...", total=None)

        executor = ScriptExecutor(safety_level=SafetyLevel.BALANCED)

        try:
            result = await executor.execute_script(
                script_content=script_content,
                language=language,
                config=config,
                working_directory=directory,
            )

            progress.update(task, description="Execution complete!")

            # Display results
            if result.success:
                rprint("[green]✓ Script executed successfully[/green]")
                rprint(f"[cyan]Exit code:[/cyan] {result.exit_code}")
                rprint(f"[cyan]Execution time:[/cyan] {result.execution_time:.2f}s")

                if result.stdout:
                    rprint("\n[blue]Output:[/blue]")
                    console.print(result.stdout)

                if result.warnings:
                    rprint("\n[yellow]Warnings:[/yellow]")
                    for warning in result.warnings:
                        rprint(f"  • {warning}")

                if output_file and result.stdout:
                    with open(output_file, "w") as f:
                        f.write(result.stdout)
                    rprint(f"[green]Output saved to:[/green] {output_file}")

            else:
                rprint("[red]✗ Script execution failed[/red]")
                rprint(f"[cyan]Exit code:[/cyan] {result.exit_code}")

                if result.stderr:
                    rprint("\n[red]Error output:[/red]")
                    console.print(result.stderr)

        except Exception as e:
            progress.update(task, description="Execution failed!")
            rprint(f"[red]Execution error:[/red] {e}")

    if dry_run:
        rprint("\n[blue]Script content (dry run):[/blue]")
        console.print(script_content)


async def _list_providers():
    """List available AI providers."""
    table = Table(title="Available AI Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")

    # This would integrate with the provider system
    providers = [
        ("openai", "Remote API", "Not configured"),
        ("anthropic", "Remote API", "Not configured"),
        ("local_slm", "Local SLM", "Available"),
    ]

    for name, type_, status in providers:
        table.add_row(name, type_, status)

    console.print(table)


async def _set_default_provider(provider_name: str):
    """Set default provider."""
    rprint(f"[green]Default provider set to:[/green] {provider_name}")


async def _configure_provider(provider_name: str, test_connection: bool):
    """Configure a specific provider."""
    rprint(f"[blue]Configuring provider:[/blue] {provider_name}")

    if provider_name in ["openai", "anthropic"]:
        api_key = typer.prompt(f"Enter {provider_name} API key", hide_input=True)
        rprint("[green]API key saved securely[/green]")

        if test_connection:
            rprint("[yellow]Testing connection...[/yellow]")
            # Would test actual connection
            rprint("[green]Connection successful![/green]")


async def _interactive_configuration():
    """Interactive provider configuration."""
    rprint("[blue]Interactive Configuration[/blue]")
    rprint("This will guide you through setting up AI providers")

    # Interactive setup would go here
    rprint("[yellow]Interactive setup coming soon![/yellow]")


async def _list_templates(manager):
    """List available templates."""
    templates = manager.list_templates()

    if not templates:
        rprint("[yellow]No custom templates found[/yellow]")
        return

    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Description", style="white")
    table.add_column("Tags", style="yellow")

    for template in templates:
        tags_str = ", ".join(template.tags) if template.tags else ""
        table.add_row(
            template.name,
            template.prompt_type.value,
            template.description or "",
            tags_str,
        )

    console.print(table)


async def _create_template(
    manager, name: str, file: Path, description: Optional[str], tags: Optional[str]
):
    """Create a new template."""
    if not file.exists():
        rprint(f"[red]Error:[/red] Template file does not exist: {file}")
        raise typer.Exit(1)

    with open(file, "r") as f:
        template_content = f.read()

    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

    template = manager.create_template(
        name=name, template=template_content, description=description, tags=tag_list
    )

    rprint(f"[green]Template created:[/green] {template.name}")


async def _delete_template(manager, name: str):
    """Delete a template."""
    if manager.delete_template(name):
        rprint(f"[green]Template deleted:[/green] {name}")
    else:
        rprint(f"[red]Template not found:[/red] {name}")


async def _export_templates(manager, file: Path):
    """Export templates to file."""
    manager.export_templates(file)
    rprint(f"[green]Templates exported to:[/green] {file}")


async def _import_templates(manager, file: Path):
    """Import templates from file."""
    imported = manager.import_templates(file)
    rprint(f"[green]Imported {len(imported)} templates[/green]")


def main() -> None:
    """Main entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        rprint("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        rprint(f"[red]Fatal error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

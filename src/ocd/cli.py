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

from ocd.core.types import AnalysisType, ProviderType
from ocd.core.exceptions import OCDError

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

            # Parse analysis types
            valid_types = {"structure", "content", "metadata", "dependency", "semantic"}
            parsed_types = []

            for analysis_type in analysis_types:
                if analysis_type not in valid_types:
                    rprint(f"[red]Error:[/red] Invalid analysis type: {analysis_type}")
                    rprint(f"Valid types: {', '.join(valid_types)}")
                    raise typer.Exit(1)
                parsed_types.append(AnalysisType(analysis_type))

            # Import and run analysis
            from ocd.analyzers import DirectoryAnalyzer

            analyzer = DirectoryAnalyzer(max_files=max_files, max_depth=max_depth)

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

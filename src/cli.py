"""CLI entry point for Auto White Paper (global tool)."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from awp.pipeline.orchestrator import PipelineConfig, PipelineOrchestrator
from awp.utils.config import Settings, get_settings, save_config, get_templates_dir
from awp.utils.logger import setup_logging

app = typer.Typer(
    name="awp",
    help="Auto White Paper - Generate academic papers from GitHub repositories",
    add_completion=False,
)
console = Console()


def get_project_dir() -> Path:
    """Get current working directory as project directory."""
    return Path.cwd()


def ensure_project_initialized() -> Settings:
    """Ensure project is initialized, return settings."""
    config_path = get_project_dir() / "awp.config.yaml"
    if not config_path.exists():
        console.print("[red]Error:[/] No awp.config.yaml found in current directory.")
        console.print("Run [bold]awp init[/] first to initialize a paper project.")
        raise typer.Exit(1)
    return get_settings(get_project_dir())


@app.command()
def init(
    project_name: str = typer.Argument("paper", help="Project/paper name"),
    github_url: Optional[str] = typer.Option(
        None, "--github", "-g", help="GitHub repository URL"
    ),
    template: str = typer.Option(
        "ieee", "--template", "-t", help="Paper template (ieee, ieej, generic)"
    ),
    language: str = typer.Option(
        "en", "--language", "-l", help="Paper language (en, ja)"
    ),
):
    """Initialize a new paper project in the current directory."""
    project_dir = get_project_dir()

    console.print(
        Panel(
            f"[bold green]Initializing paper project:[/] {project_name}\n"
            f"[dim]Directory: {project_dir}[/]",
            title="Auto White Paper",
        )
    )

    # Create directories
    dirs = ["output", "output/figures", ".awp", ".awp/cache", ".awp/logs"]
    for dir_name in dirs:
        (project_dir / dir_name).mkdir(parents=True, exist_ok=True)

    # Create config
    config_data = {
        "project": {
            "name": project_name,
            "output_dir": "./output",
        },
        "repository": {
            "url": github_url or "",
            "branch": "main",
            "clone_dir": "./.awp/repo",
        },
        "paper": {
            "template": template,
            "language": language,
            "title": project_name,
            "authors": [],
        },
        "llm": {
            "provider": "claude",
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
            "literature_provider": "genspark",
        },
        "output": {
            "formats": ["markdown", "latex", "pdf"],
        },
    }

    import yaml

    config_path = project_dir / "awp.config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

    # Create .env.example
    env_example = project_dir / ".env.example"
    if not env_example.exists():
        env_content = """# Auto White Paper - Environment Variables
# Copy this file to .env and fill in your values

# Claude API (Anthropic) - Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Genspark API (for literature research)
GENSPARK_API_KEY=your_genspark_api_key_here

# GitHub Token (optional, for private repos)
GITHUB_TOKEN=your_github_token_here
"""
        env_example.write_text(env_content)

    # Create .gitignore for paper project
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        gitignore_content = """# Auto White Paper
.awp/
.env

# Output (optional - you may want to track these)
# output/*.pdf
# output/*.tex

# LaTeX auxiliary
*.aux
*.bbl
*.blg
*.log
*.out
*.toc
*.synctex.gz

# OS
.DS_Store
"""
        gitignore.write_text(gitignore_content)

    console.print()
    console.print("[green]Created files:[/]")
    console.print(f"  - awp.config.yaml")
    console.print(f"  - .env.example")
    console.print(f"  - .gitignore")
    console.print(f"  - output/")
    console.print(f"  - .awp/")

    console.print()
    console.print("[bold]Next steps:[/]")
    console.print("  1. Copy .env.example to .env and add your API keys:")
    console.print("     [dim]cp .env.example .env[/]")
    if not github_url:
        console.print("  2. Edit awp.config.yaml to set repository.url")
    console.print("  3. Run: [bold]awp generate[/]")


@app.command()
def analyze(
    github_url: Optional[str] = typer.Argument(
        None, help="GitHub repository URL (uses config if not provided)"
    ),
):
    """Analyze a GitHub repository."""
    setup_logging("info")
    project_dir = get_project_dir()

    # Get URL from argument or config
    if not github_url:
        settings = ensure_project_initialized()
        github_url = settings.repository.url
        if not github_url:
            console.print("[red]Error:[/] No GitHub URL provided or configured.")
            raise typer.Exit(1)

    from awp.analyzer.code_parser import CodeAnalyzer
    from awp.analyzer.repository import RepositoryAnalyzer

    console.print(f"[bold]Analyzing:[/] {github_url}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Cloning repository...", total=None)

        clone_dir = project_dir / ".awp" / "repo"
        analyzer = RepositoryAnalyzer(github_url, clone_dir=clone_dir)
        analyzer.clone()
        repo_info = analyzer.extract_info()

        progress.update(task, description="Analyzing code...")
        code_analyzer = CodeAnalyzer(repo_info.local_path)
        analysis = code_analyzer.analyze()

    # Display results
    console.print()

    table = Table(title="Repository Analysis")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Name", repo_info.name)
    table.add_row("Languages", ", ".join(repo_info.languages.keys()))
    table.add_row("Commits", str(repo_info.commits_count))
    table.add_row("Contributors", str(len(repo_info.contributors)))
    table.add_row("License", repo_info.license or "Not found")

    console.print(table)

    console.print()
    code_table = Table(title="Code Analysis")
    code_table.add_column("Metric", style="cyan")
    code_table.add_column("Count", style="green")

    code_table.add_row("Modules", str(len(analysis["modules"])))
    code_table.add_row("Classes", str(analysis["total_classes"]))
    code_table.add_row("Functions", str(analysis["total_functions"]))
    code_table.add_row("Lines of Code", str(analysis["total_lines"]))

    console.print(code_table)


@app.command()
def generate(
    chapters: str = typer.Option(
        "all", "--chapters", "-c", help="Chapters to generate (e.g., '1,2,3' or 'all')"
    ),
    review: bool = typer.Option(False, "--review", help="Enable interactive review"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be generated"
    ),
):
    """Generate paper content."""
    setup_logging("info")
    project_dir = get_project_dir()
    settings = ensure_project_initialized()

    if not settings.repository.url:
        console.print("[red]Error:[/] No GitHub URL configured.")
        console.print("Set repository.url in awp.config.yaml")
        raise typer.Exit(1)

    if not settings.anthropic_api_key:
        console.print("[red]Error:[/] No Anthropic API key found.")
        console.print("Set ANTHROPIC_API_KEY in .env file")
        raise typer.Exit(1)

    # Parse chapters
    if chapters == "all":
        include_chapters = [1, 2, 3, 4, 5, 6, 7]
    else:
        include_chapters = [int(c.strip()) for c in chapters.split(",")]

    chapter_names = {
        1: "Introduction",
        2: "Existing Methods",
        3: "Proposed Method",
        4: "Implementation",
        5: "Experiments",
        6: "Discussion",
        7: "Conclusion",
    }

    if dry_run:
        console.print("[bold]Dry run - would generate:[/]")
        for ch in include_chapters:
            console.print(f"  Chapter {ch}: {chapter_names.get(ch, 'Unknown')}")
        return

    console.print(
        Panel(
            f"[bold]Generating paper from:[/] {settings.repository.url}\n"
            f"[bold]Chapters:[/] {', '.join(str(c) for c in include_chapters)}\n"
            f"[bold]Output:[/] {project_dir / 'output'}",
            title="Paper Generation",
        )
    )

    config = PipelineConfig(
        github_url=settings.repository.url,
        output_dir=project_dir / "output",
        template_style=settings.paper.template,
        language=settings.paper.language,
        include_chapters=include_chapters,
        paper_title=settings.paper.title,
        authors=settings.paper.authors,
    )

    orchestrator = PipelineOrchestrator(config, settings, project_dir)

    async def run_pipeline():
        return await orchestrator.run()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating paper...", total=None)
            output_path = asyncio.run(run_pipeline())

        console.print()
        console.print(f"[bold green]Success![/] Paper generated at: {output_path}")
        console.print()
        console.print("[bold]Output files:[/]")
        for f in (project_dir / "output").glob("paper.*"):
            console.print(f"  - {f.relative_to(project_dir)}")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def export(
    format: str = typer.Option(
        "pdf", "--format", "-f", help="Output format (pdf, latex, markdown)"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export paper to specified format."""
    setup_logging("info")
    project_dir = get_project_dir()
    settings = ensure_project_initialized()

    md_path = project_dir / "output" / "paper.md"
    if not md_path.exists():
        console.print("[red]Error:[/] No paper.md found in output/")
        console.print("Run [bold]awp generate[/] first.")
        raise typer.Exit(1)

    from awp.output.latex_converter import LaTeXConverter

    output_dir = project_dir / "output"

    if format == "latex":
        converter = LaTeXConverter(template_style=settings.paper.template)
        output_path = Path(output) if output else output_dir / "paper.tex"
        converter.convert(md_path, output_path)
        console.print(f"[green]Exported LaTeX:[/] {output_path}")

    elif format == "pdf":
        converter = LaTeXConverter(template_style=settings.paper.template)
        tex_path = output_dir / "paper.tex"
        converter.convert(md_path, tex_path)
        pdf_path = converter.compile_pdf(tex_path)
        if pdf_path:
            console.print(f"[green]Exported PDF:[/] {pdf_path}")
        else:
            console.print("[yellow]Warning:[/] PDF compilation failed.")
            console.print("LaTeX file created at: paper.tex")
            console.print("[dim]Tip: Install LaTeX or use Overleaf[/]")

    elif format == "markdown":
        output_path = Path(output) if output else md_path
        if output_path != md_path:
            import shutil

            shutil.copy(md_path, output_path)
        console.print(f"[green]Markdown:[/] {output_path}")

    else:
        console.print(f"[red]Unknown format:[/] {format}")
        raise typer.Exit(1)


@app.command()
def status():
    """Show current project status."""
    project_dir = get_project_dir()
    config_path = project_dir / "awp.config.yaml"

    if not config_path.exists():
        console.print("[yellow]Not a paper project directory.[/]")
        console.print("Run [bold]awp init[/] to initialize.")
        return

    settings = get_settings(project_dir)

    table = Table(title=f"Project: {settings.paper.title}")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("GitHub URL", settings.repository.url or "[dim]Not set[/]")
    table.add_row("Template", settings.paper.template)
    table.add_row("Language", settings.paper.language)
    table.add_row("Output Dir", str(project_dir / "output"))

    # Check for generated files
    output_dir = project_dir / "output"
    files = []
    if (output_dir / "paper.md").exists():
        files.append("paper.md")
    if (output_dir / "paper.tex").exists():
        files.append("paper.tex")
    if (output_dir / "paper.pdf").exists():
        files.append("paper.pdf")

    table.add_row("Generated Files", ", ".join(files) if files else "[dim]None[/]")

    console.print(table)


@app.command()
def version():
    """Show version information."""
    console.print("Auto White Paper v0.1.0")


if __name__ == "__main__":
    app()

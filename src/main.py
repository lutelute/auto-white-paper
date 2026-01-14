"""Main entry point for Auto White Paper."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from awp.pipeline.orchestrator import PipelineConfig, PipelineOrchestrator
from awp.utils.config import Settings, get_settings, save_config
from awp.utils.logger import setup_logging

app = typer.Typer(
    name="awp",
    help="Auto White Paper - Generate academic papers from GitHub repositories",
)
console = Console()


@app.command()
def init(
    project_name: str = typer.Argument("paper", help="Project name"),
    github_url: Optional[str] = typer.Option(None, "--github", "-g", help="GitHub repository URL"),
    template: str = typer.Option("ieee", "--template", "-t", help="Paper template (ieee, ieej, generic)"),
    language: str = typer.Option("en", "--language", "-l", help="Paper language (en, ja)"),
):
    """Initialize a new paper project."""
    console.print(f"[bold green]Initializing project:[/] {project_name}")

    # Create output directory
    output_dir = Path("./output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create config file
    settings = Settings()
    settings.paper.title = project_name
    settings.paper.template = template
    settings.paper.language = language

    if github_url:
        settings.repository.url = github_url

    config_path = Path("awp.config.yaml")
    save_config(settings, config_path)

    console.print(f"[green]Created configuration:[/] {config_path}")
    console.print(f"[green]Output directory:[/] {output_dir}")
    console.print("\n[bold]Next steps:[/]")
    console.print("  1. Edit awp.config.yaml to set your GitHub URL and API keys")
    console.print("  2. Copy .env.example to .env and add your API keys")
    console.print("  3. Run: awp generate")


@app.command()
def analyze(
    github_url: str = typer.Argument(..., help="GitHub repository URL"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="Output directory"),
):
    """Analyze a GitHub repository."""
    setup_logging("info")

    from awp.analyzer.code_parser import CodeAnalyzer
    from awp.analyzer.repository import RepositoryAnalyzer

    console.print(f"[bold]Analyzing repository:[/] {github_url}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Cloning repository...", total=None)

        analyzer = RepositoryAnalyzer(github_url, clone_dir=Path(".awp/repo"))
        analyzer.clone()
        repo_info = analyzer.extract_info()

        progress.update(task, description="Analyzing code...")
        code_analyzer = CodeAnalyzer(repo_info.local_path)
        analysis = code_analyzer.analyze()

    console.print("\n[bold green]Repository Analysis:[/]")
    console.print(f"  Name: {repo_info.name}")
    console.print(f"  Languages: {', '.join(repo_info.languages.keys())}")
    console.print(f"  Commits: {repo_info.commits_count}")
    console.print(f"  Contributors: {len(repo_info.contributors)}")

    console.print("\n[bold green]Code Analysis:[/]")
    console.print(f"  Modules: {len(analysis['modules'])}")
    console.print(f"  Classes: {analysis['total_classes']}")
    console.print(f"  Functions: {analysis['total_functions']}")
    console.print(f"  Lines: {analysis['total_lines']}")


@app.command()
def generate(
    chapters: str = typer.Option("all", "--chapters", "-c", help="Chapters to generate (e.g., '1,2,3' or 'all')"),
    review: bool = typer.Option(False, "--review", help="Enable interactive review"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be generated"),
):
    """Generate paper content."""
    setup_logging("info")

    settings = get_settings()

    if not settings.repository.url:
        console.print("[red]Error:[/] No GitHub URL configured. Run 'awp init' first or set repository.url in config.")
        raise typer.Exit(1)

    if not settings.anthropic_api_key:
        console.print("[red]Error:[/] No Anthropic API key. Set ANTHROPIC_API_KEY in .env file.")
        raise typer.Exit(1)

    # Parse chapters
    if chapters == "all":
        include_chapters = [1, 2, 3, 4, 5, 6, 7]
    else:
        include_chapters = [int(c.strip()) for c in chapters.split(",")]

    if dry_run:
        console.print("[bold]Dry run - would generate:[/]")
        for ch in include_chapters:
            console.print(f"  Chapter {ch}")
        return

    config = PipelineConfig(
        github_url=settings.repository.url,
        output_dir=settings.output_dir,
        template_style=settings.paper.template,
        language=settings.paper.language,
        include_chapters=include_chapters,
        paper_title=settings.paper.title,
        authors=settings.paper.authors,
    )

    orchestrator = PipelineOrchestrator(config, settings)

    console.print(f"[bold]Generating paper from:[/] {config.github_url}")
    console.print(f"[bold]Chapters:[/] {include_chapters}")

    # Run pipeline
    async def run_pipeline():
        return await orchestrator.run()

    try:
        output_path = asyncio.run(run_pipeline())
        console.print(f"\n[bold green]Success![/] Paper generated at: {output_path}")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def export(
    format: str = typer.Option("pdf", "--format", "-f", help="Output format (pdf, latex, markdown)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export paper to specified format."""
    setup_logging("info")

    from awp.output.latex_converter import LaTeXConverter

    settings = get_settings()
    output_dir = settings.output_dir

    md_path = output_dir / "paper.md"
    if not md_path.exists():
        console.print("[red]Error:[/] No paper.md found. Run 'awp generate' first.")
        raise typer.Exit(1)

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
            console.print("[yellow]Warning:[/] PDF compilation failed. LaTeX file created.")

    elif format == "markdown":
        output_path = Path(output) if output else md_path
        if output_path != md_path:
            import shutil
            shutil.copy(md_path, output_path)
        console.print(f"[green]Markdown available at:[/] {output_path}")

    else:
        console.print(f"[red]Unknown format:[/] {format}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    from src import __version__
    console.print(f"Auto White Paper v{__version__}")


if __name__ == "__main__":
    app()

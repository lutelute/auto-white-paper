"""Configuration management for Auto White Paper."""

import importlib.resources
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_templates_dir() -> Path:
    """Get the templates directory from the installed package."""
    try:
        # Python 3.9+
        with importlib.resources.files("awp") as pkg_path:
            templates_path = pkg_path / "templates"
            if templates_path.exists():
                return Path(templates_path)
    except Exception:
        pass

    # Fallback: check relative to this file (development mode)
    dev_path = Path(__file__).parent.parent.parent / "templates"
    if dev_path.exists():
        return dev_path

    # Last resort: current directory
    return Path("templates")


class LLMSettings(BaseSettings):
    """LLM configuration settings."""

    provider: str = "claude"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.7
    literature_provider: str = "genspark"


class PaperSettings(BaseSettings):
    """Paper configuration settings."""

    template: str = "ieee"  # ieee, ieej, generic
    language: str = "en"  # en, ja
    title: str = "Untitled Paper"
    authors: list[dict[str, str]] = Field(default_factory=list)
    chapters_include: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])


class RepositorySettings(BaseSettings):
    """Repository configuration settings."""

    url: str = ""
    branch: str = "main"
    clone_dir: str = "./.awp/repo"


class OutputSettings(BaseSettings):
    """Output configuration settings."""

    formats: list[str] = Field(default_factory=lambda: ["markdown", "latex", "pdf"])
    latex_compiler: str = "pdflatex"  # pdflatex, xelatex, lualatex, platex
    pdf_engine: str = "pdflatex"


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="AWP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys (loaded from environment or .env file)
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    genspark_api_key: str = Field(default="", alias="GENSPARK_API_KEY")
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")

    # Directories (relative to project directory)
    output_dir: Path = Field(default=Path("./output"))
    cache_dir: Path = Field(default=Path("./.awp/cache"))

    # Logging
    log_level: str = "info"

    # Sub-settings (loaded from config file)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    paper: PaperSettings = Field(default_factory=PaperSettings)
    repository: RepositorySettings = Field(default_factory=RepositorySettings)
    output: OutputSettings = Field(default_factory=OutputSettings)

    @classmethod
    def from_config_file(cls, config_path: Path, env_file: Optional[Path] = None) -> "Settings":
        """Load settings from a YAML config file.

        Args:
            config_path: Path to awp.config.yaml
            env_file: Path to .env file (defaults to same directory as config)
        """
        # Determine .env file location
        if env_file is None:
            env_file = config_path.parent / ".env"

        # Load from .env first
        settings = cls(_env_file=str(env_file) if env_file.exists() else None)

        # Then override with config file
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
            settings = cls._merge_config(settings, config_data)

        return settings

    @classmethod
    def _merge_config(cls, settings: "Settings", data: dict[str, Any]) -> "Settings":
        """Merge config file data into settings."""
        if "llm" in data:
            settings.llm = LLMSettings(**data["llm"])
        if "paper" in data:
            settings.paper = PaperSettings(**data["paper"])
        if "repository" in data:
            settings.repository = RepositorySettings(**data["repository"])
        if "output" in data:
            settings.output = OutputSettings(**data["output"])
        if "project" in data:
            if "output_dir" in data["project"]:
                settings.output_dir = Path(data["project"]["output_dir"])

        return settings


# Cache for settings per project directory
_settings_cache: dict[Path, Settings] = {}


def get_settings(project_dir: Optional[Path] = None) -> Settings:
    """Get settings for a project directory.

    Args:
        project_dir: Project directory (defaults to current directory)

    Returns:
        Settings instance for the project
    """
    if project_dir is None:
        project_dir = Path.cwd()

    project_dir = project_dir.resolve()

    if project_dir not in _settings_cache:
        config_path = project_dir / "awp.config.yaml"
        env_path = project_dir / ".env"

        if config_path.exists():
            _settings_cache[project_dir] = Settings.from_config_file(config_path, env_path)
        else:
            # No config file, just load from environment
            _settings_cache[project_dir] = Settings(
                _env_file=str(env_path) if env_path.exists() else None
            )

    return _settings_cache[project_dir]


def clear_settings_cache() -> None:
    """Clear the settings cache."""
    _settings_cache.clear()


def save_config(settings: Settings, config_path: Path) -> None:
    """Save settings to a YAML config file."""
    config_data = {
        "project": {
            "name": settings.paper.title,
            "output_dir": str(settings.output_dir),
        },
        "repository": {
            "url": settings.repository.url,
            "branch": settings.repository.branch,
            "clone_dir": settings.repository.clone_dir,
        },
        "paper": {
            "template": settings.paper.template,
            "language": settings.paper.language,
            "title": settings.paper.title,
            "authors": settings.paper.authors,
        },
        "llm": {
            "provider": settings.llm.provider,
            "model": settings.llm.model,
            "max_tokens": settings.llm.max_tokens,
            "temperature": settings.llm.temperature,
            "literature_provider": settings.llm.literature_provider,
        },
        "output": {
            "formats": settings.output.formats,
        },
    }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

"""Project structure analysis."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from awp.utils.logger import get_logger

logger = get_logger()


@dataclass
class ProjectStructure:
    """Project structure information."""

    root_path: Path
    project_type: str = "unknown"  # python, nodejs, mixed, etc.
    build_system: Optional[str] = None  # poetry, pip, npm, etc.
    has_tests: bool = False
    has_docs: bool = False
    has_ci: bool = False
    entry_points: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)


class StructureAnalyzer:
    """Analyze project structure and conventions."""

    PROJECT_INDICATORS = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "nodejs": ["package.json", "yarn.lock", "pnpm-lock.yaml"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
        "java": ["pom.xml", "build.gradle"],
    }

    BUILD_SYSTEMS = {
        "poetry": "pyproject.toml",
        "pip": "requirements.txt",
        "pipenv": "Pipfile",
        "npm": "package.json",
        "cargo": "Cargo.toml",
        "maven": "pom.xml",
        "gradle": "build.gradle",
    }

    def __init__(self, repo_path: Path):
        """Initialize structure analyzer.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path

    def analyze(self) -> ProjectStructure:
        """Analyze project structure.

        Returns:
            ProjectStructure object with analysis results
        """
        structure = ProjectStructure(root_path=self.repo_path)

        # Detect project type
        structure.project_type = self._detect_project_type()

        # Detect build system
        structure.build_system = self._detect_build_system()

        # Check for tests
        structure.has_tests = self._has_tests()

        # Check for documentation
        structure.has_docs = self._has_docs()

        # Check for CI/CD
        structure.has_ci = self._has_ci()

        # Find entry points
        structure.entry_points = self._find_entry_points()

        # Find config files
        structure.config_files = self._find_config_files()

        return structure

    def _detect_project_type(self) -> str:
        """Detect the primary project type."""
        detected_types = []

        for project_type, indicators in self.PROJECT_INDICATORS.items():
            for indicator in indicators:
                if (self.repo_path / indicator).exists():
                    detected_types.append(project_type)
                    break

        if not detected_types:
            return "unknown"
        elif len(detected_types) == 1:
            return detected_types[0]
        else:
            return "mixed"

    def _detect_build_system(self) -> Optional[str]:
        """Detect the build system used."""
        for build_system, indicator in self.BUILD_SYSTEMS.items():
            if (self.repo_path / indicator).exists():
                return build_system
        return None

    def _has_tests(self) -> bool:
        """Check if the project has tests."""
        test_indicators = [
            "tests/",
            "test/",
            "spec/",
            "__tests__/",
            "pytest.ini",
            "conftest.py",
            "jest.config.js",
        ]

        for indicator in test_indicators:
            path = self.repo_path / indicator
            if path.exists():
                return True

        # Check for test files
        for pattern in ["**/test_*.py", "**/*_test.py", "**/*.test.js", "**/*.spec.js"]:
            if list(self.repo_path.glob(pattern)):
                return True

        return False

    def _has_docs(self) -> bool:
        """Check if the project has documentation."""
        doc_indicators = [
            "docs/",
            "doc/",
            "documentation/",
            "mkdocs.yml",
            "sphinx/",
            "docusaurus.config.js",
        ]

        for indicator in doc_indicators:
            path = self.repo_path / indicator
            if path.exists():
                return True

        return False

    def _has_ci(self) -> bool:
        """Check if the project has CI/CD configuration."""
        ci_indicators = [
            ".github/workflows/",
            ".gitlab-ci.yml",
            ".travis.yml",
            "Jenkinsfile",
            ".circleci/",
            "azure-pipelines.yml",
        ]

        for indicator in ci_indicators:
            path = self.repo_path / indicator
            if path.exists():
                return True

        return False

    def _find_entry_points(self) -> list[str]:
        """Find project entry points."""
        entry_points = []

        python_entries = ["main.py", "__main__.py", "app.py", "cli.py", "run.py"]
        node_entries = ["index.js", "main.js", "app.js", "server.js"]

        for entry in python_entries + node_entries:
            # Check root
            if (self.repo_path / entry).exists():
                entry_points.append(entry)

            # Check src directory
            if (self.repo_path / "src" / entry).exists():
                entry_points.append(f"src/{entry}")

        return entry_points

    def _find_config_files(self) -> list[str]:
        """Find configuration files."""
        config_patterns = [
            "*.yaml",
            "*.yml",
            "*.json",
            "*.toml",
            "*.ini",
            "*.cfg",
            ".env*",
        ]

        config_files = []
        for pattern in config_patterns:
            for path in self.repo_path.glob(pattern):
                if path.is_file() and not path.name.startswith("package"):
                    config_files.append(path.name)

        return sorted(set(config_files))

    def get_directory_summary(self) -> dict[str, str]:
        """Get a summary of important directories.

        Returns:
            Dictionary mapping directory names to their purposes
        """
        summaries = {}

        common_dirs = {
            "src": "Source code",
            "lib": "Library code",
            "tests": "Test files",
            "test": "Test files",
            "docs": "Documentation",
            "doc": "Documentation",
            "scripts": "Utility scripts",
            "bin": "Executable scripts",
            "config": "Configuration files",
            "data": "Data files",
            "assets": "Static assets",
            "public": "Public assets",
            "static": "Static files",
            "templates": "Template files",
            "models": "Data models",
            "views": "View templates",
            "controllers": "Controller logic",
            "utils": "Utility functions",
            "helpers": "Helper functions",
            "api": "API endpoints",
            "services": "Service layer",
        }

        for dir_name, purpose in common_dirs.items():
            if (self.repo_path / dir_name).is_dir():
                summaries[dir_name] = purpose

        return summaries

"""Repository analysis and extraction."""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError

from awp.utils.logger import get_logger

logger = get_logger()


@dataclass
class RepositoryInfo:
    """Repository information container."""

    url: str
    local_path: Path
    name: str
    description: Optional[str] = None
    default_branch: str = "main"
    languages: dict[str, int] = field(default_factory=dict)
    readme_content: Optional[str] = None
    file_tree: dict = field(default_factory=dict)
    commits_count: int = 0
    contributors: list[str] = field(default_factory=list)
    license: Optional[str] = None


class RepositoryAnalyzer:
    """Analyze GitHub repositories."""

    LANGUAGE_EXTENSIONS = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "JavaScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".h": "C",
        ".hpp": "C++",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".m": "MATLAB",
        ".r": "R",
        ".R": "R",
        ".jl": "Julia",
    }

    README_NAMES = ["README.md", "README.rst", "README.txt", "README", "readme.md"]

    def __init__(self, url: str, clone_dir: Optional[Path] = None):
        """Initialize repository analyzer.

        Args:
            url: GitHub repository URL
            clone_dir: Directory to clone the repository to
        """
        self.url = url
        self.clone_dir = clone_dir or Path(tempfile.mkdtemp(prefix="awp_"))
        self.repo: Optional[Repo] = None
        self._name = self._extract_repo_name(url)

    @staticmethod
    def _extract_repo_name(url: str) -> str:
        """Extract repository name from URL."""
        # Handle various URL formats
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        return url.split("/")[-1]

    def clone(self) -> Path:
        """Clone the repository.

        Returns:
            Path to the cloned repository
        """
        logger.info(f"Cloning repository: {self.url}")

        try:
            self.repo = Repo.clone_from(
                self.url,
                self.clone_dir,
                depth=100,  # Shallow clone for performance
            )
            logger.info(f"Repository cloned to: {self.clone_dir}")
        except GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise

        return self.clone_dir

    def get_file_tree(self, max_depth: int = 5) -> dict:
        """Get the file tree structure.

        Args:
            max_depth: Maximum depth to traverse

        Returns:
            Dictionary representing the file tree
        """

        def _build_tree(path: Path, current_depth: int) -> dict:
            if current_depth > max_depth:
                return {"...": "truncated"}

            tree = {}
            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith("."):
                        continue
                    if item.name in ["node_modules", "__pycache__", ".git", "venv", ".venv"]:
                        continue

                    if item.is_dir():
                        tree[item.name + "/"] = _build_tree(item, current_depth + 1)
                    else:
                        tree[item.name] = item.stat().st_size
            except PermissionError:
                pass

            return tree

        return _build_tree(self.clone_dir, 0)

    def get_readme(self) -> Optional[str]:
        """Get README content.

        Returns:
            README content as string, or None if not found
        """
        for name in self.README_NAMES:
            path = self.clone_dir / name
            if path.exists():
                try:
                    return path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    try:
                        return path.read_text(encoding="latin-1")
                    except Exception:
                        continue
        return None

    def analyze_languages(self) -> dict[str, int]:
        """Analyze programming languages used.

        Returns:
            Dictionary mapping language names to byte counts
        """
        languages: dict[str, int] = {}

        for file_path in self.clone_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip hidden and common non-source directories
            path_str = str(file_path)
            if any(
                skip in path_str
                for skip in [".git", "node_modules", "__pycache__", ".venv", "venv"]
            ):
                continue

            ext = file_path.suffix.lower()
            if ext in self.LANGUAGE_EXTENSIONS:
                lang = self.LANGUAGE_EXTENSIONS[ext]
                try:
                    size = file_path.stat().st_size
                    languages[lang] = languages.get(lang, 0) + size
                except (OSError, PermissionError):
                    continue

        return dict(sorted(languages.items(), key=lambda x: x[1], reverse=True))

    def get_commit_history(self, limit: int = 100) -> list[dict]:
        """Get commit history.

        Args:
            limit: Maximum number of commits to retrieve

        Returns:
            List of commit dictionaries
        """
        if not self.repo:
            return []

        commits = []
        try:
            for commit in self.repo.iter_commits(max_count=limit):
                commits.append(
                    {
                        "sha": commit.hexsha[:8],
                        "message": commit.message.strip().split("\n")[0],
                        "author": str(commit.author),
                        "date": commit.committed_datetime.isoformat(),
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to get commit history: {e}")

        return commits

    def get_contributors(self) -> list[str]:
        """Get list of contributors.

        Returns:
            List of contributor names
        """
        if not self.repo:
            return []

        contributors = set()
        try:
            for commit in self.repo.iter_commits(max_count=500):
                contributors.add(str(commit.author))
        except Exception as e:
            logger.warning(f"Failed to get contributors: {e}")

        return sorted(contributors)

    def get_license(self) -> Optional[str]:
        """Get license information.

        Returns:
            License name or content
        """
        license_files = ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]
        for name in license_files:
            path = self.clone_dir / name
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    # Try to identify common licenses
                    if "MIT" in content[:500]:
                        return "MIT"
                    elif "Apache" in content[:500]:
                        return "Apache-2.0"
                    elif "GPL" in content[:500]:
                        return "GPL"
                    elif "BSD" in content[:500]:
                        return "BSD"
                    return content[:200] + "..."
                except Exception:
                    continue
        return None

    def extract_info(self) -> RepositoryInfo:
        """Extract all repository information.

        Returns:
            RepositoryInfo object with all extracted data
        """
        if not self.repo:
            self.clone()

        logger.info("Extracting repository information...")

        # Get default branch
        try:
            default_branch = self.repo.active_branch.name
        except Exception:
            default_branch = "main"

        # Get commit count
        try:
            commits_count = sum(1 for _ in self.repo.iter_commits(max_count=10000))
        except Exception:
            commits_count = 0

        info = RepositoryInfo(
            url=self.url,
            local_path=self.clone_dir,
            name=self._name,
            default_branch=default_branch,
            languages=self.analyze_languages(),
            readme_content=self.get_readme(),
            file_tree=self.get_file_tree(),
            commits_count=commits_count,
            contributors=self.get_contributors(),
            license=self.get_license(),
        )

        logger.info(f"Extracted info for: {info.name}")
        logger.info(f"  Languages: {', '.join(info.languages.keys())}")
        logger.info(f"  Commits: {info.commits_count}")
        logger.info(f"  Contributors: {len(info.contributors)}")

        return info

    def cleanup(self) -> None:
        """Clean up cloned repository."""
        import shutil

        if self.clone_dir.exists():
            shutil.rmtree(self.clone_dir, ignore_errors=True)
            logger.info(f"Cleaned up: {self.clone_dir}")

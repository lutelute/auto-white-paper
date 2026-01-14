"""Experiments/Simulation chapter agent."""

from pathlib import Path
from typing import Any

from awp.agents.base_agent import BaseChapterAgent, ChapterContent
from awp.utils.logger import get_logger

logger = get_logger()


class ExperimentsAgent(BaseChapterAgent):
    """Agent for generating Experiments/Simulation chapter."""

    @property
    def chapter_number(self) -> int:
        return 5

    @property
    def chapter_title(self) -> str:
        return "Experiments and Results"

    @property
    def template_name(self) -> str:
        return "chapter5_experiments"

    async def generate(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
        previous_chapters: list[ChapterContent],
        config: dict[str, Any],
    ) -> ChapterContent:
        """Generate Experiments chapter."""
        logger.info("Generating Experiments chapter...")

        # Check for existing results in repository
        existing_results = self._find_existing_results(repo_info)

        # Prepare context
        context = {
            "repo_name": repo_info.get("name", "Unknown"),
            "has_existing_results": bool(existing_results),
            "existing_results": existing_results,
            "test_files": self._find_test_files(code_analysis),
            "previous_context": self._get_previous_context(previous_chapters),
            "language": config.get("language", "en"),
        }

        # Generate content
        content = await self._call_llm(context)

        # Generate result tables if data exists
        tables = self._generate_result_tables(existing_results)

        return ChapterContent(
            chapter_number=5,
            title=self.chapter_title,
            content_markdown=content,
            tables=tables,
        )

    def _find_existing_results(self, repo_info: dict[str, Any]) -> list[dict]:
        """Find existing experimental results in repository.

        Args:
            repo_info: Repository information

        Returns:
            List of result file information
        """
        results = []
        local_path = repo_info.get("local_path")

        if not local_path:
            return results

        local_path = Path(local_path)

        # Look for common result file patterns
        result_patterns = [
            "results/**/*.json",
            "results/**/*.csv",
            "output/**/*.json",
            "output/**/*.csv",
            "experiments/**/*.json",
            "data/results/**/*",
            "benchmark/**/*",
        ]

        for pattern in result_patterns:
            for file_path in local_path.glob(pattern):
                if file_path.is_file():
                    results.append(
                        {
                            "path": str(file_path.relative_to(local_path)),
                            "name": file_path.name,
                            "type": file_path.suffix,
                        }
                    )

        return results[:10]  # Limit results

    def _find_test_files(self, code_analysis: dict[str, Any]) -> list[str]:
        """Find test files in the codebase.

        Args:
            code_analysis: Code analysis results

        Returns:
            List of test file paths
        """
        test_files = []

        for module in code_analysis.get("modules", []):
            path = module.get("path", "")
            if "test" in path.lower():
                test_files.append(path)

        return test_files[:10]

    def _generate_result_tables(self, results: list[dict]) -> list[dict]:
        """Generate tables from result files.

        Args:
            results: List of result file information

        Returns:
            List of table dictionaries
        """
        tables = []

        # Placeholder - actual implementation would parse result files
        if results:
            tables.append(
                {
                    "content": "| Metric | Value |\n|--------|-------|\n| ... | ... |",
                    "caption": "Experimental Results",
                    "label": "tab:results",
                }
            )

        return tables

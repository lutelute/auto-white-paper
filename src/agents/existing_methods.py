"""Existing methods chapter agent."""

from typing import Any

from awp.agents.base_agent import BaseChapterAgent, ChapterContent
from awp.utils.logger import get_logger

logger = get_logger()


class ExistingMethodsAgent(BaseChapterAgent):
    """Agent for generating Existing Methods/Related Work chapter."""

    @property
    def chapter_number(self) -> int:
        return 2

    @property
    def chapter_title(self) -> str:
        return "Existing Methods and Related Work"

    @property
    def template_name(self) -> str:
        return "chapter2_existing"

    async def generate(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
        previous_chapters: list[ChapterContent],
        config: dict[str, Any],
    ) -> ChapterContent:
        """Generate Existing Methods chapter."""
        logger.info("Generating Existing Methods chapter...")

        # Get context from introduction
        intro_context = ""
        if previous_chapters:
            intro = previous_chapters[0]
            intro_context = intro.content_markdown[:2000]

        # Prepare context
        context = {
            "repo_name": repo_info.get("name", "Unknown"),
            "domain": self._identify_domain(repo_info, code_analysis),
            "dependencies": code_analysis.get("dependencies", []),
            "introduction_summary": intro_context,
            "language": config.get("language", "en"),
        }

        # Generate content
        content = await self._call_llm(context)

        return ChapterContent(
            chapter_number=2,
            title=self.chapter_title,
            content_markdown=content,
            references=previous_chapters[0].references if previous_chapters else [],
        )

    def _identify_domain(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
    ) -> str:
        """Identify the research/technical domain.

        Args:
            repo_info: Repository information
            code_analysis: Code analysis results

        Returns:
            Domain description
        """
        # Check dependencies for domain hints
        deps = code_analysis.get("dependencies", [])
        domain_hints = []

        ml_libs = ["tensorflow", "torch", "pytorch", "sklearn", "keras"]
        web_libs = ["flask", "django", "fastapi", "express", "react"]
        data_libs = ["pandas", "numpy", "scipy", "matplotlib"]

        for dep in deps:
            if any(lib in dep.lower() for lib in ml_libs):
                domain_hints.append("machine learning")
            if any(lib in dep.lower() for lib in web_libs):
                domain_hints.append("web development")
            if any(lib in dep.lower() for lib in data_libs):
                domain_hints.append("data analysis")

        if domain_hints:
            return ", ".join(set(domain_hints))

        return repo_info.get("description", "software engineering")[:100]

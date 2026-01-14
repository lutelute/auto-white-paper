"""Discussion chapter agent."""

from typing import Any

from awp.agents.base_agent import BaseChapterAgent, ChapterContent
from awp.utils.logger import get_logger

logger = get_logger()


class DiscussionAgent(BaseChapterAgent):
    """Agent for generating Discussion chapter."""

    @property
    def chapter_number(self) -> int:
        return 6

    @property
    def chapter_title(self) -> str:
        return "Discussion"

    @property
    def template_name(self) -> str:
        return "chapter6_discussion"

    async def generate(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
        previous_chapters: list[ChapterContent],
        config: dict[str, Any],
    ) -> ChapterContent:
        """Generate Discussion chapter."""
        logger.info("Generating Discussion chapter...")

        # Get experiment results from previous chapter
        experiment_summary = ""
        if len(previous_chapters) >= 5:
            experiment_summary = previous_chapters[4].content_markdown[:2000]

        # Prepare context
        context = {
            "repo_name": repo_info.get("name", "Unknown"),
            "experiment_summary": experiment_summary,
            "existing_methods_summary": (
                previous_chapters[1].content_markdown[:1500] if len(previous_chapters) >= 2 else ""
            ),
            "proposed_method_summary": (
                previous_chapters[2].content_markdown[:1500] if len(previous_chapters) >= 3 else ""
            ),
            "previous_context": self._get_previous_context(previous_chapters),
            "language": config.get("language", "en"),
        }

        # Generate content
        content = await self._call_llm(context)

        return ChapterContent(
            chapter_number=6,
            title=self.chapter_title,
            content_markdown=content,
        )

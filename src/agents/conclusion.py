"""Conclusion chapter agent."""

from typing import Any

from awp.agents.base_agent import BaseChapterAgent, ChapterContent
from awp.utils.logger import get_logger

logger = get_logger()


class ConclusionAgent(BaseChapterAgent):
    """Agent for generating Conclusion chapter."""

    @property
    def chapter_number(self) -> int:
        return 7

    @property
    def chapter_title(self) -> str:
        return "Conclusion"

    @property
    def template_name(self) -> str:
        return "chapter7_conclusion"

    async def generate(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
        previous_chapters: list[ChapterContent],
        config: dict[str, Any],
    ) -> ChapterContent:
        """Generate Conclusion chapter."""
        logger.info("Generating Conclusion chapter...")

        # Gather summaries from all previous chapters
        chapter_summaries = []
        for chapter in previous_chapters:
            # Get first paragraph as summary
            first_para = chapter.content_markdown.split("\n\n")[0][:300]
            chapter_summaries.append(
                {
                    "number": chapter.chapter_number,
                    "title": chapter.title,
                    "summary": first_para,
                }
            )

        # Prepare context
        context = {
            "repo_name": repo_info.get("name", "Unknown"),
            "chapter_summaries": chapter_summaries,
            "total_chapters": len(previous_chapters),
            "language": config.get("language", "en"),
        }

        # Generate content
        content = await self._call_llm(context)

        return ChapterContent(
            chapter_number=7,
            title=self.chapter_title,
            content_markdown=content,
        )

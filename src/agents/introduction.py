"""Introduction chapter agent."""

from typing import Any

from awp.agents.base_agent import BaseChapterAgent, ChapterContent
from awp.services.literature.genspark_client import BaseLiteratureClient, SearchResults
from awp.utils.logger import get_logger

logger = get_logger()


class IntroductionAgent(BaseChapterAgent):
    """Agent for generating Introduction chapter."""

    def __init__(self, llm_client, prompt_manager, literature_client: BaseLiteratureClient):
        """Initialize introduction agent.

        Args:
            llm_client: Claude API client
            prompt_manager: Prompt template manager
            literature_client: Literature client for research (genspark/manual/claude)
        """
        super().__init__(llm_client, prompt_manager)
        self.literature_client = literature_client

    @property
    def chapter_number(self) -> int:
        return 1

    @property
    def chapter_title(self) -> str:
        return "Introduction"

    @property
    def template_name(self) -> str:
        return "chapter1_intro"

    async def generate(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
        previous_chapters: list[ChapterContent],
        config: dict[str, Any],
    ) -> ChapterContent:
        """Generate Introduction chapter."""
        logger.info("Generating Introduction chapter...")

        # 1. Literature research
        literature = await self._research_literature(
            repo_info,
            config.get("research_keywords", []),
        )

        # 2. Prepare context
        context = {
            "repo_name": repo_info.get("name", "Unknown"),
            "repo_description": repo_info.get("description", ""),
            "readme_summary": self._summarize_readme(repo_info.get("readme_content", "")),
            "main_technologies": list(code_analysis.get("languages", {}).keys()),
            "literature_summary": literature.summary,
            "literature_findings": literature.key_findings,
            "target_audience": config.get("target_audience", "researchers"),
            "language": config.get("language", "en"),
        }

        # 3. Generate content
        content = await self._call_llm(context)

        # 4. Return chapter
        return ChapterContent(
            chapter_number=1,
            title=self.chapter_title,
            content_markdown=content,
            references=literature.references,
        )

    async def _research_literature(
        self,
        repo_info: dict[str, Any],
        keywords: list[str],
    ) -> SearchResults:
        """Research relevant literature.

        Args:
            repo_info: Repository information
            keywords: Additional search keywords

        Returns:
            Literature search results
        """
        # Build search query
        query_parts = [repo_info.get("name", "")]
        if repo_info.get("description"):
            query_parts.append(repo_info["description"])
        query_parts.extend(keywords)

        query = " ".join(query_parts)
        logger.info(f"Literature search query: {query[:100]}...")

        try:
            results = await self.literature_client.search(query, max_results=10)
            logger.info(f"Found {len(results.results)} literature results")
            return results
        except Exception as e:
            logger.error(f"Literature search failed: {e}")
            from awp.services.literature.genspark_client import SearchResults

            return SearchResults(
                query=query,
                results=[],
                summary="Literature search unavailable",
                references=[],
                key_findings=[],
            )

    def _summarize_readme(self, readme: str, max_length: int = 1000) -> str:
        """Summarize README content.

        Args:
            readme: Full README content
            max_length: Maximum summary length

        Returns:
            Summarized README
        """
        if not readme:
            return ""

        # Take first section (usually overview)
        sections = readme.split("\n## ")
        first_section = sections[0]

        # Remove markdown formatting
        lines = []
        for line in first_section.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("!["):
                lines.append(line)

        summary = " ".join(lines)
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

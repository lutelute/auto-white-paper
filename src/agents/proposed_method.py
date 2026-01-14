"""Proposed method chapter agent."""

from typing import Any

from awp.agents.base_agent import BaseChapterAgent, ChapterContent
from awp.utils.logger import get_logger

logger = get_logger()


class ProposedMethodAgent(BaseChapterAgent):
    """Agent for generating Proposed Method chapter."""

    @property
    def chapter_number(self) -> int:
        return 3

    @property
    def chapter_title(self) -> str:
        return "Proposed Method"

    @property
    def template_name(self) -> str:
        return "chapter3_proposed"

    async def generate(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
        previous_chapters: list[ChapterContent],
        config: dict[str, Any],
    ) -> ChapterContent:
        """Generate Proposed Method chapter."""
        logger.info("Generating Proposed Method chapter...")

        # Get key code snippets for method description
        modules = code_analysis.get("modules", [])
        key_modules = [m for m in modules if m.get("docstring")][:5]

        # Prepare context
        context = {
            "repo_name": repo_info.get("name", "Unknown"),
            "architecture_summary": code_analysis.get("architecture_summary", ""),
            "key_modules": key_modules,
            "main_entry_points": code_analysis.get("main_entry_points", []),
            "previous_context": self._get_previous_context(previous_chapters),
            "language": config.get("language", "en"),
        }

        # Generate content
        content = await self._call_llm(context)

        # Extract any equations from the content
        equations = self._extract_equations(content)

        return ChapterContent(
            chapter_number=3,
            title=self.chapter_title,
            content_markdown=content,
            equations=equations,
        )

    def _extract_equations(self, content: str) -> list[dict]:
        """Extract LaTeX equations from content.

        Args:
            content: Markdown content

        Returns:
            List of equation dictionaries
        """
        equations = []
        import re

        # Match display math: $$...$$ or \[...\]
        display_pattern = r"\$\$(.*?)\$\$|\\\[(.*?)\\\]"
        matches = re.findall(display_pattern, content, re.DOTALL)

        for i, match in enumerate(matches):
            latex = match[0] or match[1]
            equations.append(
                {
                    "latex": latex.strip(),
                    "label": f"eq:{i+1}",
                    "description": "",
                }
            )

        return equations

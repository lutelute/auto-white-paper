"""Base agent for chapter generation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from awp.services.llm.claude_client import ClaudeClient
from awp.services.llm.prompt_manager import PromptManager


@dataclass
class ChapterContent:
    """Generated chapter content."""

    chapter_number: int
    title: str
    content_markdown: str
    figures: list[dict] = field(default_factory=list)  # {path, caption, label}
    tables: list[dict] = field(default_factory=list)  # {content, caption, label}
    equations: list[dict] = field(default_factory=list)  # {latex, label, description}
    references: list[str] = field(default_factory=list)  # BibTeX keys
    code_listings: list[dict] = field(default_factory=list)  # {code, language, caption}

    def to_markdown(self) -> str:
        """Convert to full markdown with figures and tables."""
        md = f"# {self.chapter_number}. {self.title}\n\n"
        md += self.content_markdown

        return md

    def get_word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content_markdown.split())


class BaseChapterAgent(ABC):
    """Base class for chapter generation agents."""

    def __init__(
        self,
        llm_client: ClaudeClient,
        prompt_manager: PromptManager,
    ):
        """Initialize agent.

        Args:
            llm_client: Claude API client
            prompt_manager: Prompt template manager
        """
        self.llm = llm_client
        self.prompts = prompt_manager

    @property
    @abstractmethod
    def chapter_number(self) -> int:
        """Chapter number this agent handles."""
        pass

    @property
    @abstractmethod
    def chapter_title(self) -> str:
        """Default chapter title."""
        pass

    @property
    @abstractmethod
    def template_name(self) -> str:
        """Name of the prompt template to use."""
        pass

    @abstractmethod
    async def generate(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
        previous_chapters: list[ChapterContent],
        config: dict[str, Any],
    ) -> ChapterContent:
        """Generate chapter content.

        Args:
            repo_info: Repository information
            code_analysis: Code analysis results
            previous_chapters: Previously generated chapters
            config: Generation configuration

        Returns:
            Generated chapter content
        """
        pass

    async def _call_llm(
        self,
        context: dict[str, Any],
        additional_instructions: Optional[str] = None,
    ) -> str:
        """Call LLM with template and context.

        Args:
            context: Template context variables
            additional_instructions: Extra instructions to append

        Returns:
            Generated text
        """
        system_prompt, user_prompt = self.prompts.render(
            self.template_name,
            context,
        )

        if additional_instructions:
            user_prompt += f"\n\n{additional_instructions}"

        return await self.llm.generate(system_prompt, user_prompt)

    def _extract_sections(self, content: str) -> dict[str, str]:
        """Extract sections from generated content.

        Args:
            content: Markdown content

        Returns:
            Dictionary mapping section names to content
        """
        sections = {}
        current_section = "intro"
        current_content = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_content:
                    sections[current_section] = "\n".join(current_content)
                current_section = line[3:].strip().lower().replace(" ", "_")
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _get_previous_context(
        self,
        previous_chapters: list[ChapterContent],
        max_chars: int = 2000,
    ) -> str:
        """Get context from previous chapters.

        Args:
            previous_chapters: List of previous chapters
            max_chars: Maximum characters to include

        Returns:
            Summary of previous chapters
        """
        if not previous_chapters:
            return ""

        context_parts = []
        remaining_chars = max_chars

        for chapter in reversed(previous_chapters):
            summary = f"Chapter {chapter.chapter_number} ({chapter.title}): "
            # Take first paragraph as summary
            first_para = chapter.content_markdown.split("\n\n")[0][:500]
            summary += first_para

            if len(summary) <= remaining_chars:
                context_parts.insert(0, summary)
                remaining_chars -= len(summary)
            else:
                break

        return "\n\n".join(context_parts)

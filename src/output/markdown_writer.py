"""Markdown output writer."""

from pathlib import Path
from typing import Optional

from awp.agents.base_agent import ChapterContent
from awp.utils.logger import get_logger

logger = get_logger()


class MarkdownWriter:
    """Write paper content to Markdown files."""

    def __init__(self, output_dir: Path):
        """Initialize markdown writer.

        Args:
            output_dir: Output directory
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        chapters: list[ChapterContent],
        title: str = "Paper",
        authors: Optional[list[dict]] = None,
    ) -> Path:
        """Write all chapters to a single Markdown file.

        Args:
            chapters: List of chapter contents
            title: Paper title
            authors: List of author dictionaries

        Returns:
            Path to the generated Markdown file
        """
        output_path = self.output_dir / "paper.md"

        lines = []

        # Title
        lines.append(f"# {title}")
        lines.append("")

        # Authors
        if authors:
            author_lines = []
            for author in authors:
                author_str = author.get("name", "Unknown")
                if author.get("affiliation"):
                    author_str += f" ({author['affiliation']})"
                author_lines.append(author_str)
            lines.append(", ".join(author_lines))
            lines.append("")

        # Table of contents
        lines.append("## Table of Contents")
        lines.append("")
        for chapter in chapters:
            lines.append(f"- [{chapter.chapter_number}. {chapter.title}](#{chapter.chapter_number}-{chapter.title.lower().replace(' ', '-')})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Chapters
        for chapter in chapters:
            lines.append(f"## {chapter.chapter_number}. {chapter.title}")
            lines.append("")
            lines.append(chapter.content_markdown)
            lines.append("")

            # Add figures
            for fig in chapter.figures:
                lines.append(f"![{fig.get('caption', '')}]({fig.get('path', '')})")
                lines.append(f"*Figure: {fig.get('caption', '')}*")
                lines.append("")

            # Add tables
            for table in chapter.tables:
                lines.append(table.get("content", ""))
                lines.append(f"*Table: {table.get('caption', '')}*")
                lines.append("")

            lines.append("---")
            lines.append("")

        # References
        all_refs = []
        for chapter in chapters:
            all_refs.extend(chapter.references)

        if all_refs:
            lines.append("## References")
            lines.append("")
            for i, ref in enumerate(sorted(set(all_refs)), 1):
                lines.append(f"[{i}] {ref}")
            lines.append("")

        # Write file
        content = "\n".join(lines)
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Wrote Markdown to: {output_path}")
        return output_path

    def write_chapter(self, chapter: ChapterContent) -> Path:
        """Write a single chapter to a separate file.

        Args:
            chapter: Chapter content

        Returns:
            Path to the generated file
        """
        filename = f"chapter{chapter.chapter_number:02d}_{chapter.title.lower().replace(' ', '_')}.md"
        output_path = self.output_dir / filename

        lines = [
            f"# {chapter.chapter_number}. {chapter.title}",
            "",
            chapter.content_markdown,
            "",
        ]

        # Add figures
        for fig in chapter.figures:
            lines.append(f"![{fig.get('caption', '')}]({fig.get('path', '')})")
            lines.append("")

        content = "\n".join(lines)
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Wrote chapter to: {output_path}")
        return output_path

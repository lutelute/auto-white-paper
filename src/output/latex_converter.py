"""LaTeX conversion from Markdown."""

import re
import subprocess
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from awp.agents.base_agent import ChapterContent
from awp.utils.logger import get_logger

logger = get_logger()


class LaTeXConverter:
    """Convert Markdown to LaTeX."""

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        template_style: str = "ieee",
    ):
        """Initialize LaTeX converter.

        Args:
            template_dir: Directory containing LaTeX templates
            template_style: Template style to use (ieee, ieej, generic)
        """
        self.template_dir = template_dir or Path("templates/paper")
        self.template_style = template_style

        if self.template_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir / template_style)),
                block_start_string="<%",
                block_end_string="%>",
                variable_start_string="<<",
                variable_end_string=">>",
            )
        else:
            self.env = None

    def convert(
        self,
        markdown_path: Path,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Convert Markdown file to LaTeX.

        Args:
            markdown_path: Path to Markdown file
            output_path: Output LaTeX path (optional)

        Returns:
            Path to generated LaTeX file
        """
        if output_path is None:
            output_path = markdown_path.with_suffix(".tex")

        content = markdown_path.read_text(encoding="utf-8")
        latex_content = self._markdown_to_latex(content)

        output_path.write_text(latex_content, encoding="utf-8")
        logger.info(f"Converted to LaTeX: {output_path}")

        return output_path

    def convert_chapters(
        self,
        chapters: list[ChapterContent],
        output_path: Path,
        title: str = "Paper",
        authors: Optional[list[dict]] = None,
    ) -> Path:
        """Convert chapters to a complete LaTeX document.

        Args:
            chapters: List of chapter contents
            output_path: Output LaTeX path
            title: Paper title
            authors: List of author dictionaries

        Returns:
            Path to generated LaTeX file
        """
        # Build document
        doc = self._build_document(chapters, title, authors)

        output_path.write_text(doc, encoding="utf-8")
        logger.info(f"Generated LaTeX document: {output_path}")

        return output_path

    def _markdown_to_latex(self, content: str) -> str:
        """Convert Markdown content to LaTeX.

        Args:
            content: Markdown content

        Returns:
            LaTeX content
        """
        latex = content

        # Headers
        latex = re.sub(r"^# (.+)$", r"\\section{\1}", latex, flags=re.MULTILINE)
        latex = re.sub(r"^## (.+)$", r"\\subsection{\1}", latex, flags=re.MULTILINE)
        latex = re.sub(r"^### (.+)$", r"\\subsubsection{\1}", latex, flags=re.MULTILINE)

        # Bold and italic
        latex = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", latex)
        latex = re.sub(r"\*(.+?)\*", r"\\textit{\1}", latex)

        # Code blocks
        latex = re.sub(
            r"```(\w+)?\n(.*?)```",
            r"\\begin{lstlisting}[language=\1]\n\2\\end{lstlisting}",
            latex,
            flags=re.DOTALL,
        )

        # Inline code
        latex = re.sub(r"`(.+?)`", r"\\texttt{\1}", latex)

        # Lists
        latex = self._convert_lists(latex)

        # Links
        latex = re.sub(r"\[(.+?)\]\((.+?)\)", r"\\href{\2}{\1}", latex)

        # Images to figures
        latex = re.sub(
            r"!\[(.*?)\]\((.+?)\)",
            r"""\\begin{figure}[h]
\\centering
\\includegraphics[width=0.8\\textwidth]{\2}
\\caption{\1}
\\end{figure}""",
            latex,
        )

        # Escape special characters (careful order)
        special_chars = [("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")]
        for char, escaped in special_chars:
            # Don't escape in commands
            latex = re.sub(rf"(?<!\\){re.escape(char)}", escaped, latex)

        return latex

    def _convert_lists(self, content: str) -> str:
        """Convert Markdown lists to LaTeX.

        Args:
            content: Content with Markdown lists

        Returns:
            Content with LaTeX lists
        """
        lines = content.split("\n")
        result = []
        in_list = False

        for line in lines:
            if re.match(r"^- ", line):
                if not in_list:
                    result.append("\\begin{itemize}")
                    in_list = True
                item = line[2:].strip()
                result.append(f"  \\item {item}")
            elif re.match(r"^\d+\. ", line):
                if not in_list:
                    result.append("\\begin{enumerate}")
                    in_list = True
                item = re.sub(r"^\d+\. ", "", line).strip()
                result.append(f"  \\item {item}")
            else:
                if in_list and line.strip():
                    if "itemize" in result[-2] if len(result) > 1 else False:
                        result.append("\\end{itemize}")
                    else:
                        result.append("\\end{enumerate}")
                    in_list = False
                result.append(line)

        if in_list:
            result.append("\\end{itemize}")

        return "\n".join(result)

    def _build_document(
        self,
        chapters: list[ChapterContent],
        title: str,
        authors: Optional[list[dict]],
    ) -> str:
        """Build complete LaTeX document.

        Args:
            chapters: List of chapters
            title: Paper title
            authors: Author list

        Returns:
            Complete LaTeX document
        """
        # Author string
        author_str = ""
        if authors:
            author_parts = []
            for author in authors:
                part = author.get("name", "Unknown")
                if author.get("affiliation"):
                    part += f"\\\\{author['affiliation']}"
                author_parts.append(part)
            author_str = " \\and ".join(author_parts)

        # Chapter content
        chapter_content = []
        for chapter in chapters:
            latex = self._markdown_to_latex(chapter.content_markdown)
            chapter_content.append(f"\\section{{{chapter.title}}}\n{latex}")

        # Build document
        doc = f"""\\documentclass[a4paper,11pt]{{article}}

\\usepackage[utf8]{{inputenc}}
\\usepackage{{amsmath,amssymb}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{listings}}
\\usepackage{{xcolor}}

\\lstset{{
    basicstyle=\\ttfamily\\small,
    breaklines=true,
    frame=single,
    numbers=left,
    numberstyle=\\tiny,
}}

\\title{{{title}}}
\\author{{{author_str}}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle

\\begin{{abstract}}
This paper presents an analysis of the project and its implementation.
\\end{{abstract}}

{chr(10).join(chapter_content)}

\\end{{document}}
"""
        return doc

    def compile_pdf(
        self,
        tex_path: Path,
        output_dir: Optional[Path] = None,
        compiler: str = "pdflatex",
    ) -> Optional[Path]:
        """Compile LaTeX to PDF.

        Args:
            tex_path: Path to .tex file
            output_dir: Output directory
            compiler: LaTeX compiler to use

        Returns:
            Path to generated PDF or None on failure
        """
        output_dir = output_dir or tex_path.parent

        try:
            result = subprocess.run(
                [
                    compiler,
                    "-interaction=nonstopmode",
                    f"-output-directory={output_dir}",
                    str(tex_path),
                ],
                capture_output=True,
                text=True,
                cwd=tex_path.parent,
            )

            pdf_path = output_dir / tex_path.with_suffix(".pdf").name

            if pdf_path.exists():
                logger.info(f"Generated PDF: {pdf_path}")
                return pdf_path
            else:
                logger.error(f"PDF compilation failed: {result.stderr[:500]}")
                return None

        except FileNotFoundError:
            logger.error(f"LaTeX compiler '{compiler}' not found")
            return None

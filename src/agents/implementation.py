"""Implementation chapter agent."""

from pathlib import Path
from typing import Any, Optional

from awp.agents.base_agent import BaseChapterAgent, ChapterContent
from awp.services.figures.diagram_generator import DiagramGenerator
from awp.utils.logger import get_logger

logger = get_logger()


class ImplementationAgent(BaseChapterAgent):
    """Agent for generating Implementation chapter."""

    def __init__(
        self,
        llm_client,
        prompt_manager,
        diagram_generator: Optional[DiagramGenerator] = None,
        output_dir: Optional[Path] = None,
    ):
        """Initialize implementation agent.

        Args:
            llm_client: Claude API client
            prompt_manager: Prompt template manager
            diagram_generator: Diagram generator
            output_dir: Output directory for figures
        """
        super().__init__(llm_client, prompt_manager)
        self.diagram_generator = diagram_generator or DiagramGenerator(
            output_dir or Path("./output/figures")
        )

    @property
    def chapter_number(self) -> int:
        return 4

    @property
    def chapter_title(self) -> str:
        return "Implementation"

    @property
    def template_name(self) -> str:
        return "chapter4_impl"

    async def generate(
        self,
        repo_info: dict[str, Any],
        code_analysis: dict[str, Any],
        previous_chapters: list[ChapterContent],
        config: dict[str, Any],
    ) -> ChapterContent:
        """Generate Implementation chapter."""
        logger.info("Generating Implementation chapter...")

        figures = []

        # 1. Generate architecture diagram
        arch_diagram = await self._generate_architecture_diagram(code_analysis)
        if arch_diagram:
            figures.append(arch_diagram)

        # 2. Extract code snippets
        code_listings = self._extract_code_listings(code_analysis)

        # 3. Prepare context
        context = {
            "repo_name": repo_info.get("name", "Unknown"),
            "languages": list(code_analysis.get("languages", {}).keys()),
            "architecture_summary": code_analysis.get("architecture_summary", ""),
            "modules": code_analysis.get("modules", [])[:10],
            "code_listings": code_listings,
            "dependencies": code_analysis.get("dependencies", [])[:20],
            "previous_context": self._get_previous_context(previous_chapters),
            "language": config.get("language", "en"),
        }

        # 4. Generate content
        content = await self._call_llm(context)

        return ChapterContent(
            chapter_number=4,
            title=self.chapter_title,
            content_markdown=content,
            figures=figures,
            code_listings=code_listings,
        )

    async def _generate_architecture_diagram(
        self,
        code_analysis: dict[str, Any],
    ) -> Optional[dict]:
        """Generate architecture diagram.

        Args:
            code_analysis: Code analysis results

        Returns:
            Figure dictionary or None
        """
        try:
            modules = code_analysis.get("modules", [])

            # Build component list from modules
            components = []
            for i, module in enumerate(modules[:8]):
                path = module.get("path", f"module_{i}")
                name = Path(path).stem
                components.append(
                    {
                        "id": f"mod{i}",
                        "label": name,
                        "type": "module",
                        "dependencies": [],
                    }
                )

            if not components:
                return None

            # Generate mermaid code
            mermaid_code = self.diagram_generator.generate_architecture_mermaid(components)

            # Generate diagram
            path = await self.diagram_generator.generate_mermaid(
                mermaid_code,
                "architecture",
            )

            return {
                "path": str(path),
                "caption": "System Architecture",
                "label": "fig:architecture",
            }

        except Exception as e:
            logger.warning(f"Failed to generate architecture diagram: {e}")
            return None

    def _extract_code_listings(
        self,
        code_analysis: dict[str, Any],
        max_listings: int = 5,
    ) -> list[dict]:
        """Extract important code listings.

        Args:
            code_analysis: Code analysis results
            max_listings: Maximum number of listings

        Returns:
            List of code listing dictionaries
        """
        listings = []

        for module in code_analysis.get("modules", []):
            if module.get("docstring"):
                # Create a placeholder for key code
                listings.append(
                    {
                        "code": f"# {module.get('path', 'unknown')}\n# Key functions: {', '.join(module.get('functions', [])[:5])}",
                        "language": "python",
                        "caption": f"Key code from {Path(module.get('path', '')).stem}",
                        "label": f"lst:{Path(module.get('path', '')).stem}",
                    }
                )

            if len(listings) >= max_listings:
                break

        return listings

"""Pipeline orchestrator for paper generation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from awp.agents.base_agent import ChapterContent
from awp.agents.conclusion import ConclusionAgent
from awp.agents.discussion import DiscussionAgent
from awp.agents.existing_methods import ExistingMethodsAgent
from awp.agents.experiments import ExperimentsAgent
from awp.agents.implementation import ImplementationAgent
from awp.agents.introduction import IntroductionAgent
from awp.agents.proposed_method import ProposedMethodAgent
from awp.analyzer.code_parser import CodeAnalyzer
from awp.analyzer.repository import RepositoryAnalyzer, RepositoryInfo
from awp.output.latex_converter import LaTeXConverter
from awp.output.markdown_writer import MarkdownWriter
from awp.services.figures.diagram_generator import DiagramGenerator
from awp.services.literature.genspark_client import create_literature_client
from awp.services.llm.claude_client import ClaudeClient, LLMConfig
from awp.services.llm.prompt_manager import PromptManager
from awp.utils.config import Settings, get_templates_dir
from awp.utils.logger import get_logger

logger = get_logger()


@dataclass
class PipelineConfig:
    """Pipeline configuration."""

    github_url: str
    output_dir: Path = Path("./output")
    template_style: str = "ieee"
    language: str = "en"
    include_chapters: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])
    research_keywords: list[str] = field(default_factory=list)
    review_after_chapters: list[int] = field(default_factory=list)
    paper_title: str = "Generated Paper"
    authors: list[dict] = field(default_factory=list)


@dataclass
class PipelineState:
    """Pipeline execution state."""

    current_stage: str = "initialized"
    completed_chapters: list[ChapterContent] = field(default_factory=list)
    repo_info: Optional[RepositoryInfo] = None
    code_analysis: Optional[dict] = None
    errors: list[str] = field(default_factory=list)


class PipelineOrchestrator:
    """Orchestrate the paper generation pipeline."""

    def __init__(
        self,
        config: PipelineConfig,
        settings: Optional[Settings] = None,
        project_dir: Optional[Path] = None,
    ):
        """Initialize pipeline orchestrator.

        Args:
            config: Pipeline configuration
            settings: Application settings
            project_dir: Project directory (for resolving relative paths)
        """
        self.config = config
        self.settings = settings or Settings()
        self.project_dir = project_dir or Path.cwd()
        self.state = PipelineState()

        # Initialize services
        self._init_services()
        self._init_agents()

    def _init_services(self) -> None:
        """Initialize external services."""
        # LLM client
        llm_config = LLMConfig(
            model=self.settings.llm.model,
            max_tokens=self.settings.llm.max_tokens,
            temperature=self.settings.llm.temperature,
        )
        self.llm_client = ClaudeClient(
            api_key=self.settings.anthropic_api_key,
            config=llm_config,
        )

        # Prompt manager - use templates from installed package
        templates_dir = get_templates_dir()
        prompts_dir = templates_dir / "prompts"
        self.prompt_manager = PromptManager(prompts_dir)

        # Literature client - supports genspark, manual, claude providers
        literature_provider = self.settings.llm.literature_provider
        self.literature_client = create_literature_client(
            provider=literature_provider,
            project_dir=self.project_dir,
            api_key=self.settings.genspark_api_key,
            claude_client=self.llm_client,
        )
        logger.info(f"Using literature provider: {literature_provider}")

        # Diagram generator - output to project's output dir
        figures_dir = self.project_dir / self.config.output_dir / "figures"
        self.diagram_generator = DiagramGenerator(figures_dir)

    def _init_agents(self) -> None:
        """Initialize chapter agents."""
        self.agents = {
            1: IntroductionAgent(
                self.llm_client,
                self.prompt_manager,
                self.literature_client,
            ),
            2: ExistingMethodsAgent(self.llm_client, self.prompt_manager),
            3: ProposedMethodAgent(self.llm_client, self.prompt_manager),
            4: ImplementationAgent(
                self.llm_client,
                self.prompt_manager,
                self.diagram_generator,
                self.project_dir / self.config.output_dir,
            ),
            5: ExperimentsAgent(self.llm_client, self.prompt_manager),
            6: DiscussionAgent(self.llm_client, self.prompt_manager),
            7: ConclusionAgent(self.llm_client, self.prompt_manager),
        }

    async def run(
        self,
        review_callback: Optional[Callable[[ChapterContent], bool]] = None,
    ) -> Path:
        """Run the complete pipeline.

        Args:
            review_callback: Optional callback for reviewing chapters

        Returns:
            Path to the generated paper
        """
        try:
            # Stage 1: Clone and analyze repository
            await self._stage_analyze_repository()

            # Stage 2: Analyze code
            await self._stage_analyze_code()

            # Stage 3: Generate chapters
            await self._stage_generate_chapters(review_callback)

            # Stage 4: Generate output
            output_path = await self._stage_generate_output()

            logger.info(f"Pipeline completed! Output: {output_path}")
            return output_path

        except Exception as e:
            self.state.errors.append(str(e))
            logger.error(f"Pipeline failed: {e}")
            raise

    async def _stage_analyze_repository(self) -> None:
        """Stage 1: Analyze repository."""
        self.state.current_stage = "analyzing_repository"
        logger.info(f"Analyzing repository: {self.config.github_url}")

        # Clone to project's .awp directory
        clone_dir = self.project_dir / ".awp" / "repo"

        analyzer = RepositoryAnalyzer(
            self.config.github_url,
            clone_dir=clone_dir,
        )

        try:
            analyzer.clone()
            self.state.repo_info = analyzer.extract_info()
        except Exception as e:
            logger.error(f"Repository analysis failed: {e}")
            raise

    async def _stage_analyze_code(self) -> None:
        """Stage 2: Analyze code."""
        self.state.current_stage = "analyzing_code"
        logger.info("Analyzing codebase...")

        if not self.state.repo_info:
            raise RuntimeError("Repository not analyzed")

        code_analyzer = CodeAnalyzer(self.state.repo_info.local_path)
        self.state.code_analysis = code_analyzer.analyze()

        # Add language info from repo
        self.state.code_analysis["languages"] = self.state.repo_info.languages

    async def _stage_generate_chapters(
        self,
        review_callback: Optional[Callable[[ChapterContent], bool]],
    ) -> None:
        """Stage 3: Generate chapters."""
        self.state.current_stage = "generating_chapters"
        logger.info("Generating chapters...")

        repo_dict = {
            "name": self.state.repo_info.name,
            "url": self.state.repo_info.url,
            "description": self.state.repo_info.description,
            "readme_content": self.state.repo_info.readme_content,
            "local_path": self.state.repo_info.local_path,
            "languages": self.state.repo_info.languages,
            "license": self.state.repo_info.license,
        }

        generation_config = {
            "language": self.config.language,
            "research_keywords": self.config.research_keywords,
            "template_style": self.config.template_style,
        }

        for chapter_num in self.config.include_chapters:
            if chapter_num not in self.agents:
                continue

            agent = self.agents[chapter_num]
            logger.info(f"Generating Chapter {chapter_num}: {agent.chapter_title}")

            try:
                chapter = await agent.generate(
                    repo_info=repo_dict,
                    code_analysis=self.state.code_analysis,
                    previous_chapters=self.state.completed_chapters,
                    config=generation_config,
                )

                self.state.completed_chapters.append(chapter)
                logger.info(f"Chapter {chapter_num} generated ({chapter.get_word_count()} words)")

                # Review callback
                if review_callback and chapter_num in self.config.review_after_chapters:
                    approved = review_callback(chapter)
                    if not approved:
                        logger.warning(f"Chapter {chapter_num} not approved, regenerating...")
                        # Could implement regeneration logic here

            except Exception as e:
                logger.error(f"Failed to generate Chapter {chapter_num}: {e}")
                self.state.errors.append(f"Chapter {chapter_num}: {e}")

    async def _stage_generate_output(self) -> Path:
        """Stage 4: Generate output files."""
        self.state.current_stage = "generating_output"
        logger.info("Generating output files...")

        output_dir = self.project_dir / self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write Markdown
        md_writer = MarkdownWriter(output_dir)
        md_path = md_writer.write(
            self.state.completed_chapters,
            title=self.config.paper_title,
            authors=self.config.authors,
        )

        # Convert to LaTeX
        templates_dir = get_templates_dir()
        latex_converter = LaTeXConverter(
            template_dir=templates_dir / "paper",
            template_style=self.config.template_style,
        )
        tex_path = latex_converter.convert_chapters(
            self.state.completed_chapters,
            output_dir / "paper.tex",
            title=self.config.paper_title,
            authors=self.config.authors,
        )

        # Try to compile PDF
        pdf_path = latex_converter.compile_pdf(tex_path)
        if pdf_path:
            return pdf_path

        return md_path

    def get_state(self) -> dict[str, Any]:
        """Get current pipeline state.

        Returns:
            State dictionary
        """
        return {
            "stage": self.state.current_stage,
            "chapters_completed": len(self.state.completed_chapters),
            "errors": self.state.errors,
        }

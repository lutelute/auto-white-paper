"""Literature research clients (Genspark, Manual, Claude)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

from awp.utils.logger import get_logger

logger = get_logger()


@dataclass
class LiteratureResult:
    """Literature search result."""

    title: str
    authors: list[str]
    year: Optional[int]
    abstract: Optional[str]
    url: Optional[str]
    citation_key: str
    source: str = "unknown"


@dataclass
class SearchResults:
    """Collection of search results."""

    query: str
    results: list[LiteratureResult]
    summary: str
    references: list[str]
    key_findings: list[str]


class BaseLiteratureClient(ABC):
    """Base class for literature research clients."""

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> SearchResults:
        """Search for literature."""
        pass

    async def close(self) -> None:
        """Close any resources."""
        pass


class GensparkClient(BaseLiteratureClient):
    """Client for Genspark API for literature research."""

    BASE_URL = "https://api.genspark.ai/v1"

    def __init__(self, api_key: str):
        """Initialize Genspark client.

        Args:
            api_key: Genspark API key
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> SearchResults:
        """Search for academic literature."""
        logger.info(f"Searching literature via Genspark: {query}")

        try:
            response = await self.client.post(
                "/search",
                json={
                    "query": query,
                    "max_results": max_results,
                    "filters": {
                        "year_from": year_from,
                        "year_to": year_to,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", []):
                results.append(
                    LiteratureResult(
                        title=item.get("title", ""),
                        authors=item.get("authors", []),
                        year=item.get("year"),
                        abstract=item.get("abstract"),
                        url=item.get("url"),
                        citation_key=self._generate_citation_key(item),
                        source="genspark",
                    )
                )

            return SearchResults(
                query=query,
                results=results,
                summary=data.get("summary", ""),
                references=[r.citation_key for r in results],
                key_findings=data.get("key_findings", []),
            )

        except httpx.HTTPError as e:
            logger.error(f"Genspark API error: {e}")
            return SearchResults(
                query=query,
                results=[],
                summary="",
                references=[],
                key_findings=[],
            )

    def _generate_citation_key(self, item: dict) -> str:
        """Generate a citation key for a paper."""
        authors = item.get("authors", [])
        year = item.get("year", "")

        if authors:
            first_author = authors[0].split()[-1]
            return f"{first_author}{year}"
        else:
            title_words = item.get("title", "unknown").split()[:2]
            return f"{'_'.join(title_words)}{year}"

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class ManualLiteratureClient(BaseLiteratureClient):
    """Client that loads literature review from a local file.

    Use this when you want to manually provide the literature review content,
    e.g., by copying from Genspark web interface or writing it yourself.
    """

    def __init__(self, project_dir: Path):
        """Initialize manual literature client.

        Args:
            project_dir: Project directory containing literature files
        """
        self.project_dir = project_dir
        self.literature_dir = project_dir / ".awp" / "literature"
        self.literature_dir.mkdir(parents=True, exist_ok=True)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> SearchResults:
        """Load literature from local file.

        Looks for files in .awp/literature/:
        - introduction_literature.md (for chapter 1)
        - literature_review.md (general)
        """
        logger.info(f"Loading manual literature review for: {query}")

        # Try to find literature file
        possible_files = [
            self.literature_dir / "introduction_literature.md",
            self.literature_dir / "literature_review.md",
            self.literature_dir / "chapter1_literature.md",
        ]

        content = ""
        for file_path in possible_files:
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                logger.info(f"Loaded literature from: {file_path}")
                break

        if not content:
            # Create template file for user to fill in
            template_path = self.literature_dir / "introduction_literature.md"
            template = f"""# Literature Review for Introduction

## Instructions
This file was auto-generated. Please fill in the literature review content.

You can:
1. Use Genspark (https://www.genspark.ai/) to search for papers
2. Copy the relevant findings here
3. Run `awp generate` again

## Query
{query}

## Summary
[Write a summary of the research landscape here]

## Key Findings
- [Finding 1]
- [Finding 2]
- [Finding 3]

## References
- [Author1 et al., 2024] Title of paper 1
- [Author2 et al., 2023] Title of paper 2
"""
            template_path.write_text(template, encoding="utf-8")
            logger.warning(f"Created literature template: {template_path}")
            logger.warning("Please fill in the template and run again.")

            return SearchResults(
                query=query,
                results=[],
                summary="[Literature review not provided. Please edit .awp/literature/introduction_literature.md]",
                references=[],
                key_findings=["[Please provide literature review content]"],
            )

        # Parse the content
        return self._parse_literature_file(query, content)

    def _parse_literature_file(self, query: str, content: str) -> SearchResults:
        """Parse a literature markdown file."""
        summary = ""
        key_findings = []
        references = []

        lines = content.split("\n")
        current_section = ""

        for line in lines:
            line = line.strip()
            if line.startswith("## Summary"):
                current_section = "summary"
            elif line.startswith("## Key Findings"):
                current_section = "findings"
            elif line.startswith("## References"):
                current_section = "references"
            elif line.startswith("## "):
                current_section = ""
            elif line.startswith("- ") and current_section == "findings":
                key_findings.append(line[2:])
            elif line.startswith("- ") and current_section == "references":
                references.append(line[2:])
            elif current_section == "summary" and line:
                summary += line + " "

        return SearchResults(
            query=query,
            results=[],
            summary=summary.strip(),
            references=references,
            key_findings=key_findings,
        )


class ClaudeLiteratureClient(BaseLiteratureClient):
    """Client that uses Claude to generate literature review content.

    This uses the Claude API to search for and summarize relevant research.
    Note: This is a simulated literature review, not actual paper citations.
    """

    def __init__(self, claude_client: Any):
        """Initialize Claude literature client.

        Args:
            claude_client: Claude API client instance
        """
        self.claude = claude_client

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> SearchResults:
        """Generate literature review using Claude."""
        logger.info(f"Generating literature review via Claude: {query}")

        system_prompt = """You are an academic research assistant specializing in literature reviews.
Generate a comprehensive literature review summary based on the query.

Important:
- Provide realistic but SIMULATED references (do not claim these are real papers)
- Focus on the key concepts and research directions
- Be academically rigorous in your analysis
- Indicate that this is an AI-generated summary that should be verified"""

        user_prompt = f"""Generate a literature review for the following research topic:

Query: {query}

Please provide:
1. A summary of the research landscape (2-3 paragraphs)
2. 5-7 key findings or research directions
3. 5-10 representative reference placeholders (use format: [AuthorYear])

Note: These should be realistic research directions, but clearly indicate they need verification."""

        try:
            response = await self.claude.generate(system_prompt, user_prompt)

            # Parse the response
            return self._parse_claude_response(query, response)

        except Exception as e:
            logger.error(f"Claude literature search failed: {e}")
            return SearchResults(
                query=query,
                results=[],
                summary="[Literature review generation failed]",
                references=[],
                key_findings=[],
            )

    def _parse_claude_response(self, query: str, response: str) -> SearchResults:
        """Parse Claude's response into SearchResults."""
        # Simple parsing - extract sections
        summary = ""
        key_findings = []
        references = []

        lines = response.split("\n")
        current_section = "summary"

        for line in lines:
            line = line.strip()

            if "key finding" in line.lower() or "research direction" in line.lower():
                current_section = "findings"
            elif "reference" in line.lower():
                current_section = "references"
            elif line.startswith("- ") or line.startswith("* "):
                item = line[2:].strip()
                if current_section == "findings":
                    key_findings.append(item)
                elif current_section == "references":
                    references.append(item)
            elif current_section == "summary" and line and not line.startswith("#"):
                summary += line + " "

        return SearchResults(
            query=query,
            results=[],
            summary=summary.strip() or response[:1000],
            references=references,
            key_findings=key_findings or ["[See summary for key findings]"],
        )


class MockGensparkClient(BaseLiteratureClient):
    """Mock client for testing without API access."""

    def __init__(self, api_key: str = "mock"):
        """Initialize mock client."""
        self.api_key = api_key

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> SearchResults:
        """Return mock search results."""
        logger.info(f"[MOCK] Searching literature for: {query}")

        return SearchResults(
            query=query,
            results=[
                LiteratureResult(
                    title=f"Sample Paper on {query}",
                    authors=["Author A", "Author B"],
                    year=2024,
                    abstract=f"This paper discusses {query} in detail.",
                    url="https://example.com/paper",
                    citation_key="AuthorA2024",
                    source="mock",
                ),
            ],
            summary=f"[MOCK] Literature review summary for {query}. "
                    "This is placeholder content. Please configure a literature provider.",
            references=["AuthorA2024"],
            key_findings=[
                f"[MOCK] Key finding about {query}",
                "[MOCK] Please configure literature provider in awp.config.yaml",
            ],
        )


def create_literature_client(
    provider: str,
    project_dir: Optional[Path] = None,
    api_key: Optional[str] = None,
    claude_client: Optional[Any] = None,
) -> BaseLiteratureClient:
    """Factory function to create literature client.

    Args:
        provider: Provider name (genspark, manual, claude, mock)
        project_dir: Project directory (for manual provider)
        api_key: API key (for genspark)
        claude_client: Claude client instance (for claude provider)

    Returns:
        Literature client instance
    """
    if provider == "genspark" and api_key:
        return GensparkClient(api_key)
    elif provider == "manual":
        return ManualLiteratureClient(project_dir or Path.cwd())
    elif provider == "claude" and claude_client:
        return ClaudeLiteratureClient(claude_client)
    else:
        logger.warning(f"Unknown or unconfigured provider '{provider}', using mock")
        return MockGensparkClient()

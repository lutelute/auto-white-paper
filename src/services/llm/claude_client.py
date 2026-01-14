"""Claude API client for text generation."""

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

import anthropic
from anthropic import AsyncAnthropic

from awp.utils.logger import get_logger

logger = get_logger()


@dataclass
class LLMConfig:
    """LLM configuration."""

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.7


class ClaudeClient:
    """Claude API client for text generation."""

    def __init__(self, api_key: str, config: Optional[LLMConfig] = None):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key
            config: Optional LLM configuration
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self.sync_client = anthropic.Anthropic(api_key=api_key)
        self.config = config or LLMConfig()

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text using Claude.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Override max tokens
            temperature: Override temperature

        Returns:
            Generated text
        """
        logger.debug(f"Generating with model: {self.config.model}")

        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    def generate_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text using Claude (synchronous).

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Override max tokens
            temperature: Override temperature

        Returns:
            Generated text
        """
        logger.debug(f"Generating with model: {self.config.model}")

        response = self.sync_client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        """Generate text with streaming.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Yields:
            Text chunks as they are generated
        """
        async with self.client.messages.stream(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate structured output as JSON.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            output_schema: Expected output schema

        Returns:
            Parsed JSON response
        """
        enhanced_prompt = f"""{user_prompt}

Please respond with a valid JSON object matching this schema:
```json
{json.dumps(output_schema, indent=2)}
```

Respond ONLY with the JSON object, no additional text."""

        response = await self.generate(
            system_prompt,
            enhanced_prompt,
            temperature=0.3,  # Lower temperature for structured output
        )

        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response}")
            raise ValueError(f"Failed to parse structured output: {e}")

    async def summarize(self, text: str, max_length: int = 500) -> str:
        """Summarize text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length

        Returns:
            Summary text
        """
        system_prompt = "You are a technical writer who creates concise, accurate summaries."
        user_prompt = f"""Summarize the following text in {max_length} characters or less.
Focus on the key technical points and main ideas.

Text to summarize:
{text}

Summary:"""

        return await self.generate(system_prompt, user_prompt)

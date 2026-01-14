"""Prompt template management."""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, Template

from awp.utils.logger import get_logger

logger = get_logger()


class PromptManager:
    """Manage and render prompt templates."""

    def __init__(self, templates_dir: Path):
        """Initialize prompt manager.

        Args:
            templates_dir: Directory containing prompt templates
        """
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._cache: dict[str, dict] = {}

    def load_template(self, template_name: str) -> dict[str, Any]:
        """Load a YAML template file.

        Args:
            template_name: Name of the template (without extension)

        Returns:
            Template data dictionary
        """
        if template_name in self._cache:
            return self._cache[template_name]

        template_path = self.templates_dir / f"{template_name}.yaml"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.safe_load(f)

        self._cache[template_name] = template_data
        return template_data

    def render(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> tuple[str, str]:
        """Render a template with context.

        Args:
            template_name: Name of the template
            context: Variables to use in rendering

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        template_data = self.load_template(template_name)

        system_template = Template(template_data.get("system_prompt", ""))
        user_template = Template(template_data.get("user_prompt", ""))

        system_prompt = system_template.render(**context)
        user_prompt = user_template.render(**context)

        return system_prompt, user_prompt

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        """Render a template string with context.

        Args:
            template_string: Template string
            context: Variables to use in rendering

        Returns:
            Rendered string
        """
        template = Template(template_string)
        return template.render(**context)

    def get_template_info(self, template_name: str) -> dict[str, Any]:
        """Get metadata about a template.

        Args:
            template_name: Name of the template

        Returns:
            Template metadata
        """
        template_data = self.load_template(template_name)
        return {
            "name": template_data.get("name", template_name),
            "description": template_data.get("description", ""),
            "version": template_data.get("version", "1.0"),
            "required_context": self._extract_required_context(template_data),
        }

    def _extract_required_context(self, template_data: dict) -> list[str]:
        """Extract required context variables from template.

        Args:
            template_data: Template data dictionary

        Returns:
            List of required variable names
        """
        required = []

        for key in ["system_prompt", "user_prompt"]:
            if key in template_data:
                # Simple extraction of {{ variable }} patterns
                import re

                pattern = r"\{\{\s*(\w+)"
                matches = re.findall(pattern, template_data[key])
                required.extend(matches)

        return list(set(required))

    def list_templates(self) -> list[str]:
        """List available templates.

        Returns:
            List of template names
        """
        templates = []
        for path in self.templates_dir.glob("*.yaml"):
            templates.append(path.stem)
        return sorted(templates)

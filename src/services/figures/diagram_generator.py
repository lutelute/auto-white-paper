"""Diagram generation using Mermaid and Graphviz."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from awp.utils.logger import get_logger

logger = get_logger()


class DiagramGenerator:
    """Generate diagrams from text descriptions."""

    def __init__(self, output_dir: Path):
        """Initialize diagram generator.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_mermaid(
        self,
        mermaid_code: str,
        name: str,
        output_format: str = "png",
    ) -> Path:
        """Generate diagram from Mermaid code.

        Args:
            mermaid_code: Mermaid diagram code
            name: Output file name (without extension)
            output_format: Output format (png, svg, pdf)

        Returns:
            Path to generated diagram
        """
        output_path = self.output_dir / f"{name}.{output_format}"

        # Write mermaid code to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
            f.write(mermaid_code)
            temp_path = f.name

        try:
            # Try using mmdc (mermaid-cli)
            result = subprocess.run(
                ["mmdc", "-i", temp_path, "-o", str(output_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.warning(f"Mermaid CLI failed: {result.stderr}")
                # Fallback: save as text
                output_path = self.output_dir / f"{name}.mmd"
                output_path.write_text(mermaid_code)

        except FileNotFoundError:
            logger.warning("Mermaid CLI not found, saving as .mmd file")
            output_path = self.output_dir / f"{name}.mmd"
            output_path.write_text(mermaid_code)
        finally:
            Path(temp_path).unlink(missing_ok=True)

        logger.info(f"Generated diagram: {output_path}")
        return output_path

    async def generate_graphviz(
        self,
        dot_code: str,
        name: str,
        output_format: str = "png",
    ) -> Path:
        """Generate diagram from Graphviz DOT code.

        Args:
            dot_code: Graphviz DOT code
            name: Output file name (without extension)
            output_format: Output format (png, svg, pdf)

        Returns:
            Path to generated diagram
        """
        output_path = self.output_dir / f"{name}.{output_format}"

        # Write DOT code to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
            f.write(dot_code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["dot", f"-T{output_format}", temp_path, "-o", str(output_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.warning(f"Graphviz failed: {result.stderr}")
                output_path = self.output_dir / f"{name}.dot"
                output_path.write_text(dot_code)

        except FileNotFoundError:
            logger.warning("Graphviz not found, saving as .dot file")
            output_path = self.output_dir / f"{name}.dot"
            output_path.write_text(dot_code)
        finally:
            Path(temp_path).unlink(missing_ok=True)

        logger.info(f"Generated diagram: {output_path}")
        return output_path

    def generate_class_diagram_mermaid(self, classes: list[dict]) -> str:
        """Generate Mermaid class diagram code.

        Args:
            classes: List of class information dictionaries

        Returns:
            Mermaid diagram code
        """
        lines = ["classDiagram"]

        for cls in classes:
            class_name = cls.get("name", "Unknown")
            lines.append(f"    class {class_name} {{")

            for method in cls.get("methods", []):
                method_name = method.get("name", "unknown")
                params = ", ".join(method.get("parameters", []))
                return_type = method.get("return_type", "")
                if return_type:
                    lines.append(f"        +{method_name}({params}) {return_type}")
                else:
                    lines.append(f"        +{method_name}({params})")

            lines.append("    }")

            # Add inheritance
            for base in cls.get("base_classes", []):
                if base and base not in ["object", "ABC"]:
                    lines.append(f"    {base} <|-- {class_name}")

        return "\n".join(lines)

    def generate_flowchart_mermaid(self, steps: list[dict]) -> str:
        """Generate Mermaid flowchart code.

        Args:
            steps: List of step dictionaries with 'id', 'label', 'next'

        Returns:
            Mermaid diagram code
        """
        lines = ["flowchart TD"]

        for step in steps:
            step_id = step.get("id", "unknown")
            label = step.get("label", step_id)
            step_type = step.get("type", "process")

            # Different node shapes
            if step_type == "start":
                lines.append(f"    {step_id}(({label}))")
            elif step_type == "end":
                lines.append(f"    {step_id}(({label}))")
            elif step_type == "decision":
                lines.append(f"    {step_id}{{{label}}}")
            else:
                lines.append(f"    {step_id}[{label}]")

            # Add connections
            for next_id in step.get("next", []):
                condition = step.get("condition", "")
                if condition:
                    lines.append(f"    {step_id} -->|{condition}| {next_id}")
                else:
                    lines.append(f"    {step_id} --> {next_id}")

        return "\n".join(lines)

    def generate_architecture_mermaid(self, components: list[dict]) -> str:
        """Generate Mermaid architecture diagram.

        Args:
            components: List of component dictionaries

        Returns:
            Mermaid diagram code
        """
        lines = ["flowchart TB"]
        lines.append("    subgraph System")

        for comp in components:
            comp_id = comp.get("id", "unknown")
            label = comp.get("label", comp_id)
            comp_type = comp.get("type", "module")

            if comp_type == "database":
                lines.append(f"        {comp_id}[({label})]")
            elif comp_type == "external":
                lines.append(f"        {comp_id}>{label}]")
            else:
                lines.append(f"        {comp_id}[{label}]")

        lines.append("    end")

        # Add connections
        for comp in components:
            comp_id = comp.get("id", "unknown")
            for dep in comp.get("dependencies", []):
                lines.append(f"    {comp_id} --> {dep}")

        return "\n".join(lines)

"""Source code parsing and analysis."""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from awp.utils.logger import get_logger

logger = get_logger()


@dataclass
class FunctionInfo:
    """Function information container."""

    name: str
    docstring: Optional[str] = None
    parameters: list[str] = field(default_factory=list)
    return_type: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False


@dataclass
class ClassInfo:
    """Class information container."""

    name: str
    docstring: Optional[str] = None
    methods: list[FunctionInfo] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    decorators: list[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Module information container."""

    path: Path
    imports: list[str] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    global_variables: list[str] = field(default_factory=list)
    docstring: Optional[str] = None


class PythonCodeParser:
    """Parse Python source code using AST."""

    def parse_file(self, file_path: Path) -> Optional[ModuleInfo]:
        """Parse a Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            ModuleInfo object or None if parsing fails
        """
        try:
            source = file_path.read_text(encoding="utf-8")
            return self.parse_source(source, file_path)
        except (UnicodeDecodeError, SyntaxError) as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None

    def parse_source(self, source: str, file_path: Optional[Path] = None) -> ModuleInfo:
        """Parse Python source code.

        Args:
            source: Python source code
            file_path: Optional path for reference

        Returns:
            ModuleInfo object
        """
        tree = ast.parse(source)

        module_info = ModuleInfo(
            path=file_path or Path("unknown"),
            docstring=ast.get_docstring(tree),
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_info.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                for alias in node.names:
                    full_name = f"{module_name}.{alias.name}" if module_name else alias.name
                    module_info.imports.append(full_name)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._extract_class(node)
                module_info.classes.append(class_info)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function(node)
                module_info.functions.append(func_info)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        module_info.global_variables.append(target.id)

        return module_info

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        """Extract function information from AST node."""
        parameters = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                param_name += f": {ast.unparse(arg.annotation)}"
            parameters.append(param_name)

        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        decorators = [ast.unparse(d) for d in node.decorator_list]

        return FunctionInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            parameters=parameters,
            return_type=return_type,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """Extract class information from AST node."""
        base_classes = [ast.unparse(base) for base in node.bases]
        decorators = [ast.unparse(d) for d in node.decorator_list]

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(item))

        return ClassInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            methods=methods,
            base_classes=base_classes,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=decorators,
        )


class CodeAnalyzer:
    """Analyze codebase structure and patterns."""

    def __init__(self, repo_path: Path):
        """Initialize code analyzer.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = repo_path
        self.python_parser = PythonCodeParser()

    def analyze(self) -> dict:
        """Analyze the entire codebase.

        Returns:
            Dictionary containing analysis results
        """
        results = {
            "modules": [],
            "total_classes": 0,
            "total_functions": 0,
            "total_lines": 0,
            "architecture_summary": "",
            "main_entry_points": [],
            "dependencies": set(),
        }

        python_files = list(self.repo_path.rglob("*.py"))
        python_files = [
            f
            for f in python_files
            if not any(
                skip in str(f)
                for skip in [".git", "node_modules", "__pycache__", ".venv", "venv", "test"]
            )
        ]

        logger.info(f"Analyzing {len(python_files)} Python files...")

        for file_path in python_files:
            module_info = self.python_parser.parse_file(file_path)
            if module_info:
                results["modules"].append(
                    {
                        "path": str(file_path.relative_to(self.repo_path)),
                        "classes": [c.name for c in module_info.classes],
                        "functions": [f.name for f in module_info.functions],
                        "imports": module_info.imports,
                        "docstring": module_info.docstring,
                    }
                )
                results["total_classes"] += len(module_info.classes)
                results["total_functions"] += len(module_info.functions)
                results["dependencies"].update(
                    imp.split(".")[0] for imp in module_info.imports if not imp.startswith(".")
                )

            try:
                results["total_lines"] += len(file_path.read_text().splitlines())
            except Exception:
                pass

        # Identify main entry points
        for module in results["modules"]:
            path = module["path"]
            if any(name in path for name in ["main.py", "__main__.py", "cli.py", "app.py"]):
                results["main_entry_points"].append(path)

        results["dependencies"] = sorted(results["dependencies"])

        # Generate architecture summary
        results["architecture_summary"] = self._generate_architecture_summary(results)

        return results

    def _generate_architecture_summary(self, results: dict) -> str:
        """Generate a summary of the codebase architecture."""
        summary_parts = []

        summary_parts.append(f"Total modules: {len(results['modules'])}")
        summary_parts.append(f"Total classes: {results['total_classes']}")
        summary_parts.append(f"Total functions: {results['total_functions']}")
        summary_parts.append(f"Total lines: {results['total_lines']}")

        if results["main_entry_points"]:
            summary_parts.append(f"Entry points: {', '.join(results['main_entry_points'])}")

        if results["dependencies"]:
            top_deps = results["dependencies"][:10]
            summary_parts.append(f"Key dependencies: {', '.join(top_deps)}")

        return "\n".join(summary_parts)

    def get_key_code_snippets(self, max_snippets: int = 10) -> list[dict]:
        """Extract key code snippets from the codebase.

        Args:
            max_snippets: Maximum number of snippets to extract

        Returns:
            List of code snippet dictionaries
        """
        snippets = []

        python_files = list(self.repo_path.rglob("*.py"))
        python_files = [
            f
            for f in python_files
            if not any(skip in str(f) for skip in [".git", "__pycache__", ".venv", "test"])
        ]

        for file_path in python_files[:20]:  # Limit files to analyze
            module_info = self.python_parser.parse_file(file_path)
            if not module_info:
                continue

            source_lines = file_path.read_text().splitlines()

            # Extract class definitions
            for class_info in module_info.classes[:3]:
                start = class_info.line_start - 1
                end = min(class_info.line_end, start + 30)  # Max 30 lines
                snippet = "\n".join(source_lines[start:end])

                snippets.append(
                    {
                        "name": f"class {class_info.name}",
                        "file": str(file_path.relative_to(self.repo_path)),
                        "language": "python",
                        "code": snippet,
                        "docstring": class_info.docstring,
                    }
                )

            # Extract important functions
            for func_info in module_info.functions[:3]:
                if func_info.name.startswith("_"):
                    continue

                start = func_info.line_start - 1
                end = min(func_info.line_end, start + 20)  # Max 20 lines
                snippet = "\n".join(source_lines[start:end])

                snippets.append(
                    {
                        "name": f"def {func_info.name}",
                        "file": str(file_path.relative_to(self.repo_path)),
                        "language": "python",
                        "code": snippet,
                        "docstring": func_info.docstring,
                    }
                )

            if len(snippets) >= max_snippets:
                break

        return snippets[:max_snippets]

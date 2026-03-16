"""
AST parser for Python code.
"""

import ast
from pathlib import Path
from typing import Optional


def parse_python_file(file_path: Path) -> ast.AST:
    """
    Parse a Python file and return its AST.

    Args:
        file_path: Path to the Python file.

    Returns:
        AST node representing the parsed file.

    Raises:
        SyntaxError: If the file contains invalid Python syntax.
        FileNotFoundError: If the file does not exist.
    """
    with open(file_path, encoding="utf-8") as f:
        source = f.read()
    return ast.parse(source, filename=str(file_path))


def get_source_lines(file_path: Path) -> list[str]:
    """
    Read source file and return lines.

    Args:
        file_path: Path to the source file.

    Returns:
        List of source code lines.
    """
    with open(file_path, encoding="utf-8") as f:
        return f.readlines()


def extract_source_segment(
    source_lines: list[str], line_start: int, line_end: int
) -> str:
    """
    Extract a segment of source code by line numbers.

    Args:
        source_lines: List of source code lines.
        line_start: Starting line number (1-indexed).
        line_end: Ending line number (1-indexed, inclusive).

    Returns:
        Extracted source code segment.
    """
    # Convert to 0-indexed
    start_idx = max(0, line_start - 1)
    end_idx = min(len(source_lines), line_end)
    return "".join(source_lines[start_idx:end_idx])


def get_node_source(node: ast.AST, source_lines: list[str]) -> str:
    """
    Get source code for an AST node.

    Args:
        node: AST node.
        source_lines: List of source code lines.

    Returns:
        Source code string for the node.
    """
    if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
        return extract_source_segment(
            source_lines, node.lineno, node.end_lineno or node.lineno
        )
    return ""


class PythonFileParser:
    """Parser for Python source files."""

    def __init__(self, file_path: Path):
        """
        Initialize parser.

        Args:
            file_path: Path to the Python file.
        """
        self.file_path = file_path
        self.source_lines: list[str] = []
        self.tree: Optional[ast.AST] = None

    def parse(self) -> ast.AST:
        """
        Parse the Python file.

        Returns:
            AST tree.
        """
        self.source_lines = get_source_lines(self.file_path)
        self.tree = parse_python_file(self.file_path)
        return self.tree

    def get_source(self) -> str:
        """
        Get the full source code.

        Returns:
            Full source code string.
        """
        return "".join(self.source_lines)

    def get_node_source(self, node: ast.AST) -> str:
        """
        Get source code for a specific AST node.

        Args:
            node: AST node.

        Returns:
            Source code for the node.
        """
        return get_node_source(node, self.source_lines)
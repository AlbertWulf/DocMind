"""
Markdown writer for outputting generated documentation.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class MarkdownWriter:
    """
    Write documentation to Markdown files.
    """

    def __init__(
        self,
        output_dir: Path,
        project_name: str = "",
    ):
        """
        Initialize the writer.

        Args:
            output_dir: Directory to write output files.
            project_name: Project name for document headers.
        """
        self.output_dir = Path(output_dir)
        self.project_name = project_name
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_user_guide(
        self,
        content: str,
        filename: str = "user-guide.md",
    ) -> Path:
        """
        Write user guide to file.

        Args:
            content: Document content.
            filename: Output filename.

        Returns:
            Path to the written file.
        """
        file_path = self.output_dir / filename
        content = self._add_header(content, "用户文档")
        self._write_file(file_path, content)
        return file_path

    def write_dev_guide(
        self,
        content: str,
        filename: str = "dev-guide.md",
    ) -> Path:
        """
        Write developer guide to file.

        Args:
            content: Document content.
            filename: Output filename.

        Returns:
            Path to the written file.
        """
        file_path = self.output_dir / filename
        content = self._add_header(content, "开发者文档")
        self._write_file(file_path, content)
        return file_path

    def write_document(
        self,
        content: str,
        filename: str,
        title: Optional[str] = None,
    ) -> Path:
        """
        Write a generic document to file.

        Args:
            content: Document content.
            filename: Output filename.
            title: Optional title for the document.

        Returns:
            Path to the written file.
        """
        file_path = self.output_dir / filename
        if title:
            content = self._add_header(content, title)
        self._write_file(file_path, content)
        return file_path

    def _add_header(self, content: str, doc_type: str) -> str:
        """Add document header with metadata."""
        # Check if content already has a title
        if content.strip().startswith("#"):
            # Remove existing title and add our header
            lines = content.strip().split("\n")
            # Find first non-title line
            content_start = 0
            for i, line in enumerate(lines):
                if not line.startswith("#"):
                    content_start = i
                    break
            content = "\n".join(lines[content_start:])

        header_lines = []

        # Add title
        title = f"{self.project_name} {doc_type}" if self.project_name else doc_type
        header_lines.append(f"# {title}")
        header_lines.append("")

        # Add generation info
        header_lines.append(f"> 文档生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        header_lines.append(">")
        header_lines.append("> 本文档由 DocMind 自动生成")
        header_lines.append("")

        header = "\n".join(header_lines)

        return header + content

    def _write_file(self, path: Path, content: str) -> None:
        """Write content to file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def create_index(
        self,
        user_guide_path: Optional[str] = None,
        dev_guide_path: Optional[str] = None,
    ) -> Path:
        """
        Create an index file linking to the generated documents.

        Args:
            user_guide_path: Path to user guide (relative).
            dev_guide_path: Path to developer guide (relative).

        Returns:
            Path to the index file.
        """
        index_path = self.output_dir / "README.md"

        lines = []
        if self.project_name:
            lines.append(f"# {self.project_name} 文档")
        else:
            lines.append("# 项目文档")

        lines.append("")
        lines.append("本目录包含自动生成的项目文档。")
        lines.append("")

        if user_guide_path:
            lines.append(f"- [用户文档](./{user_guide_path}) - 项目使用指南")

        if dev_guide_path:
            lines.append(f"- [开发者文档](./{dev_guide_path}) - 面向开发者的技术文档")

        lines.append("")

        self._write_file(index_path, "\n".join(lines))
        return index_path


def clean_markdown(content: str) -> str:
    """
    Clean up Markdown content.

    - Remove excessive blank lines
    - Fix heading hierarchy
    - Ensure proper spacing around code blocks

    Args:
        content: Markdown content to clean.

    Returns:
        Cleaned Markdown content.
    """
    # Remove excessive blank lines (more than 2 consecutive)
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Ensure blank line before headings (except at the start)
    lines = content.split("\n")
    cleaned_lines = []

    for i, line in enumerate(lines):
        if line.startswith("#") and i > 0:
            # Check if previous line is not blank
            if cleaned_lines and cleaned_lines[-1].strip():
                cleaned_lines.append("")
        cleaned_lines.append(line)

    # Ensure blank line after headings
    result_lines = []
    for i, line in enumerate(cleaned_lines):
        result_lines.append(line)
        if line.startswith("#") and i < len(cleaned_lines) - 1:
            next_line = cleaned_lines[i + 1]
            if next_line.strip() and not next_line.startswith("#"):
                result_lines.append("")

    return "\n".join(result_lines)


def extract_toc(content: str, max_level: int = 3) -> str:
    """
    Extract table of contents from Markdown content.

    Args:
        content: Markdown content.
        max_level: Maximum heading level to include.

    Returns:
        Table of contents as Markdown list.
    """
    lines = content.split("\n")
    toc_lines = []

    for line in lines:
        # Match headings
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2)

            if level <= max_level:
                # Create TOC entry
                indent = "  " * (level - 1)
                # Create anchor link
                anchor = title.lower().replace(" ", "-").replace("/", "")
                anchor = re.sub(r"[^\w\-]", "", anchor)
                toc_lines.append(f"{indent}- [{title}](#{anchor})")

    return "\n".join(toc_lines)
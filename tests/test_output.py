"""
Tests for the output module.
"""

import pytest
from pathlib import Path

from docmind.output.writer import (
    MarkdownWriter,
    clean_markdown,
    extract_toc,
)


class TestMarkdownWriter:
    """Tests for Markdown writer."""

    def test_write_user_guide(self, tmp_path: Path):
        """Test writing user guide."""
        writer = MarkdownWriter(tmp_path, "TestProject")
        content = "# Introduction\n\nThis is a test."

        path = writer.write_user_guide(content, "user.md")

        assert path.exists()
        text = path.read_text()
        assert "TestProject 用户文档" in text
        assert "Introduction" in text

    def test_write_dev_guide(self, tmp_path: Path):
        """Test writing developer guide."""
        writer = MarkdownWriter(tmp_path, "TestProject")
        content = "# Architecture\n\nModule structure."

        path = writer.write_dev_guide(content, "dev.md")

        assert path.exists()
        text = path.read_text()
        assert "TestProject 开发者文档" in text

    def test_create_index(self, tmp_path: Path):
        """Test creating index file."""
        writer = MarkdownWriter(tmp_path, "TestProject")

        index_path = writer.create_index(
            user_guide_path="user.md",
            dev_guide_path="dev.md",
        )

        assert index_path.exists()
        text = index_path.read_text()
        assert "TestProject 文档" in text
        assert "user.md" in text
        assert "dev.md" in text


class TestMarkdownUtils:
    """Tests for Markdown utilities."""

    def test_clean_markdown_excessive_blank_lines(self):
        """Test removing excessive blank lines."""
        content = "Line 1\n\n\n\n\nLine 2"
        cleaned = clean_markdown(content)
        assert "\n\n\n" not in cleaned

    def test_extract_toc(self):
        """Test extracting table of contents."""
        content = """# Main Title

## Section 1

Content here.

## Section 2

### Subsection 2.1

More content.
"""
        toc = extract_toc(content, max_level=2)

        assert "Section 1" in toc
        assert "Section 2" in toc
        assert "Subsection 2.1" not in toc  # Level 3 excluded

    def test_extract_toc_with_anchors(self):
        """Test that TOC has proper anchor links."""
        content = "## My Section\n\nContent."
        toc = extract_toc(content)

        assert "My Section" in toc
        assert "#my-section" in toc
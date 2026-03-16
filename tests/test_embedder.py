"""
Tests for the embedder module.
"""

import pytest

from docmind.embedder.splitter import (
    CodeChunk,
    TextSplitter,
    should_include_file,
)


class TestTextSplitter:
    """Tests for the text splitter."""

    def test_count_tokens(self):
        """Test token counting."""
        splitter = TextSplitter()
        count = splitter.count_tokens("Hello, world!")
        assert count > 0

    def test_split_text(self):
        """Test text splitting."""
        splitter = TextSplitter(chunk_size=50, chunk_overlap=10)

        text = "This is a test. " * 20
        chunks = splitter.split_text(text)

        assert len(chunks) > 1
        assert all(len(chunk) > 0 for chunk in chunks)

    def test_split_short_text(self):
        """Test splitting short text."""
        splitter = TextSplitter(chunk_size=500)
        text = "Short text."

        chunks = splitter.split_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text


class TestCodeChunk:
    """Tests for CodeChunk dataclass."""

    def test_create_chunk(self):
        """Test creating a code chunk."""
        chunk = CodeChunk(
            content="def hello(): pass",
            source_file="test.py",
            chunk_type="function",
            token_count=5,
            metadata={"name": "hello"},
        )

        assert chunk.content == "def hello(): pass"
        assert chunk.source_file == "test.py"
        assert chunk.chunk_type == "function"
        assert chunk.token_count == 5
        assert chunk.metadata["name"] == "hello"


class TestShouldIncludeFile:
    """Tests for file filtering."""

    def test_include_normal_file(self):
        """Test including normal Python files."""
        from pathlib import Path

        assert should_include_file(Path("src/main.py"), [])
        assert should_include_file(Path("lib/utils.py"), [])

    def test_exclude_test_directory(self):
        """Test excluding test directory."""
        from pathlib import Path

        exclude = ["tests/"]
        assert not should_include_file(Path("tests/test_main.py"), exclude)
        assert should_include_file(Path("src/main.py"), exclude)

    def test_exclude_double_star_pattern(self):
        """Test excluding with ** pattern."""
        from pathlib import Path

        exclude = ["**/__pycache__/"]
        assert not should_include_file(Path("src/__pycache__/main.pyc"), exclude)
        assert should_include_file(Path("src/main.py"), exclude)

    def test_exclude_venv(self):
        """Test excluding virtual environment."""
        from pathlib import Path

        exclude = ["**/venv/", "**/.venv/"]
        assert not should_include_file(Path(".venv/lib/site-packages/pkg.py"), exclude)
        assert not should_include_file(Path("venv/lib/python3.10/site.py"), exclude)
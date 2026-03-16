"""
Tests for the code analyzer module.
"""

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docmind.analyzer.extractor import (
    ArgInfo,
    ClassInfo,
    CodeExtractor,
    CodeStructure,
    FuncInfo,
)
from docmind.analyzer.metadata import (
    ProjectMeta,
    _extract_from_pyproject,
    _extract_requirements,
    extract_project_metadata,
)
from docmind.analyzer.parser import (
    PythonFileParser,
    get_node_source,
    get_source_lines,
    parse_python_file,
)


class TestParser:
    """Tests for the parser module."""

    def test_parse_python_file(self, tmp_path: Path):
        """Test parsing a simple Python file."""
        py_file = tmp_path / "test.py"
        py_file.write_text('''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
''')

        tree = parse_python_file(py_file)
        assert isinstance(tree, ast.Module)

    def test_get_source_lines(self, tmp_path: Path):
        """Test reading source lines."""
        py_file = tmp_path / "test.py"
        py_file.write_text("line1\nline2\nline3\n")

        lines = get_source_lines(py_file)
        assert len(lines) == 3
        assert lines[0] == "line1\n"
        assert lines[1] == "line2\n"

    def test_get_node_source(self, tmp_path: Path):
        """Test extracting source for an AST node."""
        py_file = tmp_path / "test.py"
        content = "def hello():\n    pass\n"
        py_file.write_text(content)

        lines = get_source_lines(py_file)
        tree = parse_python_file(py_file)

        func_node = tree.body[0]
        source = get_node_source(func_node, lines)
        assert "def hello():" in source

    def test_parse_invalid_syntax(self, tmp_path: Path):
        """Test parsing a file with invalid syntax."""
        py_file = tmp_path / "invalid.py"
        py_file.write_text("def broken(")

        with pytest.raises(SyntaxError):
            parse_python_file(py_file)


class TestExtractor:
    """Tests for the code extractor."""

    def test_extract_simple_function(self, tmp_path: Path):
        """Test extracting a simple function."""
        py_file = tmp_path / "test.py"
        py_file.write_text('''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
''')

        extractor = CodeExtractor(py_file)
        structure = extractor.extract()

        assert len(structure.functions) == 1
        func = structure.functions[0]
        assert func.name == "add"
        assert func.returns == "int"
        assert func.docstring == "Add two numbers."
        assert len(func.args) == 2
        assert func.args[0].name == "a"
        assert func.args[0].type_hint == "int"

    def test_extract_class(self, tmp_path: Path):
        """Test extracting a class with methods."""
        py_file = tmp_path / "test.py"
        py_file.write_text('''
class Calculator:
    """A simple calculator."""

    def __init__(self, value: int = 0):
        self.value = value

    def add(self, x: int) -> int:
        """Add x to value."""
        self.value += x
        return self.value
''')

        extractor = CodeExtractor(py_file)
        structure = extractor.extract()

        assert len(structure.classes) == 1
        cls = structure.classes[0]
        assert cls.name == "Calculator"
        assert cls.docstring == "A simple calculator."
        assert len(cls.methods) == 2
        assert cls.methods[0].name == "__init__"
        assert cls.methods[1].name == "add"

    def test_extract_private_members_excluded(self, tmp_path: Path):
        """Test that private members are excluded by default."""
        py_file = tmp_path / "test.py"
        py_file.write_text('''
def public():
    pass

def _private():
    pass

class MyClass:
    def public_method(self):
        pass

    def _private_method(self):
        pass
''')

        extractor = CodeExtractor(py_file, include_private=False)
        structure = extractor.extract()

        assert len(structure.functions) == 1
        assert structure.functions[0].name == "public"

        assert len(structure.classes[0].methods) == 1
        assert structure.classes[0].methods[0].name == "public_method"

    def test_extract_private_members_included(self, tmp_path: Path):
        """Test that private members can be included."""
        py_file = tmp_path / "test.py"
        py_file.write_text('''
def _private():
    pass
''')

        extractor = CodeExtractor(py_file, include_private=True)
        structure = extractor.extract()

        assert len(structure.functions) == 1
        assert structure.functions[0].name == "_private"

    def test_extract_async_function(self, tmp_path: Path):
        """Test extracting async functions."""
        py_file = tmp_path / "test.py"
        py_file.write_text('''
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    pass
''')

        extractor = CodeExtractor(py_file)
        structure = extractor.extract()

        assert len(structure.functions) == 1
        func = structure.functions[0]
        assert func.name == "fetch_data"
        assert func.is_async is True


class TestMetadata:
    """Tests for project metadata extraction."""

    def test_extract_from_pyproject(self, tmp_path: Path):
        """Test extracting metadata from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('''
[project]
name = "test-project"
version = "1.0.0"
description = "A test project"
authors = [{name = "Test Author"}]
dependencies = ["requests", "pydantic"]

[project.urls]
Repository = "https://github.com/test/test"
''')

        meta = ProjectMeta()
        meta = _extract_from_pyproject(pyproject, meta)

        assert meta.name == "test-project"
        assert meta.version == "1.0.0"
        assert meta.description == "A test project"
        assert meta.author == "Test Author"
        assert "requests" in meta.dependencies
        assert meta.repository == "https://github.com/test/test"

    def test_extract_requirements(self, tmp_path: Path):
        """Test extracting dependencies from requirements.txt."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text('''
requests>=2.28.0
pydantic==2.0.0
# comment
numpy
''')

        deps = _extract_requirements(req_file)
        assert "requests" in deps
        assert "pydantic" in deps
        assert "numpy" in deps
        assert len(deps) == 3

    def test_extract_project_metadata(self, tmp_path: Path):
        """Test full metadata extraction from a project."""
        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('''
[project]
name = "myproject"
version = "0.1.0"
description = "My project"
''')

        meta = extract_project_metadata(tmp_path)

        assert meta.name == "myproject"
        assert meta.version == "0.1.0"
        assert meta.description == "My project"
"""
Tests for the generator module.
"""

import pytest

from docmind.generator.mermaid import (
    DiagramType,
    MermaidDiagram,
    extract_mermaid_from_text,
    generate_architecture_diagram_code,
    generate_class_diagram_code,
    validate_mermaid_syntax,
)
from docmind.generator.prompts import PromptBuilder, PromptConfig
from docmind.generator.requirements import (
    CustomRequirements,
    extract_section,
    format_requirements_for_prompt,
    load_requirements,
)


class TestPromptBuilder:
    """Tests for prompt builder."""

    def test_build_user_guide_system_prompt(self):
        """Test building user guide system prompt."""
        builder = PromptBuilder(PromptConfig(language="zh-CN"))
        prompt = builder.build_user_guide_system_prompt()

        assert "用户友好的使用文档" in prompt
        assert "中文" in prompt

    def test_build_dev_guide_system_prompt(self):
        """Test building developer guide system prompt."""
        builder = PromptBuilder(PromptConfig(language="en-US"))
        prompt = builder.build_dev_guide_system_prompt()

        assert "developer" in prompt.lower()
        assert "English" in prompt

    def test_build_prompt_with_custom_requirements(self):
        """Test building prompt with custom requirements."""
        builder = PromptBuilder()
        custom_req = "Use specific format for functions."

        prompt = builder.build_user_guide_system_prompt(custom_requirements=custom_req)
        assert custom_req in prompt


class TestRequirements:
    """Tests for custom requirements parsing."""

    def test_extract_section(self):
        """Test extracting a section from markdown."""
        content = """# Main Title

## 通用要求

These are general requirements.

## 用户文档要求

User doc requirements here.
"""
        section = extract_section(content, "通用要求")
        assert "general requirements" in section

    def test_extract_nonexistent_section(self):
        """Test extracting a section that doesn't exist."""
        content = "# Title\n\nSome content."
        section = extract_section(content, "Nonexistent")
        assert section is None

    def test_format_requirements(self):
        """Test formatting requirements for prompt."""
        requirements = CustomRequirements(
            content="# Test\n## 通用要求\nGeneral stuff",
            general_requirements="General stuff",
        )

        formatted = format_requirements_for_prompt(requirements)
        assert "General stuff" in formatted


class TestMermaid:
    """Tests for Mermaid diagram utilities."""

    def test_extract_mermaid_from_text(self):
        """Test extracting mermaid code from text."""
        text = """
Here is a diagram:

```mermaid
graph TB
    A --> B
```

And another:

```mermaid
classDiagram
    Animal <|-- Dog
```
"""
        diagrams = extract_mermaid_from_text(text)
        assert len(diagrams) == 2
        assert "graph TB" in diagrams[0]
        assert "classDiagram" in diagrams[1]

    def test_validate_mermaid_syntax_valid(self):
        """Test validating valid mermaid syntax."""
        code = "graph TB\n    A --> B"
        is_valid, error = validate_mermaid_syntax(code)
        assert is_valid
        assert error is None

    def test_validate_mermaid_syntax_invalid(self):
        """Test validating invalid mermaid syntax."""
        code = "invalid diagram type"
        is_valid, error = validate_mermaid_syntax(code)
        assert not is_valid
        assert "Invalid diagram type" in error

    def test_generate_class_diagram_code(self):
        """Test generating class diagram code."""
        classes = [
            {
                "name": "Animal",
                "bases": [],
                "methods": ["eat", "sleep"],
                "attributes": ["name"],
            },
            {
                "name": "Dog",
                "bases": ["Animal"],
                "methods": ["bark"],
                "attributes": [],
            },
        ]

        code = generate_class_diagram_code(classes)
        assert "classDiagram" in code
        assert "class Animal" in code
        assert "class Dog" in code
        assert "Animal <|-- Dog" in code

    def test_generate_architecture_diagram_code(self):
        """Test generating architecture diagram code."""
        modules = [
            {
                "name": "api",
                "description": "API module",
                "dependencies": ["core"],
            },
            {
                "name": "core",
                "description": "Core module",
                "dependencies": [],
            },
        ]

        code = generate_architecture_diagram_code(modules)
        assert "graph TB" in code
        assert "api" in code
        assert "core" in code

    def test_mermaid_diagram_render(self):
        """Test rendering Mermaid diagram."""
        diagram = MermaidDiagram(
            diagram_type=DiagramType.GRAPH,
            code="graph TB\n    A --> B",
            title="Test Diagram",
        )

        rendered = diagram.render()
        assert "### Test Diagram" in rendered
        assert "```mermaid" in rendered
        assert "graph TB" in rendered
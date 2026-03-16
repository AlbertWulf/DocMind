"""
Mermaid diagram generation utilities.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DiagramType(Enum):
    """Types of Mermaid diagrams."""

    FLOWCHART = "flowchart"
    GRAPH = "graph"
    SEQUENCE = "sequenceDiagram"
    CLASS = "classDiagram"
    STATE = "stateDiagram"
    ER = "erDiagram"
    GANTT = "gantt"
    MINDMAP = "mindmap"


@dataclass
class MermaidDiagram:
    """A Mermaid diagram."""

    diagram_type: DiagramType
    code: str
    title: Optional[str] = None

    def render(self) -> str:
        """Render the diagram as a Markdown code block."""
        lines = []

        if self.title:
            lines.append(f"### {self.title}")
            lines.append("")

        lines.append(f"```mermaid")
        lines.append(self.code)
        lines.append("```")

        return "\n".join(lines)


def extract_mermaid_from_text(text: str) -> list[str]:
    """
    Extract Mermaid diagram code blocks from text.

    Args:
        text: Text containing Mermaid diagrams.

    Returns:
        List of Mermaid diagram code strings.
    """
    pattern = r"```mermaid\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return [m.strip() for m in matches]


def validate_mermaid_syntax(code: str) -> tuple[bool, Optional[str]]:
    """
    Validate Mermaid diagram syntax.

    This is a basic validation that checks for common syntax issues.
    For full validation, you would need a Mermaid parser.

    Args:
        code: Mermaid diagram code.

    Returns:
        Tuple of (is_valid, error_message).
    """
    code = code.strip()

    if not code:
        return False, "Empty diagram code"

    # Check for valid diagram type
    valid_starts = [
        "graph ",
        "flowchart ",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "erDiagram",
        "gantt",
        "mindmap",
    ]

    if not any(code.startswith(start) for start in valid_starts):
        return False, f"Invalid diagram type. Must start with one of: {', '.join(valid_starts)}"

    # Check for balanced brackets
    brackets = {"(": ")", "[": "]", "{": "}"}
    stack = []
    in_string = False
    escape_next = False

    for char in code:
        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char in brackets:
            stack.append(char)
        elif char in brackets.values():
            if not stack:
                return False, f"Unmatched closing bracket: {char}"
            opening = stack.pop()
            if brackets[opening] != char:
                return False, f"Mismatched brackets: {opening} vs {char}"

    if stack:
        return False, f"Unclosed brackets: {stack}"

    return True, None


def generate_class_diagram_code(
    classes: list[dict],
    show_methods: bool = True,
    show_attributes: bool = True,
) -> str:
    """
    Generate Mermaid class diagram code from class information.

    Args:
        classes: List of class dictionaries with name, methods, attributes, bases.
        show_methods: Whether to show methods.
        show_attributes: Whether to show attributes.

    Returns:
        Mermaid class diagram code.
    """
    lines = ["classDiagram"]

    for cls in classes:
        class_name = cls["name"]

        # Add class definition
        lines.append(f"    class {class_name} {{")
        lines.append("    }")

        # Add inheritance
        for base in cls.get("bases", []):
            # Clean up base name for Mermaid
            base_name = base.split(".")[-1] if "." in base else base
            lines.append(f"    {base_name} <|-- {class_name}")

    # Add relationships between classes if provided
    for cls in classes:
        for related in cls.get("related_classes", []):
            lines.append(f"    {cls['name']} --> {related}")

    return "\n".join(lines)


def generate_architecture_diagram_code(
    modules: list[dict],
) -> str:
    """
    Generate Mermaid architecture diagram code from module information.

    Args:
        modules: List of module dictionaries with name, description, dependencies.

    Returns:
        Mermaid graph diagram code.
    """
    lines = ["graph TB"]

    # Add module nodes
    for module in modules:
        name = module["name"]
        desc = module.get("description", "")
        label = f"{name}"
        if desc:
            label = f"{name}\\n{desc[:30]}..." if len(desc) > 30 else f"{name}\\n{desc}"
        # Sanitize name for Mermaid
        safe_name = name.replace(".", "_").replace("-", "_")
        lines.append(f'    {safe_name}["{label}"]')

    # Add dependencies
    for module in modules:
        name = module["name"]
        safe_name = name.replace(".", "_").replace("-", "_")
        for dep in module.get("dependencies", []):
            safe_dep = dep.replace(".", "_").replace("-", "_")
            if safe_dep != safe_name:  # Avoid self-references
                lines.append(f"    {safe_name} --> {safe_dep}")

    return "\n".join(lines)


def generate_sequence_diagram_code(
    participants: list[str],
    interactions: list[tuple[str, str, str]],
) -> str:
    """
    Generate Mermaid sequence diagram code.

    Args:
        participants: List of participant names.
        interactions: List of (from, to, message) tuples.

    Returns:
        Mermaid sequence diagram code.
    """
    lines = ["sequenceDiagram"]

    # Add participants
    for p in participants:
        lines.append(f"    participant {p}")

    # Add interactions
    for from_p, to_p, message in interactions:
        lines.append(f"    {from_p}->>{to_p}: {message}")

    return "\n".join(lines)
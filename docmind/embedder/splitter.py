"""
Text splitter for breaking code into chunks suitable for embedding.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tiktoken


@dataclass
class CodeChunk:
    """A chunk of code with metadata."""

    content: str
    source_file: str
    chunk_type: str  # "class", "function", "module", "mixed"
    token_count: int
    metadata: dict = field(default_factory=dict)
    # Metadata can include: name, line_start, line_end, docstring, etc.


class TextSplitter:
    """
    Split text/code into chunks for embedding.

    Supports both token-based and structure-aware splitting.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        encoding_name: str = "cl100k_base",
    ):
        """
        Initialize text splitter.

        Args:
            chunk_size: Target chunk size in tokens.
            chunk_overlap: Overlap between chunks in tokens.
            encoding_name: Tiktoken encoding name for token counting.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text."""
        return len(self.encoding.encode(text))

    def split_text(self, text: str) -> list[str]:
        """
        Split text into chunks based on token count.

        Args:
            text: Text to split.

        Returns:
            List of text chunks.
        """
        tokens = self.encoding.encode(text)
        chunks = []

        start = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            # Move start forward, accounting for overlap
            start = end - self.chunk_overlap if end < len(tokens) else end

        return chunks

    def split_code_structure(
        self,
        code_structure,
        source_file: str,
    ) -> list[CodeChunk]:
        """
        Split a CodeStructure into chunks, preserving logical boundaries.

        This method creates chunks for:
        1. Module-level docstring and imports (as a context chunk)
        2. Each class with its methods
        3. Each standalone function

        Args:
            code_structure: CodeStructure object from the analyzer.
            source_file: Path to the source file.

        Returns:
            List of CodeChunk objects.
        """
        chunks = []

        # Module-level chunk (docstring + imports)
        module_text = self._build_module_context(code_structure)
        if module_text:
            chunks.append(CodeChunk(
                content=module_text,
                source_file=source_file,
                chunk_type="module",
                token_count=self.count_tokens(module_text),
                metadata={"name": code_structure.module_name},
            ))

        # Class chunks
        for class_info in code_structure.classes:
            class_text = self._build_class_text(class_info)
            class_tokens = self.count_tokens(class_text)

            if class_tokens <= self.chunk_size:
                # Class fits in one chunk
                chunks.append(CodeChunk(
                    content=class_text,
                    source_file=source_file,
                    chunk_type="class",
                    token_count=class_tokens,
                    metadata={
                        "name": class_info.name,
                        "line_start": class_info.line_start,
                        "line_end": class_info.line_end,
                        "docstring": class_info.docstring,
                        "bases": class_info.bases,
                    },
                ))
            else:
                # Split class into multiple chunks
                # First chunk: class signature and docstring
                class_header = self._build_class_header(class_info)
                chunks.append(CodeChunk(
                    content=class_header,
                    source_file=source_file,
                    chunk_type="class",
                    token_count=self.count_tokens(class_header),
                    metadata={
                        "name": class_info.name,
                        "line_start": class_info.line_start,
                        "is_header": True,
                    },
                ))

                # Method chunks
                for method in class_info.methods:
                    method_text = self._build_function_text(method, is_method=True)
                    chunks.append(CodeChunk(
                        content=method_text,
                        source_file=source_file,
                        chunk_type="function",
                        token_count=self.count_tokens(method_text),
                        metadata={
                            "name": f"{class_info.name}.{method.name}",
                            "line_start": method.line_start,
                            "line_end": method.line_end,
                            "docstring": method.docstring,
                            "parent_class": class_info.name,
                        },
                    ))

        # Standalone function chunks
        for func_info in code_structure.functions:
            func_text = self._build_function_text(func_info)
            chunks.append(CodeChunk(
                content=func_text,
                source_file=source_file,
                chunk_type="function",
                token_count=self.count_tokens(func_text),
                metadata={
                    "name": func_info.name,
                    "line_start": func_info.line_start,
                    "line_end": func_info.line_end,
                    "docstring": func_info.docstring,
                },
            ))

        return chunks

    def _build_module_context(self, code_structure) -> str:
        """Build module-level context text."""
        parts = []

        if code_structure.module_name:
            parts.append(f"Module: {code_structure.module_name}")

        if code_structure.docstring:
            parts.append(f"\nModule Docstring:\n{code_structure.docstring}")

        if code_structure.imports:
            parts.append("\nImports:")
            for imp in code_structure.imports[:10]:  # Limit imports shown
                parts.append(f"  - {imp}")
            if len(code_structure.imports) > 10:
                parts.append(f"  ... and {len(code_structure.imports) - 10} more")

        return "\n".join(parts)

    def _build_class_text(self, class_info) -> str:
        """Build text representation of a class."""
        parts = []

        # Class signature
        bases_str = f"({', '.join(class_info.bases)})" if class_info.bases else ""
        parts.append(f"class {class_info.name}{bases_str}:")

        # Docstring
        if class_info.docstring:
            parts.append(f'    """{class_info.docstring}"""')

        # Methods summary
        if class_info.methods:
            parts.append("\n    Methods:")
            for method in class_info.methods:
                args_str = self._format_args(method.args)
                parts.append(f"      - {method.name}({args_str})")

        # Source code
        parts.append(f"\nSource Code:\n{class_info.source_code}")

        return "\n".join(parts)

    def _build_class_header(self, class_info) -> str:
        """Build class header (signature + docstring + method list)."""
        parts = []

        bases_str = f"({', '.join(class_info.bases)})" if class_info.bases else ""
        parts.append(f"class {class_info.name}{bases_str}:")

        if class_info.docstring:
            parts.append(f'    """{class_info.docstring}"""')

        if class_info.attributes:
            parts.append("\n    Attributes:")
            for attr in class_info.attributes:
                parts.append(f"      - {attr}")

        if class_info.methods:
            parts.append("\n    Methods:")
            for method in class_info.methods:
                args_str = self._format_args(method.args)
                return_str = f" -> {method.returns}" if method.returns else ""
                parts.append(f"      - {method.name}({args_str}){return_str}")

        return "\n".join(parts)

    def _build_function_text(self, func_info, is_method: bool = False) -> str:
        """Build text representation of a function."""
        parts = []

        # Function signature
        args_str = self._format_args(func_info.args)
        return_str = f" -> {func_info.returns}" if func_info.returns else ""
        async_str = "async " if func_info.is_async else ""
        parts.append(f"{async_str}def {func_info.name}({args_str}){return_str}:")

        # Docstring
        if func_info.docstring:
            parts.append(f'    """{func_info.docstring}"""')

        # Source code
        parts.append(f"\nSource Code:\n{func_info.source_code}")

        return "\n".join(parts)

    def _format_args(self, args: list) -> str:
        """Format function arguments as a string."""
        arg_strs = []
        for arg in args:
            if arg.type_hint:
                arg_str = f"{arg.name}: {arg.type_hint}"
                if arg.default:
                    arg_str += f" = {arg.default}"
            else:
                arg_str = arg.name
                if arg.default:
                    arg_str += f"={arg.default}"
            arg_strs.append(arg_str)
        return ", ".join(arg_strs)


def should_include_file(file_path: Path, exclude_patterns: list[str]) -> bool:
    """
    Check if a file should be included based on exclude patterns.

    Args:
        file_path: Path to the file.
        exclude_patterns: List of glob patterns to exclude.

    Returns:
        True if the file should be included, False otherwise.
    """
    file_str = str(file_path)

    for pattern in exclude_patterns:
        # Handle glob-like patterns
        if pattern.startswith("**/"):
            # Match anywhere in the path
            if pattern[3:] in file_str:
                return False
        elif pattern.endswith("/*"):
            # Match directory prefix
            dir_name = pattern[:-2]
            if f"/{dir_name}/" in file_str or file_str.startswith(f"{dir_name}/"):
                return False
        elif pattern.startswith("*"):
            # Match file extension or suffix
            if file_str.endswith(pattern[1:]):
                return False
        elif pattern in file_str:
            return False

    return True
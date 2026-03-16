"""
Code structure extractor for extracting classes, functions, and their information.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .parser import PythonFileParser


@dataclass
class ArgInfo:
    """Information about a function argument."""

    name: str
    type_hint: Optional[str] = None
    default: Optional[str] = None


@dataclass
class FuncInfo:
    """Information about a function or method."""

    name: str
    args: list[ArgInfo] = field(default_factory=list)
    returns: Optional[str] = None
    docstring: Optional[str] = None
    source_code: str = ""
    line_start: int = 0
    line_end: int = 0
    is_async: bool = False
    is_method: bool = False
    decorators: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[FuncInfo] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    docstring: Optional[str] = None
    source_code: str = ""
    line_start: int = 0
    line_end: int = 0
    decorators: list[str] = field(default_factory=list)


@dataclass
class CodeStructure:
    """Complete structure of a Python module."""

    file_path: str
    module_name: str
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FuncInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    docstring: Optional[str] = None
    source_code: str = ""


class CodeExtractor:
    """Extract code structure from Python AST."""

    def __init__(self, file_path: Path, include_private: bool = False):
        """
        Initialize extractor.

        Args:
            file_path: Path to the Python file.
            include_private: Whether to include private members (starting with _).
        """
        self.file_path = file_path
        self.include_private = include_private
        self.parser = PythonFileParser(file_path)

    def extract(self) -> CodeStructure:
        """
        Extract complete code structure from the file.

        Returns:
            CodeStructure object with all extracted information.
        """
        tree = self.parser.parse()
        source_code = self.parser.get_source()

        # Calculate module name from file path
        module_name = self._get_module_name()

        structure = CodeStructure(
            file_path=str(self.file_path),
            module_name=module_name,
            source_code=source_code,
        )

        # Extract module docstring
        structure.docstring = ast.get_docstring(tree)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    structure.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    structure.imports.append(f"{module}.{alias.name}" if module else alias.name)
            elif isinstance(node, ast.ClassDef):
                if self._should_include(node.name):
                    class_info = self._extract_class(node)
                    structure.classes.append(class_info)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._should_include(node.name):
                    func_info = self._extract_function(node)
                    structure.functions.append(func_info)

        return structure

    def _get_module_name(self) -> str:
        """Get module name from file path."""
        # Get relative path and convert to module notation
        path = self.file_path.with_suffix("")
        parts = list(path.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else ""

    def _should_include(self, name: str) -> bool:
        """Check if a name should be included based on private filter."""
        if self.include_private:
            return True
        # Exclude __dunder__ methods but include _private if include_private
        if name.startswith("__") and name.endswith("__"):
            # Include special methods like __init__, __str__, etc.
            special_methods = {
                "__init__", "__new__", "__str__", "__repr__", "__len__",
                "__getitem__", "__setitem__", "__delitem__", "__iter__",
                "__next__", "__enter__", "__exit__", "__call__", "__bool__",
                "__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__",
                "__hash__", "__contains__", "__add__", "__sub__", "__mul__",
                "__truediv__", "__floordiv__", "__mod__", "__pow__",
            }
            return name in special_methods
        return not name.startswith("_")

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """Extract class information from AST node."""
        class_info = ClassInfo(
            name=node.name,
            bases=[self._get_name(base) for base in node.bases],
            source_code=self.parser.get_node_source(node),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            decorators=[self._get_decorator(d) for d in node.decorator_list],
        )

        for item in node.body:
            if isinstance(item, ast.Assign):
                # Class attribute
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info.attributes.append(target.id)
            elif isinstance(item, ast.AnnAssign):
                # Annotated class attribute
                if isinstance(item.target, ast.Name):
                    class_info.attributes.append(item.target.id)
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._should_include(item.name):
                    method_info = self._extract_function(item, is_method=True)
                    class_info.methods.append(method_info)

        return class_info

    def _extract_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool = False
    ) -> FuncInfo:
        """Extract function information from AST node."""
        func_info = FuncInfo(
            name=node.name,
            returns=self._get_annotation(node.returns),
            source_code=self.parser.get_node_source(node),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            decorators=[self._get_decorator(d) for d in node.decorator_list],
        )

        # Extract arguments
        args = node.args

        # Regular arguments
        for i, arg in enumerate(args.args):
            arg_info = ArgInfo(
                name=arg.arg,
                type_hint=self._get_annotation(arg.annotation),
            )
            # Set default value if exists
            default_offset = len(args.args) - len(args.defaults)
            if i >= default_offset:
                default = args.defaults[i - default_offset]
                arg_info.default = ast.unparse(default) if default else None
            func_info.args.append(arg_info)

        # *args
        if args.vararg:
            func_info.args.append(ArgInfo(
                name=f"*{args.vararg.arg}",
                type_hint=self._get_annotation(args.vararg.annotation),
            ))

        # keyword-only arguments
        for i, arg in enumerate(args.kwonlyargs):
            arg_info = ArgInfo(
                name=arg.arg,
                type_hint=self._get_annotation(arg.annotation),
            )
            if i < len(args.kw_defaults) and args.kw_defaults[i]:
                arg_info.default = ast.unparse(args.kw_defaults[i])
            func_info.args.append(arg_info)

        # **kwargs
        if args.kwarg:
            func_info.args.append(ArgInfo(
                name=f"**{args.kwarg.arg}",
                type_hint=self._get_annotation(args.kwarg.annotation),
            ))

        return func_info

    def _get_annotation(self, annotation: Optional[ast.AST]) -> Optional[str]:
        """Get type annotation string from AST node."""
        if annotation is None:
            return None
        return ast.unparse(annotation)

    def _get_name(self, node: ast.AST) -> str:
        """Get name string from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return ast.unparse(node)
        return ast.unparse(node) if hasattr(ast, "unparse") else str(node)

    def _get_decorator(self, node: ast.AST) -> str:
        """Get decorator string from AST node."""
        if isinstance(node, ast.Name):
            return f"@{node.id}"
        elif isinstance(node, ast.Attribute):
            return f"@{self._get_name(node)}"
        elif isinstance(node, ast.Call):
            return f"@{ast.unparse(node)}"
        return f"@{ast.unparse(node)}"
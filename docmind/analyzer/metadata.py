"""
Project metadata extraction from pyproject.toml, setup.py, etc.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tomllib


@dataclass
class ProjectMeta:
    """Project metadata information."""

    name: str = ""
    version: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    python_requires: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    readme: Optional[str] = None
    repository: Optional[str] = None


def extract_project_metadata(project_root: Path) -> ProjectMeta:
    """
    Extract project metadata from various configuration files.

    Searches for metadata in the following order:
    1. pyproject.toml (PEP 621)
    2. setup.py (fallback)
    3. setup.cfg (fallback)
    4. requirements.txt (for dependencies only)

    Args:
        project_root: Path to the project root directory.

    Returns:
        ProjectMeta object with extracted information.
    """
    meta = ProjectMeta()

    # Try pyproject.toml first (modern Python packaging)
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        meta = _extract_from_pyproject(pyproject_path, meta)

    # Try setup.py as fallback
    if not meta.name:
        setup_py_path = project_root / "setup.py"
        if setup_py_path.exists():
            meta = _extract_from_setup_py(setup_py_path, meta)

    # Try setup.cfg as fallback
    if not meta.name:
        setup_cfg_path = project_root / "setup.cfg"
        if setup_cfg_path.exists():
            meta = _extract_from_setup_cfg(setup_cfg_path, meta)

    # Get dependencies from requirements.txt if not found
    if not meta.dependencies:
        requirements_path = project_root / "requirements.txt"
        if requirements_path.exists():
            meta.dependencies = _extract_requirements(requirements_path)

    return meta


def _extract_from_pyproject(path: Path, meta: ProjectMeta) -> ProjectMeta:
    """Extract metadata from pyproject.toml."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Check for PEP 621 project metadata
        project = data.get("project", {})
        if project:
            meta.name = project.get("name", "")
            meta.version = project.get("version", "")
            meta.description = project.get("description", "")
            meta.dependencies = project.get("dependencies", [])
            meta.readme = project.get("readme", "")

            # Extract requires-python
            requires_python = project.get("requires-python")
            if requires_python:
                meta.python_requires = requires_python

            # Extract authors
            authors = project.get("authors", [])
            if authors:
                author_names = []
                for author in authors:
                    name = author.get("name", "")
                    if name:
                        author_names.append(name)
                meta.author = ", ".join(author_names)

            # Extract license
            license_info = project.get("license", {})
            if isinstance(license_info, dict):
                meta.license = license_info.get("text", license_info.get("file", ""))
            elif isinstance(license_info, str):
                meta.license = license_info

            # Extract URLs
            urls = project.get("urls", {})
            meta.repository = urls.get("Repository", urls.get("Source", ""))

        # Fallback to poetry metadata
        if not meta.name:
            poetry = data.get("tool", {}).get("poetry", {})
            if poetry:
                meta.name = poetry.get("name", "")
                meta.version = poetry.get("version", "")
                meta.description = poetry.get("description", "")
                meta.dependencies = list(poetry.get("dependencies", {}).keys())
                meta.author = poetry.get("authors", "")

        # Fallback to setuptools metadata
        if not meta.name:
            setuptools = data.get("tool", {}).get("setuptools", {})
            # Some projects use dynamic version

    except Exception:
        pass

    return meta


def _extract_from_setup_py(path: Path, meta: ProjectMeta) -> ProjectMeta:
    """Extract metadata from setup.py by parsing the file."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()

        # Simple regex extraction for common fields
        meta.name = _extract_string_var(content, "name") or meta.name
        meta.version = _extract_string_var(content, "version") or meta.version
        meta.description = _extract_string_var(content, "description") or meta.description
        meta.author = _extract_string_var(content, "author") or meta.author
        meta.license = _extract_string_var(content, "license") or meta.license

        # Try to extract install_requires
        deps = _extract_list_var(content, "install_requires")
        if deps:
            meta.dependencies = deps

    except Exception:
        pass

    return meta


def _extract_from_setup_cfg(path: Path, meta: ProjectMeta) -> ProjectMeta:
    """Extract metadata from setup.cfg."""
    try:
        import configparser

        config = configparser.ConfigParser()
        config.read(path)

        metadata = config.get("metadata", {})
        if metadata:
            meta.name = metadata.get("name", "")
            meta.version = metadata.get("version", "")
            meta.description = metadata.get("description", "")
            meta.author = metadata.get("author", "")
            meta.license = metadata.get("license", "")

        options = config.get("options", {})
        if options:
            install_requires = options.get("install_requires", "")
            if install_requires:
                meta.dependencies = [
                    dep.strip() for dep in install_requires.split("\n") if dep.strip()
                ]

    except Exception:
        pass

    return meta


def _extract_requirements(path: Path) -> list[str]:
    """Extract dependencies from requirements.txt."""
    dependencies = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    # Remove version specifiers for cleaner output
                    pkg = re.split(r"[=<>!~\[]", line)[0]
                    dependencies.append(pkg)
    except Exception:
        pass
    return dependencies


def _extract_string_var(content: str, var_name: str) -> Optional[str]:
    """Extract a string variable value from Python code."""
    # Match patterns like: name="value", name='value', name = "value"
    pattern = rf'{var_name}\s*=\s*["\']([^"\']+)["\']'
    match = re.search(pattern, content)
    if match:
        return match.group(1)

    # Match patterns like: name=value (where value is a variable)
    pattern = rf'{var_name}\s*=\s*(\w+)'
    match = re.search(pattern, content)
    if match:
        var_value = match.group(1)
        # Try to find the variable definition
        value_pattern = rf'{var_value}\s*=\s*["\']([^"\']+)["\']'
        value_match = re.search(value_pattern, content)
        if value_match:
            return value_match.group(1)

    return None


def _extract_list_var(content: str, var_name: str) -> list[str]:
    """Extract a list variable value from Python code."""
    # Match patterns like: install_requires=["pkg1", "pkg2"]
    pattern = rf'{var_name}\s*=\s*\[([^\]]+)\]'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        list_content = match.group(1)
        # Extract individual items
        items = re.findall(r'["\']([^"\']+)["\']', list_content)
        return items
    return []
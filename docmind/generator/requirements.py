"""
Custom requirements parsing from Markdown files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CustomRequirements:
    """Parsed custom requirements from user."""

    content: str
    general_requirements: Optional[str] = None
    user_guide_requirements: Optional[str] = None
    dev_guide_requirements: Optional[str] = None


def load_requirements(file_path: str) -> Optional[CustomRequirements]:
    """
    Load custom requirements from a Markdown file.

    Args:
        file_path: Path to the requirements file.

    Returns:
        CustomRequirements object, or None if file doesn't exist.
    """
    path = Path(file_path)
    if not path.exists():
        return None

    with open(path, encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        return None

    requirements = CustomRequirements(content=content)

    # Parse sections
    requirements.general_requirements = extract_section(
        content, "通用要求"
    ) or extract_section(content, "General Requirements")

    requirements.user_guide_requirements = (
        extract_section(content, "用户文档要求")
        or extract_section(content, "User Document Requirements")
        or extract_section(content, "用户文档")
    )

    requirements.dev_guide_requirements = (
        extract_section(content, "开发文档要求")
        or extract_section(content, "Developer Document Requirements")
        or extract_section(content, "开发文档")
    )

    return requirements


def extract_section(content: str, section_title: str) -> Optional[str]:
    """
    Extract a specific section from Markdown content.

    Args:
        content: Markdown content.
        section_title: Title of the section to extract.

    Returns:
        Section content, or None if not found.
    """
    lines = content.split("\n")
    section_lines = []
    in_section = False
    section_level = 0

    for line in lines:
        # Check for section heading
        if line.startswith("#"):
            # Count heading level
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip()

            if title.lower() == section_title.lower():
                in_section = True
                section_level = level
                continue
            elif in_section and level <= section_level:
                # End of section (same or higher level heading)
                break

        if in_section:
            section_lines.append(line)

    if section_lines:
        return "\n".join(section_lines).strip()

    return None


def format_requirements_for_prompt(requirements: CustomRequirements) -> str:
    """
    Format custom requirements for inclusion in LLM prompt.

    Args:
        requirements: CustomRequirements object.

    Returns:
        Formatted string for prompt.
    """
    parts = []

    if requirements.general_requirements:
        parts.append(f"### 通用要求\n\n{requirements.general_requirements}")

    if requirements.user_guide_requirements:
        parts.append(f"### 用户文档要求\n\n{requirements.user_guide_requirements}")

    if requirements.dev_guide_requirements:
        parts.append(f"### 开发文档要求\n\n{requirements.dev_guide_requirements}")

    if not parts:
        # Return raw content if no sections parsed
        return requirements.content

    return "\n\n".join(parts)


def create_example_requirements(output_path: str) -> None:
    """
    Create an example requirements file.

    Args:
        output_path: Path where the file will be created.
    """
    content = """# 文档自定义需求

这个文件允许你自定义文档生成的格式和内容，确保生成的文档符合你的期望。

## 通用要求

以下要求会同时应用到用户文档和开发文档：

- 所有代码示例使用 Python 3.10+ 的类型注解语法
- 每个函数说明必须包含"参数"、"返回值"、"异常"三个小节
- 使用中文编写，但保留英文技术术语（如 API、Handler、Client）
- 代码示例需要有详细的注释

## 用户文档要求

以下要求仅应用到用户文档：

### 类说明格式

对于每个主要类，请按以下格式说明：

```
## 类名

**用途**：一句话描述这个类的核心用途

**主要方法**：
- `方法名()`：简短说明
- `方法名()`：简短说明

**使用示例**：
```python
# 简单的示例代码
```
```

### 不需要的内容

- 不要生成"常见问题"章节
- 不需要列出私有方法（以_开头的方法）
- 不需要过于深入的技术细节

## 开发文档要求

以下要求仅应用到开发文档：

### 架构说明

- 请先给出一个整体的 Mermaid 架构图
- 然后按模块逐个说明，包括模块职责和依赖关系

### API 文档格式

对于每个公开 API：

```
### 函数名

**用途**：一句话描述

**参数**：
- `param_name` (类型)：参数说明

**返回值**：类型和说明

**异常**：
- `ExceptionType`：触发条件

**示例**：
```python
# 示例代码
```
```

### 代码风格

- 示例代码遵循 PEP 8 规范
- 使用 4 空格缩进
- 类型注解使用内置类型（如 `list[str]` 而非 `List[str]`）
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
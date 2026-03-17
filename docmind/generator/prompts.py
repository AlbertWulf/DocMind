"""
Prompt templates and builder for document generation.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .outline import SectionInfo


@dataclass
class PromptConfig:
    """Configuration for prompt generation."""

    language: str = "zh-CN"
    max_context_tokens: int = 8000


class PromptBuilder:
    """
    Build prompts for LLM document generation.
    """

    # Language mappings
    LANGUAGE_NAMES = {
        "zh-CN": "中文",
        "en-US": "English",
        "ja-JP": "日本語",
        "ko-KR": "한국어",
    }

    def __init__(self, config: Optional[PromptConfig] = None):
        """
        Initialize the prompt builder.

        Args:
            config: Prompt configuration.
        """
        self.config = config or PromptConfig()

    def get_language_name(self) -> str:
        """Get the display name for the configured language."""
        return self.LANGUAGE_NAMES.get(self.config.language, self.config.language)

    def build_user_guide_system_prompt(
        self, custom_requirements: Optional[str] = None
    ) -> str:
        """
        Build system prompt for user guide generation.

        Args:
            custom_requirements: Custom requirements from user.

        Returns:
            System prompt string.
        """
        lang = self.get_language_name()

        prompt = f"""你是一个专业的技术文档撰写专家。你的任务是根据提供的代码信息生成用户友好的使用文档。

## 输出要求

1. 使用 {lang} 编写文档
2. 使用 Markdown 格式
3. 结构清晰，层次分明
4. 包含必要的使用示例
5. 避免过于技术性的描述，侧重于如何使用

## 文档结构

生成的用户文档应包含以下章节：

1. **项目简介** - 简要介绍项目用途和核心功能
2. **安装指南** - 详细的安装步骤和环境要求
3. **快速开始** - 最小可运行的使用示例
4. **功能模块** - 按功能模块组织使用说明
5. **配置说明** - 配置项的解释和使用方法
6. **常见使用场景** - 实际使用场景的示例
7. **注意事项** - 使用时需要注意的问题

## 代码示例要求

- 示例代码应简洁易懂
- 包含必要的注释
- 覆盖常见的使用场景
"""

        if custom_requirements:
            prompt += f"""
## 自定义需求

以下是用户对文档格式和内容的特定要求，请务必遵守：

{custom_requirements}
"""

        return prompt

    def build_dev_guide_system_prompt(
        self, custom_requirements: Optional[str] = None
    ) -> str:
        """
        Build system prompt for developer guide generation.

        Args:
            custom_requirements: Custom requirements from user.

        Returns:
            System prompt string.
        """
        lang = self.get_language_name()

        prompt = f"""你是一个专业的技术文档撰写专家。你的任务是根据提供的代码信息生成面向开发者的技术文档。

## 输出要求

1. 使用 {lang} 编写文档
2. 使用 Markdown 格式
3. 结构清晰，层次分明
4. 包含详细的API参考
5. 适合新开发者快速上手

## 文档结构

生成的开发文档应包含以下章节：

1. **项目架构** - 整体架构概述和模块职责
   - 包含 Mermaid 架构图
   - 说明各模块的职责和关系

2. **核心模块详解** - 核心模块的详细说明
   - 模块用途
   - 主要类和函数
   - 设计思路

3. **API参考** - 完整的API文档
   - 类：属性、方法、使用示例
   - 函数：参数、返回值、异常、示例
   - 类型注解

4. **数据模型** - 数据结构说明
   - 数据类定义
   - 字段说明
   - Mermaid 类图

5. **开发指南** - 贡献者指南
   - 开发环境搭建
   - 测试方法
   - 代码规范
   - 提交指南

## Mermaid图表

在适当位置生成Mermaid图表：
- 架构图使用 `graph TB` 或 `flowchart TB`
- 类图使用 `classDiagram`
- 时序图使用 `sequenceDiagram`
- 确保图表简洁清晰，不要过于复杂
"""

        if custom_requirements:
            prompt += f"""
## 自定义需求

以下是用户对文档格式和内容的特定要求，请务必遵守：

{custom_requirements}
"""

        return prompt

    def build_user_guide_prompt(
        self,
        project_info: str,
        code_context: str,
        existing_docs: Optional[str] = None,
    ) -> str:
        """
        Build the user prompt for user guide generation.

        Args:
            project_info: Project information string.
            code_context: Retrieved code context.
            existing_docs: Existing documentation (README, etc.).

        Returns:
            User prompt string.
        """
        prompt = f"""请根据以下信息生成用户文档。

## 项目信息

{project_info}

## 代码信息

{code_context}
"""

        if existing_docs:
            prompt += f"""
## 已有文档

以下是项目中已有的文档，请参考：

{existing_docs}
"""

        prompt += """
请生成完整的用户文档，包含项目简介、安装指南、快速开始、功能模块、配置说明等章节。
"""

        return prompt

    def build_dev_guide_prompt(
        self,
        project_info: str,
        code_context: str,
        existing_docs: Optional[str] = None,
    ) -> str:
        """
        Build the user prompt for developer guide generation.

        Args:
            project_info: Project information string.
            code_context: Retrieved code context.
            existing_docs: Existing documentation.

        Returns:
            User prompt string.
        """
        prompt = f"""请根据以下信息生成开发者文档。

## 项目信息

{project_info}

## 代码信息

{code_context}
"""

        if existing_docs:
            prompt += f"""
## 已有文档

以下是项目中已有的文档，请参考：

{existing_docs}
"""

        prompt += """
请生成完整的开发者文档，包含项目架构、核心模块详解、API参考、数据模型、开发指南等章节。请在适当位置生成Mermaid图表（架构图、类图、时序图等）。
"""

        return prompt

    def build_section_prompt(
        self,
        section_name: str,
        section_description: str,
        code_context: str,
        is_dev_guide: bool = False,
    ) -> str:
        """
        Build a prompt for generating a specific section.

        Args:
            section_name: Name of the section to generate.
            section_description: Description of what the section should contain.
            code_context: Retrieved code context.
            is_dev_guide: Whether this is for developer guide.

        Returns:
            Prompt string.
        """
        doc_type = "开发者文档" if is_dev_guide else "用户文档"

        prompt = f"""请为{doc_type}生成"{section_name}"章节。

## 章节要求

{section_description}

## 相关代码

{code_context}

请生成"{section_name}"章节的内容，使用Markdown格式。
"""
        return prompt

    def build_mermaid_prompt(
        self,
        diagram_type: str,
        code_context: str,
        description: str,
    ) -> str:
        """
        Build a prompt for generating Mermaid diagrams.

        Args:
            diagram_type: Type of diagram (architecture, class, sequence).
            code_context: Retrieved code context.
            description: Description of what the diagram should show.

        Returns:
            Prompt string.
        """
        diagram_hints = {
            "architecture": "使用 graph TB 或 flowchart TB 格式",
            "class": "使用 classDiagram 格式",
            "sequence": "使用 sequenceDiagram 格式",
        }

        hint = diagram_hints.get(diagram_type, "")

        prompt = f"""请根据以下代码信息生成一个{diagram_type}类型的Mermaid图表。

## 图表要求

{description}

{hint}

## 代码信息

{code_context}

请只输出Mermaid图表代码，不要包含其他解释。图表应该简洁清晰，不要包含过多的细节。
"""

        return prompt

    def build_outline_system_prompt(self, doc_type: str = "dev_guide") -> str:
        """
        Build system prompt for outline generation.

        Args:
            doc_type: Document type ("dev_guide" or "user_guide").

        Returns:
            System prompt string.
        """
        lang = self.get_language_name()
        doc_type_name = "开发者文档" if doc_type == "dev_guide" else "用户文档"

        prompt = f"""你是一个专业的技术文档架构师。你的任务是分析项目代码结构，规划{doc_type_name}的章节结构。

## 输出要求

1. 输出必须是一个有效的 XML 结构
2. 不要用 markdown 代码块包裹
3. 直接输出 XML，不要有任何前言或解释
4. 使用 {lang} 编写

## 章节设计原则

1. 章节应该覆盖项目的关键方面
2. 每个章节应该有明确的主题和范围
3. 章节之间应该有逻辑关系
4. 为每个章节指定相关的源文件路径

## XML 格式要求

<doc_outline>
  <title>[文档标题]</title>
  <description>[项目简短描述]</description>
  <sections>
    <section id="section-1">
      <title>[章节标题]</title>
      <description>[章节内容描述，说明该章节应该包含什么内容]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[相关源文件路径]</file_path>
      </relevant_files>
      <related_sections>
        <related>[相关章节ID]</related>
      </related_sections>
    </section>
  </sections>
</doc_outline>
"""
        return prompt

    def build_outline_prompt(
        self,
        project_info: str,
        file_tree: str,
        readme: str,
        doc_type: str = "dev_guide",
    ) -> str:
        """
        Build prompt for generating document outline.

        Args:
            project_info: Project information string.
            file_tree: Project file tree.
            readme: README content.
            doc_type: Document type ("dev_guide" or "user_guide").

        Returns:
            Prompt string.
        """
        doc_type_name = "开发者文档" if doc_type == "dev_guide" else "用户文档"
        
        section_templates = self._get_section_templates(doc_type)

        prompt = f"""请分析以下项目信息，为{doc_type_name}设计章节结构。

## 项目信息

{project_info}

## 文件树结构

<file_tree>
{file_tree}
</file_tree>

## README 内容

<readme>
{readme}
</readme>

## 期望的章节类型

{section_templates}

## 要求

1. 生成 5-8 个章节
2. 每个章节必须指定相关的源文件路径（从文件树中选择实际存在的文件）
3. 按 importance 标注章节重要程度（high/medium/low）
4. 章节之间要有逻辑顺序
5. 直接输出 XML，不要用 markdown 代码块包裹
"""
        return prompt

    def _get_section_templates(self, doc_type: str) -> str:
        """Get section templates for the document type."""
        if doc_type == "dev_guide":
            return """- 项目架构：整体架构概述和模块职责
- 核心模块详解：核心模块的实现和设计思路
- API参考：公开API文档，包括类、函数、方法
- 数据模型：数据结构和数据模型说明
- 开发指南：开发者贡献指南，环境搭建、测试等"""
        else:
            return """- 项目简介：项目用途和核心功能介绍
- 安装指南：详细的安装步骤和环境要求
- 快速开始：最小可运行的使用示例
- 功能模块：按功能模块组织使用说明
- 配置说明：配置项的解释和使用方法
- 常见问题：常见使用场景和问题解答"""

    def build_section_content_prompt(
        self,
        section: "SectionInfo",
        code_context: str,
        doc_type: str = "dev_guide",
    ) -> str:
        """
        Build prompt for generating a single section's content.

        Args:
            section: SectionInfo object.
            code_context: Retrieved code context.
            doc_type: Document type ("dev_guide" or "user_guide").

        Returns:
            Prompt string.
        """
        lang = self.get_language_name()
        doc_type_name = "开发者文档" if doc_type == "dev_guide" else "用户文档"

        prompt = f"""请为{doc_type_name}生成"{section.title}"章节的详细内容。

## 章节信息

- **标题**: {section.title}
- **描述**: {section.description}
- **重要程度**: {section.importance}

## 相关源代码

{code_context}

## 输出要求

1. 使用 {lang} 编写
2. 使用 Markdown 格式
3. 章节标题使用 H2 (## {section.title})
4. 内容要基于提供的源代码，不要臆造
5. 引用源文件时使用格式：`文件路径:行号`

## Mermaid 图表要求（如适用）

- 架构图使用 `graph TB` 或 `flowchart TB`
- 类图使用 `classDiagram`
- 时序图使用 `sequenceDiagram`
- 图表要简洁清晰，节点名称简短

## 代码示例要求

- 示例代码要完整可运行
- 使用正确的语法高亮
- 包含必要的注释说明

请直接输出章节内容，不要有任何前言或结束语。
"""
        return prompt
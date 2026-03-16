"""
Developer guide generator.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..analyzer.metadata import ProjectMeta
from ..llm.client import LLMClient
from ..retriever.search import Retriever
from .prompts import PromptBuilder
from .requirements import CustomRequirements, format_requirements_for_prompt


@dataclass
class DevGuideConfig:
    """Configuration for developer guide generation."""

    include_architecture: bool = True
    include_api: bool = True
    include_contributing: bool = True
    language: str = "zh-CN"


class DevGuideGenerator:
    """
    Generate developer documentation from code.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        config: Optional[DevGuideConfig] = None,
    ):
        """
        Initialize the generator.

        Args:
            llm_client: LLM client for text generation.
            retriever: Retriever for code context.
            prompt_builder: Prompt builder.
            config: Generator configuration.
        """
        self.llm_client = llm_client
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.config = config or DevGuideConfig()

    def generate(
        self,
        project_meta: ProjectMeta,
        custom_requirements: Optional[CustomRequirements] = None,
        existing_readme: Optional[str] = None,
    ) -> str:
        """
        Generate the complete developer guide.

        Args:
            project_meta: Project metadata.
            custom_requirements: Custom requirements from user.
            existing_readme: Content of existing README.md.

        Returns:
            Generated developer guide in Markdown format.
        """
        # Build project info
        project_info = self._build_project_info(project_meta)

        # Build code context
        code_context = self._build_code_context()

        # Get custom requirements string
        custom_req_str = None
        if custom_requirements:
            custom_req_str = format_requirements_for_prompt(custom_requirements)

        # Build prompts
        system_prompt = self.prompt_builder.build_dev_guide_system_prompt(custom_req_str)
        user_prompt = self.prompt_builder.build_dev_guide_prompt(
            project_info=project_info,
            code_context=code_context,
            existing_docs=existing_readme,
        )

        # Generate document
        document = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        return document

    def _build_project_info(self, project_meta: ProjectMeta) -> str:
        """Build project information string."""
        parts = []

        if project_meta.name:
            parts.append(f"项目名称: {project_meta.name}")

        if project_meta.version:
            parts.append(f"版本: {project_meta.version}")

        if project_meta.description:
            parts.append(f"描述: {project_meta.description}")

        if project_meta.author:
            parts.append(f"作者: {project_meta.author}")

        if project_meta.dependencies:
            parts.append(f"依赖: {', '.join(project_meta.dependencies)}")

        if project_meta.python_requires:
            parts.append(f"Python版本要求: {project_meta.python_requires}")

        if project_meta.repository:
            parts.append(f"仓库地址: {project_meta.repository}")

        return "\n".join(parts)

    def _build_code_context(self) -> str:
        """Build code context for document generation."""
        # Use multiple queries to get comprehensive context
        queries = [
            "项目架构和模块结构",
            "核心类和接口定义",
            "主要函数和方法",
            "数据模型和数据结构",
            "测试用例和示例",
        ]

        all_contexts = []
        seen_files = set()

        for query in queries:
            results = self.retriever.search(query)
            for result in results[:5]:
                file_key = f"{result.chunk.source_file}:{result.chunk.metadata.get('name', '')}"
                if file_key not in seen_files:
                    seen_files.add(file_key)
                    context = f"""
### {result.chunk.source_file} - {result.chunk.metadata.get('name', result.chunk.chunk_type)}

**类型**: {result.chunk.chunk_type}
**分数**: {result.score:.3f}

{result.chunk.content}
"""
                    all_contexts.append(context)

        return "\n---\n".join(all_contexts)

    def generate_architecture_section(
        self,
        custom_requirements: Optional[CustomRequirements] = None,
    ) -> str:
        """
        Generate the architecture section with Mermaid diagram.

        Args:
            custom_requirements: Custom requirements.

        Returns:
            Generated architecture section.
        """
        # Get code context about module structure
        code_context = self.retriever.get_context_for_query(
            "模块导入 结构 架构",
            max_tokens=6000,
        )

        custom_req_str = None
        if custom_requirements:
            custom_req_str = format_requirements_for_prompt(custom_requirements)

        system_prompt = self.prompt_builder.build_dev_guide_system_prompt(custom_req_str)
        user_prompt = self.prompt_builder.build_section_prompt(
            section_name="项目架构",
            section_description="描述项目的整体架构，包括模块划分、模块职责、模块间的依赖关系。必须包含一个Mermaid架构图。",
            code_context=code_context,
            is_dev_guide=True,
        )

        return self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def generate_api_section(
        self,
        module_name: Optional[str] = None,
        custom_requirements: Optional[CustomRequirements] = None,
    ) -> str:
        """
        Generate API reference section.

        Args:
            module_name: Specific module to generate API for (optional).
            custom_requirements: Custom requirements.

        Returns:
            Generated API section.
        """
        query = f"API 接口 函数 类 {module_name}" if module_name else "API 公开接口 函数 类"
        code_context = self.retriever.get_context_for_query(
            query,
            max_tokens=8000,
        )

        custom_req_str = None
        if custom_requirements:
            custom_req_str = format_requirements_for_prompt(custom_requirements)

        system_prompt = self.prompt_builder.build_dev_guide_system_prompt(custom_req_str)

        section_desc = "列出所有公开的API，包括类、函数、方法。每个API需要包含签名、参数说明、返回值说明和使用示例。"
        if module_name:
            section_desc = f"列出 {module_name} 模块的所有公开API，包括类、函数、方法。每个API需要包含签名、参数说明、返回值说明和使用示例。"

        user_prompt = self.prompt_builder.build_section_prompt(
            section_name="API参考",
            section_description=section_desc,
            code_context=code_context,
            is_dev_guide=True,
        )

        return self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def generate_mermaid_diagram(
        self,
        diagram_type: str,
        description: str,
    ) -> str:
        """
        Generate a Mermaid diagram.

        Args:
            diagram_type: Type of diagram (architecture, class, sequence).
            description: Description of what the diagram should show.

        Returns:
            Mermaid diagram code.
        """
        # Get relevant context
        query = f"{diagram_type} {description}"
        code_context = self.retriever.get_context_for_query(query, max_tokens=4000)

        prompt = self.prompt_builder.build_mermaid_prompt(
            diagram_type=diagram_type,
            code_context=code_context,
            description=description,
        )

        return self.llm_client.generate(prompt=prompt)
"""
User guide generator.
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
class UserGuideConfig:
    """Configuration for user guide generation."""

    include_installation: bool = True
    include_quickstart: bool = True
    include_examples: bool = True
    language: str = "zh-CN"


class UserGuideGenerator:
    """
    Generate user documentation from code.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        config: Optional[UserGuideConfig] = None,
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
        self.config = config or UserGuideConfig()

    def generate(
        self,
        project_meta: ProjectMeta,
        custom_requirements: Optional[CustomRequirements] = None,
        existing_readme: Optional[str] = None,
    ) -> str:
        """
        Generate the complete user guide.

        Args:
            project_meta: Project metadata.
            custom_requirements: Custom requirements from user.
            existing_readme: Content of existing README.md.

        Returns:
            Generated user guide in Markdown format.
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
        system_prompt = self.prompt_builder.build_user_guide_system_prompt(custom_req_str)
        user_prompt = self.prompt_builder.build_user_guide_prompt(
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
            parts.append(f"主要依赖: {', '.join(project_meta.dependencies[:10])}")

        if project_meta.python_requires:
            parts.append(f"Python版本要求: {project_meta.python_requires}")

        return "\n".join(parts)

    def _build_code_context(self) -> str:
        """Build code context for document generation."""
        # Use multiple queries to get comprehensive context
        queries = [
            "项目入口和主要功能",
            "配置和使用方法",
            "核心类和函数",
            "使用示例和测试",
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

{result.chunk.content}
"""
                    all_contexts.append(context)

        return "\n---\n".join(all_contexts)

    def generate_section(
        self,
        section_name: str,
        section_description: str,
        custom_requirements: Optional[CustomRequirements] = None,
    ) -> str:
        """
        Generate a specific section of the user guide.

        Args:
            section_name: Name of the section.
            section_description: Description of the section content.
            custom_requirements: Custom requirements.

        Returns:
            Generated section content.
        """
        # Get relevant code context
        code_context = self.retriever.get_context_for_query(
            f"{section_name} {section_description}",
            max_tokens=4000,
        )

        # Build prompts
        custom_req_str = None
        if custom_requirements:
            custom_req_str = format_requirements_for_prompt(custom_requirements)

        system_prompt = self.prompt_builder.build_user_guide_system_prompt(custom_req_str)
        user_prompt = self.prompt_builder.build_section_prompt(
            section_name=section_name,
            section_description=section_description,
            code_context=code_context,
            is_dev_guide=False,
        )

        # Generate section
        return self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )
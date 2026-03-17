"""
Document outline generation for multi-stage document creation.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from ..analyzer.metadata import ProjectMeta
from ..llm.client import LLMClient
from ..retriever.search import Retriever
from .prompts import PromptBuilder


@dataclass
class SectionInfo:
    """Information about a single document section."""

    id: str
    title: str
    description: str
    importance: str = "medium"  # high, medium, low
    relevant_files: list[str] = field(default_factory=list)
    related_sections: list[str] = field(default_factory=list)


@dataclass
class DocOutline:
    """Document outline containing all sections."""

    title: str
    description: str
    sections: list[SectionInfo] = field(default_factory=list)


class OutlineGenerator:
    """
    Generate document outline using LLM.
    
    This is the first stage of multi-stage document generation.
    The LLM analyzes the project structure and determines what sections
    the document should have.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
    ):
        """
        Initialize the outline generator.

        Args:
            llm_client: LLM client for text generation.
            retriever: Retriever for code context.
            prompt_builder: Prompt builder.
        """
        self.llm_client = llm_client
        self.retriever = retriever
        self.prompt_builder = prompt_builder

    def generate_outline(
        self,
        project_meta: ProjectMeta,
        file_tree: str,
        readme: Optional[str] = None,
        doc_type: str = "dev_guide",
    ) -> DocOutline:
        """
        Generate document outline.

        Args:
            project_meta: Project metadata.
            file_tree: Project file tree string.
            readme: README content (optional).
            doc_type: Document type ("dev_guide" or "user_guide").

        Returns:
            DocOutline object containing the document structure.
        """
        # Build project info
        project_info = self._build_project_info(project_meta)

        # Build prompt
        system_prompt = self.prompt_builder.build_outline_system_prompt(doc_type)
        user_prompt = self.prompt_builder.build_outline_prompt(
            project_info=project_info,
            file_tree=file_tree,
            readme=readme or "",
            doc_type=doc_type,
        )

        # Generate outline
        response = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        # Parse response
        return self._parse_outline_response(response)

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

    def _parse_outline_response(self, response: str) -> DocOutline:
        """
        Parse LLM response into DocOutline.

        Args:
            response: LLM response string (XML format).

        Returns:
            DocOutline object.
        """
        # Clean up response
        response = response.strip()
        
        # Remove markdown code blocks if present
        response = re.sub(r'^```(?:xml)?\s*\n?', '', response)
        response = re.sub(r'\n?```\s*$', '', response)

        # Extract XML content
        xml_match = re.search(
            r'<doc_outline>[\s\S]*?</doc_outline>',
            response,
            re.MULTILINE
        )
        
        if not xml_match:
            # Fallback: create a default outline
            return self._create_default_outline()

        xml_content = xml_match.group(0)

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return self._create_default_outline()

        # Parse title and description
        title_elem = root.find('title')
        desc_elem = root.find('description')
        
        title = title_elem.text if title_elem is not None and title_elem.text else "项目文档"
        description = desc_elem.text if desc_elem is not None and desc_elem.text else ""

        # Parse sections
        sections = []
        sections_elem = root.find('sections')
        
        if sections_elem is not None:
            for i, section_elem in enumerate(sections_elem.findall('section')):
                section = self._parse_section(section_elem, i)
                sections.append(section)

        # If no sections found, create default
        if not sections:
            sections = self._create_default_sections()

        return DocOutline(
            title=title,
            description=description,
            sections=sections,
        )

    def _parse_section(self, elem: ET.Element, index: int) -> SectionInfo:
        """Parse a section element from XML."""
        section_id = elem.get('id', f"section-{index + 1}")
        
        title_elem = elem.find('title')
        title = title_elem.text if title_elem is not None and title_elem.text else f"章节 {index + 1}"
        
        desc_elem = elem.find('description')
        description = desc_elem.text if desc_elem is not None and desc_elem.text else ""
        
        importance_elem = elem.find('importance')
        importance = "medium"
        if importance_elem is not None and importance_elem.text:
            importance = importance_elem.text.lower()
            if importance not in ("high", "medium", "low"):
                importance = "medium"
        
        # Parse relevant files
        relevant_files = []
        files_elem = elem.find('relevant_files')
        if files_elem is not None:
            for file_elem in files_elem.findall('file_path'):
                if file_elem.text:
                    relevant_files.append(file_elem.text.strip())
        
        # Parse related sections
        related_sections = []
        related_elem = elem.find('related_sections')
        if related_elem is not None:
            for rel_elem in related_elem.findall('related'):
                if rel_elem.text:
                    related_sections.append(rel_elem.text.strip())

        return SectionInfo(
            id=section_id,
            title=title,
            description=description,
            importance=importance,
            relevant_files=relevant_files,
            related_sections=related_sections,
        )

    def _create_default_outline(self) -> DocOutline:
        """Create a default outline when parsing fails."""
        return DocOutline(
            title="项目文档",
            description="",
            sections=self._create_default_sections(),
        )

    def _create_default_sections(self) -> list[SectionInfo]:
        """Create default sections for developer guide."""
        return [
            SectionInfo(
                id="section-1",
                title="项目架构",
                description="描述项目的整体架构，包括模块划分、模块职责、模块间的依赖关系。",
                importance="high",
            ),
            SectionInfo(
                id="section-2",
                title="核心模块详解",
                description="详细介绍核心模块的实现和设计思路。",
                importance="high",
            ),
            SectionInfo(
                id="section-3",
                title="API参考",
                description="列出所有公开的API，包括类、函数、方法及其使用示例。",
                importance="high",
            ),
            SectionInfo(
                id="section-4",
                title="数据模型",
                description="描述项目中的数据结构和数据模型。",
                importance="medium",
            ),
            SectionInfo(
                id="section-5",
                title="开发指南",
                description="开发者贡献指南，包括环境搭建、测试、代码规范等。",
                importance="medium",
            ),
        ]
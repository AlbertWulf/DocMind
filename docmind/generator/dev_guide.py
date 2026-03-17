"""
Developer guide generator with multi-stage generation support.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..analyzer.metadata import ProjectMeta
from ..llm.client import LLMClient
from ..retriever.search import Retriever
from .outline import DocOutline, OutlineGenerator, SectionInfo
from .prompts import PromptBuilder
from .requirements import CustomRequirements, format_requirements_for_prompt


@dataclass
class DevGuideConfig:
    """Configuration for developer guide generation."""

    include_architecture: bool = True
    include_api: bool = True
    include_contributing: bool = True
    language: str = "zh-CN"
    use_multi_stage: bool = True  # Enable multi-stage generation
    max_section_tokens: int = 6000  # Max tokens per section context


class DevGuideGenerator:
    """
    Generate developer documentation from code.
    
    Supports two generation modes:
    1. Multi-stage (default): First generates outline, then generates each section
    2. Single-stage: Generates entire document in one LLM call
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
        
        # Initialize outline generator
        self.outline_generator = OutlineGenerator(
            llm_client=llm_client,
            retriever=retriever,
            prompt_builder=prompt_builder,
        )

    def generate(
        self,
        project_meta: ProjectMeta,
        file_tree: Optional[str] = None,
        custom_requirements: Optional[CustomRequirements] = None,
        existing_readme: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> str:
        """
        Generate the complete developer guide.

        Args:
            project_meta: Project metadata.
            file_tree: Project file tree string (optional, will be built if not provided).
            custom_requirements: Custom requirements from user.
            existing_readme: Content of existing README.md.
            progress_callback: Callback for progress updates (section_title, current, total).

        Returns:
            Generated developer guide in Markdown format.
        """
        if self.config.use_multi_stage:
            return self._generate_multi_stage(
                project_meta=project_meta,
                file_tree=file_tree,
                custom_requirements=custom_requirements,
                existing_readme=existing_readme,
                progress_callback=progress_callback,
            )
        else:
            return self._generate_single_stage(
                project_meta=project_meta,
                custom_requirements=custom_requirements,
                existing_readme=existing_readme,
            )

    def _generate_multi_stage(
        self,
        project_meta: ProjectMeta,
        file_tree: Optional[str],
        custom_requirements: Optional[CustomRequirements],
        existing_readme: Optional[str],
        progress_callback: Optional[Callable[[str, int, int], None]],
    ) -> str:
        """
        Generate document using multi-stage approach.
        
        Stage 1: Generate outline
        Stage 2: Generate each section
        Stage 3: Assemble final document
        """
        # Build file tree if not provided
        if file_tree is None:
            file_tree = self._build_file_tree()
        
        # Stage 1: Generate outline
        outline = self.outline_generator.generate_outline(
            project_meta=project_meta,
            file_tree=file_tree,
            readme=existing_readme,
            doc_type="dev_guide",
        )
        
        # Stage 2: Generate each section
        sections_content = []
        total_sections = len(outline.sections)
        
        for i, section in enumerate(outline.sections):
            # Report progress
            if progress_callback:
                progress_callback(section.title, i + 1, total_sections)
            
            # Generate section content
            content = self._generate_section(
                section=section,
                custom_requirements=custom_requirements,
            )
            sections_content.append(content)
        
        # Stage 3: Assemble document
        return self._assemble_document(outline, sections_content)

    def _generate_single_stage(
        self,
        project_meta: ProjectMeta,
        custom_requirements: Optional[CustomRequirements],
        existing_readme: Optional[str],
    ) -> str:
        """Generate document in a single LLM call (legacy method)."""
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

    def _generate_section(
        self,
        section: SectionInfo,
        custom_requirements: Optional[CustomRequirements] = None,
    ) -> str:
        """
        Generate content for a single section.

        Args:
            section: Section information.
            custom_requirements: Custom requirements.

        Returns:
            Generated section content.
        """
        # Build code context for this section
        code_context = self._build_section_context(section)

        # Build prompt
        user_prompt = self.prompt_builder.build_section_content_prompt(
            section=section,
            code_context=code_context,
            doc_type="dev_guide",
        )
        
        custom_req_str = None
        if custom_requirements:
            custom_req_str = format_requirements_for_prompt(custom_requirements)
        
        system_prompt = self.prompt_builder.build_dev_guide_system_prompt(custom_req_str)

        # Generate section content
        return self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def _build_section_context(self, section: SectionInfo) -> str:
        """
        Build code context for a specific section.

        Args:
            section: Section information.

        Returns:
            Code context string.
        """
        context_parts = []
        seen_chunks = set()
        
        # First, try to get context from relevant files specified in the section
        if section.relevant_files:
            for file_path in section.relevant_files:
                # Search for chunks from this specific file
                results = self.retriever.search(file_path)
                for result in results:
                    if result.chunk.source_file == file_path:
                        chunk_key = f"{result.chunk.source_file}:{result.chunk.metadata.get('name', '')}"
                        if chunk_key not in seen_chunks:
                            seen_chunks.add(chunk_key)
                            context_parts.append(self._format_chunk(result))
        
        # Then, search using section title and description as query
        query = f"{section.title} {section.description}"
        results = self.retriever.search(query)
        
        for result in results[:10]:
            chunk_key = f"{result.chunk.source_file}:{result.chunk.metadata.get('name', '')}"
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                context_parts.append(self._format_chunk(result))
        
        # Limit context size
        return self._limit_context(context_parts, self.config.max_section_tokens)

    def _format_chunk(self, result) -> str:
        """Format a search result chunk for the prompt."""
        return f"""### {result.chunk.source_file} - {result.chunk.metadata.get('name', result.chunk.chunk_type)}

**类型**: {result.chunk.chunk_type}
**相关度**: {result.score:.3f}

```
{result.chunk.content}
```
"""

    def _limit_context(self, context_parts: list[str], max_tokens: int) -> str:
        """Limit context to a maximum number of tokens."""
        import tiktoken
        
        tokenizer = tiktoken.get_encoding("cl100k_base")
        result_parts = []
        total_tokens = 0
        
        for part in context_parts:
            part_tokens = len(tokenizer.encode(part))
            if total_tokens + part_tokens <= max_tokens:
                result_parts.append(part)
                total_tokens += part_tokens
            else:
                break
        
        return "\n---\n".join(result_parts)

    def _build_file_tree(self) -> str:
        """Build a file tree string from the retriever's chunks."""
        files = set()
        for chunk in self.retriever.chunks:
            files.add(chunk.source_file)
        
        # Sort and format
        sorted_files = sorted(files)
        return "\n".join(sorted_files)

    def _assemble_document(
        self,
        outline: DocOutline,
        sections_content: list[str],
    ) -> str:
        """
        Assemble the final document from outline and sections.

        Args:
            outline: Document outline.
            sections_content: List of generated section contents.

        Returns:
            Complete document string.
        """
        parts = []
        
        # Document title
        parts.append(f"# {outline.title}\n")
        
        # Document description
        if outline.description:
            parts.append(f"\n{outline.description}\n")
        
        # Table of contents
        parts.append("\n## 目录\n")
        for i, section in enumerate(outline.sections):
            anchor = section.title.lower().replace(" ", "-")
            parts.append(f"- [{section.title}](#{anchor})\n")
        
        # Sections
        for content in sections_content:
            parts.append(f"\n{content}\n")
        
        return "\n".join(parts)

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

    def generate_outline_only(
        self,
        project_meta: ProjectMeta,
        file_tree: Optional[str] = None,
        existing_readme: Optional[str] = None,
    ) -> DocOutline:
        """
        Generate only the document outline without generating content.
        
        Useful for previewing the structure before full generation.

        Args:
            project_meta: Project metadata.
            file_tree: Project file tree string.
            existing_readme: Content of existing README.md.

        Returns:
            DocOutline object.
        """
        if file_tree is None:
            file_tree = self._build_file_tree()
        
        return self.outline_generator.generate_outline(
            project_meta=project_meta,
            file_tree=file_tree,
            readme=existing_readme,
            doc_type="dev_guide",
        )

    def generate_section_by_id(
        self,
        outline: DocOutline,
        section_id: str,
        custom_requirements: Optional[CustomRequirements] = None,
    ) -> Optional[str]:
        """
        Generate a single section by its ID.
        
        Useful for regenerating specific sections.

        Args:
            outline: Document outline.
            section_id: Section ID to generate.
            custom_requirements: Custom requirements.

        Returns:
            Generated section content or None if section not found.
        """
        for section in outline.sections:
            if section.id == section_id:
                return self._generate_section(section, custom_requirements)
        return None
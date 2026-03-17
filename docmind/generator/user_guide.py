"""
User guide generator with multi-stage generation.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from ..analyzer.metadata import ProjectMeta
from ..llm.client import LLMClient
from ..retriever.search import Retriever
from .outline import DocOutline, OutlineGenerator, SectionInfo
from .prompts import PromptBuilder
from .requirements import CustomRequirements, format_requirements_for_prompt


@dataclass
class UserGuideConfig:
    """Configuration for user guide generation."""

    include_installation: bool = True
    include_quickstart: bool = True
    include_examples: bool = True
    language: str = "zh-CN"
    max_section_tokens: int = 5000


class UserGuideGenerator:
    """
    Generate user documentation from code.
    
    Uses a two-stage generation process:
    1. Generate document outline based on project structure
    2. Generate each section with focused code context
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
        Generate the complete user guide.

        Args:
            project_meta: Project metadata.
            file_tree: Project file tree string (optional).
            custom_requirements: Custom requirements from user.
            existing_readme: Content of existing README.md.
            progress_callback: Callback for progress updates (section_title, current, total).

        Returns:
            Generated user guide in Markdown format.
        """
        # Build file tree if not provided
        if file_tree is None:
            file_tree = self._build_file_tree()
        
        # Stage 1: Generate outline
        outline = self.outline_generator.generate_outline(
            project_meta=project_meta,
            file_tree=file_tree,
            readme=existing_readme,
            doc_type="user_guide",
        )
        
        # Stage 2: Generate each section
        sections_content = []
        total_sections = len(outline.sections)
        
        for i, section in enumerate(outline.sections):
            if progress_callback:
                progress_callback(section.title, i + 1, total_sections)
            
            content = self._generate_section_content(
                section=section,
                custom_requirements=custom_requirements,
            )
            sections_content.append(content)
        
        # Stage 3: Assemble document
        return self._assemble_document(outline, sections_content)

    def _generate_section_content(
        self,
        section: SectionInfo,
        custom_requirements: Optional[CustomRequirements] = None,
    ) -> str:
        """Generate content for a single section."""
        code_context = self._build_section_context(section)

        user_prompt = self.prompt_builder.build_section_content_prompt(
            section=section,
            code_context=code_context,
            doc_type="user_guide",
        )
        
        custom_req_str = None
        if custom_requirements:
            custom_req_str = format_requirements_for_prompt(custom_requirements)
        
        system_prompt = self.prompt_builder.build_user_guide_system_prompt(custom_req_str)

        return self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def _build_section_context(self, section: SectionInfo) -> str:
        """Build code context for a specific section."""
        context_parts = []
        seen_chunks = set()
        
        # Get context from relevant files specified in the section
        if section.relevant_files:
            for file_path in section.relevant_files:
                results = self.retriever.search(file_path)
                for result in results:
                    if result.chunk.source_file == file_path:
                        chunk_key = f"{result.chunk.source_file}:{result.chunk.metadata.get('name', '')}"
                        if chunk_key not in seen_chunks:
                            seen_chunks.add(chunk_key)
                            context_parts.append(self._format_chunk(result))
        
        # Search using section title and description
        query = f"{section.title} {section.description}"
        results = self.retriever.search(query)
        
        for result in results[:8]:
            chunk_key = f"{result.chunk.source_file}:{result.chunk.metadata.get('name', '')}"
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                context_parts.append(self._format_chunk(result))
        
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
        return "\n".join(sorted(files))

    def _assemble_document(
        self,
        outline: DocOutline,
        sections_content: list[str],
    ) -> str:
        """Assemble the final document from outline and sections."""
        parts = []
        
        parts.append(f"# {outline.title}\n")
        
        if outline.description:
            parts.append(f"\n{outline.description}\n")
        
        parts.append("\n## 目录\n")
        for section in outline.sections:
            anchor = section.title.lower().replace(" ", "-")
            parts.append(f"- [{section.title}](#{anchor})\n")
        
        for content in sections_content:
            parts.append(f"\n{content}\n")
        
        return "\n".join(parts)

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
        code_context = self.retriever.get_context_for_query(
            f"{section_name} {section_description}",
            max_tokens=4000,
        )

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

        return self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def generate_outline_only(
        self,
        project_meta: ProjectMeta,
        file_tree: Optional[str] = None,
        existing_readme: Optional[str] = None,
    ) -> DocOutline:
        """
        Generate only the document outline without generating content.
        
        Useful for previewing the structure before full generation.
        """
        if file_tree is None:
            file_tree = self._build_file_tree()
        
        return self.outline_generator.generate_outline(
            project_meta=project_meta,
            file_tree=file_tree,
            readme=existing_readme,
            doc_type="user_guide",
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
        """
        for section in outline.sections:
            if section.id == section_id:
                return self._generate_section_content(section, custom_requirements)
        return None
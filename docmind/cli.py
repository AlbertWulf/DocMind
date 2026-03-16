"""
Command-line interface for DocMind.
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from . import __version__
from .config import Config, create_default_config, load_config, merge_cli_args
from .utils.progress import ProgressDisplay

app = typer.Typer(
    name="docmind",
    help="AI-powered documentation generator for Python projects",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"docmind version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """DocMind - AI-powered documentation generator."""
    pass


@app.command()
def init(
    output_dir: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Directory to create configuration files in",
    ),
) -> None:
    """
    Initialize DocMind configuration files.

    Creates docmind.yaml and docmind-requirements.md template files.
    """
    output_dir = output_dir.resolve()
    config_path = output_dir / "docmind.yaml"
    requirements_path = output_dir / "docmind-requirements.md"

    # Check if files already exist
    if config_path.exists():
        console.print(f"[yellow]Warning:[/yellow] {config_path} already exists, skipping.")
    else:
        create_default_config(str(config_path))
        console.print(f"[green]Created:[/green] {config_path}")

    if requirements_path.exists():
        console.print(f"[yellow]Warning:[/yellow] {requirements_path} already exists, skipping.")
    else:
        from .generator.requirements import create_example_requirements
        create_example_requirements(str(requirements_path))
        console.print(f"[green]Created:[/green] {requirements_path}")

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("1. Edit docmind.yaml to configure your project")
    console.print("2. (Optional) Edit docmind-requirements.md to customize document format")
    console.print("3. Run: docmind generate /path/to/your/project")


@app.command()
def generate(
    project_path: Path = typer.Argument(
        ...,
        help="Path to the Python project directory",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for generated documents",
        file_okay=False,
        dir_okay=True,
        writable=True,
    ),
    requirements_file: Optional[Path] = typer.Option(
        None,
        "--requirements",
        "-r",
        help="Path to custom requirements file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    only: Optional[str] = typer.Option(
        None,
        "--only",
        help="Generate only specified document type: 'user' or 'dev'",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Show verbose output",
    ),
) -> None:
    """
    Generate documentation for a Python project.

    Analyzes the project code and generates two Markdown documents:
    - user-guide.md: User documentation focused on usage
    - dev-guide.md: Developer documentation focused on API and architecture
    """
    progress = ProgressDisplay(verbose=verbose)
    project_path = project_path.resolve()

    # Load configuration
    progress.start(f"Loading configuration...")
    config = load_config(str(config_file) if config_file else None)

    # Override config with CLI arguments
    cli_args = {}
    if requirements_file:
        cli_args["custom_requirements.file"] = str(requirements_file)

    config = merge_cli_args(config, cli_args)

    # Resolve output directory
    if output_dir:
        output_path = output_dir.resolve()
    else:
        output_path = project_path / "docs"

    progress.stop()
    progress.print(f"Project: {project_path}")
    progress.print(f"Output: {output_path}")

    # Run the main generation process
    try:
        from .analyzer.extractor import CodeExtractor
        from .analyzer.metadata import extract_project_metadata
        from .embedder.encoder import Encoder
        from .embedder.splitter import TextSplitter, should_include_file
        from .generator.dev_guide import DevGuideGenerator, DevGuideConfig
        from .generator.prompts import PromptBuilder, PromptConfig
        from .generator.requirements import load_requirements
        from .generator.user_guide import UserGuideGenerator, UserGuideConfig
        from .llm.client import LLMClient
        from .output.writer import MarkdownWriter
        from .retriever.search import Retriever

        # Step 1: Analyze project
        progress.section("Analyzing project structure")

        # Extract project metadata
        project_meta = extract_project_metadata(project_path)

        # Override with config values if provided
        if config.project.name:
            project_meta.name = config.project.name
        if config.project.version:
            project_meta.version = config.project.version
        if config.project.description:
            project_meta.description = config.project.description
        if config.project.author:
            project_meta.author = config.project.author

        if project_meta.name:
            progress.print_info(f"Project name: {project_meta.name}")
        if project_meta.version:
            progress.print_info(f"Version: {project_meta.version}")

        # Find Python files
        source_dir = project_path / config.analyzer.source_dir
        python_files = []
        for py_file in source_dir.rglob("*.py"):
            rel_path = py_file.relative_to(project_path)
            if should_include_file(rel_path, config.analyzer.exclude):
                python_files.append(py_file)

        progress.print(f"Found {len(python_files)} Python files")

        if not python_files:
            progress.print_warning("No Python files found. Generating empty documentation.")

            # Create empty documentation
            output_path.mkdir(parents=True, exist_ok=True)
            writer = MarkdownWriter(output_path, project_meta.name or "Project")

            empty_content = """
## 说明

未找到有效的 Python 源代码文件。请检查：

1. 项目路径是否正确
2. 源代码目录配置是否正确（默认为项目根目录）
3. 排除规则是否过于严格

## 配置建议

可以在 `docmind.yaml` 中配置：
- `analyzer.source_dir`: 指定源代码目录
- `analyzer.exclude`: 调整排除规则
"""

            if only != "dev":
                writer.write_user_guide(empty_content, config.output.user_guide)
                progress.print_success(f"Created {config.output.user_guide}")

            if only != "user":
                writer.write_dev_guide(empty_content, config.output.dev_guide)
                progress.print_success(f"Created {config.output.dev_guide}")

            return

        # Step 2: Extract code structures
        progress.section("Extracting code structures")
        progress.start_progress("Analyzing files", len(python_files))

        all_chunks = []
        splitter = TextSplitter(
            chunk_size=config.splitter.chunk_size,
            chunk_overlap=config.splitter.chunk_overlap,
        )

        for i, py_file in enumerate(python_files):
            try:
                extractor = CodeExtractor(
                    py_file,
                    include_private=config.analyzer.include_private,
                )
                structure = extractor.extract()

                # Split into chunks
                chunks = splitter.split_code_structure(
                    structure,
                    str(py_file.relative_to(project_path)),
                )
                all_chunks.extend(chunks)

                progress.update_progress("Analyzing files")
            except SyntaxError as e:
                progress.print_warning(f"Syntax error in {py_file}: {e}")
            except Exception as e:
                if verbose:
                    progress.print_warning(f"Error processing {py_file}: {e}")

        progress.complete_progress("Analyzing files")
        progress.print(f"Extracted {len(all_chunks)} code chunks")

        # Step 3: Build embeddings
        progress.section("Building embeddings")

        provider = config.embedder.provider
        if provider == "openai":
            progress.start(f"Connecting to embedding API ({config.embedder.model})...")
        else:
            progress.start(f"Loading embedding model ({config.embedder.model})...")

        encoder = Encoder(
            provider=config.embedder.provider,
            model=config.embedder.model,
            device=config.embedder.device,
            batch_size=config.embedder.batch_size,
            max_length=config.embedder.max_length,
            api_key=config.embedder.api_key or None,
            base_url=config.embedder.base_url,
            dimensions=config.embedder.dimensions,
            timeout=config.embedder.timeout,
        )

        progress.stop()
        progress.start_progress("Encoding", len(all_chunks) // config.embedder.batch_size + 1)

        retriever = Retriever(encoder, top_k=config.retriever.top_k)
        retriever.build_index(all_chunks)

        progress.complete_progress("Encoding")
        progress.print(f"Built index with {retriever.get_chunk_count()} chunks")

        # Step 4: Initialize LLM
        progress.section("Connecting to LLM")
        progress.start(f"Connecting to {config.llm.base_url}...")

        llm_client = LLMClient(
            base_url=config.llm.base_url,
            model=config.llm.model,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            timeout=config.llm.timeout,
        )

        # Test connection
        if not llm_client.test_connection():
            progress.stop()
            progress.print_error(f"Cannot connect to LLM server at {config.llm.base_url}")
            progress.print_info("Make sure your vLLM server is running:")
            progress.print_info("  vllm serve <model_name> --api-key EMPTY")
            raise typer.Exit(1)

        progress.stop()
        progress.print_success(f"Connected to {config.llm.model}")

        # Step 5: Load custom requirements
        custom_requirements = None
        if config.custom_requirements.file:
            req_path = Path(config.custom_requirements.file)
            if not req_path.is_absolute():
                req_path = project_path / req_path
            if req_path.exists():
                custom_requirements = load_requirements(str(req_path))
                if custom_requirements:
                    progress.print_success(f"Loaded custom requirements from {req_path}")

        # Step 6: Generate documentation
        progress.section("Generating documentation")

        prompt_builder = PromptBuilder(PromptConfig(language=config.output.language))

        # Read existing README if exists
        readme_path = project_path / "README.md"
        existing_readme = None
        if readme_path.exists():
            with open(readme_path, encoding="utf-8") as f:
                existing_readme = f.read()

        # Prepare output
        output_path.mkdir(parents=True, exist_ok=True)
        writer = MarkdownWriter(output_path, project_meta.name or "Project")

        # Generate user guide
        if only != "dev":
            progress.start("Generating user guide...")
            user_gen = UserGuideGenerator(
                llm_client=llm_client,
                retriever=retriever,
                prompt_builder=prompt_builder,
                config=UserGuideConfig(
                    language=config.output.language,
                    include_installation=config.generator.user_guide.include_installation,
                    include_quickstart=config.generator.user_guide.include_quickstart,
                    include_examples=config.generator.user_guide.include_examples,
                ),
            )

            user_guide = user_gen.generate(
                project_meta=project_meta,
                custom_requirements=custom_requirements,
                existing_readme=existing_readme,
            )

            user_path = writer.write_user_guide(user_guide, config.output.user_guide)
            progress.stop()
            progress.print_success(f"Created {user_path}")

        # Generate developer guide
        if only != "user":
            progress.start("Generating developer guide...")
            dev_gen = DevGuideGenerator(
                llm_client=llm_client,
                retriever=retriever,
                prompt_builder=prompt_builder,
                config=DevGuideConfig(
                    language=config.output.language,
                    include_architecture=config.generator.dev_guide.include_architecture,
                    include_api=config.generator.dev_guide.include_api,
                    include_contributing=config.generator.dev_guide.include_contributing,
                ),
            )

            dev_guide = dev_gen.generate(
                project_meta=project_meta,
                custom_requirements=custom_requirements,
                existing_readme=existing_readme,
            )

            dev_path = writer.write_dev_guide(dev_guide, config.output.dev_guide)
            progress.stop()
            progress.print_success(f"Created {dev_path}")

        # Create index
        writer.create_index(
            user_guide_path=config.output.user_guide if only != "dev" else None,
            dev_guide_path=config.output.dev_guide if only != "user" else None,
        )

        # Done
        progress.stop_progress()
        progress.print()
        progress.print_success("Documentation generation complete!")
        progress.print(f"Output directory: {output_path}")

    except KeyboardInterrupt:
        progress.print()
        progress.print_warning("Generation interrupted by user")
        raise typer.Exit(1)
    except Exception as e:
        progress.print_error(f"Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
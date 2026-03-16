# DocMind 设计文档

## 概述

DocMind 是一个基于 LLM 的 Python 项目文档生成工具，能够自动分析代码并生成用户文档和开发文档，支持完全离线使用。

## 需求总结

| 项目 | 选择 |
|------|------|
| 文档类型 | 两套独立：用户文档 + 开发文档 |
| 输出格式 | 单文件手册 |
| 代码输入 | 仅本地路径 |
| 离线支持 | 完全离线（vLLM + 本地嵌入模型） |
| 分析粒度 | 函数/类级别 |
| 语言支持 | 主要Python项目 |
| 使用方式 | 命令行工具 |
| 配置管理 | 配置文件优先 |
| 增量更新 | 不支持 |
| 图表 | 自动生成Mermaid |
| 代码示例 | LLM分析已有示例后生成 |
| 项目元信息 | 配置文件 + 代码提取 |
| 进度显示 | 简略进度 |
| 输出语言 | 可配置 |
| 错误处理 | 生成说明性空文档 |

## 项目架构

### 目录结构

```
docmind/
├── pyproject.toml              # 项目配置和依赖
├── README.md                   # 项目说明
├── docmind.yaml.example        # 配置文件示例
│
├── docmind/                    # 主包
│   ├── __init__.py
│   ├── cli.py                  # CLI入口
│   ├── config.py               # 配置管理
│   │
│   ├── analyzer/               # 代码分析模块
│   │   ├── __init__.py
│   │   ├── parser.py           # AST解析器
│   │   ├── extractor.py        # 代码结构提取
│   │   └── metadata.py         # 项目元信息提取
│   │
│   ├── embedder/               # 嵌入模块
│   │   ├── __init__.py
│   │   ├── splitter.py         # 文本分割器
│   │   └── encoder.py          # 向量编码器
│   │
│   ├── retriever/              # 检索模块
│   │   ├── __init__.py
│   │   ├── index.py            # FAISS索引管理
│   │   └── search.py           # 相似度检索
│   │
│   ├── generator/              # 文档生成模块
│   │   ├── __init__.py
│   │   ├── prompts.py          # 提示词模板
│   │   ├── requirements.py     # 自定义需求解析
│   │   ├── user_guide.py       # 用户文档生成器
│   │   ├── dev_guide.py        # 开发文档生成器
│   │   └── mermaid.py          # Mermaid图表生成
│   │
│   ├── llm/                    # LLM接口模块
│   │   ├── __init__.py
│   │   └── client.py           # OpenAI兼容客户端
│   │
│   ├── output/                 # 输出模块
│   │   ├── __init__.py
│   │   └── writer.py          # Markdown输出
│   │
│   └── utils/                  # 工具模块
│       ├── __init__.py
│       ├── progress.py         # 进度显示
│       └── logger.py           # 日志工具
│
└── tests/                      # 测试目录
    ├── __init__.py
    ├── test_analyzer.py
    ├── test_embedder.py
    └── ...
```

### 核心模块职责

| 模块 | 职责 | 关键功能 |
|------|------|----------|
| **cli** | 命令行入口 | 参数解析、命令分发、进度显示 |
| **config** | 配置管理 | 加载yaml配置、合并命令行参数、验证配置 |
| **analyzer** | 代码分析 | AST解析、提取类/函数/模块结构、提取项目元信息 |
| **embedder** | 向量嵌入 | 文本分割、调用本地嵌入模型生成向量 |
| **retriever** | 检索 | 构建FAISS索引、相似度检索 |
| **generator** | 文档生成 | 构建提示词、调用LLM、生成用户/开发文档 |
| **llm** | LLM接口 | OpenAI兼容API调用、流式响应处理 |
| **output** | 输出 | Markdown格式化、文件写入 |
| **utils** | 工具 | 进度条、日志、错误处理 |

## 数据流程

```
本地代码目录
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                        1. 代码分析阶段                            │
├──────────────────────────────────────────────────────────────────┤
│  analyzer.parser          → 遍历.py文件，AST解析                  │
│  analyzer.extractor       → 提取类/函数/模块信息                  │
│  analyzer.metadata        → 从pyproject.toml提取项目元信息        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼ 输出: CodeStructure对象列表
┌──────────────────────────────────────────────────────────────────┐
│                        2. 嵌入阶段                                │
├──────────────────────────────────────────────────────────────────┤
│  embedder.splitter        → 将代码块分割为合适大小的文本片段        │
│  embedder.encoder         → 调用sentence-transformers生成向量     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼ 输出: 向量列表 + 文本片段
┌──────────────────────────────────────────────────────────────────┐
│                        3. 索引阶段                                │
├──────────────────────────────────────────────────────────────────┤
│  retriever.index          → 构建FAISS向量索引                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                        4. 文档生成阶段                            │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐        ┌─────────────────────┐          │
│  │   用户文档生成流程   │        │   开发文档生成流程   │          │
│  ├─────────────────────┤        ├─────────────────────┤          │
│  │ 1. 检索相关代码     │        │ 1. 检索相关代码     │          │
│  │ 2. 构建提示词       │        │ 2. 构建提示词       │          │
│  │    (含自定义需求)   │        │    (含自定义需求)   │          │
│  │ 3. 调用LLM生成      │        │ 3. 调用LLM生成      │          │
│  │ 4. 生成Mermaid图表  │        │ 4. 生成Mermaid图表  │          │
│  └──────────┬──────────┘        └──────────┬──────────┘          │
│             └──────────────┬───────────────┘                      │
│                            ▼                                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼ 输出: 用户文档内容 + 开发文档内容
┌──────────────────────────────────────────────────────────────────┐
│                        5. 输出阶段                                │
├──────────────────────────────────────────────────────────────────┤
│  output.writer            → 格式化Markdown、写入文件              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────┐    ┌──────────────┐
              │ user-guide.md│    │ dev-guide.md │
              └──────────────┘    └──────────────┘
```

## 核心数据结构

```python
# 代码结构信息
@dataclass
class CodeStructure:
    file_path: str              # 文件路径
    module_name: str            # 模块名
    classes: List[ClassInfo]    # 类信息
    functions: List[FuncInfo]   # 函数信息
    imports: List[str]          # 导入列表
    docstring: Optional[str]    # 模块文档字符串
    source_code: str            # 源代码

# 类信息
@dataclass
class ClassInfo:
    name: str
    bases: List[str]            # 父类
    methods: List[FuncInfo]     # 方法
    attributes: List[str]        # 属性
    docstring: Optional[str]
    source_code: str
    line_start: int
    line_end: int

# 函数信息
@dataclass
class FuncInfo:
    name: str
    args: List[ArgInfo]         # 参数
    returns: Optional[str]       # 返回类型
    docstring: Optional[str]
    source_code: str
    line_start: int
    line_end: int

# 参数信息
@dataclass
class ArgInfo:
    name: str
    type_hint: Optional[str]
    default: Optional[str]

# 项目元信息
@dataclass
class ProjectMeta:
    name: str
    version: str
    description: str
    dependencies: List[str]
    python_requires: Optional[str]
    author: Optional[str]
    license: Optional[str]
```

## 配置文件设计

```yaml
# 项目信息
project:
  name: ""
  version: ""
  description: ""
  author: ""

# 自定义需求
custom_requirements:
  file: "docmind-requirements.md"
  apply_to:
    user_guide: true
    dev_guide: true

# 输出配置
output:
  user_guide: "user-guide.md"
  dev_guide: "dev-guide.md"
  language: "zh-CN"

# 代码分析配置
analyzer:
  source_dir: "."
  exclude:
    - "tests/"
    - "examples/"
    - "docs/"
    - "**/migrations/"
  include_private: false

# LLM配置
llm:
  base_url: "http://localhost:8000/v1"
  model: "Qwen/Qwen2.5-72B-Instruct"
  api_key: "EMPTY"
  temperature: 0.7
  max_tokens: 4096

# 嵌入模型配置
embedder:
  model: "BAAI/bge-m3"
  device: "cuda"
  batch_size: 32

# 检索配置
retriever:
  top_k: 15

# 文本分割配置
splitter:
  chunk_size: 500
  chunk_overlap: 100

# 文档生成配置
generator:
  user_guide:
    include_installation: true
    include_quickstart: true
    include_examples: true
  dev_guide:
    include_architecture: true
    include_api: true
    include_contributing: true
  mermaid:
    enabled: true
    max_diagrams: 5
```

## CLI接口设计

```bash
# 基本用法
docmind generate /path/to/project

# 指定配置文件
docmind generate /path/to/project --config ./docmind.yaml

# 仅生成用户文档
docmind generate /path/to/project --only user

# 仅生成开发文档
docmind generate /path/to/project --only dev

# 指定输出目录
docmind generate /path/to/project --output ./docs

# 使用自定义需求文件
docmind generate /path/to/project --requirements ./docmind-requirements.md

# 显示详细日志
docmind generate /path/to/project --verbose

# 初始化配置文件
docmind init
```

## 自定义需求文件设计

用户可以通过Markdown文件定义文档生成的特定要求：

```markdown
# 文档自定义需求

## 通用要求

- 所有代码示例使用 Python 3.10+ 的类型注解语法
- 每个函数说明必须包含"参数"、"返回值"、"异常"三个小节
- 使用中文编写，但保留英文技术术语

## 用户文档要求

### 类说明格式
[用户定义的类说明格式...]

## 开发文档要求

### API 文档
[用户定义的API文档格式...]
```

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| **CLI框架** | Typer |
| **配置解析** | PyYAML + Pydantic |
| **AST解析** | Python内置ast模块 |
| **向量嵌入** | sentence-transformers |
| **向量检索** | faiss-cpu |
| **LLM调用** | openai SDK（兼容vLLM） |

## 依赖列表

```toml
[project]
dependencies = [
    "typer>=0.9.0",
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "sentence-transformers>=2.2.0",
    "faiss-cpu>=1.7.0",
    "openai>=1.0.0",
    "rich>=13.0.0",
]
```
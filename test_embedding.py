#!/usr/bin/env python3
"""测试 Embedding 连接脚本"""

import os
import sys

# 测试阿里云 DashScope Embedding API
def test_dashscope_embedding():
    """测试阿里云 DashScope Embedding 连接"""
    import openai

    api_key = "sk-05798cf9af19473fa8a9cfd8cc8d2bc3"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = "text-embedding-v4"

    print("=" * 60)
    print("测试阿里云 DashScope Embedding API")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print()

    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60
        )

        # 测试文本
        test_texts = ["这是一个测试文本", "This is a test text"]

        print(f"发送请求，文本数量: {len(test_texts)}")
        response = client.embeddings.create(
            model=model,
            input=test_texts
        )

        print("✓ 连接成功!")
        print(f"  - 返回 embedding 数量: {len(response.data)}")
        print(f"  - 第一个 embedding 维度: {len(response.data[0].embedding)}")
        print(f"  - 使用 token 数: {response.usage.total_tokens}")
        return True

    except openai.AuthenticationError as e:
        print(f"✗ 认证错误: {e}")
        return False
    except openai.APIConnectionError as e:
        print(f"✗ 连接错误: {e}")
        return False
    except openai.APITimeoutError as e:
        print(f"✗ 超时错误: {e}")
        return False
    except openai.APIError as e:
        print(f"✗ API 错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 未知错误: {type(e).__name__}: {e}")
        return False


def test_local_embedding():
    """测试本地 Embedding 模型"""
    print()
    print("=" * 60)
    print("测试本地 Embedding 模型 (sentence-transformers)")
    print("=" * 60)

    try:
        from sentence_transformers import SentenceTransformer

        model_name = "all-MiniLM-L6-v2"
        print(f"加载模型: {model_name}")

        model = SentenceTransformer(model_name)

        test_texts = ["这是一个测试文本", "This is a test text"]
        print(f"编码文本，数量: {len(test_texts)}")

        embeddings = model.encode(test_texts)

        print("✓ 本地模型运行成功!")
        print(f"  - 返回 embedding 数量: {len(embeddings)}")
        print(f"  - embedding 维度: {len(embeddings[0])}")
        return True

    except ImportError:
        print("✗ 未安装 sentence-transformers")
        print("  安装命令: pip install sentence-transformers")
        return False
    except Exception as e:
        print(f"✗ 错误: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("Embedding 连接测试脚本\n")

    # 测试阿里云
    dashscope_ok = test_dashscope_embedding()

    # 测试本地模型
    local_ok = test_local_embedding()

    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"阿里云 DashScope: {'✓ 可用' if dashscope_ok else '✗ 不可用'}")
    print(f"本地模型: {'✓ 可用' if local_ok else '✗ 不可用'}")
    print()

    if not dashscope_ok and not local_ok:
        print("建议: 检查网络连接或安装本地模型")
        sys.exit(1)
    elif not dashscope_ok:
        print("建议: 使用本地 embedding 模型")
    else:
        print("两种方案都可用")

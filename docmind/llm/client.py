"""
LLM client for OpenAI-compatible API (supports vLLM, Ollama, etc.).
"""

from typing import AsyncIterator, Iterator, Optional

from openai import OpenAI


class LLMClient:
    """
    Client for LLM API calls using OpenAI-compatible interface.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen2.5-72B-Instruct",
        api_key: str = "EMPTY",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 300,
    ):
        """
        Initialize the LLM client.

        Args:
            base_url: Base URL for the API endpoint.
            model: Model name to use.
            api_key: API key (usually "EMPTY" for local vLLM).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: User prompt.
            system_prompt: System prompt (optional).
            temperature: Override default temperature.
            max_tokens: Override default max tokens.

        Returns:
            Generated response string.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )

        return response.choices[0].message.content or ""

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Generate a streaming response from the LLM.

        Args:
            prompt: User prompt.
            system_prompt: System prompt (optional).
            temperature: Override default temperature.
            max_tokens: Override default max tokens.

        Yields:
            Response chunks as they arrive.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Asynchronously generate a response from the LLM.

        Args:
            prompt: User prompt.
            system_prompt: System prompt (optional).
            temperature: Override default temperature.
            max_tokens: Override default max tokens.

        Returns:
            Generated response string.
        """
        from openai import AsyncOpenAI

        async_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.client.api_key,
            timeout=self.timeout,
        )

        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )

        return response.choices[0].message.content or ""

    async def generate_stream_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Asynchronously generate a streaming response from the LLM.

        Args:
            prompt: User prompt.
            system_prompt: System prompt (optional).
            temperature: Override default temperature.
            max_tokens: Override default max tokens.

        Yields:
            Response chunks as they arrive.
        """
        from openai import AsyncOpenAI

        async_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.client.api_key,
            timeout=self.timeout,
        )

        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        stream = await async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for a text string.

        Note: This is a rough estimate using tiktoken.
        The actual count may differ depending on the model's tokenizer.

        Args:
            text: Text to count tokens for.

        Returns:
            Estimated token count.
        """
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))

    def test_connection(self) -> bool:
        """
        Test the connection to the LLM server.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            response = self.generate("Hello", max_tokens=10)
            return len(response) > 0
        except Exception:
            return False
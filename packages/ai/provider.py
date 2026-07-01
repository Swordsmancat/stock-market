from typing import Protocol

import httpx


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class MockLLMProvider:
    def generate(self, prompt: str) -> str:
        return prompt


class OpenAICompatibleLLMProvider:
    def __init__(self, api_key: str, api_base: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key.strip()
        self.api_base = api_base.rstrip("/")

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            msg = "LLM API key is not configured"
            raise ValueError(msg)

        response = httpx.post(
            f"{self.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class MockLLMProvider:
    def generate(self, prompt: str) -> str:
        return prompt

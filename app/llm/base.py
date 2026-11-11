from typing import Protocol


class LLMClient(Protocol):
    def extract(self, text: str, schema: dict) -> dict:
        """Chama o modelo com temperature=0 e devolve o JSON cru (ainda não validado)."""
        ...

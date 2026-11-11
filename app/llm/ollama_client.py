import json
import os

import ollama


class OllamaClient:
    def __init__(self, model: str = "qwen3:8b", num_ctx: int = 4096, host: str | None = None):
        self.model = model
        self.num_ctx = num_ctx
        self._client = ollama.Client(host=host or os.environ.get("OLLAMA_HOST"))

    def extract(self, text: str, schema: dict) -> dict:
        resposta = self._client.chat(
            model=self.model,
            messages=[{"role": "user", "content": text}],
            think=False,
            format=schema,
            options={"temperature": 0, "num_ctx": self.num_ctx},
        )
        return json.loads(resposta["message"]["content"])

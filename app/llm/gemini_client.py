import json
import os
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError


class GeminiClient:
    def __init__(self, model: str | None = None, api_key: str | None = None, max_retries: int = 3):
        self.model = model or os.environ["GEMINI_MODEL"]
        self.max_retries = max_retries
        self._client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])

    def extract(self, text: str, schema: dict) -> dict:
        espera = 1.0
        for tentativa in range(self.max_retries):
            try:
                resposta = self._client.models.generate_content(
                    model=self.model,
                    contents=text,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                        response_json_schema=schema,
                    ),
                )
                return json.loads(resposta.text)
            except ClientError as erro:
                if erro.code == 429 and tentativa < self.max_retries - 1:
                    time.sleep(espera)
                    espera *= 2
                    continue
                raise

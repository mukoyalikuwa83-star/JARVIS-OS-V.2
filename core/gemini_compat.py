"""Drop-in compatibility layer for the legacy google.generativeai API.

The project runs on the modern `google-genai` SDK (import name `google.genai`).
This module exposes the small subset of the legacy API surface the codebase
still uses: ``configure(api_key=...)`` and ``GenerativeModel(...)`` backed by
``Client(...).models.generate_content``.
"""

from __future__ import annotations

from typing import Any

from google.genai import Client, types

_client: Client | None = None


def configure(api_key: str | None = None, **_unused: Any) -> None:
    global _client
    _client = Client(api_key=api_key)


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client()
    return _client


class _Response:
    def __init__(self, text: str) -> None:
        self.text = text


class GenerativeModel:
    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        *,
        system_instruction: str | None = None,
        **_unused: Any,
    ) -> None:
        self.model_name = model_name
        self.system_instruction = system_instruction

    def generate_content(self, prompt: str, **_: Any) -> _Response:
        config: types.GenerateContentConfig | None = None
        if self.system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction
            )
        response = _get_client().models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        return _Response(response.text or "")

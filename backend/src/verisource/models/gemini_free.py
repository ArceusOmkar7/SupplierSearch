"""Optional eligible Gemini free-tier extraction for public business text only.

Enabled only when the operator recorded a verified free-tier project, model and actual
limits. There is no billing-enabled, premium or Search-grounded fallback and no assumed
quota. HTTP 429 is bounded: one retry honoring a valid Retry-After, then unavailable.
"""

import importlib
import time
from typing import Any, TypeVar

from pydantic import BaseModel

from verisource.config import Settings
from verisource.models.ollama import ModelUnavailable

T = TypeVar("T", bound=BaseModel)
MAX_RETRY_AFTER_SECONDS = 20


class GeminiFree:
    def __init__(self, settings: Settings, *, client: Any | None = None) -> None:
        self.settings = settings
        self._client = client

    @property
    def configured(self) -> bool:
        s = self.settings
        return bool(
            s.gemini_api_key is not None
            and s.gemini_model
            and s.gemini_free_tier_verified
            and s.gemini_requests_per_day is not None
            and s.gemini_requests_per_minute is not None
        )

    def _sdk_client(self) -> Any:
        if self._client is None:
            try:
                genai = importlib.import_module("google.genai")
            except ImportError as exc:
                raise ModelUnavailable("The optional Gemini SDK is not installed") from exc
            assert self.settings.gemini_api_key is not None
            self._client = genai.Client(api_key=self.settings.gemini_api_key.get_secret_value())
        return self._client

    def extract(self, schema: type[T], instructions: str, source_text: str) -> T:
        if not self.configured:
            raise ModelUnavailable("Gemini free tier is not configured")
        client = self._sdk_client()
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=f"{instructions}\n<source>\n{source_text}\n</source>",
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                        "temperature": 0,
                    },
                )
                return schema.model_validate_json(response.text)
            except Exception as exc:
                status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                if status == 429 and attempt == 0:
                    delay = _retry_after(exc)
                    if delay is None or delay > MAX_RETRY_AFTER_SECONDS:
                        raise ModelUnavailable("The free Gemini quota is exhausted") from exc
                    time.sleep(delay)
                    continue
                if status == 429:
                    raise ModelUnavailable("The free Gemini quota is exhausted") from exc
                raise ModelUnavailable("The Gemini request failed") from exc
        raise ModelUnavailable("The Gemini request failed")


def _retry_after(exc: Exception) -> float | None:
    headers = getattr(getattr(exc, "response", None), "headers", None) or {}
    try:
        return float(str(headers.get("retry-after")))
    except ValueError:
        return None

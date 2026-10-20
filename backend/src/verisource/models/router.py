"""Route extraction by data class. Private or unclassified text never leaves the machine."""

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

from verisource.config import Settings
from verisource.models.gemini_free import GeminiFree
from verisource.models.ollama import ModelUnavailable, OllamaClient

T = TypeVar("T", bound=BaseModel)
DataClass = Literal["public_business", "private", "personal", "unknown"]


class Extractor(Protocol):
    def extract(self, schema: type[T], instructions: str, source_text: str) -> T: ...


class ModelRouter:
    """Local first. Eligible public business text may use the verified free Gemini project.

    A local failure for private/unknown input raises; it is never silently sent to a cloud
    provider. Public text may try the free tier only when local inference is unavailable and
    the free tier is configured.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        local: Extractor | None = None,
        gemini: GeminiFree | None = None,
    ) -> None:
        self.settings = settings
        self.local: Extractor = local or OllamaClient(settings)
        self.gemini = gemini or GeminiFree(settings)

    def extract(
        self, schema: type[T], instructions: str, source_text: str, *, data_class: DataClass
    ) -> tuple[T, str]:
        """Return (proposal, backend label); backend is recorded with the extraction."""
        try:
            return self.local.extract(schema, instructions, source_text), (
                f"ollama:{self.settings.ollama_model}"
            )
        except ModelUnavailable:
            if data_class != "public_business" or not self.gemini.configured:
                raise
        return (
            self.gemini.extract(schema, instructions, source_text),
            f"gemini-free:{self.settings.gemini_model}",
        )

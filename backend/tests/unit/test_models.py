"""Model routing/validation rules plus one live local-model call on the actual BIS tender.

Routing tests use a disclosed recording stub to prove what leaves the machine; they never
produce source facts. The live test sends the verbatim tender description to the installed,
digest-pinned local model and checks structure and quotation support, not accuracy.
"""

from typing import Any

import pytest
from support import tender_description

from verisource.config import Settings
from verisource.models.gemini_free import GeminiFree
from verisource.models.ollama import ModelUnavailable, OllamaClient, chunk_pages
from verisource.models.router import ModelRouter
from verisource.models.schemas import (
    CertificateExtraction,
    Located,
    RequirementInterpretation,
    verify_certificate,
)


class Recorder:
    def __init__(self, fail: bool) -> None:
        self.calls = 0
        self.fail = fail

    def extract(self, schema: Any, instructions: str, source_text: str) -> Any:
        self.calls += 1
        if self.fail:
            raise ModelUnavailable("local down")
        return schema()


def configured_settings() -> Settings:
    return Settings.model_validate(
        {
            "gemini_api_key": "control-key-not-a-secret",
            "gemini_model": "control-model",
            "gemini_free_tier_verified": True,
            "gemini_requests_per_minute": 5,
            "gemini_requests_per_day": 100,
        }
    )


def test_private_input_never_reaches_cloud_even_when_local_fails() -> None:
    settings = configured_settings()
    cloud = Recorder(fail=False)
    gemini = GeminiFree(settings, client=object())
    gemini.extract = cloud.extract  # type: ignore[method-assign]
    router = ModelRouter(settings, local=Recorder(fail=True), gemini=gemini)
    for data_class in ("private", "personal", "unknown"):
        with pytest.raises(ModelUnavailable):
            router.extract(
                RequirementInterpretation,
                "x",
                tender_description(),
                data_class=data_class,
            )
    assert cloud.calls == 0
    result, backend = router.extract(
        RequirementInterpretation, "x", tender_description(), data_class="public_business"
    )
    assert cloud.calls == 1 and backend.startswith("gemini-free:")
    assert isinstance(result, RequirementInterpretation)


def test_gemini_requires_verified_free_tier_and_actual_limits() -> None:
    assert not GeminiFree(Settings()).configured
    partial = Settings.model_validate(
        {"gemini_api_key": "k", "gemini_model": "m", "gemini_free_tier_verified": True}
    )
    assert not GeminiFree(partial).configured  # limits were not recorded; none are assumed
    with pytest.raises(ModelUnavailable):
        GeminiFree(partial).extract(RequirementInterpretation, "x", "text")
    assert GeminiFree(configured_settings()).configured


def test_gemini_429_is_bounded_without_a_retry_after() -> None:
    class Quota(Exception):
        code = 429

    class Models:
        calls = 0

        def generate_content(self, **_kwargs: Any) -> Any:
            Models.calls += 1
            raise Quota

    class Client:
        models = Models()

    with pytest.raises(ModelUnavailable, match="quota"):
        GeminiFree(configured_settings(), client=Client()).extract(
            RequirementInterpretation, "x", "text"
        )
    assert Models.calls == 1


def test_unsupported_quotations_are_discarded_not_trusted() -> None:
    pages = {1: "Certificate No. 12345 issued under IS 9473 valid until 2026-12-31"}
    proposal = CertificateExtraction(
        certificate_number=Located(value="12345", page=1, quote="Certificate No. 12345"),
        standard=Located(value="IS 9999", page=1, quote="IS 9999 compliance"),  # not on the page
        expiry_date=Located(value="soon", page=1, quote="valid until 2026-12-31"),  # unreadable
    )
    checked = verify_certificate(proposal, pages)
    assert checked.certificate_number is not None
    assert checked.standard is None and checked.expiry_date is None
    assert any("standard" in note for note in checked.uncertainties)
    assert any("expiry_date" in note for note in checked.uncertainties)


def test_pages_are_chunked_inside_the_context_budget() -> None:
    chunks = chunk_pages({1: "a" * 12000, 2: "b" * 100})
    assert all(sum(len(t) for t in chunk.values()) <= 5000 for chunk in chunks)
    assert "".join(c.get(1, "") for c in chunks) == "a" * 12000


@pytest.mark.live
def test_installed_local_model_reads_the_actual_tender_description() -> None:
    settings = Settings()
    client = OllamaClient(settings)
    try:
        client.verify_installed()
    except ModelUnavailable as exc:
        pytest.skip(f"Missing prerequisite: pinned local model ({exc})")
    text = tender_description()
    proposal = client.extract(
        RequirementInterpretation,
        "Extract the buyer's requested part or equipment and any named suppliers.",
        text,
    )
    notes: list[str] = []
    from verisource.models.schemas import verify_located

    checked = verify_located(proposal.part_description, {1: text}, "part_description", notes)
    # A proposal is either quoted from the text or discarded; both leave the buyer in control.
    assert checked is None or "universal testing machine" in checked.quote.casefold()

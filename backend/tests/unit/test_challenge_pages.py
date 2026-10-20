"""CAPTCHA wall detection on actual captured supplier pages.

The Karam catalogue page is a real download gate that asks the visitor to solve a CAPTCHA; the
Amruta page is an ordinary product page. The product never solves or bypasses a challenge.
"""

import pytest
from support import RECORDS

from verisource.sources.manifests import load_record
from verisource.sources.websites import is_challenge_page

pytestmark = pytest.mark.real_records


def test_actual_captcha_gate_is_blocked_and_ordinary_page_is_not() -> None:
    _m, gate = load_record(RECORDS / "karam-captcha-gate.manifest.json")
    _m, ordinary = load_record(RECORDS / "amruta-pumppartinvest.manifest.json")
    assert is_challenge_page(gate) is True
    assert is_challenge_page(ordinary) is False

"""Explicit pack registry; downloaded or arbitrary code is never imported as a pack."""

from verisource.country_packs.contracts import CountryPack
from verisource.country_packs.india.pack import IndiaPack

_PACKS: dict[str, CountryPack] = {"IN": IndiaPack()}


class UnsupportedJurisdiction(LookupError):
    """Unsupported coverage is explicit, never silently mapped to India."""


def pack_for(jurisdiction: str | None) -> CountryPack:
    pack = _PACKS.get((jurisdiction or "IN").upper())
    if pack is None:
        raise UnsupportedJurisdiction(jurisdiction or "")
    return pack


def supported_jurisdictions() -> list[str]:
    return sorted(_PACKS)

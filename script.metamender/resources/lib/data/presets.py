"""Country certification presets, bundled read-only in resources/presets.

A preset is one country's rating system: the valid ratings, the prefix Kodi
values get ("NL:"), the order in which other countries' ratings are tried,
and the tables that map their ratings onto this one. Presets ship with the
add-on and are never copied or edited, so a fixed mapping reaches every
install with the next update.

A preset that cannot be trusted (missing, unparseable, or mapping onto a
rating its own list lacks) fails closed: no certification is written for the
scan rather than a wrong one.

Logging:
    Logger: 'presets'
    Key events:
        - presets.invalid (ERROR): The configured country's preset is unusable
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from resources.lib.constants import COUNTRY_CODES
from resources.lib.engine.certification import sanitize_prefix
from resources.lib.utils import get_logger

log = get_logger('presets')

_PRESET_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, "presets",
)


@dataclass(frozen=True)
class Preset:
    country: str
    valid: frozenset[str]
    prefix: str
    inference: tuple[str, ...]
    mappings: dict[str, dict[str, str]]
    # Other spellings of a rating ("MA15+" for "MA 15+"), read as the rating
    # they name; only the rating's own spelling is ever written.
    aliases: dict[str, str] = field(default_factory=dict)

    def canonical(self, rating: str) -> str:
        """``rating`` in this system's own spelling: whitespace collapsed
        (non-breaking spaces too), then an alias resolved. Anything else is
        returned as it is, so an unknown value stays invalid."""
        text = " ".join((rating or "").split())
        return self.aliases.get(text, text)


def load_preset(country: str, *, report: bool = True) -> Preset | None:
    """The preset for ``country`` (a code in COUNTRY_CODES), or None, logged
    at ERROR, when it is missing or invalid. ``report=False`` leaves the
    logging to the scan, for a read-only caller that asks on every view."""
    if country not in COUNTRY_CODES:
        _invalid(country, "unknown country", report)
        return None
    path = os.path.join(_PRESET_DIR, country + ".json")
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        if report:
            log.exception("Certification preset unreadable", event="presets.invalid",
                          country=country, path=path)
        return None
    try:
        valid = frozenset(str(r) for r in raw["valid_ratings"])
        prefix = str(raw["default_prefix"])
        inference = tuple(str(c) for c in raw["inference_countries"])
        mappings = {
            str(src): {str(k): str(v) for k, v in table.items()}
            for src, table in raw["mappings"].items()
        }
        aliases = {str(k): str(v) for k, v in (raw.get("aliases") or {}).items()}
    except (KeyError, TypeError, AttributeError):
        _invalid(country, "missing or malformed keys", report)
        return None
    if not valid:
        _invalid(country, "no valid ratings", report)
        return None
    if sanitize_prefix(prefix, "\0") != prefix:
        _invalid(country, "unusable prefix", report)
        return None
    outside = sorted(
        "{}:{}".format(src, target)
        for src, table in mappings.items() for target in table.values()
        if target not in valid
    )
    if outside:
        _invalid(country, "mapping targets outside valid_ratings: " + ", ".join(outside),
                 report)
        return None
    stray = sorted(alias for alias, target in aliases.items() if target not in valid)
    if stray:
        _invalid(country, "aliases outside valid_ratings: " + ", ".join(stray), report)
        return None
    return Preset(country, valid, prefix, inference, mappings, aliases)


def country_for_setting(index: int, ui_language: str) -> str | None:
    """The country of the `country` setting: 0 is Automatic, the region of
    Kodi's interface language ("nl-NL" -> "NL") when a preset covers it;
    1.. are COUNTRY_CODES in order. None when no country applies."""
    if index == 0:
        parts = ui_language.replace("_", "-").split("-")
        region = parts[1].upper() if len(parts) > 1 else ""
        return region if region in COUNTRY_CODES else None
    if 1 <= index <= len(COUNTRY_CODES):
        return COUNTRY_CODES[index - 1]
    return None


def _invalid(country: str, reason: str, report: bool) -> None:
    if not report:
        return
    log.error("Certification preset unusable", event="presets.invalid",
              country=country, reason=reason)

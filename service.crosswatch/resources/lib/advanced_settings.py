# SPDX-License-Identifier: GPL-2.0-only
"""Kodi's own playback thresholds, so changing them in Kodi changes them here.

advancedsettings.xml resolves per profile with a fallback to the master profile
(CProfileManager::GetUserDataItem), so a profile with its own copy is honoured. Defaults
match xbmc/settings/AdvancedSettings.cpp.

Uses the standard library parser rather than defusedxml, which is a PyPI package a Kodi
addon cannot depend on without shipping a script.module addon. XXE is not reachable:
ElementTree does not expand external entities. The residual risk is entity-expansion from a
file only a local writer controls, bounded by the boundary's read cap.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree

from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger

_log = get_logger("settings")

PROFILE_PATH = "special://profile/advancedsettings.xml"
MASTER_PATH = "special://masterprofile/advancedsettings.xml"


@dataclass(frozen=True)
class Thresholds:
    ignore_seconds_at_start: int = 180
    ignore_percent_at_end: float = 8.0
    playcount_minimum_percent: float = 90.0


DEFAULTS = Thresholds()


def _video_element(kodi: KodiApi, path: str) -> ElementTree.Element | None:
    text = kodi.read_text(path)
    if not text:
        return None
    try:
        return ElementTree.fromstring(text).find("video")
    except ElementTree.ParseError:
        _log.warning("settings.advancedsettings_unparseable", path=path)
        return None


def read_thresholds(kodi: KodiApi) -> Thresholds:
    video = _video_element(kodi, PROFILE_PATH)
    source = PROFILE_PATH
    if video is None:
        video = _video_element(kodi, MASTER_PATH)
        source = MASTER_PATH
    if video is None:
        _log.debug("settings.thresholds", source="defaults")
        return DEFAULTS

    def number(tag: str, fallback: float, low: float, high: float) -> float:
        found = video.find(tag)
        if found is None:
            return fallback
        # Bound to a local: an empty element has text None, and testing the expression
        # in the guard does not make the second read of .text safe.
        text = (found.text or "").strip()
        if not text:
            return fallback
        try:
            value = float(text)
        except ValueError:
            # Kodi's atof would read this as 0, which for the watched threshold means every
            # stop counts. That is a parsing accident, not a setting, so keep the default.
            return fallback
        # Clamped rather than rejected, because that is what Kodi does: the addon must agree
        # with Kodi on what counts as watched, not merely read the same element.
        return min(max(value, low), high)

    thresholds = Thresholds(
        # Ranges from Kodi's AdvancedSettings.cpp. 101 is deliberate there: it turns off
        # automatic marking as watched.
        ignore_seconds_at_start=int(number("ignoresecondsatstart", DEFAULTS.ignore_seconds_at_start, 0, 900)),
        ignore_percent_at_end=number("ignorepercentatend", DEFAULTS.ignore_percent_at_end, 0, 100),
        playcount_minimum_percent=number("playcountminimumpercent", DEFAULTS.playcount_minimum_percent, 0, 101),
    )
    _log.info(
        "settings.thresholds",
        source="profile" if source == PROFILE_PATH else "master",
        ignore_seconds_at_start=thresholds.ignore_seconds_at_start,
    )
    return thresholds

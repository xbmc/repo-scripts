"""Label localization utilities."""

from __future__ import annotations

import re

try:
    import xbmc
    import xbmcaddon

    IN_KODI = True
    _ADDON = xbmcaddon.Addon()
except ImportError:
    IN_KODI = False
    _ADDON = None

ADDON_PATTERN = re.compile(r"\$ADDON\[([^\s\]]+)\s+(\d+)\]")
LOCALIZE_PATTERN = re.compile(r"\$LOCALIZE\[(\d+)\]")


def LANGUAGE(string_id: int) -> str:
    """Get localized string from this addon."""
    if not IN_KODI or not _ADDON:
        return str(string_id)
    return _ADDON.getLocalizedString(string_id)


def resolve_label(label: str) -> str:
    """Resolve a label string to its localized value.

    Handles formats:
        $LOCALIZE[#####] - Kodi/skin string ID
        $NUMBER[#####] - Numeric value
        $ADDON[addon.id #####] - Addon string ID
        32000-32999 - Script string ID (auto-wrapped)
        ##### - Plain number treated as $LOCALIZE string ID
        Plain text - returned as-is
    """
    if not label or not IN_KODI:
        return label

    # Must check $ADDON before generic $ since getInfoLabel doesn't support $ADDON
    if label.startswith("$ADDON["):
        match = ADDON_PATTERN.match(label)
        if match:
            addon_id = match.group(1)
            string_id = int(match.group(2))
            try:
                addon = xbmcaddon.Addon(addon_id)
                result = addon.getLocalizedString(string_id)
                if result:
                    return result
            except RuntimeError:
                pass
        return label

    if "$LOCALIZE[" in label:
        def _resolve(match: re.Match[str]) -> str:
            result = xbmc.getLocalizedString(int(match.group(1)))
            if not result:
                result = xbmc.getInfoLabel(match.group(0))
            return result or match.group(0)

        return LOCALIZE_PATTERN.sub(_resolve, label)

    if label.startswith("$"):
        result = xbmc.getInfoLabel(label)
        if result:
            return result
        return label

    if label.isdigit():
        num = int(label)
        if 32000 <= num < 33000:
            result = xbmcaddon.Addon().getLocalizedString(num)
        else:
            result = xbmc.getLocalizedString(num)
            if not result:
                result = xbmc.getInfoLabel(f"$LOCALIZE[{label}]")
        if result:
            return result
        return label

    return label

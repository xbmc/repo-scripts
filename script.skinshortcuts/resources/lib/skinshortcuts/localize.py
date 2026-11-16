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
NUMBER_PATTERN = re.compile(r"\$NUMBER\[([0-9]+)\]")


def number_label(text: str) -> str:
    """Wrap a digit-only label in $NUMBER; Kodi reads a bare one as a string ID."""
    return f"$NUMBER[{text}]" if text.isascii() and text.isdigit() else text


def LANGUAGE(string_id: int) -> str:
    """Get localized string from this addon."""
    if not IN_KODI or not _ADDON:
        return str(string_id)
    return _ADDON.getLocalizedString(string_id)


def resolve_label(label: str) -> str:
    """Resolve $LOCALIZE, $ADDON, $NUMBER or bare string ID; plain text passes through."""
    if not label or not IN_KODI:
        return label

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

    number = NUMBER_PATTERN.fullmatch(label)
    if number:
        return number.group(1)

    if label.startswith("$"):
        result = xbmc.getInfoLabel(label)
        if result:
            return result
        return label

    if label.isdecimal():
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

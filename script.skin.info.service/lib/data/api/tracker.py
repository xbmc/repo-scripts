"""Per-session rate-limit handling: HTTP 429 dialog + in-memory provider skip set."""
from __future__ import annotations

from typing import Sequence
import xbmcgui

from lib.kodi.client import ADDON
from lib.infrastructure.dialogs import DialogProgress


_session_skip_providers = set()
_session_batch_cancelled = False


def _cancel_batch() -> None:
    """Mark this run cancelled so item loops stop instead of re-prompting."""
    global _session_batch_cancelled
    _session_batch_cancelled = True


def handle_rate_limit_error(provider: str) -> str:
    """Handle an HTTP 429 by asking the user; returns retry, skip, cancel_batch or cancel_all."""
    dialog = xbmcgui.Dialog()
    choices: Sequence[str] = [
        ADDON.getLocalizedString(32698),
        ADDON.getLocalizedString(32699),
        ADDON.getLocalizedString(32700),
        ADDON.getLocalizedString(32701).format(provider.upper()),
    ]

    choice = dialog.select(ADDON.getLocalizedString(32313).format(provider.upper()), list(choices))

    if choice == 0:
        import xbmc
        monitor = xbmc.Monitor()
        progress = DialogProgress()
        progress.create(ADDON.getLocalizedString(32313).format(provider.upper()),
                        ADDON.getLocalizedString(32314))
        for i in range(60):
            if progress.iscanceled() or monitor.abortRequested():
                progress.close()
                _cancel_batch()
                return "cancel_batch"
            progress.update(int((i / 60) * 100), ADDON.getLocalizedString(32315).format(60 - i))
            monitor.waitForAbort(1)
        progress.close()
        return "retry"
    elif choice == 1:
        _cancel_batch()
        return "cancel_batch"
    elif choice == 2:
        _cancel_batch()
        return "cancel_all"
    elif choice == 3:
        _session_skip_providers.add(provider.lower())
        return "skip"

    _cancel_batch()
    return "cancel_batch"


def is_batch_cancelled() -> bool:
    """True once a rate-limit prompt has cancelled this run."""
    return _session_batch_cancelled


def is_provider_skipped(provider: str) -> bool:
    """Whether the user chose to continue without this provider for the session."""
    return provider.lower() in _session_skip_providers


def reset_session_skip() -> None:
    """Clear the skipped providers and the cancelled-run flag."""
    global _session_batch_cancelled
    _session_batch_cancelled = False
    _session_skip_providers.clear()

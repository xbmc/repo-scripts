"""Per-session rate-limit handling: HTTP 429 dialog + in-memory provider skip set."""
from __future__ import annotations

from typing import Sequence
import xbmcgui

from lib.kodi.client import ADDON
from lib.infrastructure.dialogs import DialogProgress


_session_skip_providers = set()


def handle_rate_limit_error(provider: str) -> str:
    """Show modal dialog when an HTTP 429 lands for `provider`.

    Returns one of: "cancel_batch", "cancel_all", "skip", "retry".
    """
    dialog = xbmcgui.Dialog()
    choices: Sequence[str] = [
        "Wait 60s and Retry",
        "Retry Tomorrow",
        "Stop All Updates",
        f"Continue Without {provider.upper()}"
    ]

    choice = dialog.select(f"{provider.upper()} - Rate Limit", list(choices))

    if choice == 0:
        # Wait 60 seconds then retry
        import xbmc
        monitor = xbmc.Monitor()
        progress = DialogProgress()
        progress.create(ADDON.getLocalizedString(32313).format(provider.upper()),
                        ADDON.getLocalizedString(32314))
        for i in range(60):
            if progress.iscanceled() or monitor.abortRequested():
                progress.close()
                return "cancel_batch"
            progress.update(int((i / 60) * 100), ADDON.getLocalizedString(32315).format(60 - i))
            monitor.waitForAbort(1)
        progress.close()
        return "retry"
    elif choice == 1:
        return "cancel_batch"
    elif choice == 2:
        return "cancel_all"
    elif choice == 3:
        _session_skip_providers.add(provider)
        return "skip"

    return "cancel_batch"


def is_provider_skipped(provider: str) -> bool:
    """Check if provider is skipped for this session."""
    return provider in _session_skip_providers


def reset_session_skip() -> None:
    """Clear session skip flags."""
    _session_skip_providers.clear()

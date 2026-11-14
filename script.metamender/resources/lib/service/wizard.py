"""Opening the setup wizard or the folder-languages dialog from any entry
point, and starting the first scan after a first setup.

Logging:
    Delegates to resources.lib.ui.setup_window ('setup' logger).
"""
from __future__ import annotations

from resources.lib.service import manual
from resources.lib.service.daemon import _get_sources_config_path
from resources.lib.ui.setup_model import WIZARD
from resources.lib.ui.setup_window import run_setup
from resources.lib.utils import is_setup_complete


def open_setup(mode: str) -> bool:
    """Run the wizard ("wizard") or the folder dialog ("folders"). Finishing
    the wizard for the first time starts the first scan at once; a re-run
    applies from the next scheduled scan. True when the user saved."""
    first = not is_setup_complete()
    saved = run_setup(mode, _get_sources_config_path())
    if saved and first and mode == WIZARD:
        manual.run()
    return saved

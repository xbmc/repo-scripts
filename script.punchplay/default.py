from __future__ import annotations

import os
import sys

_ADDON_DIR = os.path.dirname(__file__)
_LIB_DIR = os.path.join(_ADDON_DIR, "resources", "lib")

if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from service import PunchPlayService

PunchPlayService().run()

# SPDX-License-Identifier: GPL-2.0-only
"""Script entry point, kept to a few lines as Kodi's add-on checker asks.

At the addon root, not under resources/, so that the directory CPythonInvoker puts on
sys.path is the package root and `from resources.lib...` resolves.
"""

import sys

from resources.lib.scripts import dispatch

if __name__ == "__main__":
    dispatch(sys.argv)

"""
plugin.py: entry point of plugin://script.wetrakr/, the folders skins use as
widgets (resources/lib/widgets.py).
"""

import sys

from resources.lib import widgets

if __name__ == "__main__":
    widgets.run(sys.argv)

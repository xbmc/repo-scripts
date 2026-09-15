"""Scoreboard entry point for script.livetennisscores.

Kodi runs this when the user opens the add-on (the ``xbmc.python.script``
extension point). The window itself lives in ``resources/lib/board.py``.
"""

from resources.lib.board import show

if __name__ == "__main__":
    show()

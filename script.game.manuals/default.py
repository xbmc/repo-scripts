# -*- coding: utf-8 -*-
"""RunScript(script.game.manuals,game=<path>[,title=<name>][,manual=<path>])

Shows the game's manual, finding one first if the game has none. The title is
what the game is called on screen and given to providers as a hint; without
one it comes from the file name. A skin passes them with $ESCINFO[], e.g.

  RunScript(script.game.manuals,game=$ESCINFO[Player.FilenameAndPath],title=$ESCINFO[RetroPlayer.Title])
"""

import sys

from resources.lib import main

main.run(sys.argv[1:])

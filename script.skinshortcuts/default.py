"""Skin Shortcuts v3 Entry Point.

Usage from skin:
    RunScript(script.skinshortcuts,type=buildxml)

Or with custom paths:
    RunScript(script.skinshortcuts,type=buildxml&path=special://skin/shortcuts/)
"""

from resources.lib.skinshortcuts.entry import main

if __name__ == "__main__":
    main()

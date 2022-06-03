import sys

from resources.lib.contextmenu.set_quick_epg_timer import SetQuickEpgTimer

if __name__ == "__main__":
    SetQuickEpgTimer(label=sys.listitem.getLabel(),
                     path=sys.listitem.getPath())

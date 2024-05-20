from __future__ import absolute_import

from lib import util
from lib.util import T
from . import dropdown
from . import opener

HOME = None


class UtilMixin():
    def __init__(self):
        self.exitCommand = None

    def goHome(self, section=None):
        HOME.show()
        if section:
            self.closeWithCommand('HOME:{0}'.format(section))
        else:
            self.closeWithCommand('HOME')

    def openItem(self, obj):
        self.processCommand(opener.open(obj))

    def openWindow(self, window_class, **kwargs):
        self.processCommand(opener.handleOpen(window_class, **kwargs))

    def processCommand(self, command):
        if command and command.startswith('HOME'):
            self.exitCommand = command
            self.doClose()
        elif command and command == "NODATA":
            raise util.NoDataException

    def closeWithCommand(self, command):
        self.exitCommand = command
        self.doClose()

    def showAudioPlayer(self, **kwargs):
        from . import musicplayer
        self.processCommand(opener.handleOpen(musicplayer.MusicPlayerWindow, **kwargs))

    def getNextShowEp(self, pl, items, title):
        revitems = list(reversed(items))
        in_progress = [i for i in revitems if i.get('viewOffset').asInt()]
        if in_progress:
            n = in_progress[0]
            pl.setCurrent(n)
            choice = dropdown.showDropdown(
                options=[
                    {'key': 'resume', 'display': T(32429, 'Resume from {0}').format(
                        util.timeDisplay(n.viewOffset.asInt()).lstrip('0').lstrip(':'))},
                    {'key': 'play', 'display': T(32317, 'Play from beginning')}
                ],
                pos=(660, 441),
                close_direction='none',
                set_dropdown_prop=False,
                header=u'{0} - {1} \u2022 {2}'.format(title,
                                                      T(32310, 'S').format(n.parentIndex),
                                                      T(32311, 'E').format(n.index))
            )

            if not choice:
                return None

            if choice['key'] == 'resume':
                return True
            return False

        watched = False
        for (k, i) in enumerate(revitems):
            if watched:
                try:
                    pl.setCurrent(revitems[k-2])
                    return False
                except IndexError:
                    break
            if i.get('viewCount').asInt() > 0:
                watched = True

        non_special = [i for i in revitems if i.get('parentIndex').asInt() and i.get('viewCount').asInt() == 0]
        use = items[0]
        if non_special:
            use = non_special[-1]
        pl.setCurrent(use)
        return False


def shutdownHome():
    global HOME
    if HOME:
        HOME._shuttingDown = True
        HOME.shutdown()
    del HOME
    HOME = None
    HOME

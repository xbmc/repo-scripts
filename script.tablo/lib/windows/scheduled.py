import xbmc
import base
import guide
from lib import backgroundthread
from lib.util import T


WM = None


class ScheduledWindow(guide.GuideWindow):
    name = 'SCHEDULED'
    view = 'guide'
    state = 'scheduled'
    section = T(32195)
    emptyMessage = (T(32116),)

    types = (
        (None, ''),
        ('SERIES', ''),
        ('MOVIES', ''),
        ('SPORTS', '')
    )

    def onFirstInit(self):
        self.setProperty('hide.menu', '1')
        guide.GuideWindow.onFirstInit(self)

    def onReInit(self):
        self.setFilter()
        self.setProperty('hide.menu', '1')

        if not self._showingDialog and not WM.windowWasLast(self):
            self.fillShows(clear=True)

        self.setFocusId(self.SHOW_GROUP_ID)

    def onFocus(self, controlID):
        if controlID == 50:
            self.setShowFocus()
            guide.WM.showMenu()
            return

    @base.dialogFunction
    def showClicked(self):
        item = self.showList.getSelectedItem()
        if not item:
            return

        show = item.dataSource.get('show')

        if not show:
            self.getSingleShowData(item.dataSource['path'])
            while not show and backgroundthread.BGThreader.working() and not xbmc.abortRequested:
                xbmc.sleep(100)
                show = item.dataSource.get('show')
        if self.closing():
            return

        w = guide.GuideShowWindow.open(show=show)
        if w.modified:
            self.fillShows(clear=True)

        self.updateShowItem(show)

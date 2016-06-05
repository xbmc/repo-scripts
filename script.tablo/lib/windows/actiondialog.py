import xbmc
import xbmcgui
import kodigui
from lib import util


class ActionDialog(kodigui.BaseWindow, util.CronReceiver):
    name = 'GUIDE'
    xmlFile = 'script-tablo-action.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'

    BUTTON1_ID = 400
    BUTTON2_ID = 401

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        util.setGlobalProperty('action.button1.busy', '')
        util.setGlobalProperty('action.button2.busy', '')
        self.itemCount = kwargs.get('item_count')
        self.itemPos = kwargs.get('item_pos')
        self.skipped = {}
        self.lastUnskipped = self.itemPos
        self.init(kwargs)

    def init(self, kwargs):
        self.number = kwargs.get('number')
        self.title = kwargs.get('title')
        self.info = kwargs.get('info')
        self.plot = kwargs.get('plot')
        self.start = kwargs.get('start', '')
        self.background = kwargs.get('background')
        self.button1 = kwargs.get('button1')
        self.button2 = kwargs.get('button2')
        self.titleIndicator = kwargs.get('title_indicator', '')
        self.startIndicator1 = kwargs.get('start_indicator1', '')
        self.startIndicator2 = kwargs.get('start_indicator2', '')
        self.callback = kwargs.get('callback')
        self.object = kwargs.get('obj')
        self.action = None

    def onFirstInit(self):
        self.updateDisplayProperties()
        self.setPrevNextIndicators()
        self.setProperty('number', str(self.number or ''))
        self.setProperty('title', self.title)
        self.setProperty('info', self.info)
        self.setProperty('plot', self.plot)
        self.setProperty('start', self.start)
        self.setProperty('background', self.background)
        self.setProperty('title.indicator', self.titleIndicator)
        self.setProperty('start.indicator1', self.startIndicator1)
        self.setProperty('start.indicator2', self.startIndicator2)
        self.setFocusId(self.BUTTON1_ID)
        util.CRON.registerReceiver(self)

    def onReInit(self):
        util.CRON.registerReceiver(self)

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_MOVE_UP and not xbmc.getCondVisibility('ControlGroup(500).HasFocus(0)'):
                self.action = 'PREV_ITEM'
                return self.doPrevNextCallback()
            elif action == xbmcgui.ACTION_MOVE_DOWN and not xbmc.getCondVisibility('ControlGroup(500).HasFocus(0)'):
                self.action = 'NEXT_ITEM'
                return self.doPrevNextCallback()
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.BUTTON1_ID:
            self.action = self.button1[0]
        elif controlID == self.BUTTON2_ID:
            self.action = self.button2[0]

        if not self.doCallback():
            self.doClose()

    def tick(self):
        if self._closing:
            util.CRON.cancelReceiver(self)
        self.doCallback()

    def setPrevNextIndicators(self):
        if self.itemCount is None:
            return

        if self.itemPos > 0:
            self.setProperty('more.up', '1')
        else:
            self.setProperty('more.up', '')

        if self.itemPos < self.itemCount - 1:
            self.setProperty('more.down', '1')
        else:
            self.setProperty('more.down', '')

    def doPrevNextCallback(self):
        if not self.callback:
            self.action = None
            return False

        if self.itemCount is None:
            return

        action = self.action
        self.action = None

        pos = self.itemPos

        if action == 'PREV_ITEM':
            while pos > 0:
                pos -= 1

                if pos not in self.skipped:
                    self.itemPos = pos
                    break
            else:
                self.itemPos = self.lastUnskipped
                return
        elif action == 'NEXT_ITEM':
            while pos < self.itemCount - 1:
                pos += 1

                if pos not in self.skipped:
                    self.itemPos = pos
                    break
            else:
                self.itemPos = self.lastUnskipped
                return

        kwargs = self.callback(self.itemPos, 'CHANGE.ITEM')

        if 'SKIP' in kwargs:
            self.skipped[self.itemPos] = True
            self.action = action
            return self.doPrevNextCallback()
        else:
            self.lastUnskipped = self.itemPos

        if not kwargs:
            return False

        self.init(kwargs)
        self.onFirstInit()

    def doCallback(self):
        if not self.callback:
            self.action = None
            return False

        if self.action != 'watch':
            if self.button1 and self.button1[0] == self.action:
                util.setGlobalProperty('action.button1.busy', '1')
            elif self.button2 and self.button2[0] == self.action:
                util.setGlobalProperty('action.button2.busy', '1')

        action = self.action
        self.action = None

        try:
            changes = self.callback(self.object, action)
        finally:
            util.setGlobalProperty('action.button1.busy', '')
            util.setGlobalProperty('action.button2.busy', '')

        if not changes:
            return False

        self.button1 = changes.get('button1')
        self.button2 = changes.get('button2')
        self.titleIndicator = changes.get('title_indicator', '')
        self.start = changes.get('start', '')

        self.updateDisplayProperties()

        return True

    def updateDisplayProperties(self):
        self.setProperty('button2', self.button2 and self.button2[1] or '')
        self.setProperty('button1', self.button1 and self.button1[1] or '')
        self.setProperty('title.indicator', self.titleIndicator)
        self.setProperty('start', self.start)


def openDialog(
    title, info, plot, start, button1, **kwargs
):

    w = ActionDialog.open(
        title=title,
        info=info,
        plot=plot,
        start=start,
        button1=button1,
        **kwargs
    )

    util.CRON.cancelReceiver(w)

    action = w.action
    pos = w.itemPos
    del w
    return action or pos

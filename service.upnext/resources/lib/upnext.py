import xbmc
import xbmcgui
from platform import machine

ACTION_PLAYER_STOP = 13
OS_MACHINE = machine()


class UpNext(xbmcgui.WindowXMLDialog):
    item = None
    cancel = False
    watchnow = False
    progressStepSize = 0
    currentProgressPercent = 100

    def __init__(self, *args, **kwargs):
        if OS_MACHINE[0:5] == 'armv7':
            xbmcgui.WindowXMLDialog.__init__(self)
        else:
            xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        self.setInfo()
        self.prepareProgressControl()

    def setInfo(self):
        episodeInfo = str(self.item['season']) + 'x' + str(self.item['episode']) + '.'
        if self.item['rating'] is not None:
            rating = str(round(float(self.item['rating']), 1))
        else:
            rating = None

        if self.item is not None:
            self.setProperty(
                'fanart', self.item['art'].get('tvshow.fanart', ''))
            self.setProperty(
                'landscape', self.item['art'].get('tvshow.landscape', ''))
            self.setProperty(
                'clearart', self.item['art'].get('tvshow.clearart', ''))
            self.setProperty(
                'clearlogo', self.item['art'].get('tvshow.clearlogo', ''))
            self.setProperty(
                'poster', self.item['art'].get('tvshow.poster', ''))
            self.setProperty(
                'thumb', self.item['art'].get('thumb', ''))
            self.setProperty(
                'plot', self.item['plot'])
            self.setProperty(
                'tvshowtitle', self.item['showtitle'])
            self.setProperty(
                'title', self.item['title'])
            self.setProperty(
                'season', str(self.item['season']))
            self.setProperty(
                'episode', str(self.item['episode']))
            self.setProperty(
                'seasonepisode', episodeInfo)
            self.setProperty(
                'year', str(self.item['firstaired']))
            self.setProperty(
                'rating', rating)
            self.setProperty(
                'playcount', str(self.item['playcount']))

    def prepareProgressControl(self):
        try:
            self.progressControl = self.getControl(3014)
            if self.progressControl is not None:
                self.progressControl.setPercent(self.currentProgressPercent)
        except:
            pass

    def setItem(self, item):
        self.item = item

    def setProgressStepSize(self, progressStepSize):
        self.progressStepSize = progressStepSize

    def updateProgressControl(self):
        try:
            self.currentProgressPercent = self.currentProgressPercent - self.progressStepSize
            self.progressControl = self.getControl(3014)
            if self.progressControl is not None:
                self.progressControl.setPercent(self.currentProgressPercent)
        except:
            pass

    def setCancel(self, cancel):
        self.cancel = cancel

    def isCancel(self):
        return self.cancel

    def setWatchNow(self, watchnow):
        self.watchnow = watchnow

    def isWatchNow(self):
        return self.watchnow

    def onFocus(self, controlId):
        pass

    def doAction(self):
        pass

    def closeDialog(self):
        self.close()

    def onClick(self, controlID):

        xbmc.log('nextup info onclick: ' + str(controlID))

        if controlID == 3012:
            # watch now
            self.setWatchNow(True)
            self.close()
        elif controlID == 3013:
            # cancel
            self.setCancel(True)
            self.close()

        pass

    def onAction(self, action):

        xbmc.log('nextup info action: ' + str(action.getId()))
        if action == ACTION_PLAYER_STOP:
            self.close()
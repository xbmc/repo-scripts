from platform import machine

import xbmc
import xbmcgui


ACTION_PLAYER_STOP = 13
OS_MACHINE = machine()


class StillWatchingInfo(xbmcgui.WindowXMLDialog):
    item = None
    cancel = False
    stillwatching = False

    def __init__(self, *args, **kwargs):
        self.action_exitkeys_id = [10, 13]
        if OS_MACHINE[0:5] == 'armv7':
            xbmcgui.WindowXMLDialog.__init__(self)
        else:
            xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        image = self.item['art'].get('tvshow.poster', '')
        thumb = self.item['art'].get('thumb', '')
        landscape = self.item['art'].get('tvshow.landscape', '')
        fanartimage = self.item['art'].get('tvshow.fanart', '')
        clearartimage = self.item['art'].get('tvshow.clearart', '')
        name = self.item['label']
        rating = str(round(float(self.item['rating']),1))
        year = self.item['firstaired']
        overview = self.item['plot']
        season = self.item['season']
        episodeNum = self.item['episode']
        title = self.item['title']
        playcount = self.item['playcount']
        # set the dialog data
        self.getControl(4000).setLabel(name)
        self.getControl(4006).setText(overview)

        try:
            posterControl = self.getControl(4001)
            if posterControl is not None:
                self.getControl(4001).setImage(image)
        except:
            pass

        try:
            thumbControl = self.getControl(4002)
            if thumbControl is not None:
                self.getControl(4002).setImage(thumb)
        except:
            pass
        self.getControl(4003).setLabel(rating)
        self.getControl(4004).setLabel(year)

        try:
            landscapeControl = self.getControl(4005)
            if landscapeControl is not None:
                self.getControl(4005).setImage(landscape)
        except:
            pass

        try:
            fanartControl = self.getControl(4007)
            if fanartControl is not None:
                fanartControl.setImage(fanartimage)
        except:
            pass

        try:
            seasonControl = self.getControl(4008)
            if seasonControl is not None:
                seasonControl.setLabel(str(season))
        except:
            pass

        try:
            episodeControl = self.getControl(4009)
            if episodeControl is not None:
                episodeControl.setLabel(str(episodeNum))
        except:
            pass

        try:
            titleControl = self.getControl(4010)
            if titleControl is not None:
                titleControl.setLabel(title)
        except:
            pass

        try:
            resolutionControl = self.getControl(4011)
            if resolutionControl is not None:
                resolution1 = self.item['streamdetails'].get('video')
                resolution = resolution1[0].get('height')
                resolutionControl.setLabel(str(resolution))
        except:
            pass

        try:
            clearartControl = self.getControl(4014)
            if clearartControl is not None:
                clearartControl.setImage(clearartimage)
        except:
            pass

        try:
            playcountControl = self.getControl(4018)
            if playcountControl != None:
                playcountControl.setLabel(str(playcount))
        except:
            pass

    def setItem(self, item):
        self.item = item

    def setCancel(self, cancel):
        self.cancel = cancel

    def isCancel(self):
        return self.cancel

    def setStillWatching(self, stillwatching):
        self.stillwatching = stillwatching

    def isStillWatching(self):
        return self.stillwatching

    def onFocus(self, controlId):
        pass

    def doAction(self):
        pass

    def closeDialog(self):
        self.close()

    def onClick(self, controlID):

        xbmc.log("still watching info onclick: " + str(controlID))

        if controlID == 4012:
            # still watching
            self.setStillWatching(True)
            self.close()

        elif controlID == 4013:
            # cancel
            self.setCancel(True)
            self.close()

        pass

    def onAction(self, action):
        xbmc.log("still watching info action: " + str(action.getId()))
        if action == ACTION_PLAYER_STOP:
            self.close()


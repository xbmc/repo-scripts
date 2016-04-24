import xbmc
import xbmcgui
from platform import machine

ACTION_PLAYER_STOP = 13
OS_MACHINE = machine()


class UnwatchedInfo(xbmcgui.WindowXMLDialog):
    item = None

    def __init__(self, *args, **kwargs):
        if OS_MACHINE[0:5] == 'armv7':
            xbmcgui.WindowXMLDialog.__init__(self)
        else:
            xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        self.action_exitkeys_id = [10, 13]

        clearlogo = self.item['art'].get('tvshow.clearlogo', '')
        clearartimage = self.item['art'].get('tvshow.clearart', '')
        fanartimage = self.item['art'].get('tvshow.fanart', '')
        overview = self.item['plot']
        name = self.item['title']

        rating = str(round(float(self.item['rating']),1))

        season = self.item['season']
        episodeNum = self.item['episode']
        episodeInfo = str(season) + 'x' + str(episodeNum) + '.'

        # set the dialog data
        self.getControl(5000).setLabel(name)
        self.getControl(5001).setText(overview)
        self.getControl(5002).setLabel(episodeInfo)

        try:
            clearartimageControl = self.getControl(5004)
            if clearartimageControl != None:
                if clearlogo:
                    self.getControl(5004).setImage(clearlogo)
                elif clearartimage:
                    self.getControl(5004).setImage(clearartimage)
                elif fanartimage:
                    self.getControl(5004).setImage(fanartimage)
        except:
            pass

        if rating is not None:
            self.getControl(5003).setLabel(rating)
        else:
            self.getControl(5003).setVisible(False)


    def setItem(self, item):
        self.item = item

    def onFocus(self, controlId):
        pass

    def doAction(self):
        pass

    def closeDialog(self):
        self.close()

    def onClick(self, controlID):
        pass

    def onAction(self, action):

        xbmc.log('nextup info action: ' + str(action.getId()))
        if action == ACTION_PLAYER_STOP:
            self.close()


import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib

ACTION_PLAYER_STOP = 13
    
class NextUpInfo(xbmcgui.WindowXMLDialog):

    item = None
    cancel = False
    watchnow = False

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
    
        image = self.item['art'].get('tvshow.poster','')
        thumb = self.item['art'].get('thumb','')
        clearartimage = self.item['art'].get('tvshow.clearart','')
        landscapeimage = self.item['art'].get('tvshow.landscape','')
        fanartimage = self.item['art'].get('tvshow.fanart','')
        overview = self.item['plot']
        name = self.item['title']
        
        episodeInfo = ""
        season = self.item['season']
        episodeNum = self.item['episode']
        episodeInfo = str(season) + "x" + str(episodeNum) + "."
        
        rating = str(round(float(self.item['rating'])))
        year = self.item['firstaired']
        info = year
        # set the dialog data
        self.getControl(3000).setLabel(name)
        self.getControl(3001).setText(overview)
        self.getControl(3002).setLabel(episodeInfo)
        self.getControl(3004).setLabel(info)
        
        self.getControl(3009).setImage(image)
        
        try:
            fanartControl = self.getControl(3005)
            if(fanartControl != None):
                fanartControl.setImage(fanartimage)
        except:
            pass
        
        try:
            thumbControl = self.getControl(3008)
            if(thumbControl != None):
                self.getControl(3008).setImage(thumb)
        except:
            pass
        
        try:
            landscapeControl = self.getControl(3010)
            if(landscapeControl != None):
                self.getControl(3010).setImage(landscapeimage)
        except:
            pass
        
        self.getControl(3006).setImage(clearartimage)
        
        if rating != None:
            self.getControl(3003).setLabel(rating)
        else:
            self.getControl(3003).setVisible(False)
        
        try:
            seasonControl = self.getControl(3015)
            if(seasonControl != None):
                seasonControl.setLabel(str(season))
        except:
            pass
        
        try:
            episodeControl = self.getControl(3016)
            if(episodeControl != None):
                episodeControl.setLabel(str(episodeNum))
        except:
            pass
        
        try:
            resolutionControl = self.getControl(3011)
            if(resolutionControl != None):
                resolution1 =  self.item['streamdetails'].get('video')
                resolution = resolution1[0].get('height')    
                resolutionControl.setLabel(str(resolution))
        except:
            pass
        
    def setItem(self, item):
        self.item = item
    
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
        
        xbmc.log("nextup info onclick: "+str(controlID))

        if(controlID == 3012):
            # watch now
            self.setWatchNow(True)
            self.close()
        
        elif(controlID == 3013):
            #cancel
            self.setCancel(True)
            self.close()

        pass
    
    def onAction(self, action):
        
        xbmc.log("nextup info action: "+str(action.getId()))
        if action == ACTION_PLAYER_STOP:
            self.close()
     


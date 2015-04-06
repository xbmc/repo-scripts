# -*- coding: utf-8 -*-
import xbmc
import guitables
from base import WindowReaderBase
from lib import util

class PVRWindowReaderBase(WindowReaderBase):
    def controlIsOnView(self,controlID):
        return not xbmc.getCondVisibility('ControlGroup(9000).HasFocus(0)')

    def init(self):
        self.mode = False

    def updateMode(self,controlID):
        if self.controlIsOnView(controlID):
            self.mode = 'VIEW'
        else:
            self.mode = None
        return self.mode

    def getControlDescription(self,controlID):
        old = self.mode
        new = self.updateMode(controlID)
        if new == None and old != None:
            return 'View Options'

class PVRGuideWindowReader(PVRWindowReaderBase):
    ID = 'pvrguide'
    timelineInfo = (    util.T(32171), #PVR
                        '$INFO[ListItem.ChannelNumber]',
                        '$INFO[ListItem.ChannelName]',
                        '$INFO[ListItem.StartTime]',
                        19160,
                        '$INFO[ListItem.EndTime]',
                        '$INFO[ListItem.Plot]'
    )

    nowNextInfo = (    util.T(32171),
                        '$INFO[ListItem.ChannelNumber]',
                        '$INFO[ListItem.ChannelName]',
                        '$INFO[ListItem.StartTime]',
                        '$INFO[ListItem.Plot]'
    )

    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        if self.slideoutHasFocus(): return self.getSlideoutText(controlID)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return (u'',u'')
        compare = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel('ListItem.EndTime')
        return (text.decode('utf-8'),compare)

    def getItemExtraTexts(self,controlID):
        text = None
        if self.controlIsOnView(controlID):
            if controlID == 10: #EPG: Timeline
                text = guitables.convertTexts(self.winID,self.timelineInfo)
            elif controlID == 11 or controlID == 12 or controlID == 13: #EPG: Now/Next/Channel
                info = list(self.nowNextInfo)
                if xbmc.getCondVisibility('ListItem.IsRecording'):
                    info.append(19043)
                elif xbmc.getCondVisibility('ListItem.HasTimer'):
                    info.append(31510)
                text = guitables.convertTexts(self.winID,info)
        return text

class PVRChannelsWindowReader(PVRWindowReaderBase):
    ID = 'pvrchannels'

    channelInfo = (    '$INFO[ListItem.StartTime]',
                        19160,
                        '$INFO[ListItem.EndTime]',
                        '$INFO[ListItem.Plot]'
    )

    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        if self.slideoutHasFocus(): return self.getSlideoutText(controlID)
        text = '{0}... {1}... {2}'.format(xbmc.getInfoLabel('ListItem.ChannelNumber'),xbmc.getInfoLabel('ListItem.Label'),xbmc.getInfoLabel('ListItem.Title'))
        if not text: return (u'',u'')
        compare = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel('ListItem.EndTime')
        return (text.decode('utf-8'),compare)

    def getItemExtraTexts(self,controlID):
        text = None
        if self.controlIsOnView(controlID):
            if controlID == 50: #Channel (TV or Radio)
                info = list(self.channelInfo)
                if xbmc.getCondVisibility('ListItem.IsRecording'):
                    info.insert(0,19043)
                text = guitables.convertTexts(self.winID,info)
        return text

class PVRRecordingsWindowReader(PVRWindowReaderBase):
    ID = 'pvrrecordings'

    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        if self.slideoutHasFocus(): return self.getSlideoutText(controlID)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return (u'',u'')
        return (text.decode('utf-8'),text)

    def getItemExtraTexts(self,controlID):
        text = None
        if self.controlIsOnView(controlID):
            text = text = guitables.convertTexts(self.winID,('$INFO[ListItem.Plot]',))
        return text

class PVRTimersWindowReader(PVRWindowReaderBase):
    ID = 'pvrtimers'

    timerInfo = (   '$INFO[ListItem.ChannelName]',
                    '$INFO[ListItem.Label]',
                    '$INFO[ListItem.Date]',
                    '$INFO[ListItem.Comment]'
    )

    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        if self.slideoutHasFocus(): return self.getSlideoutText(controlID)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return (u'',u'')
        compare = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel('ListItem.EndTime')
        return (text.decode('utf-8'),compare)

    def getItemExtraTexts(self,controlID):
        text = None
        if self.controlIsOnView(controlID):
            text = guitables.convertTexts(self.winID,self.timerInfo)
        return text

class PVRSearchWindowReader(PVRWindowReaderBase):
    ID = 'pvrsearch'

    searchInfo = ( '$INFO[ListItem.ChannelNumber]',
                    '$INFO[ListItem.ChannelName]',
                    '$INFO[ListItem.Date]'
    )

    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        if self.slideoutHasFocus(): return self.getSlideoutText(controlID)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return (u'',u'')
        compare = text + xbmc.getInfoLabel('ListItem.Date')
        return (text.decode('utf-8'),compare)

    def getItemExtraTexts(self,controlID):
        text = None
        if self.controlIsOnView(controlID):
            info = list(self.searchInfo)
            if xbmc.getCondVisibility('ListItem.IsRecording'):
                info.append(19043)
            elif xbmc.getCondVisibility('ListItem.HasTimer'):
                info.append(31510)
            text = guitables.convertTexts(self.winID,info)
        return text

class PVRWindowReader(PVRWindowReaderBase):
    ID = 'pvr'
    timelineInfo = (    util.T(32171), #PVR
                        '$INFO[ListItem.ChannelNumber]',
                        '$INFO[ListItem.ChannelName]',
                        '$INFO[ListItem.StartTime]',
                        19160,
                        '$INFO[ListItem.EndTime]',
                        '$INFO[ListItem.Plot]'
    )

    channelInfo = (    '$INFO[ListItem.StartTime]',
                        19160,
                        '$INFO[ListItem.EndTime]',
                        '$INFO[ListItem.Plot]'
    )

    nowNextInfo = (    util.T(32171),
                        '$INFO[ListItem.ChannelNumber]',
                        '$INFO[ListItem.ChannelName]',
                        '$INFO[ListItem.StartTime]',
                        '$INFO[ListItem.Plot]'
    )

    def controlIsOnView(self,controlID):
        return controlID > 9 and controlID < 18

    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        text = None
        if controlID == 11 or controlID == 12: #Channel (TV or Radio)
            text = '{0}... {1}... {2}'.format(xbmc.getInfoLabel('ListItem.ChannelNumber'),xbmc.getInfoLabel('ListItem.Label'),xbmc.getInfoLabel('ListItem.Title'))
        else:
            text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return (u'',u'')
        compare = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel('ListItem.EndTime')
        return (text.decode('utf-8'),compare)

    def getItemExtraTexts(self,controlID):
        text = None
        if self.controlIsOnView(controlID):
            if controlID == 10: #EPG: Timeline
                text = guitables.convertTexts(self.winID,self.timelineInfo)
            elif controlID == 11 or controlID == 12: #Channel (TV or Radio)
                text = guitables.convertTexts(self.winID,self.channelInfo)
            elif controlID == 16: #EPG: Now/Next
                text = guitables.convertTexts(self.winID,self.nowNextInfo)
        return text
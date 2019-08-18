#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of uEPG.
#
# uEPG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# uEPG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with uEPG.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon
import os, collections, threading, datetime, time, epg, utils, itertools

class Channel(object):
    def __init__(self):
        name        = ''
        logo        = ''
        number      = -1
        listSize    = 0
        totalTime   = 0
        isFavorite  = False
        isValid     = False
        guidedata   = []
        listItems   = []
        
        
class ChannelList(object):
    def __init__(self):
        self.channels     = []
        self.channelNames = []
        self.maxGuidedata = 48
        self.maxChannels  = None
        self.uEPGRunning  = utils.getProperty('uEPGRunning') == "True"
        self.incHDHR      = utils.REAL_SETTINGS.getSetting('Enable_HDHR') == "true"
        self.useKodiSkin  = utils.REAL_SETTINGS.getSetting('useKodiSkin') == "true"

        
    def prepareListItem(self, channelPath):
        utils.log('prepareListItem, channelPath = ' + str(channelPath))
        channelnames   = []
        channelResults = utils.RPCHelper().getFileList(channelPath, life=datetime.timedelta(seconds=(self.refreshIntvl-600)))
        heading = '%s / %s'%(utils.ADDON_NAME,self.pluginName)
        self.busy = utils.adaptiveDialog(0, size=len(channelResults), string1=utils.LANGUAGE(30004), header=heading)
        for i, item in enumerate(channelResults):
            utils.adaptiveDialog((i*100//len(channelResults))//2, self.busy, string1=utils.LANGUAGE(30004))
            if len(item.get('channelname','')) > 0: channelnames.append(item['channelname'])
                                            
        channelNum   = 0
        channelItems = []
        counter      = collections.Counter(channelnames)
        channelnames = list(set(counter.elements()))
        for channel in sorted(channelnames):
            utils.adaptiveDialog((i*50//len(channelnames)), self.busy, string1=utils.LANGUAGE(30004))
            newChannel  = {}
            guidedata   = []
            starttime   = time.time()
            channelName = channel
            channelNum  = channelNum + 1
            newChannel['channelname']   = channelName
            for item in channelResults:
                if channel == item['channelname']:
                    starttime = int(item.get('starttime','') or starttime)
                    starttime = starttime + (int(item.get('duration','')) or int(item.get('runtime','')))
                    item['starttime'] = starttime
                    newChannel['channelnumber'] = (item.get('channelnumber','')      or channelNum)
                    newChannel['channellogo']   = (item.get('channellogo','')        or self.pluginIcon)
                    guidedata.append(item)
            if len(guidedata) > 0:
                newChannel['guidedata'] = guidedata
                channelItems.append(newChannel)
        utils.adaptiveDialog(100, self.busy, string1=utils.LANGUAGE(30005))
        return self.prepareJson(channelItems)
                
                
    def prepareJson(self, channelItems):
        utils.log('prepareJson')
        try:
            channelItems.sort(key=lambda x:x['channelnumber'])
            if self.incHDHR == True: 
                HDHRitems = (list(utils.HDHR().getChannelItems()) or [])
                HDHRitems.sort(key=lambda x:x['channelnumber'])
                if len(HDHRitems) == 0: utils.okDialog(utils.LANGUAGE(30013), utils.LANGUAGE(30014), utils.LANGUAGE(30015)%(self.pluginName))
                else: channelItems.extend(HDHRitems)
            if self.validateChannels(channelItems) == True:
                self.setupChannelList(channelItems)
                return True
        except Exception as e:
            utils.log("prepareJson, failed! " + str(e), xbmc.LOGERROR)
            utils.notificationDialog(utils.LANGUAGE(30002)%(self.pluginName,self.pluginAuthor),icon=self.pluginIcon)
        return False

        
    def fixChannelNumber(self, channel, channelnumbers):
        while channel in channelnumbers: channel = float(channel) + 0.1
        utils.log('fixChannelNumber, return channel = ' + str(channel))
        return channel
        
        
    def validateChannels(self, channelItems):
        channelnames   = []
        channelnumbers = []
        heading = '%s / %s'%(utils.ADDON_NAME,self.pluginName)
        self.busy = utils.adaptiveDialog(0, size=len(channelItems), string1=utils.LANGUAGE(30004), header=heading)
        
        for i, item in enumerate(channelItems):
            utils.adaptiveDialog((i*100//len(channelItems))//2, self.busy, string1=utils.LANGUAGE(30004))
            if len(item.get('guidedata','')) > 0:
                channelnames.append(item['channelname'])
                channelnumber = item['channelnumber']
                if channelnumber in channelnumbers:
                    channelnumber = self.fixChannelNumber(channelnumber, channelnumbers)
                    item['channelnumber'] = channelnumber
                channelnumbers.append(channelnumber)
             
        counter = collections.Counter(channelnames)
        self.maxChannels  = len(counter)
        self.channelNames = list(counter.elements())
        for i in range(self.maxChannels):
            utils.adaptiveDialog((i*100//self.maxChannels)//2, self.busy, string1=utils.LANGUAGE(30004))
            self.channels.append(Channel())
        utils.adaptiveDialog(100, self.busy, string1=utils.LANGUAGE(30005))
        
        if self.maxChannels is None or self.maxChannels == 0:
            utils.log('validateChannels, No channels Found')
            return False
            
        utils.log('validateChannels, maxChannels  = ' + str(self.maxChannels))
        utils.log('validateChannels, maxGuidedata = ' + str(self.maxGuidedata))
        utils.log('validateChannels, channelNames = ' + str(self.channelNames))
        return True

  
    def setupChannelList(self, channelItems):
        heading = '%s / %s'%(utils.ADDON_NAME,self.pluginName)
        self.busy = utils.adaptiveDialog(0, size=len(channelItems), string1=utils.LANGUAGE(30006), header=heading)
        for i in range(self.maxChannels):
            if utils.adaptiveDialog((i*100//len(channelItems)), self.busy, string1=utils.LANGUAGE(30006)) == False: break
            try:
                item                         = channelItems[i]
                item['guidedata']            = sorted(item['guidedata'], key=lambda x:x.get('starttime',''), reverse=False)
                item['guidedata']            = item['guidedata'][:self.maxGuidedata]#truncate guidedata to a manageable amount.
                self.channels[i].name        = item['channelname']
                self.channels[i].logo        = (item.get('channellogo','')        or '')
                self.channels[i].number      = (item.get('channelnumber','')      or i + 1)
                self.channels[i].isFavorite  = (item.get('isfavorite','')         or False)
                self.channels[i].guidedata   = (item['guidedata']                 or '')
                self.channels[i].listSize    = len(self.channels[i].guidedata)
                self.channels[i].listItems   = [utils.buildListItem(data) for data in item['guidedata']]
                self.channels[i].isValid     = True #todo
                totalTime = 0
                for idx, tmpdata in enumerate(self.channels[i].guidedata): totalTime = totalTime + int((tmpdata.get('runtime','') or tmpdata.get('duration','')))
                self.channels[i].totalTime = totalTime
                utils.log('setupChannelList, channel %s, name = %s'%(i+1,str(self.channels[i].name)))
                utils.log('setupChannelList, channel %s, number = %s'%(i+1,str(self.channels[i].number)))
                utils.log('setupChannelList, channel %s, logo = %s'%(i+1,str(self.channels[i].logo)))
                utils.log('setupChannelList, channel %s, isFavorite = %s'%(i+1,str(self.channels[i].isFavorite)))
                utils.log('setupChannelList, channel %s, listSize = %s'%(i+1,str(self.channels[i].listSize)))
                utils.log('setupChannelList, channel %s, totalTime = %s'%(i+1,str(self.channels[i].totalTime)))
            except Exception as e: utils.log("setupChannelList, failed! idx (%s), error (%s), item (%s)"%(i, e, item), xbmc.LOGERROR)
        utils.adaptiveDialog(100, self.busy, string1=utils.LANGUAGE(30007))

        
    def chkSkinPath(self):
        if self.useKodiSkin:
            folders = ['xml','720p','1080i']
            for folder in folders:#special://skin
                kodiSkinPath = os.path.join('special://home/addons/',xbmc.getSkinDir(),folder)
                if xbmcvfs.exists(os.path.join(kodiSkinPath,'%s.guide.xml'%utils.ADDON_ID)): return kodiSkinPath
        return os.path.join(utils.ADDON_PATH)
        
        
    def startRefreshTimer(self):
        utils.log('startRefreshTimer, starting refreshTimer')
        self.refreshTimer = threading.Timer(float(self.refreshIntvl), self.refresh)
        self.refreshTimer.name = "refreshTimer"
        if self.refreshTimer.isAlive() == True:
            utils.log('startRefreshTimer, canceling refreshTimer')
            self.refreshTimer.cancel()
        self.refreshTimer.start()
        
        
    def refresh(self):
        utils.log('refresh, triggering refreshTimer')
        utils.notificationDialog(utils.LANGUAGE(30003), icon=self.pluginIame)
        xbmc.executebuiltin("RunPlugin(%s)"%self.refreshPath)
        
        
if __name__ == '__main__':
    if utils.getProperty('PseudoTVRunning') != "True":
        try: params = dict(arg.split('=') for arg in sys.argv[1].split('&'))
        except: params = {}
        dataType = None
        utils.log('params = ' + str(params))
        for type in ['json','property','listitem']:
            try:
                data = params[type]
                dataType = type
                break
            except: pass
            
        hasChannels= False
        channelLST = ChannelList()
        channelLST.incHDHR      = (utils.loadJson(utils.unquote(params.get('include_hdhr','')))          or channelLST.incHDHR)
        channelLST.skinPath     = ((utils.loadJson(utils.unquote(params.get('skin_path',''))))           or channelLST.chkSkinPath())
        channelLST.mediaFolder  = os.path.join(channelLST.skinPath,'resources','skins','default','media')
        channelLST.refreshPath  = utils.loadJson(utils.unquote(params.get('refresh_path',''))            or utils.ADDON_ID)
        channelLST.refreshIntvl = int(utils.loadJson(utils.unquote(params.get('refresh_interval','')))   or '0')
        channelLST.skinFolder   = os.path.join(channelLST.skinPath,'resources','skins','default','1080i',) if xbmcvfs.exists(os.path.join(channelLST.skinPath,'resources','skins','default','1080i','%s.guide.xml'%utils.ADDON_ID)) else os.path.join(channelLST.skinPath,'resources','skins','default','720p')
        utils.setProperty('uEPG.rowCount',utils.loadJson(utils.unquote(params.get('row_count',''))       or '9'))
        channelLST.pluginName, channelLST.pluginAuthor, channelLST.pluginIcon, channelLST.pluginFanart, channelLST.pluginPath = utils.getPluginMeta(channelLST.refreshPath)
        
        utils.log('dataType = '     + str(dataType))
        utils.log('skinPath = '     + str(channelLST.skinPath))
        utils.log('skinFolder = '   + str(channelLST.skinFolder))
        utils.log('rowCount = '     + utils.getProperty('uEPG.rowCount'))
        utils.log('refreshPath = '  + str(channelLST.refreshPath))
        utils.log('refreshIntvl = ' + str(channelLST.refreshIntvl))
        utils.setProperty('PluginName'   ,channelLST.pluginName)
        utils.setProperty('PluginIcon'   ,channelLST.pluginIcon)
        utils.setProperty('PluginFanart' ,channelLST.pluginFanart)
        utils.setProperty('PluginAuthor' ,channelLST.pluginAuthor)
        
        #show optional load screen
        # if channelLST.uEPGRunning == False and utils.getProperty('uEPGSplash') != 'True' and xbmcvfs.exists(os.path.join(channelLST.skinFolder,'%s.splash.xml'%utils.ADDON_ID)) == True:
            # mySplash   = epg.Splash('%s.splash.xml'%utils.ADDON_ID,channelLST.skinPath,'default')
            # mySplash.show()
            # xbmc.sleep(100)
            
        firstHDHR = utils.REAL_SETTINGS.getSetting('FirstTime_HDHR') == "true"
        if utils.HDHR().hasHDHR() and firstHDHR and not channelLST.incHDHR:
            utils.REAL_SETTINGS.setSetting('FirstTime_HDHR','false')
            if utils.yesnoDialog((utils.LANGUAGE(30012)%(channelLST.pluginName)),custom='Later'):
                utils.REAL_SETTINGS.setSetting('Enable_HDHR','true')
                channelLST.incHDHR = True
                
        if dataType   == 'json':     hasChannels = channelLST.prepareJson(utils.loadJson(utils.unquote(data)))
        elif dataType == 'property': hasChannels = channelLST.prepareJson(utils.loadJson(utils.unquote(utils.getProperty(data))))
        elif dataType == 'listitem': hasChannels = channelLST.prepareListItem(utils.unquote(data))
        
        if utils.REAL_SETTINGS.getSetting('FirstTime_Run') == "true":
            utils.REAL_SETTINGS.setSetting('FirstTime_Run','false')
            utils.textViewer(utils.LANGUAGE(30008),'%s / %s'%(utils.ADDON_NAME,channelLST.pluginName))

        # if utils.getProperty('uEPGSplash') == 'True':
            # mySplash.close()
            # del mySplash
            # xbmc.sleep(100)
        
        if hasChannels == True:
            if channelLST.refreshIntvl > 0 and channelLST.refreshPath is not None: channelLST.startRefreshTimer()
            if channelLST.uEPGRunning == False and utils.getProperty('uEPGGuide') != 'True':
                channelLST.myEPG = epg.uEPG('%s.guide.xml'%utils.ADDON_ID,channelLST.skinPath,'default')
                channelLST.myEPG.channelLST = channelLST
                channelLST.myEPG.doModal()
                del channelLST.myEPG
                xbmc.sleep(100)
        else:
            utils.log("invalid uEPG information", xbmc.LOGERROR)
            # utils.notificationDialog(utils.LANGUAGE(30002)%(channelLST.pluginName,channelLST.pluginAuthor),icon=channelLST.pluginIcon)
            # utils.REAL_SETTINGS.openSettings() 
        del utils.KODI_MONITOR
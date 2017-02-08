#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import xbmc, xbmcaddon, xbmcgui
import json
import os
import re

import handler

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

__IconDefault__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'default.png'))
__IconAlert__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'alert.png'))
__IconOk__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'ok.png'))

INTERVAL = 10 # More than that will make switching too fuzzy because service isn't synchronize with real time
HOME = xbmcgui.Window(10000)

def jsonrpc(query):
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    return json.loads(xbmc.executeJSONRPC(json.dumps(querystring, encoding='utf-8')))

class XBMCMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.SettingsChanged = False

    def onSettingsChanged(self):
        self.SettingsChanged = True

class Service(XBMCMonitor):

    def __init__(self, *args):
        XBMCMonitor.__init__(self)
        self.__dateFormat = None
        self.getSettings()
        handler.notifyLog('Init Service %s %s' % (__addonname__, __version__))

        self.timers = handler.getTimer()
        handler.setTimerProperties(self.timers)

    def getSettings(self):

        # There seems to be a bug in kodi as sometimes changed properties wasn't read/update properly even if
        # monitor signaled a change.
        # Reading of settings is now outsourced to handler as a workaround.

        self.__showNoticeBeforeSw = True if handler.getSetting('showNoticeBeforeSw').upper() == 'TRUE' else False
        self.__useCountdownTimer = True if handler.getSetting('useCountdownTimer').upper() == 'TRUE' else False
        self.__dispMsgTime = int(re.match('\d+', handler.getSetting('dispTime')).group())*1000
        self.__discardTmr = int(re.match('\d+', handler.getSetting('discardOldTmr')).group())*60
        self.__confirmTmrAdded = True if handler.getSetting('confirmTmrAdded').upper() == 'TRUE' else False
        self.__dateFormat = handler.getDateFormat()

        self.SettingsChanged = False

    @classmethod

    def resetTmr(cls, date):
        for prefix in ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']:
            if HOME.getProperty('%s:date' % (prefix)) == '': continue
            elif HOME.getProperty('%s:date' % (prefix)) == date: handler.clearTimerProperties(prefix)

    @classmethod

    def channelName2channelId(cls, channelname):
        query = {
                "method": "PVR.GetChannels",
                "params": {"channelgroupid": "alltv"},
                }
        res = jsonrpc(query)
        if 'result' in res and 'channels' in res['result']:
            res = res['result'].get('channels')
            for channels in res:
                if channels['label'] == channelname: return channels['channelid']
        return False

    @classmethod

    def getPlayer(cls):
        props = {'player': None, 'playerid': None, 'media': None, 'id': None}
        query = {
                "method": "Player.GetActivePlayers",
                }
        res = jsonrpc(query)
        if 'result' in res and res['result']:
            res = res['result'][0]
            props['player'] = res['type']
            props['playerid'] = res['playerid']

            query = {
                    "method": "Player.GetItem",
                    "params": {"properties": ["title", "season", "episode", "file"],
                               "playerid": props['playerid']},
                    "id": "VideoGetItem"
                    }
            res = jsonrpc(query)
            if 'result' in res:
                res = res['result'].get('item')
                props['media'] = res['type']
                if 'id' in res: props['id'] = res['id']
        return props

    def poll(self):

        while not XBMCMonitor.abortRequested(self):

            if XBMCMonitor.waitForAbort(self, INTERVAL): 
                break
            if self.SettingsChanged:
                self.getSettings()

            _now = time.time()
            _switchInstantly = False

            for _timer in self.timers:

                if not _timer['utime']:
                    handler.notifyLog('Couldn\'t calculate timestamp, delete timer', xbmc.LOGERROR)
                    self.resetTmr(_timer['date'])
                    break

                # delete old/discarded timers
                if _timer['utime'] + self.__discardTmr < _now:
                    self.resetTmr(_timer['date'])
                    continue

                if _timer['utime'] < _now: _switchInstantly = True
                if (_timer['utime'] - _now < INTERVAL + self.__dispMsgTime / 1000) or _switchInstantly:
                    chanIdTmr = self.channelName2channelId(_timer['channel'].decode('utf-8'))
                    if chanIdTmr:

                        # get player properties, switch if necessary

                        plrProps = self.getPlayer()
                        if chanIdTmr == plrProps['id']:
                            handler.notifyLog('Channel switching unnecessary')
                            handler.notifyOSD(__LS__(30000), __LS__(30027) % (_timer['channel'].decode('utf-8')), time=self.__dispMsgTime)
                        else:
                            switchAborted = False
                            secs = 0
                            handler.notifyLog('Channel switch to %s required' %  (_timer['channel'].decode('utf-8')))

                            if _switchInstantly:
                                handler.notifyLog('immediate channel switching required')
                                handler.notifyOSD(__LS__(30000), __LS__(30027) % (_timer['channel'].decode('utf-8')), time=5000)

                            elif not self.__showNoticeBeforeSw: xbmc.sleep(self.__dispMsgTime)

                            elif self.__useCountdownTimer:
                                handler.OSDProgress.create(__LS__(30028), __LS__(30026) % _timer['channel'].decode('utf-8'), __LS__(30029) % (int(self.__dispMsgTime / 1000 - secs)))
                                while secs < self.__dispMsgTime /1000:
                                    secs += 1
                                    percent = int((secs * 100000) / self.__dispMsgTime)
                                    handler.OSDProgress.update(percent, __LS__(30026) % _timer['channel'].decode('utf-8'), __LS__(30029) % (int(self.__dispMsgTime / 1000 - secs)))
                                    xbmc.sleep(1000)
                                    if (handler.OSDProgress.iscanceled()):
                                        switchAborted = True
                                        break
                                handler.OSDProgress.close()
                            else:
                                idleTime = xbmc.getGlobalIdleTime()
                                handler.notifyOSD(__LS__(30000), __LS__(30026) % (_timer['channel'].decode('utf-8')), time=self.__dispMsgTime)
                                while secs < self.__dispMsgTime /1000:
                                    if idleTime > xbmc.getGlobalIdleTime():
                                        switchAborted = True
                                        break
                                    xbmc.sleep(1000)
                                    idleTime += 1
                                    secs += 1

                            if switchAborted: handler.notifyLog('Channelswitch cancelled by user')
                            else:
                                if plrProps['player'] == 'audio' or (plrProps['player'] == 'video' and plrProps['media'] != 'channel'):

                                    # stop all other players except pvr

                                    handler.notifyLog('player:%s media:%s @id:%s is running' % (plrProps['player'], plrProps['media'], plrProps['playerid']))
                                    query = {
                                            "method": "Player.Stop",
                                            "params": {"playerid": plrProps['playerid']},
                                            }
                                    res = jsonrpc(query)
                                    if 'result' in res and res['result'] == "OK":
                                        handler.notifyLog('Player stopped')

                                handler.notifyLog('Currently playing channelid %s, switch to id %s' % (plrProps['id'], chanIdTmr))
                                query = {
                                        "method": "Player.Open",
                                        "params": {"item": {"channelid": chanIdTmr}}
                                        }
                                res = jsonrpc(query)
                                if 'result' in res and res['result'] == 'OK':
                                    handler.notifyLog('Switched to channel \'%s\'' % (_timer['channel'].decode('utf-8')))
                                else:
                                    handler.notifyLog('Couldn\'t switch to channel \'%s\'' % (_timer['channel'].decode('utf-8')))
                                    handler.notifyOSD(__LS__(30000), __LS__(30025) % (_timer['channel'].decode('utf-8')), icon=__IconAlert__)

                    self.resetTmr(_timer['date'])
            self.timers = handler.getTimer()

        handler.notifyLog('Service kicks off')

service = Service()
service.poll()
del service

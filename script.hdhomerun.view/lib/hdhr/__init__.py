# -*- coding: utf-8 -*-
import time
import requests
import base64
import urllib
import json
import discovery

try:
    from collections import OrderedDict
except:
    from ordereddict_compat import OrderedDict

from lib import util

GUIDE_URL = 'http://my.hdhomerun.com/api/guide.php?DeviceAuth={0}'
SEARCH_URL = 'http://my.hdhomerun.com/api/search?DeviceAuth={0}&Search={1}'

class NoCompatibleDevicesException(Exception): pass

class NoDevicesException(Exception): pass

class NoDeviceAuthException(Exception): pass

class NoGuideDataException(Exception): pass

class EmptyLineupException(Exception): pass

def chanTuple(guide_number,chanCount):
    major, minor = (guide_number + '.0').split('.',2)[:2]
    return (int(major),int(minor),chanCount*-1)

class ChannelSource(dict):
    @property
    def url(self):
        return self['url']

    @property
    def ID(self):
        return self['ID']

class Channel(object):
    def __init__(self,data,device_response):
        self.number = data['GuideNumber']
        self.name = data['GuideName']
        self.sources = [ChannelSource({'url':data['URL'],'ID':device_response.ID})]
        self.favorite = bool(data.get('Favorite',False))
        self.DRM = bool(data.get('DRM',False))
        self.guide = None

    def add(self,data,device_response):
        self.sources.append(ChannelSource({'url':data['URL'],'ID':device_response.ID}))

    def setGuide(self,guide):
        self.guide = guide

    def matchesFilter(self,filter_):
        if filter_.isdigit():
            return self.number.startswith(filter_)
        else:
            return filter_ in self.name.lower() or filter_ in self.guide.affiliate.lower() or filter_ == self.number

class LineUp(object):
    MAX_AGE = 3600

    def __init__(self):
        self.channels = OrderedDict()
        self.devices = {}
        self.hasGuideData = False
        self.hasSubChannels = False
        self._discoveryTimestamp = 0
        self.collectLineUp()

    def __getitem__(self,key):
        return self.channels[key]

    def __contains__(self, key):
        return key in self.channels

    def __len__(self):
        return len(self.channels.keys())

    def isOld(self):
        return (time.time() - self._discoveryTimestamp) > self.MAX_AGE

    def index(self,key):
        if not key in self.channels: return -1
        return self.channels.keys().index(key)

    def indexed(self,index):
        if index < 0 or index >= len(self):
            return None
        return self.channels[ [k for k in self.channels.keys()][index] ]

    def getDeviceByIP(self,ip):
        for d in self.devices.values():
            if d.ip == ip:
                return d
        return None

    def defaultDevice(self):
        #Return device with the most number of channels as default
        highest = None
        for d in self.devices.values():
            if not highest or highest.channelCount < d.channelCount:
                highest = d
        return highest

    def collectLineUp(self):
        try:
            self._collectLineUp()
            self._discoveryTimestamp = time.time()
        except:
            self.devices = {}
            raise

    def _collectLineUp(self):
        responses = discovery.discover(discovery.TUNER_DEVICE)

        if not responses:
            util.DEBUG_LOG('ERROR: No discovery responses!')
            raise NoDevicesException()

        lineUps = []

        err = None
        for r in responses:
            self.devices[r.ID] = r
            try:
                req = requests.get(r.url)
            except:
                err = util.ERROR()
                continue

            try:
                lineup = req.json()
            except:
                util.ERROR('Failed to parse lineup JSON data. Older device?',hide_tb=True)
                continue

            if lineup:
                r.channelCount = len(lineup)
                lineUps.append((r,lineup))

        if not lineUps:
            if err:
                util.LOG('ERROR: No compatible devices found!')
                raise NoCompatibleDevicesException()
            else:
                util.DEBUG_LOG('ERROR: Empty lineup!')
                raise EmptyLineupException()

        hideDRM = not util.getSetting('show.DRM',False)

        while lineUps:
            lowest = min(lineUps,key=lambda l: l[1] and chanTuple(l[1][0]['GuideNumber'],l[0].channelCount) or (0,0,0)) #Prefer devices with the most channels assuming (possibly wrongly) that they are getting a better signal
            if not lowest[1]:
                lineUps.pop(lineUps.index(lowest))
                continue

            chanData = lowest[1].pop(0)

            if hideDRM and chanData.get('DRM'): continue

            channelNumber = chanData['GuideNumber']

            if '.' in channelNumber: self.hasSubChannels = True

            if channelNumber in self.channels:
                self.channels[chanData['GuideNumber']].add(chanData,lowest[0])
            else:
                self.channels[chanData['GuideNumber']] = Channel(chanData,lowest[0])

        if not self.channels: util.DEBUG_LOG(lineUps)

    def search(self,terms):
        url = SEARCH_URL.format(self.apiAuthID(),urllib.quote(terms.encode('utf-8')))
        util.DEBUG_LOG('Search URL: {0}'.format(url))
        try:
            results = requests.get(url).json()
            return results
        except:
            util.ERROR()

        return None

    def apiAuthID(self):
        combined = ''
        ids = []
        for d in self.devices.values():
            ids.append(d.ID)
            authID = d.deviceAuth
            if not authID: continue
            combined += authID

        if not combined:
            util.LOG('WARNING: No device auth for any devices!')
            raise NoDeviceAuthException()

        return base64.standard_b64encode(combined)

class Show(dict):
    @property
    def title(self):
        return self.get('Title','')

    @property
    def epTitle(self):
        return self.get('EpisodeTitle','')

    @property
    def icon(self):
        return self.get('ImageURL','')

    @property
    def synopsis(self):
        return self.get('Synopsis','')

    @property
    def start(self):
        return self.get('StartTime')

    @property
    def end(self):
        return self.get('EndTime')

    def matchesFilter(self,filter_):
        return filter_ in self.title.lower()

    def progress(self):
        start = self.get('StartTime')
        if not start: return None
        end = self.get('EndTime')
        duration = end - start
        sofar = time.time() - start
        return int((sofar/duration)*100)

class GuideChannel(dict):
    @property
    def number(self):
        return self.get('GuideNumber','')

    @property
    def name(self):
        return self.get('GuideName','')

    @property
    def icon(self):
        return self.get('ImageURL','')

    @property
    def affiliate(self):
        return self.get('Affiliate','')

    def currentShow(self):
        shows = self.get('Guide')
        if not shows: return Show()
        now = time.time()
        for s in shows:
            if now >= s.get('StartTime') and now < s.get('EndTime'):
                return Show(s)
        return Show()

    def nextShow(self):
        shows = self.get('Guide')
        if not shows: return Show()
        if len(shows) < 2: return Show()
        now = time.time()
        for i,s in enumerate(shows):
            if now >= s.get('StartTime') and now < s.get('EndTime'):
                i+=1
                if i >= len(shows): break
                return Show(shows[i])

        return Show()

class Guide(object):
    def __init__(self,lineup=None):
        self.init(lineup)

    def init(self,lineup):
        self.guide = OrderedDict()
        if not lineup:
            return
        url = GUIDE_URL.format(urllib.quote(lineup.apiAuthID(),''))

        data = self.getData(url)

        if not data:
            util.LOG('WARNING: No guide data returned!')
            raise NoGuideDataException()

        for chan in data:
            self.guide[chan['GuideNumber']] = chan

    def getData(self,url):
        for second in (False,True):
            if second: util.LOG('Failed to get guide data on first try - retrying...')
            try:
                util.DEBUG_LOG('Fetching guide from: {0}'.format(url))
                raw = requests.get(url).text
                util.DEBUG_LOG('Guide data received.'.format(url))
            except:
                util.ERROR()
                if second: raise
                time.sleep(0.2)
                continue
            if not raw: continue

            data = json.loads(raw)
            if data: return data
        return None

    def getChannel(self,guide_number):
        return GuideChannel(self.guide.get(guide_number) or {})
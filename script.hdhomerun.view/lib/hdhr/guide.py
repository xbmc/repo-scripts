# -*- coding: utf-8 -*-
import time
import requests
import urllib
import json

try:
    from collections import OrderedDict
except:
    from ordereddict_compat import OrderedDict

from lib import util
import errors

GUIDE_URL = 'http://my.hdhomerun.com/api/guide.php?DeviceAuth={0}'
SEARCH_URL = 'http://mytest.hdhomerun.com/api/search?DeviceAuth={deviceAuth}&Search={search}'
EPISODES_URL = 'http://mytest.hdhomerun.com/api/episodes?DeviceAuth={deviceAuth}&SeriesID={seriesID}'
SUGGEST_URL = 'http://mytest.hdhomerun.com/api/suggest?DeviceAuth={deviceAuth}&Category={category}'


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

'''
{
        "SeriesID": "11942433",
        "Title": "Zoo",
        "Synopsis": "A rebel biologist joins a race to determine the mystery behind a wave of brutal animal attacks against human beings from all across the globe before humanity is left without any hope of salvation, as the raids begin to grow increasingly calculated.",
        "ImageURL": "http://usca-my.hdhomerun.com/fyimediaservices/v_3_3_6_1/Program.svc/96/1942433/Primary",
        "OriginalAirdate": 1435622400,
        "ChannelNumber": "7.1",
        "ChannelName": "KIRO-DT",
        "ChannelImageURL": "http://usca-my.hdhomerun.com/fyimediaservices/v_3_3_6_1/Station.svc/2/765/Logo/120x120"
    },
'''

class Series(dict):
    @property
    def title(self):
        return self.get('Title','')

    @property
    def synopsis(self):
        return self.get('Synopsis','')

    @property
    def ID(self):
        return self.get('SeriesID')

    @property
    def icon(self):
        return self.get('ImageURL','')

    @property
    def channelNumber(self):
        return self.get('ChannelNumber','')

    @property
    def channelName(self):
        return self.get('ChannelName','')

    @property
    def channelIcon(self):
        return self.get('ChannelImageURL','')

    @property
    def originalTimestamp(self):
        return int(self.get('OriginalAirdate',0))

    @property
    def hasRule(self):
        return self.get('RecordingRule') == 1

    @property
    def hidden(self):
        return self.get('SuggestHide') == 1

    def episodes(self,device_auth):
        url = EPISODES_URL.format(deviceAuth=urllib.quote(device_auth, ''),seriesID=self.ID)
        util.DEBUG_LOG('Episodes URL: {0}'.format(url))

        req = requests.get(url)

        try:
            results = req.json()
            if not results: return []
            return [Episode(r) for r in results]
        except:
            util.ERROR()

        return None


class Episode(dict):
    @property
    def ID(self):
        return self.get('ProgramID')

    @property
    def title(self):
        return self.get('EpisodeTitle','')

    @property
    def synopsis(self):
        return self.get('Synopsis','')

    @property
    def number(self):
        return self.get('EpisodeNumber','')

    @property
    def icon(self):
        return self.get('ImageURL','')

    @property
    def channelNumber(self):
        return self.get('ChannelNumber','')

    @property
    def channelName(self):
        return self.get('ChannelName','')

    @property
    def channelIcon(self):
        return self.get('ChannelImageURL','')

    @property
    def startTimestamp(self):
        return int(self.get('StartTime',0))

    @property
    def endTimestamp(self):
        return int(self.get('EndTime',0))

    @property
    def duration(self):
        duration = self.endTimestamp - self.startTimestamp
        if duration > 0: return duration
        return 0

    @property
    def originalTimestamp(self):
        return int(self.get('OriginalAirdate',0))

    def displayDate(self,original=False):
        return time.strftime('%b %d, %Y',time.localtime(original and self.originalTimestamp or self.startTimestamp))

    def displayTime(self,original=False):
        return time.strftime('%I:%M:%S %p',time.localtime(original and self.originalTimestamp or self.startTimestamp))

    def durationString(self):
        s = self.duration
        hours = s // 3600
        s = s - (hours * 3600)
        minutes = s // 60
        seconds = s - (minutes * 60)
        if hours:
            return '%d:%02d:%02d' % (hours, minutes, seconds)
        else:
            return '%d:%02d' % (minutes, seconds)

def search(deviceAuth,category='',terms=''):
    if terms:
        url = SEARCH_URL.format(deviceAuth=urllib.quote(deviceAuth,''),search=urllib.quote(terms.encode('utf-8'), ''))
    elif category:
        url = SUGGEST_URL.format(deviceAuth=urllib.quote(deviceAuth,''),category=category)

    util.DEBUG_LOG('Search URL: {0}'.format(url))

    req = requests.get(url)

    try:
        results = req.json()
        if not results: return []
        return [Series(r) for r in results]
    except:
        util.ERROR()

    return None

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
            raise errors.NoGuideDataException()

        for chan in data:
            self.guide[chan['GuideNumber']] = chan

    def getData(self,url):
        for second in (False,True):
            if second: util.LOG('Failed to get guide data on first try - retrying...')
            try:
                util.DEBUG_LOG('Fetching guide from: {0}'.format(url))
                r = requests.get(url)
                if not r.ok:
                    raise Exception('Server Error ({0})'.format(r.status_code))
                raw = r.text
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

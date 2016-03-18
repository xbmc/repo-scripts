# -*- coding: utf-8 -*-
import time
import datetime
import random
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
SLICE_URL = 'http://my.hdhomerun.com/api/guide.php?DeviceAuth={deviceAuth}&Channel={channel}{start}'
SEARCH_URL = 'http://my.hdhomerun.com/api/search?DeviceAuth={deviceAuth}&Search={search}'
EPISODES_URL = 'http://my.hdhomerun.com/api/episodes?DeviceAuth={deviceAuth}&SeriesID={seriesID}'
SUGGEST_URL = 'http://my.hdhomerun.com/api/suggest?DeviceAuth={deviceAuth}&Category={category}'
NOW_SHOWING_URL = 'http://my.hdhomerun.com/api/up_next?DeviceAuth={deviceAuth}{start}'
NOW_SHOWING_START = '&Start={utcUnixtime}'


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

def episodes(device_auth, ID):
    url = EPISODES_URL.format(deviceAuth=urllib.quote(device_auth, ''),seriesID=ID)
    util.DEBUG_LOG('Episodes URL: {0}'.format(url))

    req = requests.get(url)

    try:
        results = req.json()
        if not results: return []
        return [Episode(r) for r in results]
    except:
        util.ERROR()

    return None

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
    def startTimestamp(self):
        return int(self.get('StartTime',0))

    @property
    def endTimestamp(self):
        return int(self.get('EndTime',0))

    @property
    def hasRule(self):
        return self.get('RecordingRule') == 1

    @property
    def hidden(self):
        return self.get('SuggestHide') == 1

    def episodes(self,device_auth):
        return episodes(device_auth, self.ID)


class Episode(dict):
    @property
    def ID(self):
        return self.get('ProgramID')

    @property
    def title(self):
        return self.get('EpisodeTitle','')

    @property
    def showTitle(self):
        return self.get('Title','')

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

    def onNow(self):
        return self.startTimestamp < time.time() < self.endTimestamp

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
    url = None
    if terms:
        url = SEARCH_URL.format(deviceAuth=urllib.quote(deviceAuth,''),search=urllib.quote(terms.encode('utf-8'), ''))
    elif category:
        url = SUGGEST_URL.format(deviceAuth=urllib.quote(deviceAuth,''),category=category)

    if not url:
        util.DEBUG_LOG('Search: No category or terms')
        return

    util.DEBUG_LOG('Search URL: {0}'.format(url))

    req = requests.get(url)

    try:
        results = req.json()
        if not results: return []
        return [Series(r) for r in results]
    except:
        util.ERROR()

    return None

def nowShowing(deviceAuth, utcUnixtime=None):
    start = ''
    if utcUnixtime:
        start = NOW_SHOWING_START.format(utcUnixtime=int(utcUnixtime))

    url = NOW_SHOWING_URL.format(deviceAuth=urllib.quote(deviceAuth,''), start=start)

    util.DEBUG_LOG('Now Showing URL: {0}'.format(url))

    req = requests.get(url)

    try:
        results = req.json()
        if not results: return []
        return [Series(r) for r in results]
    except:
        util.ERROR()

    return None

def slice(deviceAuth, channel, utcUnixtime=None):
    start = ''
    if utcUnixtime:
        start = NOW_SHOWING_START.format(utcUnixtime=int(utcUnixtime))

    url = SLICE_URL.format(deviceAuth=urllib.quote(deviceAuth,''), channel=channel.number, start=start)

    util.DEBUG_LOG('Slice URL: {0}'.format(url))

    req = requests.get(url)

    try:
        results = req.json()
        if not results: return []
        return [Episode(r) for r in results[0]['Guide']]
    except:
        util.ERROR()

    return None


class EndOfNowShowingException(Exception): pass

class NowShowing(object):
    def __init__(self, devices):
        self.devices = devices
        self.init()

    def init(self):
        self.data = []
        self.buckets = []
        self.pos = 0
        self.highestStart = 0
        self.atEnd = False
        self.data = self.getData()
        self.createBuckets()
        self.updateTimes()

    def createBuckets(self, add=False):
        util.DEBUG_LOG('Creating buckets from {0} items...'.format(len(self.data)))

        now = datetime.datetime.now()
        nowTS = time.mktime(now.timetuple())
        nowHalfHour = now - datetime.timedelta(minutes=now.minute%30, seconds=now.second, microseconds=now.microsecond)

        if add:
            nowHalfHour += datetime.timedelta(seconds=1800*(len(self.buckets)-1))
        else:
            self.buckets = []

            nowShowing = []
            while self.data:
                series = self.data.pop()

                if series.startTimestamp > self.highestStart:
                    self.highestStart = series.startTimestamp

                if series.startTimestamp <= nowTS < series.endTimestamp:
                    nowShowing.append(series)
                else:
                    self.data.append(series)
                    break

            nextHalfHour = nowHalfHour + datetime.timedelta(seconds=1800)

            self.buckets.append([nowShowing, 'NOW SHOWING', nextHalfHour])
            util.DEBUG_LOG('  Now showing: {0}'.format(len(nowShowing)))

        startHalfHour = nowHalfHour + datetime.timedelta(seconds=1800)
        endHalfHour = startHalfHour + datetime.timedelta(seconds=1800)
        startTS = time.mktime(startHalfHour.timetuple()) - 120
        endTS = time.mktime(endHalfHour.timetuple()) - 120

        curr = []
        while self.data:
            series = self.data.pop()

            if series.startTimestamp > self.highestStart:
                self.highestStart = series.startTimestamp

            if series.startTimestamp < endTS:
                curr.append(series)
            elif series.endTimestamp <= startTS:
                util.DEBUG_LOG('   -Discared old series')  # In case we happen to get a NS show that ended during processing
            else:
                self.data.append(series)

                self.buckets.append([curr, startHalfHour, endHalfHour])
                util.DEBUG_LOG('  Bucket  ({0}): {1}'.format(len(self.buckets) - 1, len(curr)))
                curr = []
                startHalfHour = startHalfHour + datetime.timedelta(seconds=1800)  # Add 28mins
                endHalfHour = startHalfHour + datetime.timedelta(seconds=1800)
                startTS += 1800
                endTS += 1800

        if curr:
            self.buckets.append([curr, startHalfHour, endHalfHour])
            util.DEBUG_LOG('  Bucket  ({0}): {1}'.format(len(self.buckets) - 1, len(curr)))

        self.nextUpdateTimestamp = self.highestStart - random.randint(0, 1800)

    def getData(self, utcUnixtime=None):
        start = ''
        if utcUnixtime:
            start = NOW_SHOWING_START.format(utcUnixtime=int(utcUnixtime))

        url = NOW_SHOWING_URL.format(deviceAuth=urllib.quote(self.devices.apiAuthID(),''), start=start)

        util.DEBUG_LOG('Now Showing URL: {0}'.format(url))

        req = requests.get(url)

        try:
            results = req.json()
            if not results:
                return []
            results.reverse()
            if not results: return []
            return [Series(r) for r in results]
        except:
            util.ERROR()

        return None

    def nowShowing(self):
        results, heading, endHalfHour = self.buckets[0]
        return results, heading, self.getTimeHeadingDisplay(endHalfHour)

    def upNext(self):
        if self.pos == 0:
            return self.nowShowing()

        if self.pos >= len(self.buckets):
            if self.atEnd:
                raise EndOfNowShowingException()
            self.addData()

        results, startHalfHour, endHalfHour = self.buckets[self.pos]
        if self.atEnd and self.pos == len(self.buckets) - 1:
            endDisp = 'END'
        else:
            endDisp = self.getTimeHeadingDisplay(endHalfHour)
        return results, self.getTimeHeadingDisplay(startHalfHour), endDisp

    def addData(self):
        util.DEBUG_LOG('NOW SHOWING: Adding data')
        self.atEnd = False
        self.data = self.getData(self.highestStart + 1)
        if not self.data:
            self.atEnd = True
            raise EndOfNowShowingException()
        self.createBuckets(add=True)

    def getTimeHeadingDisplay(self, dt, now=None):
        now = now or datetime.datetime.now()
        if now.day != dt.day:
            return dt.strftime('%A ') + dt.strftime('%I:%M %p').lstrip('0')
        else:
            return dt.strftime('%I:%M %p').lstrip('0')

    def unHide(self, series):
        if series.hidden:
            return

        for bucket in self.buckets:
            for s in bucket[0]:
                if s.ID == series.ID:
                    if 'SuggestHide' in s:
                        del s['SuggestHide']

    def updateBuckets(self):
        now = datetime.datetime.now()
        nowTS = time.mktime(now.timetuple())

        moved = 0
        new0 = []
        for s in self.buckets[0][0]:
            if s.endTimestamp <= nowTS:
                moved += 1
                continue
            new0.append(s)

        if moved:
            util.DEBUG_LOG('NOW SHOWING: {0} shows removed'.format(moved))

        moved = 0
        new1 = []
        for s in self.buckets[1][0]:
            if s.startTimestamp <= nowTS:
                moved += 1
                new0.append(s)
            else:
                new1.append(s)

        if not new0:
            return self.init()

        self.buckets[0][0] = new0

        if moved:
            util.DEBUG_LOG('NOW SHOWING: {0} shows moved'.format(moved))

        if len(self.buckets) <= 1:
            return

        if not new1:
            util.DEBUG_LOG('NOW SHOWING: Bucket Removed')
            del self.buckets[1]
            self.buckets[0][2] = self.buckets[1][1]
            self.atEnd = False

            if self.pos > 0:
                self.pos -= 1
        else:
            self.buckets[1][0] = new1

    def updateTimes(self):
        self.nextCheck = 31536000000
        for s in self.buckets[0][0]:
            if s.endTimestamp < self.nextCheck:
                self.nextCheck = s.endTimestamp

        for s in self.buckets[1][0]:
            if s.startTimestamp < self.nextCheck:
                self.nextCheck = s.startTimestamp

    def checkTime(self):
        now = time.time()
        if now > self.nextUpdateTimestamp:
            try:
                self.addData()
            except EndOfNowShowingException:
                pass

        if now >= self.nextCheck:
            self.updateBuckets()
            self.updateTimes()
            return True
        return False

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

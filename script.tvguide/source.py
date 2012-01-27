#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import os
import simplejson
import datetime
import time
import urllib2
from xml.etree import ElementTree
from strings import *
import ysapi

import xbmc
import xbmcgui
import xbmcvfs
import pickle
from sqlite3 import dbapi2 as sqlite3

STREAM_DR1 = 'plugin://plugin.video.dr.dk.live/?playChannel=1'
STREAM_DR2 = 'plugin://plugin.video.dr.dk.live/?playChannel=2'
STREAM_DR_UPDATE = 'plugin://plugin.video.dr.dk.live/?playChannel=3'
STREAM_DR_K = 'plugin://plugin.video.dr.dk.live/?playChannel=4'
STREAM_DR_RAMASJANG = 'plugin://plugin.video.dr.dk.live/?playChannel=5'
STREAM_DR_HD = 'plugin://plugin.video.dr.dk.live/?playChannel=6'
STREAM_24_NORDJYSKE = 'plugin://plugin.video.dr.dk.live/?playChannel=200'

class Channel(object):
    def __init__(self, id, title, logo = None, streamUrl = None):
        self.id = id
        self.title = title
        self.logo = logo
        self.streamUrl = streamUrl

    def isPlayable(self):
        return hasattr(self, 'streamUrl') and self.streamUrl

    def __repr__(self):
        return 'Channel(id=%s, title=%s, logo=%s, streamUrl=%s)' \
               % (self.id, self.title, self.logo, self.streamUrl)

class Program(object):
    def __init__(self, channel, title, startDate, endDate, description, imageLarge = None, imageSmall=None):
        """

        @param channel:
        @type channel: source.Channel
        @param title:
        @param startDate:
        @param endDate:
        @param description:
        @param imageLarge:
        @param imageSmall:
        """
        self.channel = channel
        self.title = title
        self.startDate = startDate
        self.endDate = endDate
        self.description = description
        self.imageLarge = imageLarge
        self.imageSmall = imageSmall

    def __repr__(self):
        return 'Program(channel=%s, title=%s, startDate=%s, endDate=%s, description=%s, imageLarge=%s, imageSmall=%s)' % \
            (self.channel, self.title, self.startDate, self.endDate, self.description, self.imageLarge, self.imageSmall)


class SourceException(Exception):
    pass


class Source(object):
    KEY = "undefiend"
    STREAMS = {}
    SOURCE_DB = 'source.db'

    def __init__(self, settings):
        self.cachePath = settings['cache.path']
        self.playbackUsingDanishLiveTV = False

        self.conn = sqlite3.connect(os.path.join(self.cachePath, self.SOURCE_DB), check_same_thread = False)
        self._createTables()

        try:
            if settings['danishlivetv.playback'] == 'true':
                xbmcaddon.Addon(id = 'plugin.video.dr.dk.live') # raises Exception if addon is not installed
                self.playbackUsingDanishLiveTV = True
        except Exception:
            ADDON.setSetting('danishlivetv.playback', 'false')
            xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), strings(DANISH_LIVE_TV_MISSING_1),
                strings(DANISH_LIVE_TV_MISSING_2), strings(DANISH_LIVE_TV_MISSING_3))


    def __del__(self):
        self.conn.close()

    def updateChannelAndProgramListCaches(self):
        xbmc.log("[script.tvguide] Updating channel list caches...", xbmc.LOGDEBUG)
        channelList = self.getChannelList()
        date = datetime.datetime.now()

        for channel in channelList:
            xbmc.log("[script.tvguide] Updating program list caches for channel " + channel.title.decode('iso-8859-1') + "...", xbmc.LOGDEBUG)
            self.getProgramList(channel, date)

        xbmc.log("[script.tvguide] Done updating caches.", xbmc.LOGDEBUG)

    def getChannelList(self):
        cacheFile = os.path.join(self.cachePath, self.KEY + '.channellist')
        channelList = None

        try:
            cachedOn = datetime.datetime.fromtimestamp(os.path.getmtime(cacheFile))
            cacheHit = cachedOn.day == datetime.datetime.now().day
        except OSError:
            cacheHit = False

        if cacheHit:
            try:
                channelList = pickle.load(open(cacheFile))
            except Exception:
                # Ignore cache load problem
                xbmc.log('[script.tvguide] Exception while loading cached channel list')

        if not cacheHit or not channelList:
            xbmc.log('[script.tvguide] Caching channel list...', xbmc.LOGDEBUG)
            try:
                channelList = self._getChannelList()
            except Exception as ex:
                raise SourceException(ex)

            # Setup additional stream urls
            for channel in channelList:
                if channel.streamUrl:
                    continue
                elif self.playbackUsingDanishLiveTV and self.STREAMS.has_key(channel.id):
                    channel.streamUrl = self.STREAMS[channel.id]

            pickle.dump(channelList, open(cacheFile, 'w'))

        return channelList

    def _getChannelList(self):
        return None

    def getProgramList(self, channel, date):
        if type(channel.id) in [str, unicode]:
            id = channel.id.encode('utf-8', errors='ignore')
        else:
            id = str(channel.id)

        dateString = date.strftime('%Y%m%d')
        cacheFile = os.path.join(self.cachePath, '%s-%s-%s.programlist' % (self.KEY, id.replace('/', ''), dateString))

        programList = None
        if os.path.exists(cacheFile):
            try:
                programList = pickle.load(open(cacheFile))
            except Exception:
                xbmc.log('[script.tvguide] Exception while loading cached program list for channel %s' % id)

        if not programList:
            xbmc.log('[script.tvguide] Caching program list for channel %s...' % id, xbmc.LOGDEBUG)
            try:
                programList = self._getProgramList(channel, date)
                pickle.dump(programList, open(cacheFile, 'w'))
            except Exception as ex:
                raise SourceException(ex)

        return programList
    
    def _getProgramList(self, channel, date):
        return None

    def _downloadUrl(self, url):
        u = urllib2.urlopen(url)
        content = u.read()
        u.close()
            
        return content

    def setCustomStreamUrl(self, channel, stream_url):
        c = self.conn.cursor()
        c.execute("DELETE FROM custom_stream_url WHERE channel=?", [channel.id])
        c.execute("INSERT INTO custom_stream_url(channel, stream_url) VALUES(?, ?)", [channel.id, stream_url])
        self.conn.commit()
        c.close()

    def getCustomStreamUrl(self, channel):
        c = self.conn.cursor()
        c.execute("SELECT stream_url FROM custom_stream_url WHERE channel=?", [channel.id])
        stream_url = c.fetchone()
        c.close()

        if stream_url:
            return stream_url[0]
        else:
            return None

    def deleteCustomStreamUrl(self, channel):
        c = self.conn.cursor()
        c.execute("DELETE FROM custom_stream_url WHERE channel=?", [channel.id])
        self.conn.commit()
        c.close()

    def isPlayable(self, channel):
        customStreamUrl = self.getCustomStreamUrl(channel)
        return customStreamUrl is not None or channel.isPlayable()

    def play(self, channel):
        customStreamUrl = self.getCustomStreamUrl(channel)
        if customStreamUrl:
            xbmc.log("Playing custom stream url: %s" % customStreamUrl)
            xbmc.Player().play(item = customStreamUrl)

        elif channel.isPlayable():
            xbmc.log("Playing : %s" % channel.streamUrl)
            xbmc.Player().play(item = channel.streamUrl)

    def _createTables(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS custom_stream_url(channel TEXT, stream_url TEXT)")
        c.close()


class DrDkSource(Source):
    KEY = 'drdk'
    CHANNELS_URL = 'http://www.dr.dk/tjenester/programoversigt/dbservice.ashx/getChannels?type=tv'
    PROGRAMS_URL = 'http://www.dr.dk/tjenester/programoversigt/dbservice.ashx/getSchedule?channel_source_url=%s&broadcastDate=%s'

    STREAMS = {
        'dr.dk/mas/whatson/channel/DR1' : STREAM_DR1,
        'dr.dk/mas/whatson/channel/DR2' : STREAM_DR2,
        'dr.dk/external/ritzau/channel/dru' : STREAM_DR_UPDATE,
        'dr.dk/mas/whatson/channel/TVR' : STREAM_DR_RAMASJANG,
        'dr.dk/mas/whatson/channel/TVK' : STREAM_DR_K,
        'dr.dk/mas/whatson/channel/TV' : STREAM_DR_HD
    }

    def __init__(self, settings):
        Source.__init__(self, settings)

    def _getChannelList(self):
        jsonChannels = simplejson.loads(self._downloadUrl(self.CHANNELS_URL))
        channelList = list()

        for channel in jsonChannels['result']:
            c = Channel(id = channel['source_url'], title = channel['name'])
            channelList.append(c)

        return channelList

    def _getProgramList(self, channel, date):
        url = self.PROGRAMS_URL % (channel.id.replace('+', '%2b'), date.strftime('%Y-%m-%dT00:00:00'))
        jsonPrograms = simplejson.loads(self._downloadUrl(url))
        programs = list()

        for program in jsonPrograms['result']:
            if program.has_key('ppu_description'):
                description = program['ppu_description']
            else:
                description = strings(NO_DESCRIPTION)

            programs.append(Program(channel, program['pro_title'], self._parseDate(program['pg_start']), self._parseDate(program['pg_stop']), description))

        return programs
    
    def _parseDate(self, dateString):
        t = time.strptime(dateString[:19], '%Y-%m-%dT%H:%M:%S')
        return datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)


class YouSeeTvSource(Source):
    KEY = 'youseetv'

    STREAMS = {
        1 : STREAM_DR1,
        2 : STREAM_DR2,
        889 : STREAM_DR_UPDATE,
        505: STREAM_DR_RAMASJANG,
        504 : STREAM_DR_K,
        503 : STREAM_DR_HD
    }

    def __init__(self, settings):
        Source.__init__(self, settings)
        self.date = datetime.datetime.today()
        self.channelCategory = settings['youseetv.category']
        self.ysApi = ysapi.YouSeeTVGuideApi()
        self.playbackUsingYouSeeWebTv = False

        try:
            if settings['youseewebtv.playback'] == 'true':
                xbmcaddon.Addon(id = 'plugin.video.yousee.tv') # raises Exception if addon is not installed
                self.playbackUsingYouSeeWebTv = True
        except Exception:
            ADDON.setSetting('youseewebtv.playback', 'false')
            xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), strings(YOUSEE_WEBTV_MISSING_1),
                strings(YOUSEE_WEBTV_MISSING_2), strings(YOUSEE_WEBTV_MISSING_3))

    def _getChannelList(self):
        channelList = list()
        for channel in self.ysApi.channelsInCategory(self.channelCategory):
            c = Channel(id = channel['id'], title = channel['name'], logo = channel['logo'])
            if self.playbackUsingYouSeeWebTv:
                c.streamUrl = 'plugin://plugin.video.yousee.tv/?channel=' + str(c.id)
            channelList.append(c)

        return channelList

    def _getProgramList(self, channel, date):
        programs = list()
        for program in self.ysApi.programs(channel.id, tvdate = date):
            description = program['description']
            if description is None:
                description = strings(NO_DESCRIPTION)

            imagePrefix = program['imageprefix']

            p = Program(
                channel,
                program['title'],
                self._parseDate(program['begin']),
                self._parseDate(program['end']),
                description,
                imagePrefix + program['images_sixteenbynine']['large'],
                imagePrefix + program['images_sixteenbynine']['small'],
            )
            programs.append(p)

        return programs

    def _parseDate(self, dateString):
        return datetime.datetime.fromtimestamp(dateString)


class TvTidSource(Source):
    KEY = 'tvtiddk'

    BASE_URL = 'http://tvtid.tv2.dk%s'
    CHANNELS_URL = BASE_URL % '/api/channels.php/'
    PROGRAMS_URL = BASE_URL % '/api/programs.php/date-%s.json'

    STREAMS = {
        11825154 : STREAM_DR1,
        11823606 : STREAM_DR2,
        11841417 : STREAM_DR_UPDATE,
        25995179 : STREAM_DR_RAMASJANG,
        26000893 : STREAM_DR_K,
        26005640 : STREAM_DR_HD
    }

    def __init__(self, settings):
        Source.__init__(self, settings)

    def _getChannelList(self):
        response = self._downloadUrl(self.CHANNELS_URL)
        channels = simplejson.loads(response)
        channelList = list()
        for channel in channels:
            logoFile = channel['images']['114x50']['url']

            c = Channel(id = channel['id'], title = channel['name'], logo = logoFile)
            channelList.append(c)

        return channelList

    def _getProgramList(self, channel, date):
        """

        @param channel:
        @param date:
        @type date: datetime.datetime
        @return:
        """
        dateString = date.strftime('%Y%m%d')
        cacheFile = os.path.join(self.cachePath, '%s-%s-%s.programlist.source' % (self.KEY, channel.id, dateString))
        json = None
        if os.path.exists(cacheFile):
            try:
                json = pickle.load(open(cacheFile))
            except Exception:
                pass

        if not os.path.exists(cacheFile) or json is None:
            response = self._downloadUrl(self.PROGRAMS_URL % date.strftime('%Y%m%d'))
            json = simplejson.loads(response)
            pickle.dump(json, open(cacheFile, 'w'))


        # assume we always find a channel
        programs = list()

        for program in json[str(channel.id)]:
            if program.has_key('review'):
                description = program['review']
            else:
                description = strings(NO_DESCRIPTION)

            programs.append(Program(channel, program['title'], datetime.datetime.fromtimestamp(program['sts']), datetime.datetime.fromtimestamp(program['ets']), description))

        return programs

class XMLTVSource(Source):
    KEY = 'xmltv'

    STREAMS = {
        'DR1.dr.dk' : STREAM_DR1,
        'www.ontv.dk/tv/1' : STREAM_DR1
    }

    def __init__(self, settings):
        self.logoFolder = settings['xmltv.logo.folder']
        self.time = time.time()

        super(XMLTVSource, self).__init__(settings)

        self.xmlTvFile = os.path.join(self.cachePath, '%s.xmltv' % self.KEY)
        if xbmcvfs.exists(settings['xmltv.file']):
            xbmc.log('[script.tvguide] Caching XMLTV file...')
            xbmcvfs.copy(settings['xmltv.file'], self.xmlTvFile)

        # calculate nearest hour
        self.time -= self.time % 3600

    def _getChannelList(self):
        doc = self._loadXml()
        channelList = list()
        for channel in doc.findall('channel'):
            title = channel.findtext('display-name')
            logo = None
            if self.logoFolder:
                logoFile = os.path.join(self.logoFolder, title + '.png')
                if xbmcvfs.exists(logoFile):
                    logo = logoFile
            if channel.find('icon'):
                logo = channel.find('icon').get('src')
            c = Channel(id = channel.get('id'), title = title, logo = logo)
            channelList.append(c)

        return channelList

    def _getProgramList(self, channel, date):
        doc = self._loadXml()
        programs = list()
        for program in doc.findall('programme'):
            if program.get('channel') != channel.id:
                continue

            description = program.findtext('desc')
            if description is None:
                description = strings(NO_DESCRIPTION)

            programs.append(Program(channel, program.findtext('title'), self._parseDate(program.get('start')), self._parseDate(program.get('stop')), description))

        return programs

    def _loadXml(self):
        f = open(self.xmlTvFile)
        xml = f.read()
        f.close()

        return ElementTree.fromstring(xml)


    def _parseDate(self, dateString):
        dateStringWithoutTimeZone = dateString[:-6]
        t = time.strptime(dateStringWithoutTimeZone, '%Y%m%d%H%M%S')
        return datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)


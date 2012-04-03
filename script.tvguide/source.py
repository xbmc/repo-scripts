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
import StringIO
import os
import simplejson
import datetime
import threading
import time
import urllib2
from xml.etree import ElementTree
from strings import *
import ysapi
import buggalo
import xbmc
import xbmcgui
import xbmcvfs
from sqlite3 import dbapi2 as sqlite3

STREAM_DR1 = 'plugin://plugin.video.dr.dk.live/?playChannel=1'
STREAM_DR2 = 'plugin://plugin.video.dr.dk.live/?playChannel=2'
STREAM_DR_UPDATE = 'plugin://plugin.video.dr.dk.live/?playChannel=3'
STREAM_DR_K = 'plugin://plugin.video.dr.dk.live/?playChannel=4'
STREAM_DR_RAMASJANG = 'plugin://plugin.video.dr.dk.live/?playChannel=5'
STREAM_DR_HD = 'plugin://plugin.video.dr.dk.live/?playChannel=6'

SETTINGS_TO_CHECK = ['source', 'youseetv.category', 'youseewebtv.playback', 'danishlivetv.playback', 'xmltv.file',
                     'xmltv.logo.folder', 'ontv.url']

class Channel(object):
    def __init__(self, id, title, logo = None, streamUrl = None, visible = True, weight = -1):
        self.id = id
        self.title = title
        self.logo = logo
        self.streamUrl = streamUrl
        self.visible = visible
        self.weight = weight

    def isPlayable(self):
        return hasattr(self, 'streamUrl') and self.streamUrl

    def __repr__(self):
        return 'Channel(id=%s, title=%s, logo=%s, streamUrl=%s)' \
               % (self.id, self.title, self.logo, self.streamUrl)

class Program(object):
    def __init__(self, channel, title, startDate, endDate, description, imageLarge = None, imageSmall=None, notificationScheduled = None):
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
        self.notificationScheduled = notificationScheduled

    def __repr__(self):
        return 'Program(channel=%s, title=%s, startDate=%s, endDate=%s, description=%s, imageLarge=%s, imageSmall=%s)' % \
            (self.channel, self.title, self.startDate, self.endDate, self.description, self.imageLarge, self.imageSmall)

class SourceException(Exception):
    pass

class SourceUpdateInProgressException(SourceException):
    pass

class SourceUpdateCanceledException(SourceException):
    pass

class Source(object):
    KEY = "undefined"
    STREAMS = {}
    SOURCE_DB = 'source.db'

    def __init__(self, addon, cachePath):
        self.cachePath = cachePath
        self.updateInProgress = False
        buggalo.addExtraData('source', self.KEY)
        for key in SETTINGS_TO_CHECK:
            buggalo.addExtraData('setting: %s' % key, ADDON.getSetting(key))

        try:
            self.conn = sqlite3.connect(os.path.join(self.cachePath, self.SOURCE_DB), detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread = False)
            self.conn.execute('PRAGMA foreign_keys = ON')
            self.conn.row_factory = sqlite3.Row
            self._createTables()
        except sqlite3.OperationalError, ex:
            raise SourceUpdateInProgressException(ex)

        self.playbackUsingDanishLiveTV = False
        self.channelList = list()
        self.player = xbmc.Player()
        self.settingsChanged = self.wasSettingsChanged(addon)

        try:
            if addon.getSetting('danishlivetv.playback') == 'true':
                xbmcaddon.Addon(id = 'plugin.video.dr.dk.live') # raises Exception if addon is not installed
                self.playbackUsingDanishLiveTV = True
        except Exception:
            ADDON.setSetting('danishlivetv.playback', 'false')
            xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), strings(DANISH_LIVE_TV_MISSING_1),
                strings(DANISH_LIVE_TV_MISSING_2), strings(DANISH_LIVE_TV_MISSING_3))

    def close(self):
        #self.conn.rollback() # rollback any non-commit'ed changes to avoid database lock
        self.conn.close()

    def wasSettingsChanged(self, addon):
        settingsChanged = False
        noRows = True
        count = 0

        c = self.conn.cursor()
        c.execute('SELECT * FROM settings')
        for row in c:
            count += 1
            noRows = False
            key = row['key']
            if SETTINGS_TO_CHECK.count(key) and row['value'] != addon.getSetting(key):
                settingsChanged = True

        if count != len(SETTINGS_TO_CHECK):
            settingsChanged = True

        if settingsChanged or noRows:
            for key in SETTINGS_TO_CHECK:
                c.execute('INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)', [key, addon.getSetting(key)])
                if not c.rowcount:
                    c.execute('UPDATE settings SET value=? WHERE key=?', [addon.getSetting(key), key])
            self.conn.commit()

        c.close()
        print 'Settings changed: ' + str(settingsChanged)
        return settingsChanged

    def getDataFromExternal(self, date, progress_callback = None):
        """
        Retrieve data from external as a list or iterable. Data may contain both Channel and Program objects.
        The source may choose to ignore the date parameter and return all data available.

        @param date: the date to retrieve the data for
        @param progress_callback:
        @return:
        """
        raise SourceException('getDataFromExternal not implemented!')

    def isCacheExpired(self, date = datetime.datetime.now()):
        return self.settingsChanged or self._isChannelListCacheExpired() or self._isProgramListCacheExpired(date)

    def updateChannelAndProgramListCaches(self, date = datetime.datetime.now(), progress_callback = None, clearExistingProgramList = True):
        self.updateInProgress = True
        dateStr = date.strftime('%Y-%m-%d')
        c = self.conn.cursor()
        try:
            xbmc.log('[script.tvguide] Updating caches...', xbmc.LOGDEBUG)
            if progress_callback:
                progress_callback(0)

            if self.settingsChanged:
                c.execute('DELETE FROM channels WHERE source=?', [self.KEY])
                c.execute('DELETE FROM programs WHERE source=?', [self.KEY])
                c.execute("DELETE FROM updates WHERE source=?", [self.KEY])
            self.settingsChanged = False # only want to update once due to changed settings

            if clearExistingProgramList:
                c.execute("DELETE FROM updates WHERE source=?", [self.KEY]) # cascades and deletes associated programs records
            else:
                c.execute("DELETE FROM updates WHERE source=? AND date=?", [self.KEY, dateStr]) # cascades and deletes associated programs records

            # programs updated
            c.execute("INSERT INTO updates(source, date, programs_updated) VALUES(?, ?, ?)", [self.KEY, dateStr, datetime.datetime.now()])
            updatesId = c.lastrowid

            imported = 0
            for item in self.getDataFromExternal(date, progress_callback):
                imported += 1

                if imported % 10000 == 0:
                    self.conn.commit()

                if isinstance(item, Channel):
                    channel = item
                    if not channel.streamUrl and self.playbackUsingDanishLiveTV and self.STREAMS.has_key(channel.id):
                        channel.streamUrl = self.STREAMS[channel.id]
                    c.execute('INSERT OR IGNORE INTO channels(id, title, logo, stream_url, visible, weight, source) VALUES(?, ?, ?, ?, ?, (CASE ? WHEN -1 THEN (SELECT COALESCE(MAX(weight)+1, 0) FROM channels WHERE source=?) ELSE ? END), ?)', [channel.id, channel.title, channel.logo, channel.streamUrl, channel.visible, channel.weight, self.KEY, channel.weight, self.KEY])
                    if not c.rowcount:
                        c.execute('UPDATE channels SET title=?, logo=?, stream_url=?, visible=?, weight=(CASE ? WHEN -1 THEN weight ELSE ? END) WHERE id=? AND source=?', [channel.title, channel.logo, channel.streamUrl, channel.visible, channel.weight, channel.weight, channel.id, self.KEY])

                elif isinstance(item, Program):
                    program = item
                    if isinstance(program.channel, Channel):
                        channel = program.channel.id
                    else:
                        channel = program.channel

                    c.execute('INSERT INTO programs(channel, title, start_date, end_date, description, image_large, image_small, source, updates_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        [channel, program.title, program.startDate, program.endDate, program.description, program.imageLarge, program.imageSmall, self.KEY, updatesId])

            # channels updated
            c.execute("UPDATE sources SET channels_updated=? WHERE id=?", [datetime.datetime.now(),self.KEY])
            self.conn.commit()

        except SourceUpdateCanceledException:
            # force source update on next load
            c.execute('UPDATE sources SET channels_updated=? WHERE id=?', [datetime.datetime.fromtimestamp(0), self.KEY])
            c.execute("DELETE FROM updates WHERE source=?", [self.KEY]) # cascades and deletes associated programs records
            self.conn.commit()

        except Exception, ex:
            self.conn.rollback()

            import traceback as tb
            import sys
            (type, value, traceback) = sys.exc_info()
            tb.print_exception(type, value, traceback)

            # invalidate cached data
            c.execute('UPDATE sources SET channels_updated=? WHERE id=?', [datetime.datetime.fromtimestamp(0), self.KEY])
            self.conn.commit()

            raise SourceException(ex)
        finally:
            self.updateInProgress = False
            c.close()

    def getChannel(self, id):
        c = self.conn.cursor()
        c.execute('SELECT * FROM channels WHERE source=? AND id=?', [self.KEY, id])
        row = c.fetchone()
        channel = Channel(row['id'], row['title'],row['logo'], row['stream_url'], row['visible'], row['weight'])
        c.close()

        return channel

    def getNextChannel(self, currentChannel):
        channels = self.getChannelList()
        idx = channels.index(currentChannel)
        idx += 1
        if idx > len(channels) - 1:
            idx = 0
        return channels[idx]

    def getPreviousChannel(self, currentChannel):
        channels = self.getChannelList()
        idx = channels.index(currentChannel)
        idx -= 1
        if idx < 0:
            idx = len(channels) - 1
        return channels[idx]

    def getChannelList(self):
        # cache channelList in memory
        if not self.channelList:
            self.channelList = self._retrieveChannelListFromDatabase()

        return self.channelList

    def _storeChannelListInDatabase(self, channelList):
        c = self.conn.cursor()
        for idx, channel in enumerate(channelList):
            c.execute('INSERT OR IGNORE INTO channels(id, title, logo, stream_url, visible, weight, source) VALUES(?, ?, ?, ?, ?, (CASE ? WHEN -1 THEN (SELECT COALESCE(MAX(weight)+1, 0) FROM channels WHERE source=?) ELSE ? END), ?)', [channel.id, channel.title, channel.logo, channel.streamUrl, channel.visible, channel.weight, self.KEY, channel.weight, self.KEY])
            if not c.rowcount:
                c.execute('UPDATE channels SET title=?, logo=?, stream_url=?, visible=?, weight=(CASE ? WHEN -1 THEN weight ELSE ? END) WHERE id=? AND source=?', [channel.title, channel.logo, channel.streamUrl, channel.visible, channel.weight, channel.weight, channel.id, self.KEY])

        c.execute("UPDATE sources SET channels_updated=? WHERE id=?", [datetime.datetime.now(), self.KEY])
        self.channelList = None
        self.conn.commit()

    def _retrieveChannelListFromDatabase(self, onlyVisible = True):
        c = self.conn.cursor()
        channelList = list()
        if onlyVisible:
            c.execute('SELECT * FROM channels WHERE source=? AND visible=? ORDER BY weight', [self.KEY, True])
        else:
            c.execute('SELECT * FROM channels WHERE source=? ORDER BY weight', [self.KEY])
        for row in c:
            channel = Channel(row['id'], row['title'],row['logo'], row['stream_url'], row['visible'], row['weight'])
            channelList.append(channel)
        c.close()
        return channelList

    def _isChannelListCacheExpired(self):
        c = self.conn.cursor()
        c.execute('SELECT channels_updated FROM sources WHERE id=?', [self.KEY])
        lastUpdated = c.fetchone()['channels_updated']
        c.close()

        today = datetime.datetime.now()
        return lastUpdated.day != today.day

    def getCurrentProgram(self, channel):
        """

        @param channel:
        @type channel: source.Channel
        @return:
        """
        now = datetime.datetime.now()
        c = self.conn.cursor()
        c.execute('SELECT * FROM programs WHERE channel=? AND source=? AND start_date <= ? AND end_date >= ?', [channel.id, self.KEY, now, now])
        row = c.fetchone()
        program = Program(channel, row['title'], row['start_date'], row['end_date'], row['description'], row['image_large'], row['image_small'])
        c.close()

        return program

    def getNextProgram(self, program):
        nextProgram = None
        c = self.conn.cursor()
        c.execute('SELECT * FROM programs WHERE channel=? AND source=? AND start_date >= ? ORDER BY start_date ASC LIMIT 1', [program.channel.id, self.KEY, program.endDate])
        row = c.fetchone()
        if row:
            nextProgram = Program(program.channel, row['title'], row['start_date'], row['end_date'], row['description'], row['image_large'], row['image_small'])
        c.close()

        return nextProgram

    def getPreviousProgram(self, program):
        previousProgram = None
        c = self.conn.cursor()
        c.execute('SELECT * FROM programs WHERE channel=? AND source=? AND end_date <= ? ORDER BY start_date DESC LIMIT 1', [program.channel.id, self.KEY, program.startDate])
        row = c.fetchone()
        if row:
            previousProgram = Program(program.channel, row['title'], row['start_date'], row['end_date'], row['description'], row['image_large'], row['image_small'])
        c.close()

        return previousProgram

    def getProgramList(self, channels, startTime):
        """

        @param channels:
        @type channels: list of source.Channel
        @param startTime:
        @type startTime: datetime.datetime
        @return:
        """
        endTime = startTime + datetime.timedelta(hours = 2)
        programList = list()

        channelMap = dict()
        for c in channels:
            channelMap[c.id] = c

        c = self.conn.cursor()
        c.execute('SELECT p.*, (SELECT 1 FROM notifications n WHERE n.channel=p.channel AND n.program_title=p.title AND n.source=p.source) AS notification_scheduled FROM programs p WHERE p.channel IN (\'' + ('\',\''.join(channelMap.keys())) + '\') AND p.source=? AND p.end_date >= ? AND p.start_date <= ?', [self.KEY, startTime, endTime])
        for row in c:
            program = Program(channelMap[row['channel']], row['title'], row['start_date'], row['end_date'], row['description'], row['image_large'], row['image_small'], row['notification_scheduled'])
            programList.append(program)

        return programList

    def _isProgramListCacheExpired(self, date = datetime.datetime.now()):
        # check if data is up-to-date in database
        dateStr = date.strftime('%Y-%m-%d')
        c = self.conn.cursor()
        c.execute('SELECT programs_updated FROM updates WHERE source=? AND date=?', [self.KEY, dateStr])
        row = c.fetchone()
        today = datetime.datetime.now()
        expired = row is None or row['programs_updated'].day != today.day
        c.close()
        return expired


    def _downloadUrl(self, url):
        u = urllib2.urlopen(url, timeout=30)
        content = u.read()
        u.close()
            
        return content

    def setCustomStreamUrl(self, channel, stream_url):
        c = self.conn.cursor()
        c.execute("DELETE FROM custom_stream_url WHERE channel=?", [channel.id])
        c.execute("INSERT INTO custom_stream_url(channel, stream_url) VALUES(?, ?)", [channel.id, stream_url.decode('utf-8', 'ignore')])
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

    def isPlaying(self):
        return self.player.isPlaying()

    def play(self, channel, playBackStoppedHandler):
        threading.Timer(0.5, self.playInThread, [channel, playBackStoppedHandler]).start()

    @buggalo.buggalo_try_except({'method' : 'source.playThread'})
    def playInThread(self, channel, playBackStoppedHandler):
        customStreamUrl = self.getCustomStreamUrl(channel)
        if customStreamUrl:
            customStreamUrl = customStreamUrl.encode('utf-8', 'ignore')
            xbmc.log("Playing custom stream url: %s" % customStreamUrl)
            self.player.play(item = customStreamUrl, windowed=True)

        elif channel.isPlayable():
            streamUrl = channel.streamUrl.encode('utf-8', 'ignore')
            xbmc.log("Playing : %s" % streamUrl)
            self.player.play(item = streamUrl, windowed=True)

        while True:
            xbmc.sleep(250)
            if not self.player.isPlaying():
                break

        playBackStoppedHandler.onPlayBackStopped()

    def _createTables(self):
        c = self.conn.cursor()

        try:
            c.execute('SELECT major, minor, patch FROM version')
            (major, minor, patch) = c.fetchone()
            version = [major, minor, patch]
        except sqlite3.OperationalError:
            version = [0, 0, 0]

        if version < [1, 3, 0]:
            c.execute('CREATE TABLE IF NOT EXISTS custom_stream_url(channel TEXT, stream_url TEXT)')
            c.execute('CREATE TABLE version (major INTEGER, minor INTEGER, patch INTEGER)')
            c.execute('INSERT INTO version(major, minor, patch) VALUES(1, 3, 0)')

            # For caching data
            c.execute('CREATE TABLE sources(id TEXT PRIMARY KEY, channels_updated TIMESTAMP)')
            c.execute('CREATE TABLE updates(id INTEGER PRIMARY KEY, source TEXT, date TEXT, programs_updated TIMESTAMP)')
            c.execute('CREATE TABLE channels(id TEXT, title TEXT, logo TEXT, stream_url TEXT, source TEXT, visible BOOLEAN, weight INTEGER, PRIMARY KEY (id, source), FOREIGN KEY(source) REFERENCES sources(id) ON DELETE CASCADE)')
            c.execute('CREATE TABLE programs(channel TEXT, title TEXT, start_date TIMESTAMP, end_date TIMESTAMP, description TEXT, image_large TEXT, image_small TEXT, source TEXT, updates_id INTEGER, FOREIGN KEY(channel, source) REFERENCES channels(id, source) ON DELETE CASCADE, FOREIGN KEY(updates_id) REFERENCES updates(id) ON DELETE CASCADE)')
            c.execute('CREATE INDEX program_list_idx ON programs(source, channel, start_date, end_date)')
            c.execute('CREATE INDEX start_date_idx ON programs(start_date)')
            c.execute('CREATE INDEX end_date_idx ON programs(end_date)')

            # For active setting
            c.execute('CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT)')

            # For notifications
            c.execute("CREATE TABLE notifications(channel TEXT, program_title TEXT, source TEXT, FOREIGN KEY(channel, source) REFERENCES channels(id, source) ON DELETE CASCADE)")


        # make sure we have a record in sources for this Source
        c.execute("INSERT OR IGNORE INTO sources(id, channels_updated) VALUES(?, ?)", [self.KEY, datetime.datetime.fromtimestamp(0)])

        self.conn.commit()
        c.close()


class DrDkSource(Source):
    KEY = 'drdk'
    CHANNELS_URL = 'http://www.dr.dk/tjenester/programoversigt/dbservice.ashx/getChannels?type=tv'
    PROGRAMS_URL = 'http://www.dr.dk/tjenester/programoversigt/dbservice.ashx/getSchedule?channel_source_url=%s&broadcastDate=%s'

    STREAMS = {
        'dr.dk/mas/whatson/channel/DR1' : STREAM_DR1,
        'dr.dk/mas/whatson/channel/DR2' : STREAM_DR2,
        'dr.dk/external/ritzau/ channel/dru' : STREAM_DR_UPDATE,
        'dr.dk/mas/whatson/channel/TVR' : STREAM_DR_RAMASJANG,
        'dr.dk/mas/whatson/channel/TVK' : STREAM_DR_K,
        'dr.dk/mas/whatson/channel/TV' : STREAM_DR_HD
    }

    def __init__(self, addon, cachePath):
        super(DrDkSource, self).__init__(addon, cachePath)

    def getDataFromExternal(self, date, progress_callback = None):
        jsonChannels = simplejson.loads(self._downloadUrl(self.CHANNELS_URL))

        channels = jsonChannels['result']
        for idx, channel in enumerate(channels):
            c = Channel(id = channel['source_url'], title = channel['name'])
            yield c

            url = self.PROGRAMS_URL % (channel['source_url'].replace('+', '%2b'), date.strftime('%Y-%m-%dT00:00:00'))
            jsonPrograms = simplejson.loads(self._downloadUrl(url))
            for program in jsonPrograms['result']:
                if program.has_key('ppu_description'):
                    description = program['ppu_description']
                else:
                    description = strings(NO_DESCRIPTION)

                p = Program(c, program['pro_title'], self._parseDate(program['pg_start']), self._parseDate(program['pg_stop']), description)
                yield p

            if progress_callback:
                if not progress_callback(100.0 / len(channels) * idx):
                    raise SourceUpdateCanceledException()

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

    def __init__(self, addon, cachePath):
        super(YouSeeTvSource, self).__init__(addon, cachePath)
        self.date = datetime.datetime.today()
        self.channelCategory = addon.getSetting('youseetv.category')
        self.ysApi = ysapi.YouSeeTVGuideApi()
        self.playbackUsingYouSeeWebTv = False

        try:
            if addon.getSetting('youseewebtv.playback') == 'true':
                xbmcaddon.Addon(id = 'plugin.video.yousee.tv') # raises Exception if addon is not installed
                self.playbackUsingYouSeeWebTv = True
        except Exception:
            ADDON.setSetting('youseewebtv.playback', 'false')
            xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), strings(YOUSEE_WEBTV_MISSING_1),
                strings(YOUSEE_WEBTV_MISSING_2), strings(YOUSEE_WEBTV_MISSING_3))

    def getDataFromExternal(self, date, progress_callback = None):
        channels = self.ysApi.channelsInCategory(self.channelCategory)
        for idx, channel in enumerate(channels):
            c = Channel(id = channel['id'], title = channel['name'], logo = channel['logo'])
            if self.playbackUsingYouSeeWebTv:
                c.streamUrl = 'plugin://plugin.video.yousee.tv/?channel=' + str(c.id)
            yield c

            for program in self.ysApi.programs(c.id, tvdate = date):
                description = program['description']
                if description is None:
                    description = strings(NO_DESCRIPTION)

                imagePrefix = program['imageprefix']

                p = Program(
                    c,
                    program['title'],
                    self._parseDate(program['begin']),
                    self._parseDate(program['end']),
                    description,
                    imagePrefix + program['images_sixteenbynine']['large'],
                    imagePrefix + program['images_sixteenbynine']['small'],
                )
                yield p


            if progress_callback:
                if not progress_callback(100.0 / len(channels) * idx):
                    raise SourceUpdateCanceledException()

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

    def __init__(self, addon, cachePath):
        super(TvTidSource, self).__init__(addon, cachePath)

    def getDataFromExternal(self, date, progress_callback = None):
        response = self._downloadUrl(self.CHANNELS_URL)
        channels = simplejson.loads(response)

        response = self._downloadUrl(self.PROGRAMS_URL % date.strftime('%Y%m%d'))
        programs = simplejson.loads(response)

        for idx, channel in enumerate(channels):
            logoFile = channel['images']['114x50']['url']

            c = Channel(id = channel['id'], title = channel['name'], logo = logoFile)
            yield c

            for program in programs[str(c.id)]:
                if program.has_key('review'):
                    description = program['review']
                else:
                    description = strings(NO_DESCRIPTION)
                p = Program(c, program['title'], datetime.datetime.fromtimestamp(program['sts']), datetime.datetime.fromtimestamp(program['ets']), description)
                yield p

            if progress_callback:
                if not progress_callback(100.0 / len(channels) * idx):
                    raise SourceUpdateCanceledException()


class XMLTVSource(Source):
    KEY = 'xmltv'

    STREAMS = {
        'www.ontv.dk/tv/1' : STREAM_DR1,
        'www.ontv.dk/tv/2' : STREAM_DR2,
        'www.ontv.dk/tv/10153' : STREAM_DR_RAMASJANG,
        'www.ontv.dk/tv/10154' : STREAM_DR_K,
        'www.ontv.dk/tv/10155' : STREAM_DR_HD
    }

    def __init__(self, addon, cachePath):
        super(XMLTVSource, self).__init__(addon, cachePath)
        self.logoFolder = addon.getSetting('xmltv.logo.folder')
        self.xmlTvFileLastChecked = datetime.datetime.fromtimestamp(0)

        self.xmlTvFile = os.path.join(self.cachePath, '%s.xmltv' % self.KEY)
        tempFile = os.path.join(self.cachePath, '%s.xmltv.tmp' % self.KEY)
        if xbmcvfs.exists(addon.getSetting('xmltv.file')):
            xbmc.log('[script.tvguide] Caching XMLTV file...')
            xbmcvfs.copy(addon.getSetting('xmltv.file'), tempFile)

            # if xmlTvFile doesn't exists or the file size is different from tempFile
            # we copy the tempFile to xmlTvFile which in turn triggers a reload in self._isChannelListCacheExpired(..)
            if not os.path.exists(self.xmlTvFile) or os.path.getsize(self.xmlTvFile) != os.path.getsize(tempFile):
                os.rename(tempFile, self.xmlTvFile)

    def getDataFromExternal(self, date, progress_callback = None):
        context, f, size = self._loadXml()
        event, root = context.next()
        elements_parsed = 0

        for event, elem in context:
            if event == "end":
                result = None
                if elem.tag == "programme":
                    channel = elem.get("channel")
                    description = elem.findtext("desc")
                    iconElement = elem.find("icon")
                    icon = None
                    if iconElement is not None:
                        icon = iconElement.get("src")
                    if not description:
                        description = strings(NO_DESCRIPTION)
                    result = Program(channel, elem.findtext('title'), self._parseDate(elem.get('start')), self._parseDate(elem.get('stop')), description, imageSmall=icon)

                elif elem.tag == "channel":
                    id = elem.get("id")
                    title = elem.findtext("display-name")
                    logo = None
                    if self.logoFolder:
                        logoFile = os.path.join(self.logoFolder, title + '.png')
                        if xbmcvfs.exists(logoFile):
                            logo = logoFile
                    if not logo:
                        iconElement = elem.find("icon")
                        if iconElement is not None:
                            logo = iconElement.get("src")
                    result = Channel(id, title, logo)

                if result:
                    elements_parsed += 1
                    if progress_callback and elements_parsed % 500 == 0:
                        if not progress_callback(100.0 / size * f.tell()):
                            raise SourceUpdateCanceledException()
                    yield result

            root.clear()

    def _isChannelListCacheExpired(self):
        """
        Check if xmlTvFile was modified, otherwise cache is not expired.
        Only check filesystem once every 5 minutes
        """
        delta = datetime.datetime.now() - self.xmlTvFileLastChecked
        print str(delta.seconds)
        if delta.seconds < 300:
            return False

        c = self.conn.cursor()
        c.execute('SELECT channels_updated FROM sources WHERE id=?', [self.KEY])
        lastUpdated = c.fetchone()['channels_updated']
        c.close()

        fileModified = datetime.datetime.fromtimestamp(os.path.getmtime(self.xmlTvFile))
        return fileModified > lastUpdated


    def _isProgramListCacheExpired(self, startTime):
        return self._isChannelListCacheExpired()

    def _loadXml(self):
        size = os.path.getsize(self.xmlTvFile)
        f = open(self.xmlTvFile, "rb")
        context = ElementTree.iterparse(f, events=("start", "end"))
        return context, f, size

    def _parseDate(self, dateString):
        dateStringWithoutTimeZone = dateString[:-6]
        t = time.strptime(dateStringWithoutTimeZone, '%Y%m%d%H%M%S')
        return datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)


class ONTVSource(XMLTVSource):
    KEY = 'ontv'

    def __init__(self, addon, cachePath):
        super(ONTVSource, self).__init__(addon, cachePath)
        self.ontvUrl = addon.getSetting('ontv.url')

    def _isChannelListCacheExpired(self):
        return Source._isChannelListCacheExpired(self)

    def _loadXml(self):
        xml = self._downloadUrl(self.ontvUrl)
        io = StringIO.StringIO(xml)
        context = ElementTree.iterparse(io)
        return context, io, len(xml)


def instantiateSource(addon):
    SOURCES = {
        'YouSee.tv' : YouSeeTvSource,
        'DR.dk' : DrDkSource,
        'TVTID.dk' : TvTidSource,
        'XMLTV' : XMLTVSource,
        'ONTV.dk' : ONTVSource
    }

    cachePath = xbmc.translatePath(ADDON.getAddonInfo('profile'))

    if not os.path.exists(cachePath):
        os.makedirs(cachePath)

    try:
        activeSource = SOURCES[addon.getSetting('source')]
    except KeyError:
        activeSource = SOURCES['YouSee.tv']

    return activeSource(addon, cachePath)



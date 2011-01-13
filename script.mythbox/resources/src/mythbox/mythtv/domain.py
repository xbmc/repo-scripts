#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2010 analogue@yahoo.com
# 
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import datetime
import logging
import os
import re
import sre
import time

import mythbox.msg as m
from ffmpeg import FFMPEG
from mythbox.mythtv.db import inject_db
from mythbox.mythtv.enums import CheckForDupesIn, CheckForDupesUsing, \
    EpisodeFilter, FlagMask, JobStatus, JobType, RecordingStatus, \
    ScheduleType, Upcoming
from mythbox.platform import WindowsPlatform
from mythbox.ui.toolkit import showPopup
from mythbox.util import timed, formatSeconds, formatSize, synchronized, requireDir
from odict import odict

log = logging.getLogger('mythbox.core')


def dbTime2MythTime(dt):
    """
    Converts a time from the database into a format MythTV understands. 
    
    @type dt: a datetime, timedelta, or string time returned from the pure python mysql module
    @return: time in mythtv format as a string
    """
    if dt is None:
        raise Exception, 'datetime paramater is None'
    elif type(dt) is str:
        # TODO: Remove me - pure python mysql support
        s = sre.sub( "[T:|\\-| ]", "", dt) 
    elif type(dt) is datetime.datetime:
        # Native MySQLdb
        s = dt.strftime("%Y%m%d%H%M%S")
    elif type(dt) is datetime.timedelta:
        #print('dt = %s dt.days = %s dt.ms = %s dt.scs = %s' % (str(dt), str(dt.days), str(dt.microseconds), str(dt.seconds)))
        #xxx = 'dt.seconds = %d' % dt.seconds
        #print(xxx)
        #xtype = type(dt.seconds)
        #print('dt.seconds type = %s' % xtype)
        gt = time.gmtime(dt.seconds)
        s = time.strftime("%H%M%S", gt)
    elif type(dt) is datetime.date:
        s = dt.strftime("%Y%m%d")
    elif type(dt) is datetime.time:
        s = dt.strftime("%H%M%S")
    else:
        raise Exception, 'Expected datetime, date, timedelta, or string. Actual type: %s' % type(dt)
    return s


def ctime2MythTime(ctimeLong):
    """
    Converts a long representing a ctime into a format MythTV understands. 
     
    @param ctimeLong: millis elapsed since some date in 1970 as a string or int
    @return: time as a string in 'MythTV' format: YYYYMMDDHHmmSS 
    """
    return time.strftime("%Y%m%d%H%M%S", time.localtime(float(ctimeLong)))


def frames2seconds(frames, fps):
    """
    Converts a number of frames (long) to number of seconds (float w/ 2 decimal precision) 
    with given fps (float) 
    """
    return float('%.2f'%(float(long(frames) / float(fps))))


def seconds2frames(seconds, fps):
    """
    Converts number of seconds (float) to number of frames (long) with fiven fps (float)
    """  
    return long(float(seconds) * float(fps))


class StatusException(Exception):
    """Thrown when various status are invalid""" 
    pass


class CommercialBreak(object):
    """
    Commercial break with a starting and ending position in seconds relative
    to the start of the recording.
    """
    
    def __init__(self, start, end):
        """
        @param start: start of commercial in seconds
        @type start: float
        @param end: end of commercial in seconds
        @type end: float
        @precondition: start < end
        """
        assert end > start, 'Starting time of the commercial break cannot be after the end time'
        self.start = start
        self.end = end
        self.skipped = False
    
    def duration(self):
        """
        @return: Duration of this commercial in seconds
        @rtype: float
        """
        return self.end - self.start
    
    def isDuring(self, position):
        """
        @param position: Current position in seconds
        @type position: float
        @return: True if position in within the commercial break, False otherwise.
        """
        return position >= self.start and position <= self.end

    def __repr__(self):
        return "%s {start = %s, end = %s, duration = %s}" % (
            type(self).__name__,                                                  
            formatSeconds(self.start),
            formatSeconds(self.end),
            formatSeconds(self.duration()))


class Channel(object):
    """
    Channel retrieved from the channel table in the MythTV database.
    """
    
    def __init__(self, data):
        self._data = dict(data)
        # make sure getIconPath() returns a reasonable value when it is not available
        if not 'icon' in self._data or not self._data['icon'] or self._data['icon'] == "none":
            self._data['icon'] = None

    def getChannelId(self):
        """
        @return: unique channel id 
        @rtype: int
        """ 
        return int(self._data['chanid'])
    
    def getChannelNumber(self): 
        """
        @rtype: string
        @note: 7_1 or 7.1 or 7; not necessarily unique across mutiple tuners
        """
        return self._data['channum']
    
    def getSortableChannelNumber(self):
        """
        @return: Channel number approximated as close as possible to a numeric value that can be used for sorting.
                 Returns channelId if all else fails.
        @rtype: int or float
        """
        return Channel.sortableChannelNumber(self.getChannelNumber(), self.getChannelId())
    
    @staticmethod
    def sortableChannelNumber(channelNumber, alternative):
        c = channelNumber
        try:
            n = int(c)
        except:
            try:
                c = c.replace('_', '.')
                c = c.replace('-', '.')
                n = float(c)
            except:
                log.warn('Was not able to convert channel number %s into a number' % channelNumber)
                n = alternative
        return n
        
    def getCallSign(self): 
        """
        @rtype: string
        @note: MTVHD
        """
        return self._data['callsign']
    
    def getChannelName(self): 
        """
        @rtype: string
        @note: Music Television HD
        """
        return self._data['name']
    
    def getIconPath(self): 
        """
        @return: absolute path to file containing channel icon or None
        @rtype: string
        """
        return self._data['icon']
    
    def getTunerId(self):
        """
        @return: unique id of tuner which can play/record this channel
        @rtype: int
        """ 
        return int(self._data['cardid'])

    def __repr__(self):
        return '%s {id=%s, number=%s, callsign=%s, tunerId=%s, name=%s, icon=%s}' % (
                type(self).__name__,
                self.getChannelId(),
                self.getChannelNumber(),
                self.getCallSign(),
                self.getTunerId(),
                self.getChannelName(),
                self.getIconPath())

    @staticmethod
    def mergeChannels(channels):
        """
        The same channel may be available avilable across multiple tuners (unique 
        channelId but identical channelNumber). This method consolidates duplicate 
        channels by channelNumber into a single channel. The channel chosen is from 
        an arbitrary tuner.
        
        @param channels: Channel[]
        @rtype: Channel[]
        """
        bucket = odict()
        for channel in reversed(channels):
            bucket[channel.getChannelNumber()] = channel
        channels = bucket.values()
        return channels
        

class Program(object):
    """
    Base class which represents a TV show in the MythTV system. 
    - Could be an existing recorded program
    - Could be a yet to be recorded scheduled program. 
    """
    def __init__(self, translator):
        self.translator = translator

    def __eq__(self, rhs):
        return \
            isinstance(rhs, Program) and \
            self.getChannelId() == rhs.getChannelId() and \
            self.starttime() == rhs.starttime()

    def getChannelId(self):
        raise Exception, "Abstract base class"
    
    def getChannelNumber(self):
        raise Exception, "Abstract base class"
    
    def getCallSign(self):
        raise Exception, "Abstract base class"
    
    def starttime(self):
        raise Exception, "Abstract base class"

    def endtime(self):
        raise Exception, "Abstract base class"
    
    def title(self):
        raise Exception, "Abstract base class"

    def subtitle(self):
        raise Exception, "Abstract base class"

    def description(self):
        raise Exception, "Abstract base class"

    def category(self):
        raise Exception, "Abstract base class"

    def originalAirDate(self):
        raise Exception, "Abstract base class"

    def getDuration(self):
        """
        @rtype: int
        @return: Duration of the program in minutes
        """
        delta = self.endtimeAsTime() - self.starttimeAsTime() 
        return int(int(delta.seconds) / 60)
        
    def starttimeAsTime(self):
        """
        @rtype: datetime.datetime
        @note: Seconds are chopped off and are always zero
        """
        starttime = self.starttime()
        if str(starttime[4:5]) == "-":
            return datetime.datetime(
                int(starttime[0:4]), 
                int(starttime[5:7]), 
                int(starttime[8:10]), 
                int(starttime[11:13]), 
                int(starttime[14:16]) )
        else:
            return datetime.datetime(
                int(starttime[0:4]), 
                int(starttime[4:6]), 
                int(starttime[6:8]), 
                int(starttime[8:10]), 
                int(starttime[10:12]) )

    def endtimeAsTime(self):
        """
        @rtype: datetime.datetime
        """
        endtime = self.endtime()
        if str(endtime[4:5]) == "-":
            return datetime.datetime(
                int(endtime[0:4]), 
                int(endtime[5:7]), 
                int(endtime[8:10]), 
                int(endtime[11:13]), 
                int(endtime[14:16]) )
        else: 
            return datetime.datetime(
                int(endtime[0:4]), 
                int(endtime[4:6]), 
                int(endtime[6:8]), 
                int(endtime[8:10]), 
                int(endtime[10:12]) )
    
    def formattedAirDateTime(self):
        """
        @deprecated: Legacy
        Returns air times as a formattted string for display purposes
        """
        value = ""
        value += self.starttimeAsTime().strftime("%A %b %d, %I:%M%p")
        value += " - " + self.endtimeAsTime().strftime("%I:%M%p")
        if abs(self.starttimeAsTime() - self.endtimeAsTime()) > datetime.timedelta(days = 1):
            value += " +1"
        return value

    def formattedStartTime(self):
        """
        @return: 3:30 PM, 3:00 PM, 12:00 AM 
        """
        dt = datetime.datetime.fromtimestamp(self.starttimets())
        sh = dt.strftime('%I')
        sm = dt.strftime(':%M %p')
        return '%d%s' % (int(sh), sm)

    def formattedDuration(self):
        """
        @return: Something like  1 hr, 2 hrs, 30 mins, 3 hrs 30 mins 
        """
        totalMins = self.getDuration()
        hours = int(totalMins / 60)
        mins = totalMins % 60
        h = ['', '%d hr%s' % (hours, (hours > 1) * 's')][hours > 0]
        m = ['', '%d m' % mins][mins > 0]
        #m = ['', '%d min%s' % (mins, (mins > 1) * 's')][mins > 0]
        return '%s%s%s' % (h, ((len(h) > 0 and len(m) > 0)) * ' ', m)
        
    def formattedAirTime(self, short=True):
        """
        @return: Something like  3:30 - 4:30:pm, 3 - 4pm, or 3 - 4:40pm 
        """
        st = self.starttimeAsTime()
        sh = '%d' % int(st.strftime('%I'))
        if short:
            sm = [st.strftime(':%M'), ''][st.minute == 0]
        else:
            sm = st.strftime(':%M')
        
        et = self.endtimeAsTime()
        eh = '%d' % int(et.strftime('%I'))
        if short:
            em = [et.strftime(':%M'), ''][et.minute == 0] + et.strftime('%p')
        else:
            em = et.strftime(':%M') + et.strftime('%p')    
        
        return '%s%s - %s%s' % (sh, sm, eh, em)
    
    def formattedAirDate(self):
        """
        @return: Something like 11/07
        """
        dt = datetime.datetime.fromtimestamp(self.starttimets())
        return '%2.2d/%2.2d' % (dt.month, dt.day)
    
    def formattedChannel(self):
        """
        @return: channel number and callsign
        """
        s = ''
        s += self.getChannelNumber()
        if self.getChannelName():
            s += ' ' + self.getChannelName()
        return s

    def fullTitle(self):
        """
        @return: Title and subtitle (if it exists)
        """
        fullTitle = ""
        if self.title():
            fullTitle += self.title()
        if self.subtitle() and not sre.match('^\s+$', self.subtitle()):
            fullTitle += " - " + self.subtitle()
        return fullTitle
        
    def formattedOriginalAirDate(self):
        """
        @return: original air date or the localized string for no airdate
        """
        try:
            if self.originalAirDate():
                value = u'%s' % self.originalAirDate()
            else:
                value = u''
        except:
            value = self.translator.get(m.UNKNOWN)
        return value

    def formattedDescription(self):
        """
        @return: description upto 200 chars long
        """
        if self.description():
            value = self.description()
        else:
            value = self.translator.get(m.NOT_AVAILABLE)
        return value[:200]

    def __repr__(self):
        return "%s {chan = %s, start = %s, end = %s, title = '%s', Sub = %s, desc = '%.10s'}" % (
            type(self).__name__,
            self.getChannelNumber(),                                                                                           
            self.starttimeAsTime(), 
            self.endtimeAsTime(), 
            repr(self.title()), 
            repr(self.subtitle()), 
            repr(self.description()))

    def isShowing(self):
        now = datetime.datetime.now()
        return now >= self.starttimeAsTime() and now <= self.endtimeAsTime()


class TVProgram(Program):
    """
    TV Program retrieved from the PROGRAM database table. Used in the TV Guide.
      
    @see: MythDatabase for data dictionary passed into the constructor.
    """
    
    def __init__(self, data, translator):
        """
        @param data: dict returned from MySQL query
        """
        Program.__init__(self, translator)
        self._data = data    

    def data(self):
        return self._data

    def title(self):
        return self._data['title']

    def subtitle(self):
        return self._data['subtitle']

    def description(self):
        return self._data['description']

    def category(self):
        """
        @rtype: str
        @return: Animals, Animated, Auto, Bus./financial, Children, Comedy, Comedy-drama, Cooking, Crime, Docudrama
                 Documentary, Drama, Entertainment, Environment, Game, Health, Home, House/garden, Music, News 
                 Outdoors, Religious, Romance-comedy, Shopping, Sitcom, Skateboarding, Special, Sports, Talk
        """
        return self._data['category']
    
    def categoryType(self):
        """
        @rtype : str
        @return: movie, tvshow, sports, or series
        """
        return self._data['category_type']
 
    def showType(self):
        """
        @rtype: str
        @return: Miniseries, Paid Programming, Series, Special, or emptystring
        """
        return self._data['showtype']
    
    def isHD(self):
        return int(self._data['hdtv'])
        
    def isMovie(self):
        return self.categoryType() == 'movie'
    
    def getChannelId(self):
        return int(self._data['chanid'])

    def getChannelNumber(self):
        return self._data['channum']
    
    def originalAirDate(self): 
        return self._data['originalairdate']
                
    def getCallSign(self):
        """
        @rtype: string
        @note: MTVHD
        """
        return self._data['callsign'] 

    def getChannelName(self):
        """
        @rtype: string
        @note: Music Television HD        
        """
        return self._data['channame']

    def seriesid(self):
        return self._data['seriesid']
    
    def programid(self):
        return self._data['programid']
    
    def getIconPath(self):
        return self._data['icon']
    
    def starttime(self):
        """
        @rtype: string
        @note: 20081121140000
        """
        return dbTime2MythTime(self._data['starttime'])
    
    def endtime(self):
        """
        @rtype: string
        @note: 20081121140000
        """
        return dbTime2MythTime(self._data['endtime'])        
    

from mythbox.mythtv.conn import inject_conn


class RecordedProgram(Program):
    """
    Recorded program retrieved via Myth's socket interface.
    
    1     STR_TO_LIST(title)
    2     STR_TO_LIST(subtitle)
    3     STR_TO_LIST(description)
    4     STR_TO_LIST(category)
    5     STR_TO_LIST(chanid)
    6     STR_TO_LIST(chanstr)
    7     STR_TO_LIST(chansign)
    8     STR_TO_LIST(channame)
    9     STR_TO_LIST(pathname)
    10    LONGLONG_TO_LIST(filesize)
    11    DATETIME_TO_LIST(startts)
    12    DATETIME_TO_LIST(endts)
    13    INT_TO_LIST(findid)
    14    STR_TO_LIST(hostname)
    15    INT_TO_LIST(sourceid)
    16    INT_TO_LIST(cardid)
    17    INT_TO_LIST(inputid)
    18    INT_TO_LIST(recpriority)
    19    INT_TO_LIST(recstatus)
    20    INT_TO_LIST(recordid)
    21    INT_TO_LIST(rectype)
    22    INT_TO_LIST(dupin)
    23    INT_TO_LIST(dupmethod)
    24    DATETIME_TO_LIST(recstartts)
    25    DATETIME_TO_LIST(recendts)
    26    INT_TO_LIST(programflags)
    27    STR_TO_LIST((recgroup != "") ? recgroup : "Default")
    28    STR_TO_LIST(chanOutputFilters)
    29    STR_TO_LIST(seriesid)
    30    STR_TO_LIST(programid)
    31    DATETIME_TO_LIST(lastmodified)
    32    FLOAT_TO_LIST(stars)
    33    DATE_TO_LIST(originalAirDate)
    34    STR_TO_LIST((playgroup != "") ? playgroup : "Default")
    35    INT_TO_LIST(recpriority2)
    36    INT_TO_LIST(parentid)
    37    STR_TO_LIST((storagegroup != "") ? storagegroup : "Default")
    38    INT_TO_LIST(audioproperties)
    39    INT_TO_LIST(videoproperties)
    40    INT_TO_LIST(subtitleType)
    41    STR_TO_LIST(year)
    """
    _rec_program_dict = {}
    _rec_program_dict_empty = {}
    
    def __init__(self, data, settings, translator, platform, protocol, conn=None):
        '''
        @param data: list of fields from mythbackend. libs/libmythtv/programinfo.cpp in the mythtv source 
                     describes the ordering of these fields.
        @param conn: Non-null for unit tests only otherwise inject via @inject_conn
        '''
        Program.__init__(self, translator)
        self._data = data[:]
        self.settings = settings
        self._platform = platform
        self.protocol = protocol
        self._conn = conn
        
        self._fps = None
        self._commercials = None
        self._localPath = None
        
        for index, item in enumerate(self.protocol.recordFields()):
            self._rec_program_dict[item] = index
        
        for index, item in enumerate(self.protocol.emptyRecordFields()):
            self._rec_program_dict_empty[item] = index

    def getField(self, fieldName):
        return self._data[self.getFieldPos(fieldName)]

    def getFieldPos(self, fieldName):
        if fieldName in self._rec_program_dict:
            return self._rec_program_dict[fieldName]
        elif fieldName in self._rec_program_dict_empty:
            return ""
        else:
            from mythbox.mythtv.conn import ClientException
            raise ClientException("Can't get position of fieldName %s in RecordingInfo as does not exist" % (fieldName)) 

    def isMovie(self):
        """
        @todo: not available via myth protocol record. Fix me!
        """
        return self.getDuration() >= 90
    
    def conn(self):
        return self._conn
    
    def data(self):
        """
        @rtype: list
        """        
        return self._data
    
    def title(self):
        """
        @rtype: string
        """
        return self.getField('title')
    
    def subtitle(self):
        """
        @rtype: string
        """
        return self.getField('subtitle')
    
    def description(self):
        """
        @rtype: string
        """
        return self.getField('description')
    
    def category(self):
        """
        @rtype: string
        @return: Biography, Comedy, Documentary, Entertainment, Game,House/garden, How-to, News, Newsmagazine,
                 Reality, Science, Sitcom, or Talk
        """
        return self.getField('category')
    
    def getChannelId(self):
        """
        @rtype: int
        """
        return int(self.getField('chanid'))
    
    def setChannelId(self, channelId):
        """
        @type channelId: int
        """
        self._data[self.getFieldPos('chanid')] = str(channelId)
        
    def getChannelNumber(self):
        return [self.getField('channum'), ''][self.getField('channum') is None]
        
    def getCallSign(self):
        """
        @rtype: string
        @note: MTVHD
        """
        return self.getField('callsign')
    
    def getChannelName(self):
        """
        @rtype: string
        @note: Music Television HD
        """
        return self.getField('channame')
    
    def getFilename(self):
        """
        @rtype: string
        @note: myth://some/dir/on/backend/000_111122223333.mpg
        """
        # str scrubs unicode, remove the full path as not needed any more
        #return re.sub(r'myth://.+?/','/', str(self.getField('filename'))) 
        return str(self.getField('filename')) # str scrubs unicode

    def starttimets(self):
        """
        @rtype: int
        """
        return int(self.getField('starttime'))
    
    def endtimets(self):
        """
        @rtype: int
        """
        return int(self.getField('endtime'))
    
    def starttime(self):
        """
        @return: '200906211430'  which is 6/21/2009 2:30 pm 
        @note: internal type is an int aka time.time() 
        """
        if self.starttimets() < 0:
            return ctime2MythTime(self.recstarttimets())
        else:
            return ctime2MythTime(self.starttimets())
    
    def endtime(self):
        """
        @return: '200906211430'  which is 6/21/2009 2:30 pm 
        @note: internal type is an int aka time.time() 
        """
        if self.endtimets() < 0:
            return ctime2MythTime(self.recendtime())
        else:
            return ctime2MythTime(self.endtimets())
    
    def duplicate(self):
        return 0
    
    def hostname(self):
        """
        @return: Backend that captured this recording
        """
        return self.getField('hostname')
    
    def sourceid(self):
        return self.getField('sourceid')
    
    def getTunerId(self):
        """
        @return: Unique id of the tuner this program was/will be recorded on.
        @rtype: int
        """
        return int(self.getField('cardid'))
    
    def inputid(self):
        return self.getField('inputid')
    
    def getPriority(self):
        """
        @rtype: int
        @note: -99 <= priority <= 99
        """
        return int(self.getField('recpriority'))
    
    def getRecordingStatus(self):
        """
        @return: RecordingStatus
        @rtype: int
        """
        return int(self.getField('recstatus'))
        
    def getScheduleId(self):
        return int(self.getField('recordid'))
    
    def rectype(self):
        return self.getField('rectype')

    def recstarttimets(self):
        '''
        @return: Scheduled start time of this program according to the tv guide data.
        @note: int ctime
        '''
        return int(self.getField('recstartts'))
    
    def recstarttime(self):
        '''
        @return: Scheduled start time of this program according to the tv guide data.
        @note: str myth format
        '''
        return ctime2MythTime(self.recstarttimets())
    
    def recendtime(self):
        """
        @return: Scheduled end time of this program according to the tv guide data.
        @todo: rename to scheduledEndTime()
        """
        return self.getField('recendts')
    
    def repeat(self):
        return 0
    
    def getProgramFlags(self):
        """
        @rtype: int
        """
        return int(self.getField('programflags'))
    
    def setProgramFlags(self, flags):
        """
        @type flags: int
        @note: set flags by or'ing together FlagMask.FL_*
        """
        self._data[self.getFieldPos('programflags')] = str(flags)
        
    def getRecordingGroup(self):
        """
        @rtype: string
        @note: Default, LiveTV, etc
        """
        return self.getField('recgroup')

    def seriesId(self):
        """
        @rtype: str
        @sample: TODO
        """
        return self.getField('seriesid')
    
    def programId(self):
        """
        @rtype: str
        @sample: TODO
        """
        return self.getField('programid')

    def hasOriginalAirDate(self):
        return int(self._data[38]) == 1
    
    def originalAirDate(self):
        '''
        @rtype: str
        @sample: 2010-07-14
        '''
        return self.getField('airdate')
    
    def getStorageGroup(self):
        """
        @rtype: str
        @note: Usually 'Default'
        """
        return self.getField('storagegroup')
    
    def isAutoExpire(self):
        return self.getProgramFlags() & FlagMask.FL_AUTOEXP == FlagMask.FL_AUTOEXP
    
    def isCommFlagged(self):
        return self.getProgramFlags() & FlagMask.FL_COMMFLAG == FlagMask.FL_COMMFLAG
    
    def isWatched(self):
        return self.getProgramFlags() & FlagMask.FL_WATCHED == FlagMask.FL_WATCHED
        
    def isBookmarked(self):
        return self.getProgramFlags() & FlagMask.FL_BOOKMARK == FlagMask.FL_BOOKMARK

    def isEditing(self):
        return self.getProgramFlags() & FlagMask.FL_EDITING == FlagMask.FL_EDITING

    def isCutListed(self):
        return self.getProgramFlags() & FlagMask.FL_CUTLIST == FlagMask.FL_CUTLIST
    
    def hasCommercials(self):
        return len(self.getCommercials()) > 0

    @inject_conn
    def getCommercials(self):
        """
        @rtype: CommercialBreak[]
        """
        if not self.isCommFlagged():
            self._commercials = []
        if self._commercials is None:
            self._commercials = self.conn().getCommercialBreaks(self)
        return self._commercials

    @inject_conn
    def setBookmark(self, seconds):
        """
        @param seconds: Bookmark in seconds
        @type seconds: float
        """
        self.conn().setBookmark(self, seconds2frames(seconds, self.getFrameRate()))
        self.setProgramFlags(self.getProgramFlags() | FlagMask.FL_BOOKMARK)

    @inject_conn
    def getBookmark(self):
        """
        @return: Bookmark in seconds or 0.0 if a bookmark does not exist.
        @rtype: float
        """
        if not self.isBookmarked():
            return 0.0
        else:
            return frames2seconds(self.conn().getBookmark(self), self.getFrameRate())

    def getFileSize(self):
        """
        @return: filesize in KB
        @rtype: int
        """
        return self.protocol.getFileSize(self)
    
    def getLocalPath(self):
        """
        @return: Absolute path to the location of this recording on the local filesystem.
        @rtype: string
        @note: Value cached after first invocation.
        @raise ClientException: If recording file could not be located. 
        """
        if self._localPath:
            return self._localPath
        else:
            # Start with myth:// style path and cut off everything except for the base file name. 
            # Check each local recording dir for existence of the file until we get our guy.
            fileOnly = self.getBareFilename()
            for localDir in self.settings.getRecordingDirs():
                localPath = os.path.join(localDir, fileOnly)
                if os.path.exists(localPath):
                    log.debug('Local path for %s is %s' % (self.getFilename(), localPath))
                    self._localPath = str(localPath) # scrub unicode
                    return self._localPath
            from mythbox.mythtv.conn import ClientException
            raise ClientException("Recording %s not found in %s. Check Settings > Myth TV > Local Recording Dirs" % (fileOnly, ', '.join(self.settings.getRecordingDirs()))) 

    def getBareFilename(self):
        """
        @rtype: string
        @note: 001_000111222333.mpg
        """
        # Find rightmost path sep and return whats trailing
        return self.getFilename()[self.getFilename().rfind("/")+1:]
        
    def getRemoteThumbnailPath(self):
        """
        @rtype: string
        """
        return self.getFilename() + '.png'

    @timed
    @synchronized
    def getFrameRate(self):
        """
        @rtype: float
        @note: cached 
        @note: most recordings are either 29.97 or 59.97
        @todo: GUIInfoManager.cpp - look at refs to GetFPS()
        """
        if not self._fps:
            
            ffmpeg_cache_dir=os.path.join(self._platform.getScriptDataDir(), 'cache', 'ffmpeg')
            requireDir(ffmpeg_cache_dir) 
                
            ffmpegParser = FFMPEG(
                ffmpeg=self._platform.getFFMpegPath(),
                closeFDs=(type(self._platform) != WindowsPlatform),  # WORKAROUND: close_fds borked on windows
                windows=(type(self._platform) == WindowsPlatform),   # WORKAROUND: let pyxcoder know we're on windows
                tempdir=ffmpeg_cache_dir)
            
            try:
                metadata = ffmpegParser.get_metadata(self.getLocalPath())
            except:
                log.exception('ffmpeg parsing failed')
                metadata = None
                
            log.debug('ffmpeg metadata for %s = %s' % (self.getLocalPath(), metadata))
            if metadata:
                self._fps = float(metadata.frame_rate)
                
                # Hack for FFMPEG returning incorrect framerate (59.94 instead of 29.97) for 1080i HDPVR recordings
                try:
                    hdpvr1080i = {'format': 'mpegts', 'pixel_format': 'yuv420p', 'frame_rate': '59.94', 'video_codec': ': h264', 'dimension': '1920x1080 [PAR 1:1 DAR 16:9]'}
                    if  metadata.format       == hdpvr1080i['format'] and       \
                        metadata.pixel_format == hdpvr1080i['pixel_format'] and \
                        metadata.frame_rate   == hdpvr1080i['frame_rate'] and   \
                        metadata.video_codec  == hdpvr1080i['video_codec'] and  \
                        metadata.dimension    == hdpvr1080i['dimension']:
                        log.debug('HDPVR 1080i recording detected. Defaulting to 29.97 fps')
                        self._fps = 29.97
                except:
                    log.exception('HDPVR 1080i detection code blew up. FPS remains at %s' % self._fps)
            else:
                self._fps = 29.97
                log.error("""Could not determine FPS for file %s so defaulting to %s FPS.
                             Make sure you have the ffmpeg executable in your path. 
                             Commercial skipping may be inaccurate""" % (self._fps, self.getLocalPath()))
                showPopup(self.translator.get(m.ERROR), 'FFMPEG error - comm skips may be incorrect')
        return self._fps

    @timed
    @inject_db
    @inject_conn
    def getFrameRate2(self):
        """
        Get framerate without the recording being accessible via the filesystem.
        @rtype: float
        @note: cached 
        @note: most recordings are either 29.97 or 59.97
        """
        
        #
        # TODO: Integrate for Issue 111
        #
        if not self._fps:
            ffmpegParser = FFMPEG(
                ffmpeg=self._platform.getFFMpegPath(),
                closeFDs=(type(self._platform) != WindowsPlatform),
                windows=(type(self._platform) == WindowsPlatform))  
                # WORKAROUND: close_fds borked on windows

                        
            import tempfile
            fileSink = tempfile.mktemp('.mpg', 'mythbox')
            log.debug('Saving recording fragment to: %s' % fileSink)
            transferred = self.conn().transferFile(self.getFilename(), fileSink, self.db().toBackend(self.hostname()).ipAddress, max=5000000)

            if not transferred:
                showPopup('Error', 'Transfer fragment failed')
                self._fps = 29.97
                return self._fps
            
            try:
                metadata = ffmpegParser.get_metadata(fileSink)
            except:
                log.exception('ffmpeg parsing failed')
                metadata = None
                
            log.debug('ffmpeg metadata for %s = %s' % (fileSink, metadata))
            if metadata:
                self._fps = float(metadata.frame_rate)
            else:
                self._fps = 29.97
                log.error("""Could not determine FPS for file %s so defaulting to %s FPS.
                             Make sure you have the ffmpeg executable in your path. 
                             Commercial skipping may be inaccurate""" % (self._fps, self.getLocalPath()))
                showPopup(self.translator.get(m.ERROR), 'FFMpeg could not determine framerate. Comm skip may be inaccurate')
        return self._fps

    def formattedFileSize(self):
        """
        @return: filesize with MB or GB suffix
        """
        return formatSize(self.getFileSize(), True)
        
    def formattedRecordingStatus(self):
        """
        @return: Recording status converted to a ui friendly string
        """
        return self.translator.get(RecordingStatus.translations[self.getRecordingStatus()])
        
    def __repr__(self):
        return "%s {channel = %s, start = %s, end = %s, file = %s, title = '%s', sub = %s, desc = '%.10s', hostname = %s}" % (
            type(self).__name__,                                                                                                                                       
            self.getChannelNumber(),                                                                                           
            self.starttimeAsTime(), 
            self.endtimeAsTime(), 
            self.getFilename(),
            repr(self.title()), 
            repr(self.subtitle()), 
            repr(self.description()), 
            self.hostname())
        
    def dumpData(self):
        for i,d in enumerate(self.data()):
            log.debug('data[%d] = %s' % (i,d))


class Schedule(object):
    """
    Abstract base class to represent a recording schedule in the mythtv system.

    This class is based on the Myth TV RECORD table.
    """

    def __init__(self, translator):
        self.translator = translator

    def getIconPath(self):
        raise NotImplementedError, "Abstract base class"
    
    def starttime(self):
        raise NotImplementedError, "Abstract base class"
    
    def startdate(self):
        raise NotImplementedError, "Abstract base class"
    
    def endtime(self):
        raise NotImplementedError, "Abstract base class"
    
    def enddate(self):
        raise NotImplementedError, "Abstract base class"
    
    def title(self):
        raise NotImplementedError, "Abstract base class"
    
    def subtitle(self):
        raise NotImplementedError, "Abstract base class"
    
    def description(self):
        raise NotImplementedError, "Abstract base class"
    
    def category(self):
        raise NotImplementedError, "Abstract base class"
    
    def profile(self):
        raise NotImplementedError, "Abstract base class"
    
    def getRecordingGroup(self):
        raise NotImplementedError, "Abstract base class"
    
    def getCheckForDupesUsing(self):
        raise NotImplementedError, "Abstract base class"

    def getCheckForDupesIn(self):
        raise NotImplementedError, "Abstract base class"

    def getEpisodeFilter(self):
        raise NotImplementedError, "Abstract base class"
    
    def getDupin(self):
        raise NotImplementedError, "Abstract base class"
    
    def station(self):
        raise NotImplementedError, "Abstract base class"
    
    def seriesid(self):
        raise NotImplementedError, "Abstract base class"
    
    def programid(self):
        raise NotImplementedError, "Abstract base class"
    
    def search(self):
        raise NotImplementedError, "Abstract base class"
    
    def isAutoUserJob1(self):
        raise NotImplementedError, "Abstract base class"
    
    def isAutoUserJob2(self):
        raise NotImplementedError, "Abstract base class"
    
    def isAutoUserJob3(self):
        raise NotImplementedError, "Abstract base class"
    
    def isAutoUserJob4(self):
        raise NotImplementedError, "Abstract base class"
    
    def findday(self):
        raise NotImplementedError, "Abstract base class"
    
    def findtime(self):
        raise NotImplementedError, "Abstract base class"
    
    def findid(self):
        raise NotImplementedError, "Abstract base class"
    
    def parentid(self):
        raise NotImplementedError, "Abstract base class"
    
    def __repr__(self):
        return "%s {recordid=%s, type=%s, title=%s, subtitle=%s, starttime=%s, endtime=%s startdate=%s, enddate=%s}" % (
            type(self).__name__,
            self.getScheduleId(),
            self.formattedScheduleType(),
            repr(self.title()),
            repr(self.subtitle()),
            self.starttime(),
            self.endtime(),
            self.startdate(),
            self.enddate())

    def startdateAsTime(self):
        """
        @rtype: datetime.datetime
        """
        sd = self.startdate()
        return datetime.datetime(int(sd[0:4]), int(sd[4:6]), int(sd[6:8]), 0, 0)
        
    def formattedChannel(self):
        text = u''
        if self.getChannelNumber():
            text += self.getChannelNumber()
        if self.getCallSign():
            text += u' - ' + self.getCallSign()
        return text

    def formattedDuplicateMethod(self):
        return self.translator.get(CheckForDupesUsing.translations[self.getCheckForDupesUsing()()])
    
    def formattedDuplicateIn(self):
        return self.translator.get(CheckForDupesIn.translations[self.getCheckForDupesIn()])
    
    def formattedStartDate(self):
        value = u''
        value += self.startdateAsTime().strftime("%a, %b %d")
        return value
    
    def formattedTime(self):
        startHours = int(self.starttime()[0:2])
        startAMPM = "am"
        if startHours > 12:
            startAMPM = "pm"
            startHours -= 12
            
        endHours = int(self.endtime()[0:2])
        endAMPM = "am"
        if endHours > 12:
            endAMPM = "pm"
            endHours -= 12
        
        text = "%s:%s%s - %s:%s%s"%(
            startHours,
            self.starttime()[2:4],
            startAMPM,
            endHours,
            self.endtime()[2:4],
            endAMPM)
        
        if self.startdate() != self.enddate():
            text += " +1"
        return text
    
    def formattedScheduleType(self):
        return self.translator.get(ScheduleType.translations[self.getScheduleType()])
    
    def formattedScheduleTypeDescription(self):
        return self.translator.get(ScheduleType.long_translations[self.getScheduleType()])
    
    def fullTitle(self):
        """
        @return: Title and subtitle
        """
        fullTitle = u''
        if self.title():
            fullTitle += self.title()
        if self.subtitle() and not sre.match('^\s+$', self.subtitle()):
            fullTitle += u' - ' + self.subtitle()
        return fullTitle


class RecordingSchedule(Schedule):
    """Recording schedule as persisted in the 'record' table."""
    
    def __init__(self, data, translator):
        """
        @param data: dict of data
        @param translator: Translator
        """
        Schedule.__init__(self, translator)
        self._data = data    
        
        if not 'icon' in self._data or not self._data['icon'] or self._data['icon'] == "none":
            self._data['icon'] = None
    
    def data(self):
        """
        @return: internal storage dict
        @rtype: dict
        """
        return self._data

    def getScheduleId(self):
        """
        @return: schedule id if persisted, None otherwise
        @rtype: int
        @note: 275
        """
        if self._data['recordid']:
            return int(self._data['recordid'])
        else:
            return None

    def setScheduleId(self, scheduleId):
        """
        @param scheduleId: None or int
        """
        self._data['recordid'] = scheduleId

    def getScheduleType(self):
        """
        @rtype: int
        @see: ScheduleType
        """
        return int(self._data['type'])
    
    def setScheduleType(self, scheduleType):
        """
        @type scheduleType: int
        @see: SchduleType
        """
        self._data['type'] = scheduleType
    
    def getChannelId(self):
        """
        @rtype: int
        @note: 1112
        """
        return int(self._data['chanid'])
    
    def setChannelId(self, channelId):
        """
        @type channelId: int
        """
        self._data['chanid'] = str(channelId)
    
    def getChannelNumber(self):
        """
        @rtype: string
        @note: 11_2 or 11.2 or 11
        """
        return self._data['channum']
    
    def getCallSign(self):
        """
        @rtype: string
        @note: MTVHD
        """
        return self._data['callsign']
    
    def getChannelName(self):
        """
        @rtype: string
        @note: Music Television HD
        """ 
        return self._data['channame']
    
    def getIconPath(self):
        """
        @return: path to image of channel icon
        @rtype: string
        @note: /home/mythtv/.mythtv/channels/wttw_chicago.jpg
        @note: Not persisted to db
        """
        return self._data['icon']
    
    def getCategoryType(self):
        """
        @rtype : str
        @return: movie, tvshow, sports, or series
        """
        return self._data['category_type']
    
    def isMovie(self):
        # TODO: Fixme!
        return False
    
    def starttime(self):
        """
        @return: string
        @note: 123000
        @note: rawtype is datetime.timedelta
        """
        #print('starttime = %s' % self._data['starttime'])
        return dbTime2MythTime(self._data['starttime'])
    
    def startdate(self):
        """
        @rtype: string
        @note: 20081124 
        @note: rawtype is datetime.date
        """ 
        return dbTime2MythTime(self._data['startdate'])
    
    def endtime(self):
        """
        @rtype: string
        @note: 113000
        @note: rawtype is datetime.timedelta
        """
        return dbTime2MythTime(self._data['endtime'])
    
    def enddate(self):
        """
        @rtype: string
        @note: 20081101
        @note: rawtype is datetime.date
        """
        return dbTime2MythTime(self._data['enddate'])
    
    def title(self):
        """
        @rtype: string
        @note: Austin City Limits
        """
        return self._data['title']
    
    def subtitle(self):
        """
        @rtype: string
        @note: Thievery Corporation
        """
        return self._data['subtitle']
    
    def description(self):
        """
        @rtype: string
        @note: Thievery Corporation performs songs from Radio Retaliation.
        """
        return self._data['description']
    
    def category(self):
        """
        @return: recording category
        @rtype: string
        @note: Music, Documentary, etc
        """
        return self._data['category']
    
    def profile(self):
        """
        @return: recording profile
        @rtype: string
        @note: Default
        """
        return self._data['profile']
    
    def getPriority(self):
        """
        @rtype: int
        @note: -99 <= priority <= 99
        """
        return self._data['recpriority']
    
    def setPriority(self, priority):
        """
        @type priority: int
        @note: -99 <= priority <= 99
        """
        self._data['recpriority'] = priority
        
    def isAutoExpire(self):
        """
        @return: True if recordings are set to autoexpire, False otherwise
        @note: Rawtype 0 or 1
        """
        return bool(self._data['autoexpire'])
        
    def setAutoExpire(self, b):
        """
        @param b: boolean
        """
        self._data['autoexpire'] = int(b)

    def getMaxEpisodes(self):
        """
        @return: Max number of episodes to keep before auto-expiration kicks in. Zero means keep all episodes. 
        @rtype: int
        """
        return self._data['maxepisodes']

    def setMaxEpisodes(self, num):
        """
        @param num: Max episodes to keep before auto-expiration kicks in. Zero means keep all episodes.
        @type num: int
        """
        self._data['maxepisodes'] = num
        
    def isRecordNewAndExpireOld(self):
        """
        @return: True if old recordings are expired to make space for new recordings, False otherwise
        """
        return bool(self._data['maxnewest'])
    
    def setRecordNewAndExpireOld(self, b):
        """
        @type b: boolean
        """
        self._data['maxnewest'] = int(b)
    
    def getRecordingGroup(self):
        """
        @rtype: string
        @note: Default
        """
        return self._data['recgroup']
    
    def getDupin(self):
        """
        @return: Flag represents both CheckForDupesIn and EpisodeFilter (masked)
        @rtype: int
        """
        return int(self._data['dupin'])
    
    def setDupin(self, dupin):
        """
        @type dupin: int
        """
        self._data['dupin'] = dupin

    def getCheckForDupesIn(self):
        """
        @rtype : int
        @see: CheckForDupesIn 
        """
        return self.getDupin() & (CheckForDupesIn.ALL_RECORDINGS | CheckForDupesIn.PREVIOUS_RECORDINGS | CheckForDupesIn.CURRENT_RECORDINGS)  

    def setCheckForDupesIn(self, checkForDupesIn):
        """
        @type checkForDupesIn: int
        @see checkForDupesIn
        """
        self.setDupin(self.getEpisodeFilter() | checkForDupesIn)
        
    def getEpisodeFilter(self):
        """
        @rtype : int
        @see: EpisodeFilter 
        """
        return self.getDupin() & (EpisodeFilter.NEW_EPISODES_ONLY | EpisodeFilter.EXCLUDE_REPEATS | EpisodeFilter.EXCLUDE_GENERICS)  
        
    def setEpisodeFilter(self, episodeFilter):
        """
        @type episodeFilter: int
        @see: EpisodeFilter
        """
        self.setDupin(self.getCheckForDupesIn() | episodeFilter)

    def getCheckForDupesUsing(self):
        """
        @return: CheckForDupesUsing as int
        """
        return int(self._data['dupmethod'])
    
    def setCheckForDupesUsing(self, checkForDupesUsing):
        """
        @param checkForDupesUsing: CheckForDupesUsing as int
        """
        self._data['dupmethod'] = checkForDupesUsing
        
    def station(self):
        """
        @rtype: string
        @note: WTTW-DT
        """
        return self._data['station']
    
    def seriesid(self):
        """    
        @rtype: string
        @note: EP00000439
        """
        return self._data['seriesid']
    
    def programid(self):
        """
        @rtype: string
        @note: EP000004390402
        """
        return self._data['programid']
    
    # TODO: Whats this?
    def search(self):
        """
        @rtype: int
        """
        return self._data['search']
    
    def isAutoTranscode(self):
        """
        @return: True if recording is set to autotranscode, False otherwise.
        @note: Raw type is 0 or 1
        """ 
        return bool(self._data['autotranscode']) 

    def setAutoTranscode(self, b):
        """
        @type b: boolean
        """
        self._data['autotranscode'] = int(b)
        
    def isAutoCommFlag(self):
        """
        @return: True if recording is set to be automatically commercial flagged, False otherwise.
        @note: Raw type 0 or 1
        """
        return bool(self._data['autocommflag'])
        
    def setAutoCommFlag(self, b):
        """
        @type b: boolean
        """
        self._data['autocommflag'] = int(b)
        
    def isAutoUserJob1(self):
        """
        @return: True if userjob1 set to run automatically, False otherwise.
        """
        # Internal value 0 or 1
        return bool(self._data['autouserjob1'])
    
    def isAutoUserJob2(self):
        """
        @return: True if userjob2 set to run automatically, False otherwise.
        """
        # Internal value 0 or 1
        return bool(self._data['autouserjob2'])
    
    def isAutoUserJob3(self):
        """
        @return: True if userjob3 set to run automatically, False otherwise.
        """
        # Internal value 0 or 1
        return bool(self._data['autouserjob3'])
    
    def isAutoUserJob4(self):
        """
        @return: True if userjob4 set to run automatically, False otherwise.
        """
        # Internal value 0 or 1
        return bool(self._data['autouserjob4'])
    
    def findday(self):
        """
        @rtype: int
        """
        return self._data['findday']
    
    def findtime(self):
        """
        @rtype: datetime.timedelta
        """
        return self._data['findtime']
    
    def findid(self):
        """
        @rtype: int - 
        @note: 733735L
        """
        return self._data['findid']
    
    def isEnabled(self):
        """
        @rtype: boolean
        @note: Raw type 0 or 1
        """
        return not bool(self._data['inactive'])
    
    def setEnabled(self, b):
        """
        @type b: boolean
        """
        self._data['inactive'] = int(not b)
        
    def parentid(self):
        """
        @rtype: int
        """
        return self._data['parentid']

    def getStartOffset(self):
        """
        @return: Number of minutes before start time to start recording
        @rtype: int
        @note: 0 <= minutes <= 60
        """
        return self._data['startoffset']

    def setStartOffset(self, minutes):
        """
        @param minutes: Number of minutes before start time to start recording. 
        @type minutes: int
        @note: 0 <= minutes <= 60
        """
        self._data['startoffset'] = minutes
    
    def getEndOffset(self):
        """
        @return: Number of minutes after end time to stop recording
        @rtype: int
        @note: 0 <= minutes <= 60
        """
        return self._data['endoffset']
    
    def setEndOffset(self, minutes):
        """
        @param minutes: Number of minutes after end time to stop recording. 
        @type minutes: int
        @note: 0 <= minutes <= 60
        """
        self._data['endoffset'] = minutes
    

class ScheduleFromProgram(RecordingSchedule):
    """
    Schedule seeded from TVProgram.
    """
    def __init__(self, program, translator):
        RecordingSchedule.__init__(self, dict(), translator)
        
        self.data()['icon']          = program.getIconPath()
        self.data()['title']         = program.data()['title']
        self.data()['subtitle']      = program.data()['subtitle']
        self.data()['description']   = program.data()['description']
        self.data()['category']      = program.category()
        self.data()['chanid']        = program.getChannelId()
        self.data()['channum']       = program.getChannelNumber()  
        self.data()['callsign']      = program.getCallSign()
        self.data()['seriesid']      = program.seriesid()
        self.data()['programid']     = program.programid()
        self.data()['channame']      = program.getChannelName()
        self.data()['recordid']      = None
        self.data()['type']          = ScheduleType.CHANNEL
        self.data()['startdate']     = program.starttime()[0:8]
        self.data()['starttime']     = program.starttime()[8:14]
        self.data()['enddate']       = program.endtime()[0:8]
        self.data()['endtime']       = program.endtime()[8:14]
        self.data()['profile']       = 'Default'
        self.data()['recpriority']   = 0
        self.data()['autoexpire']    = 0
        self.data()['maxepisodes']   = 0
        self.data()['maxnewest']     = 0
        self.data()['startoffset']   = 0
        self.data()['endoffset']     = 0
        self.data()['recgroup']      = 'Default'
        self.data()['dupmethod']     = CheckForDupesUsing.SUBTITLE
        self.data()['dupin']         = CheckForDupesIn.ALL_RECORDINGS | EpisodeFilter.NONE
        self.data()['station']       = self.getCallSign()
        self.data()['search']        = '0'
        self.data()['autotranscode'] = 0
        self.data()['autocommflag']  = 0 
        self.data()['autouserjob1']  = 0 
        self.data()['autouserjob2']  = 0 
        self.data()['autouserjob3']  = 0 
        self.data()['autouserjob4']  = 0 
        self.data()['findday']       = '0'
        self.data()['findtime']      = '00:00:00'
        self.data()['findid']        = '0'
        self.data()['inactive']      = 0
        self.data()['parentid']      = '0'


class Tuner(object):
    """MythTV Tuner (aka encoder, recorder, card). Maps to the mythtv capturecard 
    database table."""

    def __init__(self, tunerId, hostname, signalTimeout, channelTimeout, tunerType='', conn=None, db=None, translator=None):
        """
        @param tunerId: unique tunerid as int
        @param hostname: physical hostname where tuner is located as string
        @param signalTimeout: timeout in millis as int
        @param channelTimeout: channel timeout in millis as int
        @param tunerType: HDHOMERUN for example as string
        """
        self.tunerId = tunerId
        self.hostname = hostname
        self.signalTimeout = signalTimeout
        self.channelTimeout = channelTimeout
        self.tunerType = tunerType  # HDHOMERUN, HDPVR, etc
        self._conn = conn
        self._db = db
        self.translator = translator
        self._channels = None
        self._backend = None
        
    def conn(self):
        return self._conn

    def db(self):
        return self._db
        
    def __repr__(self):
        return '%s {tunerId = %s, hostname = %s, signalTimeout = %s, channelTimeout = %s, tunerType = %s}' % (
            type(self).__name__,
            self.tunerId,
            self.hostname,
            self.signalTimeout,
            self.channelTimeout,
            self.tunerType)

    @inject_conn
    def isWatchingOrRecording(self, showName):
        """
        @return: True if this tuner is watching (LiveTV) or recording (according to a schedule) 
                 the given showName, False otherwise
        """
        return self.tunerId == self.conn().getTunerShowing(showName)
    
    @inject_conn
    def isRecording(self):
        """
        @rtype: boolean
        """
        return self.conn().isTunerRecording(self)
    
    def waitForRecordingToStart(self, timeout, tick=1):
        """
        Block until backend reports that recording has started.
        
        @param timeout: seconds 
        @param tick: how often to check as a float in seconds
        @raise ClientException: on timeout
        """
        starttime = time.time()
        timedOut = False 
        while not self.isRecording() and not timedOut:
            time.sleep(tick)
            timedOut = (time.time() - starttime) > timeout
            log.debug('Waiting for tuner to start recording...')
        if timedOut:
            from mythbox.mythtv.conn import ClientException
            raise ClientException('Timed out waiting for recording to start on tuner %s%s' % (self.tunerType, self.tunerId))

    def waitForRecordingWritten(self, numKB, timeout, tick=1, callback=None):
        """
        Block until the given number of kilobytes of the recording has been written to the disk.
        
        @precondition: isRecording() == true
        @param numKB: kilobytes as int 
        @param timeout: seconds as int 
        @param tick: interval in seconds as float
        @param updateBuffered: callback with current bytes written 
        @raise ClientException: on timeout
        """
        elapsed = 0
        while True:
            currPos = int(self.getRecordingBytesWritten() / 1024)
            if callback:
                callback(currPos)
            if currPos > numKB:
                break
            if elapsed > timeout:
                from mythbox.mythtv.conn import ClientException
                raise ClientException('Timed out waiting for recording to start on tuner %s' % self.tunerId)   
            time.sleep(tick)
            elapsed += tick
            log.debug('Waited %s seconds for tuner %s %s to write %d/%d KB'%(elapsed, self.tunerType, self.tunerId, currPos, numKB))
            
    @inject_conn
    def getRecordingBytesWritten(self):
        """
        @precondition: isRecording() == true
        @rtype: int
        """
        return self.conn().getTunerFilePosition(self)
        
    @inject_conn
    def getWhatsPlaying(self):
        """
        Return whatever program is currrently being watched as livetv.
        
        @precondition: isRecording() == True
        @rtype: RecordedProgram
        """
        return self.conn().getCurrentRecording(self)
        
    def hasChannel(self, channel):
        """
        Is this tuner capable of tuning the passed in channel? 
        
        @type channel: Channel
        @rtype: boolean
        """
        result = filter(lambda c: c.getChannelNumber() == channel.getChannelNumber(), self.getChannels())
        return len(result) == 1
    
    @inject_conn
    def getChannels(self):
        """
        @return: Channels this tuner can view
        @rtype: Channel[]
        @attention: Cached value returned after first call.
        """
        if self._channels is None:
            self._channels = filter(lambda c: c.getTunerId() == self.tunerId, self.conn().getChannels())
        return self._channels
    
    @inject_conn
    def startLiveTV(self, channelNumber):
        """
        @type channelNumber: string
        @todo: Change type to Channel instead, maybe?
        """
        self.conn().spawnLiveTV(self, channelNumber)
    
    @inject_conn
    def stopLiveTV(self):
        self.conn().stopLiveTV(self)
    
    @inject_conn    
    def getLiveTVStatus(self):
        frames = self.conn().getFramesWritten(self)
        filePos = self.conn().getTunerFilePosition(self)
        frameRate = self.conn().getTunerFrameRate(self)
        #recording = self.conn().getCurrentRecording(self)
        return "Frames written = %s   File pos = %s  FPS = %s" % (frames, filePos, frameRate)        

    @inject_conn
    def getTunerStatus(self):
        """
        @return: TVState enum
        """
        return self.conn().getTunerStatus(self)

    @inject_conn
    def formattedTunerStatus(self):
        t = self.translator.get
        tunerStatus = self.getTunerStatus()
        tvState = self.conn().protocol.tvState()
        
        if tunerStatus in (tvState.WatchingLiveTV, tvState.WatchingRecording, tvState.RecordingOnly):
            recording = self.conn().getCurrentRecording(self)
        
        if tvState.OK == tunerStatus:
            next = self.getNextScheduledRecording() 
            status = t(m.IDLE) + u'. '
            if next:
                status += t(m.NEXT_RECORDING_STARTS_AT) % (next.title(), next.formattedStartTime())
        elif tvState.Error == tunerStatus:
            status = t(m.UNKNOWN)
        elif tvState.WatchingLiveTV == tunerStatus:
            status = t(m.WATCHING_AND_ENDS_AT) %(
                recording.title(), 
                recording.getChannelName(), 
                self.time2string(recording.recendtime()))
        elif tvState.WatchingPreRecorded == tunerStatus:
            status = t(m.WATCHING_PRERECORDED)
        elif tvState.WatchingRecording == tunerStatus:
            status = t(m.WATCHING_AND_RECORDING_UNTIL) % (
                recording.title(), 
                recording.getChannelName(), 
                self.time2string(recording.recendtime()))
        elif tvState.RecordingOnly == tunerStatus: 
            status = t(m.RECORDING_ON_UNTIL) % (
                recording.title(), 
                recording.getChannelName(),
                self.time2string(recording.recendtime()))                    
        elif tvState.ChangingState == tunerStatus:
            status = t(m.BUSY)
        else: 
            status = t(m.UNKNOWN_TUNER_STATUS) % tunerStatus
        return status

    def time2string(self, t):
        '''Workaround for strftime(%-I) -- hour without the leading zero not working on macs'''
        lt = time.localtime(float(t))
        h = '%d' % int(time.strftime('%I', lt)) 
        return '%s%s' % (h, time.strftime(':%M %p', lt))                    
            
    @inject_conn    
    def getNextScheduledRecording(self):
        """
        @return: Next show that is scheduled to be recorded by this tuner
        @rtype: RecordedProgram or None
        """
        upcoming = self.conn().getUpcomingRecordings(filter=Upcoming.SCHEDULED)
        upcoming = filter(lambda x: x.getTunerId() == self.tunerId, upcoming)
        upcoming.sort(key=lambda x: x.starttimeAsTime())
        if len(upcoming) > 0:
            return upcoming[0]
        else:
            return None
 
    @inject_db
    def getBackend(self):
        backend = self.db().toBackend(self.hostname)
        if backend is None:
            raise Exception, 'Could not match tuner to backend: hostname: %s  backends: %s' % (self.hostname, self.db().getBackends())
        else:
            return backend


class Job(object):
    """Represents a scheduled commercial flagging, transcoding, or user defined job."""

    def __init__(self, id, channelId, startTime, insertTime, 
                 jobType, cmds, flags, jobStatus, statusTime,
                 hostname, comment, scheduledRunTime, translator, 
                 conn=None, db=None):
        """
        @type id: int
        @type channelId: int
        @type startTime: datetime.datetime
        @type insertTime: datetime.datetime
        @type jobType: int from JobType
        @type cmds: str
        @type flags: int
        @type jobStatus: int from JobStatus
        @type statusTime: datetime.datetime
        @type hostname: str
        @type comment: str
        @type scheduledRunTime: datetime.datetime
        @type translator: Translator
        @param conn: Only pass in for unit tests   
        @param db: Only pass in for unit tests
        """
        self._db = db
        self._conn = conn
        self.id = id
        self.channelId = channelId
        self.startTime = startTime
        self.insertTime = insertTime
        self.jobType = jobType
        self.cmds = cmds
        self.flags = flags
        self.jobStatus = jobStatus
        self.statusTime = statusTime
        self.hostname = hostname
        self.comment = comment
        self.scheduledRunTime = scheduledRunTime
        self.translator = translator

    def db(self):
        return self._db
    
    def conn(self):
        return self._conn
    
    def isJobFor(self, program):
        """
        @type program: RecordedProgram 
        @rtype: bool
        @return: True if this job is for the given Program, False otherwise
        """
        log.debug("Program start time = %s" % program.starttimeAsTime())
        log.debug("Job     start time = %s" % self.startTime)
        return program.getChannelId() == self.channelId and \
               program.starttimeAsTime() == self.startTime
            
    def formattedJobType(self):
        return self.translator.get(JobType.translations[self.jobType])
    
    def formattedJobStatus(self):
        return self.translator.get(JobStatus.translations[self.jobStatus])
    
    @inject_conn
    def getProgram(self):
        """
        @rtype: RecordedProgram
        """
        return self.conn().getRecording(self.channelId, self.startTime);
        
    def getPercentComplete(self):
        """
        @rtype: int
        """
        if self.jobStatus == JobStatus.FINISHED: return 100
        elif self.jobStatus == JobStatus.QUEUED: return 0
        elif self.jobStatus == JobStatus.RUNNING: 
            # Sample comment: 76% Completed @ 13.9645 fps.
            m = re.match(r'^(.*)\%.*$', self.comment)
            if m:
                return int(m.group(1))
            else:
                raise StatusException('Percent completion not available: %s' % self.comment)
        else: return 0
        
    def getCommFlagRate(self):
        """
        @rtype: float
        """
        # Sample comment: 76% Completed @ 13.9645 fps.
        m = re.match(r'^.*\@ (.*) fps\.$', self.comment)
        if m:
            rate = m.group(1)
            return float(rate)
        else:
            raise StatusException('Comm flag rate not available: %s' % self.comment)
   
    @inject_db             
    def getPositionInQueue(self):
        """
        @return: (position in job queue, size of job queue)
        @rtype: (int, int)
        @raise StatusException: when job status is not queued 
        """
        if self.jobStatus != JobStatus.QUEUED:
            raise StatusException('Job %s with status %s is not in the job queue' % (self.id, self.formattedJobStatus()))
        jobQueue = self.db().getJobs(jobStatus=JobStatus.QUEUED)
        return (jobQueue.index(self) + 1, len(jobQueue))
    
    @inject_db
    def moveToFrontOfQueue(self):
        if self.jobStatus != JobStatus.QUEUED:
            raise StatusException('Job %s with status %s is not queued' % (self.id, self.formattedJobStatus()))
        
        currentPos = self.getPositionInQueue()[0] # pos is 1st in returned tuple
        if currentPos == 1:
            log.warn('Job %d is already at the front of the queue' % self.id)
            
        jobs = self.db().getJobs(jobType=JobType.COMMFLAG, jobStatus=JobStatus.QUEUED)

        self.scheduledRunTime = jobs[0].scheduledRunTime
        self.db().updateJobScheduledRunTime(self)            
        
        for i, job in enumerate(jobs[:currentPos-1]):
            log.debug('moving %d runtime to %d' % (i+1, i))
            job.scheduledRunTime = jobs[i+1].scheduledRunTime
            self.db().updateJobScheduledRunTime(job)
             
    def __eq__(self, rhs):
        """Equality based on job id only"""
        return isinstance(rhs, Job) and self.id == rhs.id

    def __repr__(self):
        return '%s {id = %s, channelId = %s, startTime = %s %s, jobType = %s, jobStatus = %s, scheduledRunTime = %s}' % (
            type(self).__name__,
            self.id,
            self.channelId,
            type(self.startTime),
            self.startTime,
            self.formattedJobType(),
            self.formattedJobStatus(),
            self.scheduledRunTime)


class MythUrl(object):
    
    pattern = re.compile('myth://([A-Za-z0-9\.]*):([0-9]*)(.*)')
     
    def __init__(self, url):
        self.url = url
        self.parsed = False
        self.matches = None
    
    def match(self):
        self.matches = MythUrl.pattern.match(self.url)
        if self.matches:
            log.debug('groups = %s' % len(self.matches.groups()))
        self.parsed = True
            
    def hostname(self):
        if not self.parsed: 
            self.match()
        if self.matches:
            return self.matches.group(1)
    
    def port(self):
        if not self.parsed: 
            self.match()
        if self.matches:
            return self.matches.group(2)
     
    def path(self):
        if not self.parsed: 
            self.match()
        if self.matches:
            return self.matches.group(3)
        
                
class Backend(object):
    
    def __init__(self, hostname, ipAddress, port, master):
        self.ipAddress = ipAddress
        self.hostname = hostname
        self.port = int(port)
        self.master = master
        self.slave = not self.master
        
    def __repr__(self):
        return '%s {ip = %s, hostname = %s, port = %s, master = %s}' % (
            type(self).__name__,
            self.ipAddress,
            self.hostname,
            self.port,
            self.master)
        
    def __eq__(self, rhs):
        return isinstance(rhs, Backend) and \
            self.ipAddress == rhs.ipAddress and \
            self.hostname == rhs.hostname and \
            self.port == rhs.port and \
            self.master == rhs.master

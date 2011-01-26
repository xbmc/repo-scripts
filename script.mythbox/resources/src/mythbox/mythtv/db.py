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
import odict

try:
    # native mysql client libs
    import MySQLdb  
    cursorArgs = [MySQLdb.cursors.DictCursor]
except:
    # pure python mysql client
    import mysql.connector as MySQLdb
    cursorArgs = []
    
import string

from decorator import decorator
from mythbox import pool
from mythbox.pool import PoolableFactory
from mythbox.util import timed, threadlocals, safe_str
        
log = logging.getLogger('mythbox.core')
ilog = logging.getLogger('mythbox.inject')


def mythtime2dbtime(mythtime):
    """Turn 001122 -> 00:11:22"""
    return mythtime[0:2] + ':' + mythtime[2:4] + ':' + mythtime[4:6]


def mythdate2dbdate(mythdate):
    """Turn 20080102 -> 2008-01-02"""
    return mythdate[0:4] + '-' + mythdate[4:6] + '-' + mythdate[6:8]


def quote(someValue):
    if someValue is None:
        return 'None'
    else:
        return "'" + str(someValue) + "'"


class MythDatabaseFactory(PoolableFactory):
    
    def __init__(self, *args, **kwargs):
        self.settings = kwargs['settings']
        self.translator = kwargs['translator']
    
    def create(self):
        db = MythDatabase(self.settings, self.translator)
        return db
    
    def destroy(self, db):
        db.close()
        del db


@decorator
def inject_db(func, *args, **kwargs):
    """Decorator to inject a thread-safe MythDatabase object into the context 
    of a method invocation.

    To use:
          1. Decorate method with @inject_db
          2. Within method, use self.db() to obtain a reference to the database."""
    self = args[0]

    # bypass injection if dependency passed in via constructor
    if hasattr(self, '_db') and self._db:
        return func(*args, **kwargs)

    dbPool = pool.pools['dbPool']
    
    # Create thread local storage if not already allocated
    import thread
    tlsKey = thread.get_ident()
    try:
        threadlocals[tlsKey]
        ilog.debug('threading.local() already allocated')
    except KeyError:
        import threading
        threadlocals[tlsKey] = threading.local()
        ilog.debug('Allocating threading.local() to thread %d'  % tlsKey)
                    
#    try:
#        self.db
#        if self.db == None:
#            raise AttributeError # force allocation
#        ilog.debug('db accessor already bolted on')
#    except AttributeError:
#        ilog.debug('bolting on db accessor')
#        def db_accessor():
#            return threadlocals[thread.get_ident()].db 
#        self.db = db_accessor  

    # Bolt-on getter method so client can access db.
    def db_accessor():
        return threadlocals[thread.get_ident()].db 
    self.db = db_accessor  

    # Only acquire resource once per thread
    try:
        if threadlocals[tlsKey].db == None:
            raise AttributeError # force allocation
        alreadyAcquired = True; 
        ilog.debug('Skipping acquire resource')
    except AttributeError:
        alreadyAcquired = False
        ilog.debug('Going to acquire resource')

    try:
        if not alreadyAcquired:
            # store db in thread local storage
            threadlocals[tlsKey].db = dbPool.checkout()
            ilog.debug('--> injected db %s into %s' % (threadlocals[tlsKey].db, threadlocals[tlsKey]))
        
        # TODO: Recover from broken pipe (for example, after suspend/resume cycle)
        #       File "mysql-connector-python/mysql/connector/connection.py", line 71, in send
        #           raise errors.OperationalError('%s' % e)
        #           OperationalError: (32, 'Broken pipe')
        result = func(*args, **kwargs) 
    finally:
        if not alreadyAcquired:
            ilog.debug('--> removed db %s from %s' % (threadlocals[tlsKey].db, threadlocals[tlsKey]))
            dbPool.checkin(threadlocals[tlsKey].db)
            threadlocals[tlsKey].db = None
    return result


@decorator
def inject_cursor(func, *args, **kwargs):
    """Cursor management via a decorator for simple cases."""
    db = args[0]
    db.cursor = db.conn.cursor(*cursorArgs)
    try:
        result = func(*args, **kwargs)
    finally:
        db.cursor.close()
        db.cursor = None
    return result


class MythDatabase(object):
    
    def __init__(self, *args, **kwargs):
        # Static data cached on demand
        self._channels = None
        self._tuners = None
        self._master = None
        self._slaves = None
        
        if len(args) == 2:
            self.initWithSettings(args[0], args[1])
        else:
            self.initWithDict(args[0])
    
    def initWithDict(self, dbSettings):
        self.settings = dbSettings
        self.translator = None
        
        log.debug("Initializing myth database connection")
        self.conn = MySQLdb.connect(
            host = self.settings['mysql_host'].encode('utf-8'), 
            db = self.settings['mysql_database'].encode('utf-8'),
            user = self.settings['mysql_user'].encode('utf-8'),
            password = self.settings['mysql_password'].encode('utf-8'),
            port = int(self.settings['mysql_port']),
            connection_timeout = 60)
                
    def initWithSettings(self, settings, translator):
        self.settings = settings
        self.translator = translator

        log.debug("Initializing myth database connection")
        self.conn = MySQLdb.connect(
            host = self.settings.get('mysql_host').encode('utf-8'), 
            db = self.settings.get('mysql_database').encode('utf-8'),
            user = self.settings.get('mysql_user').encode('utf-8'),
            password = self.settings.get('mysql_password').encode('utf-8'),
            port = int(self.settings.get('mysql_port')),
            connection_timeout = 60)
    
    @staticmethod
    def toDict(cursor, row):
        """Compensate for myconnpy's lack of a dict based cursor"""
        if isinstance(row, dict):
            return row
        elif isinstance(row, list) or isinstance(row, tuple):
            #log.debug('%s' % type(row))
            rowDict = dict()
            # cursor.description is a list(tuple(columnName, other crap))
            for i, field in enumerate(cursor.description):
                rowDict[field[0]] = row[i] 
            #    log.debug('%s %s' % (type(r),r))
            return rowDict
        else:
            raise Exception, 'Unknown row type: %s' % type(row)
        
    def close(self):
        if self.conn:
            log.debug('Closing myth db connection')
            self.conn.close()
            del self.conn

    def getBackends(self):
        backends = [self.getMasterBackend()]
        backends.extend(self.getSlaveBackends())
        return backends
    
    def toBackend(self, hostnameOrIpAddress):
        for b in self.getBackends():
            if hostnameOrIpAddress in (b.hostname, b.ipAddress,):
                return b
        master = self.getMasterBackend()
        log.warn('Host %s could not be mapped to a backend. Returning master backend %s instead.' % (hostnameOrIpAddress, master.hostname))
        return master
            
    @inject_cursor
    def getMasterBackend(self):
        if not self._master:
            sql = """
                select 
                    a.data as ipaddr,
                    b.data as port,
                    c.hostname as hostname
                from 
                    settings a, 
                    settings b,
                    settings c
                where 
                    a.value = 'MasterServerIP' and
                    b.value = 'MasterServerPort' and
                    c.value = 'BackendServerIP' and
                    c.data  = a.data
                """
                    
            self.cursor.execute(sql)
            rows = map(lambda r: self.toDict(self.cursor, r), self.cursor.fetchall())
            from mythbox.mythtv.domain import Backend
            for row in rows:
                self._master = Backend(row['hostname'], row['ipaddr'], row['port'],  True)
        return self._master
    
    @inject_cursor
    def getSlaveBackends(self):
        if self._slaves is None:
            sql = """
                select  
                    a.data as ipaddr,  
                    a.hostname as hostname,
                    b.data as port
                from 
                    settings a,
                    settings b,
                    settings c
                where 
                    a.value = 'BackendServerIP' and
                    b.value = 'BackendServerPort' and
                    a.hostname = b.hostname and
                    c.data != a.data and
                    c.value = 'MasterServerIP'        
                """
            self.cursor.execute(sql)
            rows = map(lambda r: self.toDict(self.cursor, r), self.cursor.fetchall())
            from mythbox.mythtv.domain import Backend
            self._slaves = []
            for row in rows:
                self._slaves.append(Backend(row['hostname'], row['ipaddr'], row['port'],  False))
        return self._slaves
        
    @timed
    @inject_cursor
    def getChannels(self):
        """
        @return: cached list of viewable channels across all tuners.
        @rtype: Channel[]
        """
        if not self._channels:
            sql = """
                select
                    ch.chanid, 
                    ch.channum, 
                    ch.callsign, 
                    ch.name, 
                    ch.icon, 
                    ci.cardid
                from 
                    channel ch,
                    cardinput ci 
                where 
                    ch.channum is not null
                    and ch.channum != ''
                    and ch.visible = 1
                    and ch.sourceid = ci.sourceid
                order by 
                    ch.chanid
                """
            self.cursor.execute(sql)
            rows = map(lambda r: self.toDict(self.cursor, r), self.cursor.fetchall())
            from mythbox.mythtv.domain import Channel
            self._channels = map(lambda rd: Channel(rd), rows)
        return self._channels

    @inject_cursor            
    def getRecordingGroups(self):
        """
        @return: List of recording group names
        """
        sql = """
            select  
                distinct recgroup 
            from 
                recorded 
            group by 
                recgroup asc
            """
        recordingGroups = []
        self.cursor.execute(sql)
        for row in self.cursor.fetchall():
            row = self.toDict(self.cursor, row)
            recordingGroups.append(row['recgroup'])
        return recordingGroups
          
    @timed            
    @inject_cursor
    def getRecordingTitles(self, recordingGroup):
        """
        @param recordingGroup: 'All Groups' or any valid recording group.
        @type recordingGroup: string
        @rtype: list[0] = ('All Shows', total # of shows)
                list[1..n] = (title, # recordings) 
        @return: for the given string recording group ['All Shows', total # of shows] 
                 is always the first index of the returned list regardless of the 
                 recording group.
        """

        sql = """
          select  
              distinct title, 
              count(title) as cnt 
          from 
              recorded
          """
          
        if string.upper(recordingGroup) != "ALL GROUPS":
            sql += " where recgroup='%s' " % str(recordingGroup)
        
        sql += " group by title asc"

        # TODO: What a mess! This is now NOT to do it... 
        titlegroups = []
        self.cursor.execute(sql)
        titlegroups.append(['All Shows', 0])
        grpcnt = 0
        for row in self.cursor.fetchall():
            row = self.toDict(self.cursor, row)
            thisRow = ['', 0]
            for k in row.keys():
                if k == 'cnt':
                    grpcnt += int(row[k])
                    thisRow[1] = int(row[k])
                else:
                    thisRow[0] = row[k]
            titlegroups.append(thisRow)
        titlegroups[0][1] = grpcnt
        return titlegroups

    @timed
    @inject_cursor
    def getTuners(self):
        """
        @rtype: Tuner[] 
        @return: Cached tuners ordered by cardid
        """
        if not self._tuners:
            sql = """
                select 
                    cardid, 
                    hostname, 
                    signal_timeout, 
                    channel_timeout, 
                    cardtype
                from   
                    capturecard
                order by 
                    cardid
                """
            self._tuners = []
            self.cursor.execute(sql)
            
            from mythbox.mythtv.domain import Tuner

            for row in self.cursor.fetchall():
                row = self.toDict(self.cursor, row)
                self._tuners.append(Tuner(
                    int(row['cardid']),
                    row['hostname'],
                    int(row['signal_timeout']),
                    int(row['channel_timeout']),
                    row['cardtype'],
                    conn=None,
                    db=self,   # TODO: Should be None. self is for unit tests
                    translator=self.translator)) 
        return self._tuners

    @timed
    @inject_cursor
    def getTVGuideData(self, startTime, endTime, channels):
        """
        @type startTime: datetime.datetime 
        @type endTime: datetime.datetime
        @type channels: Channel[] 
        @rtype: dict(Channel, TVProgram[])
        """
        strStartTime = startTime.strftime("%Y%m%d%H%M%S")
        strEndTime = endTime.strftime("%Y%m%d%H%M%S")

        sql = """
            select
                c.chanid,
                c.channum,
                c.callsign,
                c.icon,
                c.name as channame,                
                p.starttime,
                p.endtime,
                p.title,
                p.subtitle,
                p.description,
                p.showtype,
                p.originalairdate,
                p.category,
                p.category_type,
                p.seriesid,
                p.programid,
                p.hdtv
            from 
                channel c, 
                program p
            where c.visible = 1
                and c.chanid in (%s)
                and c.chanid = p.chanid
                and p.starttime != p.endtime
                and 
                (   
                       (p.endtime   >  %s and p.endtime   <= %s) 
                    or (p.starttime >= %s and p.starttime <  %s) 
                    or (p.starttime <  %s and p.endtime   >  %s) 
                    or (p.starttime =  %s and p.endtime   =  %s)
                )
            order by 
                c.chanid, 
                p.starttime
                """ % (','.join(map(lambda c: str(c.getChannelId()), channels)),
                       strStartTime, strEndTime,
                       strStartTime, strEndTime,
                       strStartTime, strEndTime,
                       strStartTime, strEndTime)
        shows = []
        self.cursor.execute(sql)
        from mythbox.mythtv.domain import TVProgram
        for row in self.cursor.fetchall():
            shows.append(TVProgram(self.toDict(self.cursor, row), self.translator))

        channelById = odict.odict()  # dict(int, Channel)
        showsByChannel = {}          # dict(Channel, TVProgram[])
        for c in channels:
            channelById[c.getChannelId()] = c
            showsByChannel[c] = []
                    
        for s in shows:
            showsByChannel[channelById[s.getChannelId()]].append(s)
            
        for shows in showsByChannel.values():
            shows.sort(key=lambda x: x.starttimeAsTime())
            
        return showsByChannel
        
    def getTVGuideDataFlattened(self, startTime, endTime, channels):
        # flatten into list of shows in channel order (incoming arg)
        showsByChannel = self.getTVGuideData(startTime, endTime, channels)
        flattened = []
        for channel in showsByChannel.keys():
            flattened.extend(showsByChannel[channel])
        return flattened
        
    @inject_cursor
    def getMythSetting(self, key, hostname=None):
        """
        @rtype: str
        @return: Setting from the  SETTINGS table or None if not found
        """
        sql = 'select data from settings where value = "%s"  '% key
        if hostname: sql += ' and hostname = "%s"' % hostname
                   
        result = None
        self.cursor.execute(sql)
        for row in self.cursor.fetchall():
            row = self.toDict(self.cursor, row)
            result = row['data']
        return result
        
    @timed
    @inject_cursor
    def getRecordingSchedules(self, chanId='', scheduleId=-1):
        """
        @return: All recording schedules unless a specific channel or schedule id is given.
        @rtype: RecordingSchedule[]
        """
        sql = """
            SELECT
                r.recordid,
                r.type,
                r.chanid,
                r.starttime,
                r.startdate,
                r.endtime,
                r.enddate,
                r.title,
                r.subtitle,
                r.description,
                r.category,
                r.profile,
                r.recpriority,
                r.autoexpire,
                r.maxepisodes,
                r.maxnewest,
                r.startoffset,
                r.endoffset,
                r.recgroup,
                r.dupmethod,
                r.dupin,
                r.station,
                r.seriesid,
                r.programid,
                r.search,
                r.autotranscode,
                r.autocommflag,
                r.autouserjob1,
                r.autouserjob2,
                r.autouserjob3,
                r.autouserjob4,
                r.findday,
                r.findtime,
                r.findid,
                r.inactive,
                r.parentid,
                c.channum,
                c.callsign,
                c.name as channame,
                c.icon
            FROM
                record r
            LEFT JOIN channel c ON r.chanid = c.chanid
            """
            
        if chanId != "":
            sql += "WHERE r.chanid = '%s' "%chanId
            
        if scheduleId != -1:
            if chanId == "":
                sql+="WHERE "
            else:
                sql +="AND "
            sql += "r.recordid = %d "%scheduleId
            
        sql += """
            ORDER BY
                r.recordid
                DESC
            """
        schedules = []
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        from mythbox.mythtv.domain import RecordingSchedule
        for row in rows:
            row = self.toDict(self.cursor, row)
            schedules.append(RecordingSchedule(row, self.translator))
        return schedules

    @inject_cursor
    def updateJobScheduledRunTime(self, job):
        sql = "update jobqueue set schedruntime = %(scheduledRunTime)s where id = %(jobId)s and starttime = %(startTime)s"
        log.debug("sql = %s"%sql)
        args = {
            'scheduledRunTime': job.scheduledRunTime,
            'jobId' : job.id,
            'startTime' : job.startTime
        }
        self.cursor.execute(sql, args)
        log.debug('Row count = %s' % self.cursor.rowcount)

    @inject_cursor
    def getJobs(self, program=None, jobType=None, jobStatus=None):
        """
        Get jobs from the MythTV job queue matching a program, job type, and/or job status.
        
        @type program: RecordedProgram
        @type jobType: int from enums.JobTye
        @type jobStatus: int from enums.JobStatus
        @rtype: Job[]
        """
        
        sql = """
            select
                id, 
                chanid, 
                starttime, 
                inserttime, 
                type, 
                cmds, 
                flags, 
                status,
                statustime,
                hostname, 
                comment,
                schedruntime 
            from   
                jobqueue
            """
        
        where = ''
        if program is not None:
            where += "chanid = %s " % program.getChannelId()
            where += "and "
            where += "starttime = '%s' " % program.starttimeAsTime()
            
        if jobType is not None:
            if program is not None:
                where += " and "
            where += "type = %d " % jobType
        
        if jobStatus is not None:
            if program is not None or jobType is not None:
                where += " and "
            where += "status = %d " % jobStatus
                
        if where != '':
            sql += " where " + where
            
        sql += " order by schedruntime, id"
        
        log.debug('%s' % sql)
        
        jobs = []
        self.cursor.execute(sql)
        from mythbox.mythtv.domain import Job
        for row in self.cursor.fetchall():
            row = self.toDict(self.cursor, row)
            jobs.append(Job(
                id=int(row['id']), 
                channelId=int(row['chanid']), 
                startTime=row['starttime'], 
                insertTime=row['inserttime'], 
                jobType=row['type'], 
                cmds=row['cmds'], 
                flags=row['flags'], 
                jobStatus=row['status'],
                statusTime=row['statustime'],
                hostname=row['hostname'],
                comment=row['comment'],
                scheduledRunTime=row['schedruntime'],
                translator=self.translator))
        return jobs

    def setRecordingAutoexpire(self, program, shouldExpire):
        """
        Set the autoexpire setting for a recorded program.
        
        @param param: RecordedProgram
        @param shouldExpire: boolean
         
        chanid, starttime, shouldExpire = 0
        """
        raise NotImplementedError("TODO setRecordingAutoexpire")
        # TODO: Convert impl to mysql native client
        #sql = """
        #    update recorded set
        #        autoexpire = "%d",
        #        starttime = '%s'
        #    where
        #        chanid = '%s'
        #        and starttime = '%s'
        #"""%(shouldExpire, starttime, chanid, starttime)
        #
        #log.debug("sql = %s"%sql)
        #
        #rc = self.conn.executeSQL(sql)
        #if rc != 1:
        #    raise ClientException, self.conn.getErrorMsg()

    @timed
    @inject_cursor
    def deleteSchedule(self, schedule):
        """
        Delete a recording schedule.
        
        @type schedule: Schedule 
        @return: Number of rows deleted from the 'record' table
        """
        sql = "DELETE FROM record WHERE recordid = %d" % schedule.getScheduleId()
        self.cursor.execute(sql)
        return self.cursor.rowcount
    
    @timed
    def saveSchedule(self, schedule):
        """
        Method to save a schedule to the database. If schedule.getScheduleId() is None 
        then it will be populated with an id and returned from
        database (i.e. a new one will be created).

        Connection.rescheduleNotify() must be called after scheduling changes
        have been made so that the backend will apply the changes.

        @param schedule: Schedule
        @return: saved schedule w/ populated scheduleId (if a new schedule)
        """
        s = schedule
        
        recordid = s.getScheduleId()
        if not recordid:
            recordid = 'NULL'
            
        programid = s.programid()
        if not programid:
            programid = ''

        seriesid = s.seriesid()
        if not seriesid:
            seriesid = ''

        sql = """
            REPLACE INTO record (
                recordid, 
                type,
                chanid, 
                starttime,
                startdate, 
                endtime,
                enddate, 
                title,
                subtitle, 
                description,
                category, 
                profile,
                recpriority, 
                autoexpire,
                maxepisodes, 
                maxnewest,
                startoffset, 
                endoffset,
                recgroup, 
                dupmethod,
                dupin, 
                station,
                seriesid, 
                programid,
                search, 
                autotranscode,
                autocommflag, 
                autouserjob1,
                autouserjob2, 
                autouserjob3,
                autouserjob4, 
                findday,
                findid,
                inactive, 
                parentid) 
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, 
                %%s, %%s, %%s, 
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s)""" % (
                recordid, 
                s.getScheduleType(),
                s.getChannelId(), 
                quote(mythtime2dbtime(s.starttime())),
                quote(mythdate2dbdate(s.startdate())), 
                quote(mythtime2dbtime(s.endtime())),
                quote(mythdate2dbdate(s.enddate())), 
                #quote(s.title()),            #
                #quote(s.subtitle()),         #
                #quote(s.description()),      #
                quote(s.category()),
                quote(s.profile()),
                s.getPriority(), 
                int(s.isAutoExpire()),
                s.getMaxEpisodes(), 
                int(s.isRecordNewAndExpireOld()),
                s.getStartOffset(), 
                s.getEndOffset(),
                quote(s.getRecordingGroup()), 
                s.getCheckForDupesUsing(),
                s.getDupin(), 
                quote(s.station()),
                quote(seriesid),  
                quote(programid),
                int(s.search()), 
                int(s.isAutoTranscode()),
                int(s.isAutoCommFlag()), 
                int(s.isAutoUserJob1()),
                int(s.isAutoUserJob2()), 
                int(s.isAutoUserJob3()),
                int(s.isAutoUserJob4()), 
                int(s.findday()),
                int(s.findid()),
                int(not s.isEnabled()), 
                int(s.parentid()))

        log.debug("sql = %s" % safe_str(sql))
        args = (s.title(), s.subtitle(), s.description())

        c = self.conn.cursor(*cursorArgs)       
        try:
            c.execute(sql, args)
        finally:
            c.close()

        if s.getScheduleId() is None:
            c2 = self.conn.cursor(*cursorArgs)
            try:
                c2.execute("select max(recordid) from record")
                scheduleId = c2.fetchall()[0][0]
                s.setScheduleId(scheduleId)
                log.debug('New scheduleId = %s' % scheduleId)
            finally:
                c.close()
        return s
    
        # INSERT INTO `record` (
        # `recordid`,       241,  
        # `type`,           5, 
        # `chanid`,         1051, 
        # `starttime`,      '19:00:00',  
        # `startdate`,      '2008-10-06',  
        # `endtime`,        '20:00:00',  
        # `enddate`,        '2008-10-06',  
        # `title`,          'Chuck',  
        # `subtitle`,       'Chuck Versus the Seduction', 
        # `description`,    'Chuck must learn the art of seduction so he can retrieve the cipher from a sultry female spy known as the Black Widow (Melinda Clarke); Morgan gives Capt. Awesome advice for a romantic night with Ellie.',  
        # `category`,       'Comedy',   
        # `profile`,        'Default',  
        # `recpriority`,    0,  
        # `autoexpire`,     1,  
        # `maxepisodes`,    0,  
        # `maxnewest`,      1,  
        # `startoffset`,    0,  
        # `endoffset`,      0,  
        # `recgroup`,       'Default',  
        # `dupmethod`,      6,  
        # `dupin`,          15,  
        # `station`,        'NBC5-DT',  
        # `seriesid`,       'EP00930779',  
        # `programid`,      'EP009307790016',  
        # `search`,         0,  
        # `autotranscode`,  0,  
        # `autocommflag`,   1,  
        # `autouserjob1`,   0,  
        # `autouserjob2`,   0,  
        # `autouserjob3`,   0,  
        # `autouserjob4`,   0,  
        # `findday`,        2,  
        # `findtime`,       '19:00:00',  
        # `findid`,         733687,  
        # `inactive`,       0,  
        # `parentid`,       0,  
        #
        # New ======
        # `transcoder`,     0,  
        # `tsdefault`,      1,  
        # `playgroup`,      'Default',  
        # `prefinput`,      0,  
        # `next_record`,    '0000-00-00 00:00:00',  
        # `last_record`,    '2008-12-15 19:00:03',  
        # `last_delete`,    '2008-10-06 23:29:08',  
        # `storagegroup`,   'Default', 
        # `avg_delay`)      76)

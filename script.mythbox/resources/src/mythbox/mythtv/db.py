#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2011 analogue@yahoo.com
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
import mysql.connector as MySQLdb # pure python mysql client
import odict
import string

from mythbox.mythtv.enums import RecordingStatus, JobType
from decorator import decorator
from mythbox import pool
from mythbox.pool import PoolableFactory
from mythbox.util import timed, threadlocals, safe_str
from mysql.connector import errors
        
log = logging.getLogger('mythbox.core')
ilog = logging.getLogger('mythbox.inject')

cursorArgs = []

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
        self.domainCache = kwargs['domainCache']
    
    def create(self):
        from mythbox import config
        if config.offline:
            db = OfflineDatabase()
        else:
            db = MythDatabase(self.settings, self.translator, self.domainCache)
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
    result = None
    
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
            threadlocals[tlsKey].discarded = False
            ilog.debug('--> injected db %s into %s' % (threadlocals[tlsKey].db, threadlocals[tlsKey]))
        
        # TODO: Recover from broken pipe (for example, after suspend/resume cycle)
        #       File "mysql-connector-python/mysql/connector/connection.py", line 71, in send
        #           raise errors.OperationalError('%s' % e)
        #           OperationalError: (32, 'Broken pipe')
        #    InterfaceError: 2013: Lost connection to MySQL server during query         

        try:
            result = func(*args, **kwargs)
        except errors.InterfaceError, ie:
            log.error(str(ie))
            log.error('\n\n\t\tDiscarding stale db conn...\n\n')
            dbPool.discard(threadlocals[tlsKey].db)
            threadlocals[tlsKey].discarded = True
            
    finally:
        if not alreadyAcquired and not threadlocals[tlsKey].discarded:
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
        self._master = None
        self._slaves = None
        
        if len(args) == 3:
            self.initWithSettings(args[0], args[1], args[2])
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
                
    def initWithSettings(self, settings, translator, domainCache):
        self.settings = settings
        self.translator = translator
        self.domainCache = domainCache

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
            if hostnameOrIpAddress.lower() in (b.hostname.lower(), b.ipAddress.lower(),):
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
        channels = map(lambda rd: Channel(rd), rows)
        return channels

    @inject_cursor
    def getRecordingProfileNames(self):
        sql = """
            select 
                distinct(rp.name) as recording_profile_name
            from 
                capturecard cc,
                cardinput ci,
                profilegroups pg,
                recordingprofiles rp
            where
                cc.cardid = ci.cardid
                and cc.cardtype = pg.cardtype
                and rp.profilegroup = pg.id
                and rp.name != 'Live TV'
            order by 
                rp.name asc;
        """
        self.cursor.execute(sql)
        return [self.toDict(self.cursor,row)['recording_profile_name'] for row in self.cursor.fetchall()]
        
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

    @inject_cursor
    def getFramerate(self, recording):
        '''Returns fps as a float or defaults to 29.97 if problems occur'''

        sql = '''        
            select 
                rs.mark/time_to_sec(timediff(r.progend,r.progstart)) as fps_actual,
                rs.mark/time_to_sec(timediff(r.endtime,r.starttime)) as fps_duration
            from 
                recorded r, 
                recordedseek rs
            where
                r.chanid = %d 
            and r.starttime={ts '%s'}
            and r.chanid = rs.chanid
            and r.starttime = rs.starttime
            order by rs.mark desc
            limit 1 
            ''' % (recording.getChannelId(), recording.starttimeAsTime())       
        fps = float(29.97)
        self.cursor.execute(sql)
        for row in self.cursor.fetchall():
            row = self.toDict(self.cursor, row)
            try:
                log.debug('FPS actual   %s' % row['fps_actual'])
                log.debug('FPS duration %s' % row['fps_duration'])
                
                holder = float(row['fps_duration'])
                if holder is not None and holder > 0:
                    fps = holder
                else:
                    fps = float(row['fps_actual'])
            except TypeError, te:
                log.warn('Decimal to float conversion failed for "%s" with error %s. Returning default of 29.97' % (fps, safe_str(te)))
        
        # since we're deriving an approximation from the recordedseek table, just fudge to the
        # most obvious correct values
        if fps >= 28.0 and fps <= 32.0:
            fps = float(29.97)
        elif fps >= 57.0 and fps <= 62.0:
            fps = float(59.94)
        elif fps >= 22.0 and fps <= 26.0:
            fps = float(24.0)
        return fps
    
    @timed
    @inject_cursor
    def getTuners(self):
        """
        @rtype: Tuner[] 
        @return: Cached tuners ordered by cardid
        """
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
        tuners = []
        self.cursor.execute(sql)
        
        from mythbox.mythtv.domain import Tuner

        for row in self.cursor.fetchall():
            row = self.toDict(self.cursor, row)
            tuners.append(Tuner(
                int(row['cardid']),
                row['hostname'],
                int(row['signal_timeout']),
                int(row['channel_timeout']),
                row['cardtype'],
                domainCache=self.domainCache,
                conn=None,
                db=self,   # TODO: Should be None. self is for unit tests
                translator=self.translator)) 
        return tuners

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
        sql = 'select data from settings where value = "%s" '% key
        if hostname: 
            sql += ' and hostname = "%s"' % hostname
                   
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
                c.icon,
                (select count(*) from oldrecorded where oldrecorded.title=r.title and oldrecorded.recstatus = %d) as numRecorded
            FROM
                record r
            LEFT JOIN channel c ON r.chanid = c.chanid
            """ % RecordingStatus.RECORDED
    
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

    def addJob(self, job):
        '''Add a new job to the job queue'''        
        sql = """INSERT INTO jobqueue (
                    chanid,
                    starttime,
                    type,
                    inserttime,
                    hostname, 
                    status,
                    comment, 
                    schedruntime)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        
        log.debug("sql = %s" % safe_str(sql))
        args = (job.channelId, job.startTime, job.jobType, job.insertTime, job.hostname, job.jobStatus, job.comment, datetime.datetime.now(),)

        if log.isEnabledFor(logging.DEBUG):
            for i,arg in enumerate(args):
                log.debug('Positional arg %d: %s' % (i,safe_str(arg)))

        c = self.conn.cursor(*cursorArgs)       
        try:
            c.execute(sql, args)
        finally:
            c.close()

        if job.id is None:
            c2 = self.conn.cursor(*cursorArgs)
            try:
                c2.execute("select max(id) from jobqueue")
                job.id = c2.fetchall()[0][0]
                log.debug('New job id = %s' % job.id)
            finally:
                c2.close()
 
    def getUserJobs(self):
        '''Returns max of 4 user jobs defined in the SETTING table'''
        from mythbox.mythtv.domain import UserJob
        userJobs = []
        types = [JobType.USERJOB1, JobType.USERJOB2, JobType.USERJOB3, JobType.USERJOB4]
        keys = [('UserJob%d' % i, 'UserJobDesc%d' % i, types[i-1]) for i in xrange(1,5)]
        for jobCommand, jobDesc, jobType in keys:            
            userJobs.append(UserJob(jobType, self.getMythSetting(jobDesc), self.getMythSetting(jobCommand)))  
        return userJobs
    
    @inject_cursor
    def getJobs(self, program=None, jobType=None, jobStatus=None):
        """
        Get jobs from the MythTV job queue matching a program, job type, and/or job status in order of scheduled run time.
        
        @type program: RecordedProgram
        @type jobType: int from enums.JobType
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
                translator=self.translator,
                domainCache=self.domainCache))
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
                station,
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
                %%s, %%s, %%s, %%s, %%s, %%s, 
                %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s)""" % (
                recordid, 
                s.getScheduleType(),
                s.getChannelId(), 
                quote(mythtime2dbtime(s.starttime())),
                quote(mythdate2dbdate(s.startdate())), 
                quote(mythtime2dbtime(s.endtime())),
                quote(mythdate2dbdate(s.enddate())), 
                #quote(s.title()),            # passed as args to execute(..) for encoding
                #quote(s.subtitle()),         #
                #quote(s.description()),      #
                #quote(s.category()),         #
                #quote(s.station()),          #
                #quote(s.getRecordingProfile()),
                s.getPriority(), 
                int(s.isAutoExpire()),
                s.getMaxEpisodes(), 
                int(s.isRecordNewAndExpireOld()),
                s.getStartOffset(), 
                s.getEndOffset(),
                quote(s.getRecordingGroup()), 
                s.getCheckForDupesUsing(),
                s.getDupin(), 
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
        args = (s.title(), s.subtitle(), s.description(), s.category(), s.station(), s.getRecordingProfile())

        if log.isEnabledFor(logging.DEBUG):
            for i,arg in enumerate(args):
                log.debug('Positional arg %d: %s' % (i,safe_str(arg)))

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
                c2.close()
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


class OfflineDatabase(MythDatabase):
    """For offline testing"""
    
    def __init__(self, *args, **kwargs):
        pass
 
    def getMasterBackend(self):
        from mythbox.mythtv.domain import Backend
        return Backend('localhost', '127.0.0.1', 6543, True)
    
    def getSlaveBackends(self):
        return []
    
    def initWithSettings(self, settings, translator, domainCache):
        pass
    
    def close(self):
        pass

    def toBackend(self, hostnameOrIpAddress):
        return self.getMasterBackend()
    
    def getTuners(self):
        return [] # Tuner[]

    def getJobs(self, program=None, jobType=None, jobStatus=None):
        jobs = []
        return jobs

    def getChannels(self):
        return []
    
    def getTVGuideDataFlattened(self, startTime, endTime, channels):
        return []
    
    def getRecordingSchedules(self, chanId='', scheduleId=-1):
        #from mythbox.mythtv.domain import RecordingSchedule
        return []
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

from mythbox.bus import Event
from mythbox.mythtv.conn import inject_conn
from mythbox.mythtv.db import inject_db
from mythbox.util import synchronized

class DomainCache(object):
    '''Lazy/Aggressive cache for domain based queries'''
    
    def __init__(self, *args, **kwargs):
        self.bus = kwargs['bus']
        self.bus.register(self, firstDibs=True)
        self.cache = {}
        
    def clear(self):
        self.cache = {}
        
    def onEvent(self, event):
        '''invalidate caches based on event'''
        id = event['id']
        
        if id == Event.SCHEDULE_CHANGED:
            self.getRecordingSchedules(force=True, lazy=True)
            self.getUpcomingRecordings(force=True, lazy=True)
            
        elif id == Event.SCHEDULER_RAN:
            self.getUpcomingRecordings(force=True, lazy=True)
            
        elif event['id'] == Event.RECORDING_DELETED:
            self.getAllRecordings(force=True, lazy=True)
            
    # TODO: self.bus.deregister(self)
    
    @synchronized
    @inject_db    
    def getRecordingSchedules(self, force=False, lazy=False):
        '''Experiment: combine invalidation into getter instead of a separate method so we 
        don't have the ugliness of managing a separate synchronization lock/method'''
        return self.process('recordingSchedules', self.db().getRecordingSchedules, force, lazy)

    @synchronized
    @inject_conn
    def getAllRecordings(self, force=False, lazy=False):
        return self.process('allRecordings', self.conn().getAllRecordings, force, lazy)

    @synchronized
    @inject_conn
    def getUpcomingRecordings(self, force=False, lazy=False):
        return self.process('upcomingRecordings', self.conn().getUpcomingRecordings, force, lazy)
    
    @synchronized
    @inject_db
    def getChannels(self, force=False, lazy=False):
        return self.process('channels', self.db().getChannels, force, lazy)
     
    @synchronized
    @inject_db
    def getUserJobs(self, force=False, lazy=False):
        return self.process('userJobs', self.db().getUserJobs, force, lazy)
    
    @synchronized
    @inject_conn
    def getTuners(self, force=False, lazy=False):
        return self.process('tuners', self.conn().getTuners, force, lazy)
    
    def process(self, key, func, force, lazy):
        if force:
            if key in self.cache:
                del self.cache[key]
                if lazy:
                    return None
                
        if not key in self.cache:
            self.cache[key] =  func()
        
        return self.cache[key][:]


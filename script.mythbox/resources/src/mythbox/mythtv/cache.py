from mythbox.mythtv.db import inject_db
from mythbox.util import synchronized
from mythbox.bus import Event

class DomainCache(object):
    '''Lazy/Aggressive cache for domain based queries'''
    
    def __init__(self, *args, **kwargs):
        self.bus = kwargs['bus']
        self.bus.register(self)
        self.cache = {}
        
    def clear(self):
        self.cache = {}
        
    def onEvent(self, event):
        if event['id'] == Event.SCHEDULE_CHANGED:
            self.getRecordingSchedules(invalidate=True, async=True)
    
    # TODO: self.bus.deregister(self)
    
    @synchronized
    @inject_db    
    def getRecordingSchedules(self, invalidate=False, async=True):
        '''Experiment: combine invalidation into getter instead of a separate method so we 
        don't have the ugliness of managing a separate synchronization lock/method'''

        if invalidate:
            if 'recordingSchedules' in self.cache:
                del self.cache['recordingSchedules']
                if async:
                    return None
                
        if not 'recordingSchedules' in self.cache:
            self.cache['recordingSchedules'] =  self.db().getRecordingSchedules()
        
        return self.cache['recordingSchedules'][:]

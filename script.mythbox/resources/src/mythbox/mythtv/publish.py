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

import logging
import xbmc

from mythbox.bus import Event
from mythbox.util import run_async
from mythbox.mythtv.conn import EventConnection, inject_conn

log = logging.getLogger('mythbox.core')

class MythEventPublisher(object):

    #  Before recording starts: 
    #
    #      [u'BACKEND_MESSAGE', u'SYSTEM_EVENT REC_PENDING SECS 120 CARDID 7 CHANID 4282 STARTTIME 2011-05-27T20:00:00 SENDER athena', u'empty']
    #
    #  Delete recording
    #
    #     [u'BACKEND_MESSAGE', u'RECORDING_LIST_CHANGE DELETE 1071 2011-05-27T15:30:00', u'empty']
    #
    #  Create/edit/delete schedule
    #
    #     [u'BACKEND_MESSAGE', u'SCHEDULE_CHANGE', u'empty']        
    #
    
    def __init__(self, *args, **kwargs):
        [setattr(self, k, v) for k,v in kwargs.items() if k in ['bus', 'settings','translator','platform']]
        self.closed = False

    @inject_conn
    def supportsSystemEvents(self):
        return self.conn().platform.supportsSystemEvents()
    
    @run_async
    def startup(self):
        log.debug('Starting MythEventPublisher..')
        self.eventConn = EventConnection(settings=self.settings, translator=self.translator, platform=self.platform, bus=self.bus)
        while not self.closed and not xbmc.abortRequested:
            try:
                tokens = self.eventConn.readEvent()
                
                if len(tokens) >= 2 and not tokens[1].startswith(u'UPDATE_FILE_SIZE'): 
                    log.debug('EVENT: %s' % tokens)
                
                if len(tokens)>=3 and tokens[0] == 'BACKEND_MESSAGE':

                    if tokens[1].startswith('SYSTEM_EVENT') and 'SCHEDULER_RAN' in tokens[1]:
                        self.bus.publish({'id':Event.SCHEDULER_RAN})
                            
                    elif tokens[1].startswith('COMMFLAG_START'):
                        self.bus.publish({'id':Event.COMMFLAG_START})
                            
                    elif tokens[1].startswith('SCHEDULE_CHANGE'):
                        self.bus.publish({'id':Event.SCHEDULE_CHANGED}) 

            except Exception, e:
                log.exception(e)
        log.debug('Exiting MythEventPublisher')
    
    def shutdown(self):
        self.closed = True
        try:
            self.eventConn.close()
        except:
            log.exception('On shutting down MythEventPublisher')
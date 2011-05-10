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
                #log.debug(tokens)
                if len(tokens)>=3 and tokens[0] == 'BACKEND_MESSAGE':
                    if tokens[1].startswith('SYSTEM_EVENT'):
                        if 'SCHEDULER_RAN' in tokens[1]:
                            log.debug('Publishing scheduler ran...')
                            self.bus.publish({'id':Event.SCHEDULER_RAN})
            except Exception, e:
                log.exception(e)
        log.debug('Exiting MythEventPublisher')
    
    def shutdown(self):
        self.closed = True
        try:
            self.eventConn.close()
        except:
            log.exception('On shutting down MythEventPublisher')
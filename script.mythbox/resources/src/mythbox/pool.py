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
import threading
import time

from mythbox.util import sync_instance, run_async

log = logging.getLogger('mythbox.inject')

# Globally available resources pools
#    key   = name of pool
#    value = Pool instance
pools = {}
          

class PoolableFactory(object):
    """Pooled resources needs a factory to create/destroy concrete instances."""
    
    def create(self):
        raise Exception, "Abstract method"
    
    def destroy(self, resource):
        raise Exception, "Abstract method"


class Pool(object):
    """Simple no frills unbounded resource pool"""
    
    def __init__(self, factory):
        """
        @type factory: PoolableFactory
        """
        self.factory = factory
        self.isShutdown = False
        self.inn = []
        self.out = []

    @sync_instance
    def checkout(self):
        if self.isShutdown: raise Exception, 'Pool shutdown'
        if len(self.inn) == 0:
            log.debug('Creating resource %d' % (len(self.out)+1))
            resource = self.factory.create()
        else:
            resource = self.inn.pop()
        self.out.append(resource)
        return resource

    @sync_instance
    def checkin(self, resource):
        if self.isShutdown: raise Exception, 'Pool shutdown'
        self.inn.append(resource)
        self.out.remove(resource)

    @sync_instance
    def discard(self, resource):
        self.out.remove(resource)
        try:
            self.factory.destroy(resource)
        except:
            log.exception('while discarding')
            
    @sync_instance
    def shutdown(self):
        for resource in self.inn:
            try:
                self.factory.destroy(resource)
            except:
                log.exception('Destroy pooled resource')
        if len(self.out) > 0:
            log.warn('%d pooled resources still out on shutdown' % len(self.out))
        self.isShutdown = True
    
    @sync_instance
    def size(self):
        return len(self.inn) + len(self.out)
    
    @sync_instance
    def available(self):
        return len(self.inn)
    
    @sync_instance
    def shrink(self):
        if self.isShutdown: raise Exception, 'Pool shutdown'
        if len(self.inn) > 0:
            for r in self.inn[:]:
                try:
                    self.inn.remove(r)
                    self.factory.destroy(r)
                except:
                    log.exception('while shrinking')

    @sync_instance
    def grow(self, size):
        if self.isShutdown: raise Exception, 'Pool shutdown'
        if size > self.size():
            delta = size - self.size()
            for i in range(delta):
                r = self.factory.create()
                self.inn.append(r)

                
class EvictingPool(Pool):
    """Evicts resources asynchronously based on a configurable maximum age.
    Surprisingly, I came up empty finding an existing FOSS implementation 
    where evictions were async."""
       
    def __init__(self, factory, maxAgeSecs, reapEverySecs):
        Pool.__init__(self, factory)
        self.maxAgeSecs = maxAgeSecs
        self.reapEverySecs = reapEverySecs
        self.dobs = {}
        self.stopReaping = False
        self.numEvictions = 0
        self.startLock = threading.Event()
        self.startLock.clear()
        self.evictorThread = self.evictor()  # TODO: Don't start evictor until something is actually in the pool
        self.startLock.wait()
        log.debug('Evictor thread = %s' % self.evictorThread)
        
    @run_async
    def evictor(self):
        log.debug('Evictor started')
        self.startLock.set()
        cnt = 1
        while not self.isShutdown and not self.stopReaping:
            time.sleep(1)
            if cnt % self.reapEverySecs == 0:
                self.reap(cnt)
            cnt+=1
        log.debug('Evictor exiting')

    @sync_instance
    def reap(self, cnt):
        now = datetime.datetime.now()
        for r in self.inn:
            dob = self.dobs[r]
            evictAfter = dob + datetime.timedelta(seconds=self.maxAgeSecs)
            
            #log.debug('Reaper check:')
            #log.debug('  dob        = %s' % dob)
            #log.debug('  evictAfter = %s' % evictAfter)
            #log.debug('  now        = %s' % now)
            
            if now > evictAfter:
                try:
                    log.debug('Evicting resource %s in sweep %d' % (r, cnt/self.reapEverySecs))
                    self.inn.remove(r)
                    self.factory.destroy(r)
                    del self.dobs[r]
                    self.numEvictions += 1
                except:
                    log.exception('while reaping')
            
    @sync_instance
    def checkin(self, resource):
        super(EvictingPool, self).checkin(resource)
        self.dobs[resource] = datetime.datetime.now()

    @sync_instance
    def discard(self, resource):
        super(EvictingPool, self).discard(resource)
        if resource in self.dobs:
            del self.dobs[resource]

    @sync_instance
    def grow(self, size):
        super(EvictingPool, self).grow(size)
        now = datetime.datetime.now()
        for r in self.inn:
            if not r in self.dobs:
                self.dobs[r] = now
                
    # SYNC ALERT:
    #   It is very important that call is not synchronized since we join() on the reaper thread
    #   which may itself be in synchronized call to reap()
    def shutdown(self):
        self.isShutdown = True
        if self.evictorThread.isAlive():
            log.debug('joining evictor')
            self.evictorThread.join(self.reapEverySecs * 2) # 2x == fudge factor
        super(EvictingPool, self).shutdown()
        log.debug('Total num evictions = %d' % self.numEvictions)

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
import os
import shutil
import urllib
import threading

from hashlib import md5
from mythbox.bus import Event
from mythbox.util import sync_instance, safe_str, SynchronizedDict, requireDir,\
    run_async, catchall

log = logging.getLogger('mythbox.cache')


class FileResolver(object):
    
    def store(self, fileUrl, dest):
        raise Exception, 'AbstractMethod'
    
    def hash(self, fileUrl):
        return md5(safe_str(fileUrl)).hexdigest()
    

class FileSystemResolver(FileResolver):
    """Resolves files accessible via the local filesystem"""
    
    def store(self, fileUrl, dest):
        shutil.copyfile(fileUrl, dest)


class HttpResolver(FileResolver):
    """Resolves files accessible via a http:// url"""
    
    def store(self, fileUrl, dest):
        filename, headers = urllib.urlretrieve(fileUrl, dest)
        

class FileCache(object):
    """File cache which uses a FileResolver to populate the cache on-demand"""
    
    def __init__(self, rootDir, resolver):
        """
        @type rootDir: str
        @param rootDir: root directory of the cache. will be created if it does not exist.
        @type resolver: FileResolver
        @param resolver: Pluggable component to retrieve (resolve) files.
        """
        self.rootDir = rootDir
        self.resolver = resolver
        self.locksByResource = SynchronizedDict()
        
        requireDir(rootDir)
        if not os.path.isdir(rootDir):
            raise Exception, 'File cache root dir already exists as a file: %s' % rootDir

    def _mapToPath(self, fileUrl):
        return os.path.join(self.rootDir, self.resolver.hash(fileUrl))
        
    def contains(self, fileUrl):
        return os.path.exists(self._mapToPath(fileUrl))
     
    def get(self, fileUrl):
        """
        @return: local path if file resolution was successful, None otherwise
        """
        filepath = self._mapToPath(fileUrl) 
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            log.debug('Cache MISS %s' % safe_str(fileUrl))
            
            self.lockResource(fileUrl)
            try:
                if not self.contains(fileUrl): 
                    self.resolver.store(fileUrl, filepath)
            finally:
                self.unlockResource(fileUrl)
            
            # Don't cache zero byte files
            if not os.path.exists(filepath):
                log.warn('File could not be resolved: %s and not at path: %s' % (safe_str(fileUrl), filepath) )
                return None
            
            if os.path.getsize(filepath) == 0:
                log.warn('file %s resulted in zero byte file...removing...' % safe_str(fileUrl))
                self.remove(fileUrl)
                return None
        else:
            if log.isEnabledFor(logging.DEBUG):
                if hasattr(fileUrl, 'title'):
                    s = fileUrl.title()
                elif hasattr(fileUrl, 'getChannelName'):
                    s = fileUrl.getChannelName()
                else:
                    s = fileUrl
                #log.debug('Cache HIT %s ' % safe_str(s))
        return filepath

    @sync_instance
    def createAndClaimLock(self, resource):
        if not self.locksByResource.has_key(resource):
            #log.debug('Thread created lock %s' % threading.currentThread().getName())
            lock = threading.RLock()
            lock.acquire()
            self.locksByResource.put(resource, lock)
        else:
            #log.debug('Thread nearly createdlock %s' % threading.currentThread().getName())
            lock = self.locksByResource.get(resource)
            lock.acquire()
            
    
    def lockResource(self, resource):
        if self.locksByResource.has_key(resource):
            #log.debug('Thread waiting for lock %s' % threading.currentThread().getName())
            lock = self.locksByResource.get(resource)
            lock.acquire()
        else:
            self.createAndClaimLock(resource)
    
    def unlockResource(self, resource):
        lock = self.locksByResource.get(resource)
        #log.debug('lock = %s'%lock)
        lock.release()
    
    def remove(self, fileUrl):
        filepath = self._mapToPath(fileUrl)
        if os.path.exists(filepath):
            os.remove(filepath)
            
    def clear(self):
        shutil.rmtree(self.rootDir, True)
        requireDir(self.rootDir)
        self.locksByResource.clear()
        

class MythThumbnailFileCache(FileCache):
    """File cache + interested in bus events"""
    
    def __init__(self, rootDir, resolver, bus, domainCache):
        """
        @type rootDir: str
        @param rootDir: root directory of the cache. will be created if it does not exist.
        @type resolver: FileResolver
        @param resolver: Pluggable component to retrieve (resolve) files.
        @type bus: EventBus
        """
        FileCache.__init__(self, rootDir, resolver)
        self.bus = bus
        self.bus.register(self)
        self.domainCache = domainCache
    
    @run_async
    @catchall
    def reap(self):
        '''Delete thumbnails which no longer have an associated recording'''
        active = set([self.resolver.hash(r) for r in self.domainCache.getAllRecordings()])
        ondisk = set(os.listdir(self.rootDir))
        delta = ondisk.difference(active)

        if delta:
            c = 0
            for f in delta:
                abspath = os.path.join(self.rootDir, f)
                c += os.path.getsize(abspath)
                os.remove(abspath)
            log.info('Reclaimed %d kb by deleting %d thumbnails' % ((c/1000), len(delta)))
        else:
            log.debug('Nothing to reap from thumbnail cache')
            
    def onEvent(self, event):
        """When a recording is deleted, remove its thumbnail from the cache"""
        if event['id'] == Event.RECORDING_DELETED:
            log.debug('MythThumbnailFileCache received event: %s' % event)
            self.remove(event['program'])

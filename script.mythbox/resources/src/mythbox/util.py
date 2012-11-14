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
import ConfigParser
import logging
import os
import Queue
import re
import sys
import time
import xbmcgui

from datetime import datetime, timedelta
from decorator import decorator
from odict import odict
from threading import RLock, Thread


log = logging.getLogger('mythbox.core')
plog = logging.getLogger('mythbox.perf')
elog = logging.getLogger('mythbox.event')

#
#  Thread local storage used by @inject_conn and @inject_db decorators
#
threadlocals = {}   

def to_kwargs(obj, attrNames):
    '''Useful for building **kwargs dependencies by plucking the attributes by name from self'''
    kwargs = {}
    for attrName in attrNames:
        kwargs[attrName] = getattr(obj, attrName)
    return kwargs


def requireDir(dir):
    '''Create dir with missing path segments and return for chaining'''
    if not os.path.exists(dir):
        os.makedirs(dir)
    return dir

    
def formatSize(sizeKB, gb=False):
    size = float(sizeKB)
    if size > 1024*1000 and gb:
        value = str("%.2f %s"% (size/(1024.0*1000.0), "GB"))
    elif size > 1024:
        value = str("%.2f %s"% (size/(1024.0), 'MB')) 
    else:
        value = str("%.2f %s"% (size, 'KB')) 
    return re.sub(r'(?<=\d)(?=(\d\d\d)+\.)', ',', value)
    

def formatSeconds(secs):
    """
    Returns number of seconds into a nicely formatted string --> 00h 00m 00s
    The hours and minutes are left off if zero 
    """
    assert secs >= 0, 'Seconds must be > 0'
    time_t  = time.gmtime(secs)
    hours   = time_t[3]  # tm_hour
    mins    = time_t[4]  # tm_min 
    seconds = time_t[5]  # tm_sec
    result  = ""
    
    if hours > 0:
        result += "%sh" % hours
        if mins > 0 or seconds > 0:
            result += " "
            
    if mins > 0:
        result += "%sm" % mins
        if seconds > 0:
            result += " "
            
    if (len(result) == 0) or (len(result) > 0 and seconds > 0):
        result += "%ss"%seconds
        
    return result


def slice(items, num):
    """
    Slices a list of items into the given number of separate lists
    @param items: list of items to split
    @param num: number of lists to split into
    @return: list of lists
    @example: [1,2,3,4,5,6,7,8] with num=3 returns [[1,4,7], [2,5,8], [3,6]]
    """
    queues = []
    for i in range(num):
        queues.append([])
    for i, item in enumerate(items):
        queues[i%num].append(item)
    return queues


def safe_unicode(obj, *args):
    """ return the unicode representation of obj """
    try:
        return unicode(obj, *args)
    except UnicodeDecodeError:
        # obj is byte string
        ascii_text = str(obj).encode('string_escape')
        return unicode(ascii_text)
    

def safe_str(obj):
    """ return the byte string representation of obj """
    try:
        return str(obj)
    except UnicodeEncodeError:
        # obj is unicode
        return unicode(obj).encode('unicode_escape')


class BoundedEvictingQueue(object):
    """
    Fixed size queue that evicts objects in FIFO order when capacity
    has been reached. 
    """

    def __init__(self, size):
        self._queue = Queue.Queue(size)
        
    def empty(self):
        return self._queue.empty()
    
    def qsize(self):
        return self._queue.qsize()
    
    def full(self):
        return self._queue.full()
    
    def put(self, item):
        if self._queue.full():
            self._queue.get()
        self._queue.put(item, False, None)
        
    def get(self):
        return self._queue.get(False, None)


__workersByName = odict()  # key = thread name, value = Thread


def clearWorkers():
    """Only to be used by unit tests"""
    __workersByName.clear()


def hasPendingWorkers():
    for workerName, worker in __workersByName.items():
        if worker:
            if worker.isAlive():
                return True
    return False
     

def waitForWorkersToDie(timeout=None):
    """
    If the main python thread exits w/o first letting all child threads die, then
    xbmc has a bad habit of coredumping. Certainly not desired from a user experience
    perspective. 
    """
    log.debug('Total threads spawned = %d' % len(__workersByName))
    for workerName, worker in __workersByName.items():
        if worker:
            if worker.isAlive():
                log.debug('Waiting for thread %s to die...' % workerName)
                worker.join(timeout)
                if worker.isAlive():
                    # apparently, join timed out
                    log.error('Thread %s still alive after timeout', workerName)
                    
    log.debug('Done waiting for threads to die')


@decorator
def run_async(func, *args, **kwargs):
    """
        run_async(func)
            function decorator, intended to make "func" run in a separate
            thread (asynchronously).
            Returns the created Thread object

            E.g.:
            @run_async
            def task1():
                do_something

            @run_async
            def task2():
                do_something_too

            t1 = task1()
            t2 = task2()
            ...
            t1.join()
            t2.join()
    """
    from threading import Thread
    worker = Thread(target = func, args = args, kwargs = kwargs)
    __workersByName[worker.getName()] = worker
    worker.start()
    # TODO: attach post-func decorator to target function and remove thread from __workersByName
    return worker


@decorator
def timed(func, *args, **kw):
    """
    Decorator for logging method execution times. 
    Make sure 'mythtv.perf' logger in is set to WARN or lower. 
    """
    if plog.isEnabledFor(logging.DEBUG):
        t1 = time.time()
        result = func(*args, **kw)
        t2 = time.time()
        diff = t2 - t1
        if diff > 1.0:
            plog.warning("TIMER: %s took %2.2f seconds" % (func.__name__, diff))
        #elif diff > 0.1:
        else:
            pass # plog.debug("TIMER: %s took %2.2f seconds" % (func.__name__, diff))
        return result
    else:
        return func(*args, **kw)

@decorator
def catchall(func, *args, **kw):
    """
    Decorator for catching and logging exceptions on methods which
    can't safely propagate exceptions to the caller
    """
    try:
        return func(*args, **kw)
    except Exception, ex:
        log.error(sys.exc_info())
        log.exception('CATCHALL: Caught exception %s on method %s' % (str(ex), func.__name__))


@decorator
def catchall_ui(func, *args, **kw):
    """
    Decorator for catching, logging, and displaying exceptions on methods which
    can't safely propagate exceptions to the caller (on* callback methods from xbmc)
    """
    try:
        return func(*args, **kw)
    except Exception, ex:
        log.error(sys.exc_info())
        log.exception('CATCHALL_UI: Caught %s exception %s on method %s' % (type(ex), str(ex), func.__name__))
        msg1 = str(ex)
        msg2 = ''
        msg3 = ''
        n = 45
        if len(msg1) > n:
            msg2 = msg1[n:]
            msg1 = msg1[:n]
        if len(msg2) > n:
            msg3 = msg2[n:]
            msg2 = msg2[:n]
        xbmcgui.Dialog().ok('Error: %s' % func.__name__, msg1, msg2, msg3)


def synchronized(func):
    """Synchronizes method invocation on an object using the method name as the mutex"""
    
    def wrapper(self,*__args,**__kw):
        try:
            rlock = self.__get__('_sync_lock_%s' % func.__name__)
            #rlock = self._sync_lock
        except AttributeError:
            from threading import RLock
            rlock = self.__dict__.setdefault('_sync_lock_%s' % func.__name__, RLock())
        rlock.acquire()
        try:
            return func(self,*__args,**__kw)
        finally:
            rlock.release()
            
    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper


def sync_instance(func):
    """Synchronizes method invocation on an object using the object instance as the mutex"""
    
    def wrapper(self,*__args,**__kw):
        try:
            rlock = self._sync_lock
        except AttributeError:
            from threading import RLock
            rlock = self.__dict__.setdefault('_sync_lock', RLock())
        rlock.acquire()
        try:
            return func(self,*__args,**__kw)
        finally:
            rlock.release()
            
    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper


def coalesce(func):
    """Coalesces concurrent calls to a function with no return value from multiple threads."""

    def wrapper(self,*__args,**__kw):
        try:
            rlock = self.__get__('_coalesce_lock_%s' % func.__name__)
        except AttributeError:
            from threading import RLock
            rlock = self.__dict__.setdefault('_coalesce_lock_%s' % func.__name__,RLock())
        
        #print type(self)
        #print __args
        #print __kw
        #print func.__name__
        
        acquired = rlock.acquire(blocking=False)
        if acquired:
            try:
                return func(self,*__args,**__kw)
            finally:
                rlock.release()
        else:
            log.debug('Coalesced call to method: %s' % func.__name__)
            return
        
    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper


def max_threads(t=1):
    '''Limits the number of threads that can execute the decorated method concurrently'''
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            if not hasattr(f, '_semaphore'):
                import threading
                f._semaphore = threading.BoundedSemaphore(t)
            f._semaphore.acquire()
            try:
                r = f(*args, **kwargs)
            finally:
                f._semaphore.release()
            return r
        
        return wrapped_f
    return wrap
    

def timed_cache(seconds=0, minutes=0, hours=0, days=0):
    """
    Lifted from http://www.willmcgugan.com/blog/tech/2007/10/14/timed-caching-decorator/
    """
    time_delta = timedelta( seconds=seconds,
                            minutes=minutes,
                            hours=hours,
                            days=days )

    def decorate(f):

        f._lock = RLock()
        f._updates = {}
        f._results = {}

        def do_cache(*args, **kwargs):

            lock = f._lock
            lock.acquire()

            try:
                key = (args, tuple(sorted(kwargs.items(), key=lambda i:i[0])))

                updates = f._updates
                results = f._results

                t = datetime.now()
                updated = updates.get(key, t)

                if key not in results or t-updated > time_delta:
                    # Calculate
                    updates[key] = t
                    result = f(*args, **kwargs)
                    
                    # DIFF: Removed deepcopy
                    # results[key] = deepcopy(result)
                    results[key] = result
                    return result

                else:
                    # Cache
                    # DIFF: Removed deepcopy
                    #return deepcopy(results[key])
                    return results[key]

            finally:
                lock.release()

        return do_cache

    return decorate


def which(program, all=False):
    """emulates unix' "which" command (with one argument only)"""
    
    def is_exe(exe):
        return os.path.exists(exe) and os.access(exe, os.X_OK)

    def full_exes(program):
        for path in os.environ['PATH'].split(os.pathsep):
            log.debug('Checking PATH %s for %s' %(path, program))
            exe = os.path.join(path, program)
            if is_exe(exe):
                yield exe

    ppath, pname = os.path.split(program)
    if ppath:
        if is_exe(program):
            return program
    else:
        paths = full_exes(program)
        if not all:
            try:
                return paths.next()
            except StopIteration:
                return None
        else:
            return list(paths)
    return None


class NativeTranslator(object):
    
    def __init__(self, scriptPath, defaultLanguage=None, *args, **kwargs):
        import xbmcaddon
        self.addon = xbmcaddon.Addon('script.mythbox')
        
    def get(self, id):
        """
        Alias for getLocalizedString(...)

        @param id: translation id
        @type id: int
        @return: translated text
        @rtype: unicode
        """
        # if id is a string, assume no need to lookup translation
        if isinstance(id, basestring):
            return id
        else:
            return self.addon.getLocalizedString(id)
     
    def toList(self, someMap):
        """
        @param someMap: dict with translation ids as values. Keys are ignored
        @return: list of strings containing translations
        """
        result = []
        for key in someMap.keys():
            result.append(self.get(someMap[key]))
        return result
    

class OnDemandConfig(object):
    """
    Used by unit tests to query user for values on stdin as they
    are needed (passwords, for example) . Once entered, the value is saved
    to a config file so future invocations can run unattended.  
    """ 
    
    def __init__(self, filename='ondemandconfig.ini', section='blah'):
        self.filename = filename
        self.section = section
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.filename)
    
    def get(self, key):
        if not self.config.has_section(self.section):
            self.config.add_section(self.section)
        
        if self.config.has_option(self.section, key):
            value = self.config.get(self.section, key)
        else:
            print "\n==============================="
            print "Enter a value for key %s:" % key
            value = sys.stdin.readline()
            print "Value is stored in %s if you would like to change it later." % self.filename
            print "===============================\n"
            
            value = str(value).strip() # nuke newline
            self.config.set(self.section, key, value)
            inifile = file(self.filename, "w")
            self.config.write(inifile)
            inifile.close()
        return value


class SynchronizedDict(object):
    
    def __init__(self):
        self.delegate = {}
    
    @sync_instance     
    def put(self, k, v):
        self.delegate[k] = v
        
    @sync_instance     
    def has_key(self, k):
        return self.delegate.has_key(k)
    
    @sync_instance
    def get(self, k):
        return self.delegate.get(k)
    
    @sync_instance
    def remove(self, k):
        del self.delegate[k]
        
    @sync_instance
    def clear(self):
        self.delegate.clear()


class BidiIterator(object):
    """
    Bidirectional list iterator
    
    Surprisingly, googling bi-directional python iterators yielded nothing so
    here you have it.
    """
    
    def __init__(self, items, position=None):
        """
        @type items: list
        @type position: zero based index for initial position of the iterator
        """
        self.i = position
        self.items = items
        
    def previous(self):
        if not self.items or self.i is None or self.i == 0:
            raise StopIteration
        self.i -= 1
        return self.items[self.i]
        
    def next(self):
        if not self.items:
            raise StopIteration
        if self.i is None:
            self.i = 0
        elif (self.i + 1) == len(self.items):
            raise StopIteration
        else:
            self.i += 1
        return self.items[self.i]
    
    def index(self):
        """return zero based index of current element or None if iterator not initialized"""
        return self.i
    
    def current(self):
        if self.i is not None:
            return self.items[self.i]
        else:
            raise StopIteration

    def size(self):
        return len(self.items)
    

class CyclingBidiIterator(BidiIterator):
    """Adds some cycle(...) goodness to our bidirectional iterator"""
    
    def __init__(self, items, position=None):
        BidiIterator.__init__(self, items, position)
    
    def previous(self):
        if self.i is None or self.i == 0:
            self.i = len(self.items)
        return super(CyclingBidiIterator, self).previous()
        
    def next(self):
        if self.i is not None and (self.i + 1) == len(self.items): 
            self.i = None
        return super(CyclingBidiIterator, self).next()    

# -*- coding: utf-8 -*-
import xbmc
import os, json, hashlib, time

IS_WEB = False
try:
    import xbmcgui
except ImportError:
    IS_WEB = True

class JsonRAFifoQueue(object):
    def __init__(self,path):
        self.path = path
        self.lockPath = os.path.join(os.path.dirname(self.path),os.path.basename(self.path) + '.lock')
        self.timeout = 5
        self._size = 0

    def _locking(f):
        def wrapper(self,*args):
            self.lock()
            try:
                return f(self,*args)
            finally:
                self.unlock()
        return wrapper

    def _createLockFile(self):
        with open(self.lockPath,'w') as f: f.write(str(time.time()))

    def _lockFileIsStale(self):
        with open(self.lockPath,'r') as f:
            if time.time() - float(f.read()) > self.timeout: return True
        return False

    def lock(self):
        if os.path.exists(self.lockPath):
            if self._lockFileIsStale(): return self._createLockFile() #Lock file is stale so recreate and return

            for x in (range(self.timeout*10)): #We timeout because all accesses should not block long so if we wait too long that means the lock is invalid
                if not os.path.exists(self.lockPath): break
                time.sleep(0.1)
        self._createLockFile() #We either timed out or there was no lock, either way we update/create the lockfile

    def unlock(self):
        if os.path.exists(self.lockPath): os.remove(self.lockPath)

    def loadQueue(self):
        if not os.path.exists(self.path): return []

        with open(self.path,'r') as f:
            try:
                return json.load(f) or []
            except:
                import traceback
                traceback.print_exc()
        return []

    def saveQueue(self,queue):
        self.size = len(queue)
        with open(self.path,'w') as f:
            json.dump(queue,f)

    def nextID(self,string):
        ID = hashlib.md5(string).hexdigest() + str(time.time())
        return ID

    @_locking
    def push(self,string):
        queue = self.loadQueue()
        queue.append((self.nextID(string),string))
        self.saveQueue(queue)

    @_locking
    def pop(self):
        queue = self.loadQueue()
        ID, val = queue and queue.pop(0) or (None,None)
        self.saveQueue(queue)
        return val

    @_locking
    def remove(self,ID):
        queue = self.loadQueue()
        for i in range(len(queue)):
            if queue[i][0] == ID:
                queue.pop(i)
                break
        else:
            #We didn't change the queue
            return False
        #Queue was modified
        self.saveQueue(queue)
        return True

    @_locking
    def clear(self):
        self.saveQueue([])

    def items(self):
        return self.loadQueue()

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self,val):
        self._size = val

class XBMCJsonRAFifoQueue(JsonRAFifoQueue):
    def __init__(self,path):
        JsonRAFifoQueue.__init__(self,path)
        filename = os.path.basename(self.path)
        self.lockProperty = 'XBMCJsonRAFifoQueue_{0}.lock'.format(filename)
        self.sizeProperty = 'XBMCJsonRAFifoQueue_{0}.size'.format(filename)

    def _lockIsStale(self):
        last = self._lockProperty()
        if not last: return True
        if time.time() - float(last) > self.timeout: return True
        return False

    def _lockProperty(self):
        return xbmc.getInfoLabel('Window(10000).Property({0})'.format(self.lockProperty))

    def _createLockProperty(self):
        xbmcgui.Window(10000).setProperty( self.lockProperty, str(time.time()) )

    def lock(self):
        if self._lockProperty():
            if self._lockIsStale(): return self._createLockProperty() #Lock file is stale so recreate and return

            for x in (range(self.timeout*10)): #We timeout because all accesses should not block long so if we wait too long that means the lock is invalid
                if not self._lockProperty(): break
                time.sleep(0.1)
        self._createLockProperty() #We either timed out or there was no lock, either way we update/create the lockfile

    def unlock(self):
        xbmcgui.Window(10000).setProperty( self.lockProperty,'' )

    @property
    def size(self):
        return xbmc.getInfoLabel('Window(10000).Property({0})'.format(self.sizeProperty))

    @size.setter
    def size(self,val):
        xbmcgui.Window(10000).setProperty( self.sizeProperty,str(val))

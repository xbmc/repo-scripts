# -*- coding: utf-8 -*-
import Queue
import pbclient
import pushhandler

class KodiDevice(pbclient.Device):
    def init(self):
        self.queue = Queue.Queue()

    def clear(self):
        push = True
        while push: push = self.getNext()

    def hasPush(self):
        return not self.queue.empty()

    def getNext(self):
        if self.queue.empty(): return None
        try:
            data = self.queue.get_nowait()
            self.queue.task_done()
            return data
        except Queue.Empty:
            pass
        return None

    def link(self,data):
        if not pushhandler.canHandle(data):
            pushhandler.checkForWindow()
            return

        self.queue.put_nowait(data)
        return False

    def file(self,data):
        if not pushhandler.canHandle(data):
            pushhandler.checkForWindow()
            return

        self.queue.put_nowait(data)
        return False

    def note(self,data):
        if not pushhandler.canHandle(data):
            pushhandler.checkForWindow()
            return

        self.queue.put_nowait(data)
        return False

    def list(self,data):
        if not pushhandler.canHandle(data):
            pushhandler.checkForWindow()
            return

        self.queue.put_nowait(data)
        return False
    
    def address(self,data):
        if not pushhandler.canHandle(data):
            pushhandler.checkForWindow()
            return

        self.queue.put_nowait(data)
        return False

def getDefaultKodiDevice(ID,name):
    assert ID and name, 'Must provide device ID and name'
    return KodiDevice(ID,name)
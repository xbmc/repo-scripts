#VirtualEvents.py

try:
    from Tkinter import *
    import tkMessageBox
except ImportError:
    try:
        from tkinter import *
        from tkinter import messagebox
    except Exception:
        pass

import time
from threading import Thread

from resources.lib.Utilities.DebugPrint import DbgPrint


def TS_decorator(func):
    def stub(*args, **kwargs):
        func(*args, **kwargs)

    def hook(*args,**kwargs):
        threadname="Thread-{}".format(func.__name__)
        Thread(target=stub, name=threadname, args=args).start()

    return hook


class VirtualEvent(object):
    def __init__(self, master, virtualEvent):
        self.master = master
        self.widget = Label(master)
        self.widget.pack()
        self.makeVirtualEvent(virtualEvent)
        DbgPrint("VirtualEvent Init Finished")


    def makeVirtualEvent(self, virtualEvent):
        self.widget.event_add(virtualEvent, 'None')

    def bindVirtualEvent(self, vEvent, handler):
        self.widget.bind(vEvent, handler)

    def FireVirtualEvent(self, vEvent, data):
        Event.VirtualEventData=data
        self.widget.event_generate(vEvent)
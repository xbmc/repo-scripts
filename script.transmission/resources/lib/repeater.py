# -*- coding: utf-8 -*-
# Copyright (c) 2010 Correl J. Roush

import threading
import time

class Repeater:
    def __init__(self, interval, action, arguments = []):
        self.interval = interval
        self.action = action
        self.arguments = arguments
        self.event = None
    def start(self):
        if self.event:
            return
        self.event = threading.Event()
        self.thread = threading.Thread(target=Repeater.repeat, args=(self.event, self.interval, self.action, self.arguments))
        self.thread.start()
    def stop(self):
        if not self.event:
            return
        self.event.set()
        self.thread.join()
        self.event = None
    def repeat(cls, event, interval, action, arguments = []):
        while True:
            event.wait(interval)
            if event.isSet():
                break;
            action(*arguments)
    repeat = classmethod(repeat)



if __name__ == '__main__':
    def foo(a, b):
        print a, b

    r = Repeater(1.0, foo, ['foo', 'bar'])
    r.start()
    time.sleep(10)
    r.stop()
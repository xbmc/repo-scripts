#AlarmsMgr.py
#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

__Version__ = "0.9.4"

try:
    import Queue as Q  # ver. < 3.0
except ImportError:
    import queue as Q

import threading
from threading import RLock
from datetime import datetime, timedelta
from time import sleep
from resources.lib.Utilities.DebugPrint import DbgPrint, DEBUGMODE, myLog

masterRlock = RLock()
MODULEDEBUGMODE = True


def cmp(a,b):
    return((a > b) - (a < b))

def TS_decorator(func):
    def stub(*args, **kwargs):
        func(*args, **kwargs)

    def hook(*args, **kwargs):
        threading.Thread(target=stub, args=args).start()

    return hook

def status():
    if not (DEBUGMODE and MODULEDEBUGMODE):
        return

    global masterRlock
    masterRlock.acquire()
    try:
        myLog("Active:")
        myLog(_alarms.activetimer)
    except:
        pass

    myLog("Queued:")
    for i in range(_alarms.pq.qsize()):
        try:
            myLog(_alarms.pq.queue[i])
        except:
            pass

    myLog()
    masterRlock.release()

class _alarm(object):
    def __init__(self, parent, alarmtime, fn, *args):
        """

        :param parent: _Alarms
        :param alarmtime: datetime
        :param fn:
        :param args:
        """
        self.alarmtime = alarmtime
        self.fn = fn
        self.args = args
        self.active = False
        self.parent = parent
        self.refDate = parent.refDate

    def start(self):
        self.active = True
        self.parent.update(self, self.parent.START)

    def cancel(self):
        self.active = False
        self.parent.update(self, self.parent.CANCEL)

    def isAlive(self):
        return self.active

    @property
    def priority(self):
        return int((self.alarmtime - self.refDate).total_seconds())


    def __repr__(self):
        return str(self.alarmtime) + " : " + str(self.priority)

    def __cmp__(self, other):
        if not self.active:
            return 1
        else:
            return cmp(self.priority, other.priority)

    def __le__(self, other):
        return self.priority <= other.priority

    def __lt__(self, other):
        return self.priority < other.priority

    def __ge__(self, other):
        return self.priority <= other.priority

    def __gt__(self, other):
        return self.priority < other.priority

    def __eq__(self, other):
        return self.priority == other.priority

class _Alarms(object):
    START = 1
    CANCEL = 2
    UPDATE = 3

    def __init__(self, noargs=True):
        self.pq = Q.PriorityQueue()
        self.Timer = None # type: threading.Timer
        self.activetimer = None # type: _alarm
        self.noargs = noargs
        self.rlock = RLock()
        self.refDate = datetime(datetime.today().year,1,1)


    def _addTimer(self, timer):
        self.pq.put(timer)


    def _findTimer(self, timer):
        for i in range(self.pq.qsize()):
            a=self.pq.queue[i]
            if a == timer:
                return i
        return -1

    def _removeTimer(self, timer):
        i = self._findTimer(timer)
        if i >= 0:
            del(self.pq.queue[i])

    @TS_decorator
    def _launchActiveTimerFn(self):
        if self.noargs:
            self.activetimer.fn()
        else:
            if len(self.activetimer.args) == 0:
                self.activetimer.fn(None)
            else:
                args = self.activetimer.args[0]
                self.activetimer.fn(args)


    def _eventHandler(self):
        self.activetimer.active = False
        self._launchActiveTimerFn()
        sleep(1)
        self.Timer = None
        self.activetimer = None
        self._StartTimer()
        status()


    def _stopTimer(self):
        self.Timer.cancel()
        count = 10
        while count >= 0:
            count -= 1
            if not self.Timer.is_alive():
                break

            sleep(1)

        self.Timer = None # type: threading.Timer


    def _startTimer(self, timer):
        if timer.active:
            if self.Timer is not None:
                self._stopTimer()

            td = timer.alarmtime - datetime.now()
            if td.days >= 0:
                self.Timer = threading.Timer(td.total_seconds() - 2, self._eventHandler)
                self.Timer.start()
                if self.activetimer is not None:
                    oldtimer = self.activetimer
                    self.activetimer = timer
                    self.pq.put(oldtimer)
                else:
                    self.activetimer = timer
            else:
                raise Exception("AlarmsMgr: Invalid Start Time")

    def _StartTimer(self):
        if self.activetimer is None:
            try:
                timer = self.pq.get(block=False) #pop the top item off the queue
                self._startTimer(timer)
            except:
                pass
        else: #self.activetimer is not None
            try:
                newTimer = self.pq.get(block=False) #pop the top item off the queue
                if newTimer < self.activetimer:
                    self._startTimer(newTimer) #launch new timer
                else:
                    self.pq.put(newTimer) #put timer item back on the queue
            except:
                pass


    def _cancelTimer(self, timer):
        DbgPrint("Deleting Timer: {}".format(timer))
        if self.activetimer is not None:
            if timer == self.activetimer:
                self._stopTimer()
                self.activetimer = None
            else:
                self._removeTimer(timer)

        self._StartTimer()



    def update(self, timer, operation):
        if operation == self.START:
           self._StartTimer()
        elif operation == self.CANCEL:
            self._cancelTimer(timer)

        status()


    def shutdown(self):
        DbgPrint("Stopping AlarmsMgr...")
        if self.Timer is not None:
            self._stopTimer()
        DbgPrint("AlarmsMgr Stopped...")

_alarms = _Alarms()

def ActivateParms():
    global _alarms
    _alarms = _Alarms(noargs=False)

def deActivateParms():
    global _alarms
    _alarms = _Alarms(noargs=True)

def Timer(alarmseconds, fn, *args):
    global _alarms
    alarmtime = datetime.now() + timedelta(seconds=alarmseconds - 1)
    if len(args) == 1:
        if len(args[0]) == 1:
            if type(args[0]) == list:
                args = args[0]
                timer = _alarm(_alarms, alarmtime, fn, *args)
        else: # len(list) > 1
            if type(args[0]) == list:
                args = args[0]
                timer = _alarm(_alarms, alarmtime, fn, args)
    else:
        timer = _alarm(_alarms, alarmtime, fn, *args)

    _alarms._addTimer(timer)

    return timer




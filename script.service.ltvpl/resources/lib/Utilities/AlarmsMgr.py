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

__Version__ = "1.0.0"

try:
    import Queue as Q  # ver. < 3.0
except ImportError:
    import queue as Q

import threading
from threading import RLock
from datetime import datetime, timedelta
from time import sleep
from resources.lib.Utilities.DebugPrint import DbgPrint, DEBUGMODE, myLog
from .VirtualEvents import TS_decorator

masterRlock = RLock()
activeTimerLock = RLock()
MODULEDEBUGMODE = True


def cmp(a,b):
    return((a > b) - (a < b))


def status():
    if not (DEBUGMODE and MODULEDEBUGMODE):
        return

    global masterRlock
    masterRlock.acquire()
    try:
        myLog("Alarms Active:")
        myLog("   {:>3}->{}".format(0, _alarms.mt.Activetimer))
    except Exception as e:
        DbgPrint(e)

    myLog("Alarms Queued:")
    for n,i in enumerate(range(_alarms.pq.qsize())):
        try:
            myLog("   {:>3}->{}".format(n+1, _alarms.pq.queue[i]))
        except Exception as e:
            DbgPrint(e)

    myLog("*****")
    masterRlock.release()

class MasterTimer(object):
    def __init__(self, parentstartTimer, noargs=True):
        self.parentstartTimer = parentstartTimer
        self._activetimer = None # type: _alarm
        self.Timer = None
        self.noargs = noargs

    @property
    def Activetimer(self):
        return self._activetimer

    @Activetimer.setter
    def Activetimer(self, alarm):
        """
        :type alarm: _alarm
        """
        if alarm is not None:
            self._activetimer = alarm
            self._startTimer()
        else:
            self.stopTimer()
            self._activetimer = None


    def _eventHandler(self):
        activeTimerLock.acquire()
        DbgPrint("***ActiveTimer:{}".format(self._activetimer))
        if self._activetimer is not None:
            self._activetimer.active = False
            self._launchActiveTimerFn()
        sleep(1)
        self.Timer = None
        DbgPrint("***Clearing ActiveTimer:{}".format(self._activetimer))
        self._activetimer = None
        self.parentstartTimer(blocktimerlock=True)
        activeTimerLock.release()
        status()


    def stopTimer(self):
        if self.Timer is not None:
            self.Timer.cancel()
            count = 10
            while count >= 0:
                count -= 1
                if self.Timer is not None and not self.Timer.is_alive():
                    break

                sleep(1)

            self.Timer = None # type: threading.Timer


    def _startTimer(self):
        if self._activetimer is not None:
            if self.Timer is not None:
                self.stopTimer()

            td = self._activetimer.alarmtime - datetime.now()
            if td.days >= 0:
                self.Timer = threading.Timer(td.total_seconds() - 2, self._eventHandler)
                self.Timer.name = "Thread-MasterTimer"
                self.Timer.start()
                DbgPrint("***ActiveTimer:{}".format(self._activetimer))
            else:
                raise Exception("AlarmsMgr: Invalid Start Time")

    @TS_decorator
    def _launchActiveTimerFn(self):
        DbgPrint("***ActiveTimer:{}".format(self._activetimer))
        if self._activetimer is not None:
            if self.noargs:
                self._activetimer.fn()
            else:
                if len(self._activetimer.args) == 0:
                    self._activetimer.fn(None)
                else:
                    args = self._activetimer.args[0]
                    self._activetimer.fn(args)



class _alarm(object):
    def __init__(self, parent, alarmtime, fn, ch, *args):
        """

        :param _Alarms parent:
        :param datetime alarmtime:
        :param fn:
        :param str ch: channel # to change to
        :param args:
        """
        self.alarmtime = alarmtime
        self.fn = fn
        self.ch = ch
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
        return "Ch:{:>4.4} : {} : {}".format(self.ch, self.alarmtime, self.priority)

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
        return self.priority >= other.priority

    def __gt__(self, other):
        return self.priority > other.priority

    def __eq__(self, other):
        return self.priority == other.priority


class _Alarms(object):
    START = 1
    CANCEL = 2
    UPDATE = 3

    def __init__(self, noargs=True):
        self.pq = Q.PriorityQueue()
        self.mt = MasterTimer(self._startTimer, noargs=noargs)
        self.noargs = noargs
        self.refDate = datetime(datetime.today().year,1,1)


    def _addTimer(self, timer):
        self.pq.put(timer)
        self._findDuplicates()
        DbgPrint("AddTimer: {}".format(timer))


    def _findTimer(self, timer):
        for i in range(self.pq.qsize()):
            a=self.pq.queue[i]
            if a == timer:
                return i
        return -1

    def _removeTimer(self, timer):
        i = self._findTimer(timer)
        if i >= 0:
            DbgPrint("RemoveTimer: {}".format(self.pq.queue[i]))
            del(self.pq.queue[i])


    def _startTimer(self, blocktimerlock=False):
        if not blocktimerlock:
            activeTimerLock.acquire()

        oldtimer = self.mt.Activetimer
        if oldtimer is None:
            try:
                timer = self.pq.get(block=False)  # pop the top item off the queue
                DbgPrint("***NewTimer:{}".format(timer))
                self.mt.Activetimer = timer
            except Exception as e:
                DbgPrint(e)
        else:
            try:
                newTimer = self.pq.get(block=False)  # pop the top item off the queue
                if newTimer < oldtimer:
                    DbgPrint("***NewTimer:{}".format(newTimer))
                    self.mt.Activetimer = newTimer  # launch new timer
                    DbgPrint("***Putting Oldtimer back in queue:{}".format(oldtimer))
                    self.pq.put(oldtimer)
                else:
                    self.pq.put(newTimer)  # put timer item back in the queue
            except Exception as e:
                DbgPrint(e)

        if not blocktimerlock:
            activeTimerLock.release()

    def _cancelTimer(self, timer):
        activeTimerLock.acquire()
        DbgPrint("Deleting Timer: {}".format(timer))
        DbgPrint("***Current ActiveTimer:{}".format(self.mt.Activetimer))
        DbgPrint("timer == self.mt.Activetimer:{}".format(timer == self.mt.Activetimer))
        if timer == self.mt.Activetimer:
            self.mt.Activetimer = None
        else:
            self._removeTimer(timer)

        self._startTimer(blocktimerlock=True)
        activeTimerLock.release()


    def _findDuplicates(self):
        numitems = self.pq.qsize()
        activetimer = self.mt.Activetimer
        if activetimer is None:
            return

        index = 0
        dlist= [activetimer]
        for i in range(numitems):
            if activetimer == self.pq.queue[i]:
                dlist.append(self.pq.queue[i])

        dlistsize = len(dlist)
        offset = 30
        if dlistsize > 1:
            for i in range(1, dlistsize):
                alarmtime = dlist[i].alarmtime + timedelta(seconds=offset)
                dlist[i].alarmtime = alarmtime
                offset += 30

        dlist2= [self.pq.queue[0]]
        for i in range(1, numitems):
            if dlist2[0] == self.pq.queue[i]:
                dlist2.append(self.pq.queue[i])

        dlist2size = len(dlist2)
        offset = 30
        if dlist2size > 1:
            for i in range(1, dlist2size):
                alarmtime = dlist2[i].alarmtime + timedelta(seconds=offset)
                dlist2[i].alarmtime = alarmtime
                offset += 30


    def update(self, timer, operation):
        if operation == self.START:
           self._startTimer()
        elif operation == self.CANCEL:
            self._cancelTimer(timer)

        status()


    def shutdown(self):
        DbgPrint("Stopping AlarmsMgr...")
        self.mt.stopTimer()
        del(self.pq)
        DbgPrint("AlarmsMgr Stopped...")

_alarms = _Alarms()

def ActivateParms():
    global _alarms
    _alarms = _Alarms(noargs=False)

def deActivateParms():
    global _alarms
    _alarms = _Alarms(noargs=True)

def Timer(alarmseconds, fn, ch, *args):
    global _alarms
    timer = None
    alarmtime = datetime.now() + timedelta(seconds=alarmseconds - 1)
    if len(args) == 1:
        if len(args[0]) == 1:
            if type(args[0]) == list:
                args = args[0]
                timer = _alarm(_alarms, alarmtime, fn, ch, *args)
        else: # len(list) > 1
            if type(args[0]) == list:
                args = args[0]
                timer = _alarm(_alarms, alarmtime, fn, ch, args)
    else:
        timer = _alarm(_alarms, alarmtime, fn, ch, *args)

    _alarms._addTimer(timer)

    return timer




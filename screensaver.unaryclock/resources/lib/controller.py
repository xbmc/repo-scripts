#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Philip Schmiegelt
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#


import threading
import datetime

import xbmc

class Controller(threading.Thread):
  
    def __init__(self, log_callback, drawClock_callback, showSeconds, redrawInterval):
      super(Controller, self).__init__()
      self.log_callback = log_callback
      self.drawClock_callback = drawClock_callback
      self.showSeconds = showSeconds
      self.redrawInterval = redrawInterval
      self.waitCondition = threading.Condition()
      self._stop = False
      
    def run(self):
         self.waitCondition.acquire()
         while not self.shouldStop():
             self.now = datetime.datetime.today()
             if (self.now.second % self.redrawInterval == 0):
                self.drawClock_callback(False)
             elif (self.showSeconds):
                self.drawClock_callback(True)

             self.waitFor =  1000000 - self.now.microsecond
             self.waitCondition.wait(float(self.waitFor) / 1000000)
         self.waitCondition.release()
      
      
    def shouldStop(self):
        if (xbmc.abortRequested):
            return True
        return self._stop
        
    def stop(self):
        self.waitCondition.acquire()
        self._stop = True
        self.waitCondition.notifyAll()
        self.waitCondition.release()

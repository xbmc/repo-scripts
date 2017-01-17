# -*- coding: utf-8 -*-

'''
    Funimation|Now Add-on
    Copyright (C) 2016 Funimation|Now

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
#https://pymotw.com/2/threading/
#https://pymotw.com/2/multiprocessing/basics.html


'''import threading;


class Thread(threading.Thread):
    def __init__(self, target, *args):
        
        self._target = target;
        self._args = args;

        threading.Thread.__init__(self);

    def run(self):
        self._target(*self._args);'''

import threading;
import logging;


threadLimiter = threading.BoundedSemaphore(5);


class DetailsThread(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):

        self._target = target;
        self._args = args;

        threading.Thread.__init__(self);

    
    def run(self):

        threadLimiter.acquire();

        try:
            self._target(*self._args);

        finally:
            threadLimiter.release();



class DisplayThread(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):

        self._target = target;
        self._args = args;

        threading.Thread.__init__(self);

    
    def run(self):

        try:
            self._target(*self._args);

        finally:
            pass;
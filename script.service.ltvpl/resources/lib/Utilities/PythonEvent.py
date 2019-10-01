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
import sys
if sys.version_info[0]==2:
    from threading import Thread
else:
    from threading import Thread
import time

__Version__ = "1.0.0"

class Event(list):
    """
        PythonEvent creates an event system
        Syntax:
            PythonEvent(name,[spawn])
            
        The constructor is called with an event name and an optional spawn flag.
        The AddHandler method subscribes to the event.
        The RemoveHandler method unsubscribes from the event
        The spawn flag causes each call to a subscribing event handler
            to execute in its own thread.
            
        Example:
            e = Event('MyStuff')

            def test1(*args, **kwargs):
                print("test1->arg:{}\n".format(args))

            def test2(*args, **kwargs):        
                if len(kwargs) > 0:
                    print("test2->arg:{},{}\n".format(args,kwargs))
                else:
                    print("test2->arg:{}".format(*args))
            
            
            e.AddHandler(test1)
            e.AddHandler(test2)

            e('John') #Calls event subscribers with the arg
            e('John',Sam,age=50,gender=male) #Calls event subscribers with the args
    """
    def __init__(self, eventName, spawn=False):
        list.__init__(self)
        self.name = eventName
        self.spawn = spawn

    def __str__(self):
        return self.name

    def AddHandler(self, handler):
        self.append(handler)

    def RemoveHandler(self, handler):
        self.remove(handler)

    def __call__(self, *args, **kwargs):
        #print(kwargs)
        for item in self:
            if self.spawn:
                Thread(target=item, name=self.name,args=args,kwargs=kwargs).start()
            else:
                #print("*len(kwargs):{}".format(len(kwargs)))
                if len(kwargs) > 0:
                    #print("call with kwargs")
                    item(*args, **kwargs)
                else:
                    #print("plain call")
                    item(*args)
    @property
    def EventName(self):
        """Returns the Event Name"""
        return self.name


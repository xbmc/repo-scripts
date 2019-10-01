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
import logging
import os
import json
from datetime import datetime, timedelta
import threading
import inspect

try:
    from resources.data.debugFileLocation import DEBUGCACHEFILE
except ImportError:
    print("import error for DEBUGCACHEFILE")
    from util import DEBUGFILE_DEFAULTPATH as DEBUGCACHEFILE


__Version__ = "1.0.3"

"""
    Place MODULEDEBUGMODE=value at the top of a module to control DebugMode
    MODULEDEBUGMODE==True will print debug statements
    MODULEDEBUGMODE==False will not print debug statements
"""
#logging.basicConfig(stream=sys.stderr)
logging.basicConfig(level=logging.DEBUG)
log=logging.getLogger('=>')

class _dbmm():
    def __init__(self):
        self.debugmode=False
        self.debugmode = self.getDebugMode()


    def getDebugMode(self):

        try:
            with open(DEBUGCACHEFILE, 'r') as fp:
                jvalue = fp.read()
                jvalue = json.loads(jvalue)
            fp.close()

        except:
            jvalue = self.setDebugMode(True)

        return jvalue


    def setDebugMode(self, value):
        global DEBUGMODE
        if type(value) is not bool:
            raise TypeError("DEBUGMODE value not boolean")

        if self.debugmode == value:
            return value

        self.debugmode = value

        try:
            with open(DEBUGCACHEFILE,'w') as fp:
                jval = json.dumps(value)
                fp.write(jval)
            fp.close()
            DEBUGMODE = value
            return value
        except:
            pass

    @property
    def DebugMode(self):
        return self.getDebugMode()

dbmm = _dbmm()

try:
    import xbmc
    XBMC_PRESENT = xbmc.getFreeMem() != long
except:
    XBMC_PRESENT = False

if XBMC_PRESENT:
    def myLog(*args, **kwargs):
        DEBUGMODE = dbmm.DebugMode
        if DEBUGMODE:
            if len(args) == 0:
                fmtmsg = ""
            else:
                msg = args[0]
                try:
                    fmtmsg = msg.format(*args[1:])
                except TypeError:
                    fmtmsg = msg.format(args)
                except:
                    fmtmsg = msg

            xbmc.log(fmtmsg)

else:
    def myLog(*args, **kwargs):
        if len(args) == 0:
            fmtmsg = ""
        else:
            msg = args[0]
            try:
                fmtmsg = msg.format(*args[1:])
            except TypeError:
                fmtmsg = msg.format(args)
            except:
                fmtmsg = msg

        log.debug(fmtmsg)




DEBUGMODE = dbmm.DebugMode
setDebugMode = dbmm.setDebugMode
getDebugMode = dbmm.getDebugMode



def DbgPrint(*args, **kwargs):
    DEBUGMODE = dbmm.DebugMode
    try:
        # DebugFlag=kwargs['MODULEDEBUGMODE'] and DEBUGMODE
        del kwargs['MODULEDEBUGMODE']
        DebugFlag = DEBUGMODE
    except Exception as e:
        DebugFlag=DEBUGMODE

    if DebugFlag:
        #get module, class, function, linenumber information
        className = None
        dataRow=1
        info=inspect.stack()[dataRow]
        threadname = threading.current_thread().name
        try:
            className = info[0].f_locals['self'].__class__.__name__
        except:
            pass
        modName=None
        try:
            modName = os.path.basename(info[1])
        except:
            pass
        lineNo=info[2]
        fnName=None
        try:
            fnName = info[3]
        except:
            pass
        DbgText="{}:line#{}:{}->{}->{}()".format(threadname,lineNo, modName,className, fnName)
        argCnt=len(args)
        kwargCnt=len(kwargs)

        fmt=""
        fmt1=datetime.now().strftime("%H:%M:%S.%f")[:-3]+":"+DbgText+":"+"->"
        if argCnt > 0:
            fmt1+=(argCnt-1)*"{},"
            fmt1+="{}"
            fmt+=fmt1
        
        if kwargCnt>0:
            fmt2="{}"
            args+=("{}".format(kwargs),)
            if len(fmt)>0:
                fmt+=","+fmt2
            else:
                fmt+=fmt2


        myLog(fmt,*args)


def _LoggerSetup(fn):
    def hook(*args, **kwargs):
        fn(*args,**kwargs)
    return hook

def LoggerSetup(xDEBUGMODE=True):
    global DEBUGMODE
    DEBUGMODE=xDEBUGMODE
    if DEBUGMODE:
        return _LoggerSetup(DbgPrint)
    else:
        def NoOp(*arg,**kwargs):
            pass
        return NoOp

import time
_startTime = 0

def startTimer():
    global _startTime
    _startTime = time.clock()

def stopTimer():
    global _startTime
    duration = time.clock() - _startTime
    return duration



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
import pickle
import os, sys
from enum import Enum
from time import sleep

try:
    from Queue import Queue
except ImportError:
    from queue import Queue

from glob import glob
from datetime import datetime, timedelta

from resources.lib.Network.PL_json import json
from resources.lib.Utilities.Messaging import Cmd, MsgType, NotificationAction, OpStatus
from resources.lib.Utilities.DebugPrint import DbgPrint
from resources.lib.Network.SecretSauce import DATAEndMarker, RUHERE

__Version__ = "1.0.2"

MODULEDEBUGMODE=False
PYVER = float('{}.{}'.format(*sys.version_info[:2]))

jqueue = Queue()

class DataMode(Enum):
    XML=0
    PKL=1
    JSON=2

EncodingFMT='utf-8'

def getDictKey(dict):
    if PYVER < 3.0:
        keyslist = dict.keys()
    else:
        keyslist = list(dict.keys())

    return keyslist[0]

def getFileTimeStamp(file):
    """
    converts the timestamp associated with the file into a datetime object
    :param file: string
    :return: datetime
    """
    ts = os.path.getmtime(file)
    return datetime.fromtimestamp(ts)

def isValidTimeDiff(t1, t2, maxdiff=3600):
    """
    Computes difference between two times and returns True if diff.seconds is less than maxdiff
    :param t1: datetime
    :param t2: datetime
    :param maxdiff: int
    :return: boolean
    """
    diff = (t2 - t1).total_seconds()
    # print("diff:{}".format(diff))
    return diff < maxdiff

def getFilteredDirList(path, filter='*', sortdescending=True):
    """
    This function will return a list of files based on the path and filter
    Example filter: '*.bak?'
    :param path: string # parent directory
    :param filter: string # filename filter
    :param sortdescending: boolean #sort order
    :return: list # filtered list of files
    """
    pattern = os.path.join(path,filter)
    files = glob(pattern)
    files.sort(key=os.path.getmtime, reverse=sortdescending)
    return files

def getTimeFilteredDirList(path, filter='*', olderfiles=True, maxdiff=3600):
    """
    This function returns a time filtered list of files.
    :param path: string #parent directory
    :param filter: string # filename filter
    :param olderfiles: if True older files will be returned
    :return: list # time filtered list of files
    """
    now = datetime.now()
    files = getFilteredDirList(path, filter=filter)
    if olderfiles:
        vlist = [f for f in files if not isValidTimeDiff(getFileTimeStamp(f), now, maxdiff=maxdiff)]
    else:
        vlist = [f for f in files if isValidTimeDiff(getFileTimeStamp(f), now, maxdiff=maxdiff)]

    return vlist

def checkForDict(data):
    if not type(data) == dict:
        return data

    newData=dict([(str(k),v) for k,v in data.items()])
    return newData


def parseCmdData(data):
    try:
        cmd=getDictKey(data)#string
        args=checkForDict(data[cmd])
        cmd=Cmd[cmd] #Convert string to Cmd object
    except:
        cmd=None
        args=data

    return(cmd,args)

def parseErrorData(data):
    try:
        err=getDictKey(data)#string
        args=checkForDict(data[err])
        error= OpStatus[err] #Convert string to Cmd object
    except:
        try:
            error = MsgType[err]
        except:
            error=None
            args=data

    return(error,args)

def validateCmd(cmd):
    if cmd not in Cmd:
        raise Exception("{} is an Invalid Command".format(cmd))

def genericEncode(cmd,data):
    return {str(cmd): data}

def genericDecode(encodedData):
    try:
        key=getDictKey(encodedData)
        cmd=Cmd[key]
        return (cmd,encodedData[key])
    except Exception as e:
        try:
            cmd= OpStatus[key]
            return (cmd, encodedData[key])
        except:
            try:
                cmd=MsgType[key]
                return(cmd,encodedData[key])
            except:
                try:
                    cmd=NotificationAction[key]
                    return(cmd,encodedData[key])
                except Exception as e:
                    raise Exception("Invalid Cmd Decoded")

def encodeRequest(cmd, data):
    return {str(MsgType.Request):genericEncode(cmd,data)}

def decodeRequest(request):
    """
    :type request: dict
    """

    try:
        key = str(MsgType.Request)
        rData = request[key]
        cmd, data = genericDecode(rData)
    except Exception as e:
        DbgPrint("Error:{}:{}".format(request,str(e)))
        raise Exception("MsgType is Not a Request:{}".format(str(e)))

    #validateCmd(cmd)
    return (cmd,parseCmdData(data))

def encodeNotification(data):
    return {str(MsgType.Notification): data}

def decodeNotification(data):
    try:
        key=str(MsgType.Notification)
        rData = data[key]
        return rData
    except:
        DbgPrint("Not a Notification:{}".format(data),MODULEDEBUGMODE=MODULEDEBUGMODE)
        raise Exception("MsgType is Not a Notification")

def encodeResponse(cmd, data):
    rData = {str(MsgType.Response):genericEncode(cmd,data)}
    return rData


def decodeResponse(result):
    """
    :type result: dict
    """
    try:
        key=str(MsgType.Response)
        data=result[key]
        cmd, rData=genericDecode(data)
    except:
        raise Exception("MsgType is Result Not a Response")

    return parseCmdData(data)

def encodeErrorResponse(opstatus,errMsg):
    errdata=genericEncode(opstatus,errMsg)
    rData=genericEncode(MsgType.Error,errdata)
    return rData


def decodeErrorResponse(result):
    """
    :type result: dict
    """
    try:
        cmd,rData=genericDecode(result)
    except:
        DbgPrint("Not an Error Response:{}".format(result),MODULEDEBUGMODE=MODULEDEBUGMODE)
        raise Exception("MsgType is Not an Error Response")

    return (parseErrorData(rData))

def encodeError(opstatus,errMsg):
    rData={str(MsgType.Error):genericEncode(opstatus,errMsg)}
    return rData

def decodeError(result):
    try:
        key=str(MsgType.Error)
        data=result[key]
        err, errMsg=genericDecode(data)
        return (err,errMsg)
    except Exception as e:
        raise Exception("MsgType is Result Not an Error", str(e))

class Utilities(object):
    def __init__(self):
        pass

    def rawWritePKL(self,data):
        return pickle.dumps(data, protocol=2)
     
    def writePKL(self,conn,data):
        try:
            pdata=pickle.dumps(data, protocol=2)
        except Exception as e:
            pdata=data.encode(EncodingFMT)
            DbgPrint("ERROR:",str(e),MODULEDEBUGMODE=MODULEDEBUGMODE)
        
        conn.sendall(pdata)


    def rawReadPKL(self, data):
        return pickle.loads(data)

    def readPKL(self,conn):
        try:
            pdata=conn.recv(4096).decode()
            data = pickle.loads(pdata)
        except Exception as e:
            data=pdata.decode(EncodingFMT)
            DbgPrint("ERROR:",str(e),MODULEDEBUGMODE=MODULEDEBUGMODE)
                
        return data


    def toStr(self, item):
        if type(item)==str:
            return item
        elif type(item)==unicode:
            return str(item)
        else:
            return str(item)

    def rawWriteJSON(self, data):
        return json.dumps(data)


    def writeJSON(self,conn,data):
        # DbgPrint("writeJSON Called",MODULEDEBUGMODE=MODULEDEBUGMODE)
        try:
            if PYVER < 3.0:
                jdata=json.dumps(data) + DATAEndMarker.decode()
            else:
                jdata = json.dumps(data) + DATAEndMarker

            conn.sendall(jdata.encode(EncodingFMT))

        except Exception as e:
            DbgPrint("ERROR:",str(e),MODULEDEBUGMODE=MODULEDEBUGMODE)
            raise e

    def rawReadJSON(self,data):
        return json.loads(data)


    def readJSON(self,conn):
        data=None

        try:
            if jqueue.empty():
                tmp=conn.recv(4096).decode()

                if DATAEndMarker in tmp:
                    pos = 0
                    while True:
                        pos2 = tmp.find(DATAEndMarker)
                        if pos2 >=0 and pos2 > pos:
                            jdata = tmp[:pos2]
                            jqueue.put_nowait(jdata)
                            pos = pos2 + len(DATAEndMarker)
                            if pos >= len(tmp):
                                break
                        else:
                            break
                else:
                    jqueue.put_nowait(tmp)

            if not jqueue.empty():
                jdata = jqueue.get_nowait()

                try:
                    data=json.loads(jdata)
                except Exception as e:
                    data=jdata.decode(EncodingFMT)
                    DbgPrint("ERROR:",str(e),MODULEDEBUGMODE=MODULEDEBUGMODE)
        except Exception as e:
            DbgPrint(e,MODULEDEBUGMODE=MODULEDEBUGMODE)


        return data
    

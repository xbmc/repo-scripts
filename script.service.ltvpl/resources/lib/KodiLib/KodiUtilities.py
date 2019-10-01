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
from datetime import datetime, timedelta
import time
from .kodiflags import KODI_ENV
from .kodijson import Kodi, PLAYER_VIDEO
import json
from resources.lib.Utilities.DebugPrint import DbgPrint

__Version__ = "1.3.1"

def GetOE2():
    """
    :rtype Kodi
    :return:
    """
    return(Kodi("http://192.168.3.107:8080/jsonrpc"))


if KODI_ENV:
    kodiObj=Kodi('')
else:
    kodiObj=GetOE2()

KODI_OPERATION_FAILED = "Kodi Operation Failed: "
RESULT = 'result'
CHANNELID = 'channelid'
BROADCASTS = 'broadcasts'
TIMERID = 'timerid'
STARTTIME = 'starttime'
RECORDINGID = 'recordingid'
EPISODE = 'episode'
TVSHOW = 'tvshow'
LABEL = 'label'
PROPERTIES = 'properties'
BROADCASTID = 'broadcastid'
RECORDINGS = 'recordings'
CHANNEL = 'channel'
CHANNELNUMBER = 'channelnumber'
CHANNELS = 'channels'
SUBCHANNELNUMBER = 'subchannelnumber'
ITEM = 'item'
STATIONID = 'stationID'
CHANNELGROUPID = 'channelgroupid'

def getRecordings2(kodiObj,params=None):
    """
    :param kodiObj: Kodi
    :param params:
    :return: list[string]
    """
    try:
        rList = getRecordings(kodiObj, params)
        newList = []
        for item in rList:
            recordingID = item[RECORDINGID]
            details=getRecordingDetails(kodiObj, recordingID)
            newData= {RECORDINGID: recordingID, TVSHOW: details['directory'], EPISODE: item[LABEL]}
            newList.append(newData)

        tmp = sorted(newList, key=lambda item: (item[TVSHOW],item[EPISODE]))
        return(tmp)
    except:
        raise Exception(KODI_OPERATION_FAILED + "Could Not Retrieve Recordings")

    
def getRecordingDetails(kodiObj, recordingID):
    """
    :param kodiObj: Kodi
    :param recordingID:
    :return:
    """
    try:
        return(kodiObj.PVR.GetRecordingDetails({"recordingid":recordingID,\
                PROPERTIES:["plot","title","runtime","directory"]})[RESULT]['recordingdetails'])
    except:
        raise Exception(KODI_OPERATION_FAILED + "Could Not Retrieve Recording Details")


def getRecordings(kodiObj, params=None):
    """
    :param kodiObj: Kodi
    :param params:
    :return:
    """
    try:
        if params is None:
            return(kodiObj.PVR.GetRecordings()[RESULT][RECORDINGS])
        else:
            return(kodiObj.PVR.GetRecordings(params)[RESULT][RECORDINGS])
    except:
        raise Exception(KODI_OPERATION_FAILED + "Could Not Retrieve Recordings")


def getChannelGroups(kodiObj):
    """
    :param kodiObj: Kodi
    :return:
    """
    try:
        channelGroups = kodiObj.PVR.GetChannelGroups({"channeltype":"tv"})[RESULT]['channelgroups']
        groupList = [(dItem[LABEL],dItem[CHANNELGROUPID]) for dItem in channelGroups]
        return([dict(groupList)])
    except:
        raise Exception(KODI_OPERATION_FAILED + "Cannot Retrieve Channel Groups")


def processChannelNumber(channelNumber):
    """
    :param channelNumber: float
    :return: list[int,int]
    """
    t1=str(channelNumber).split('.')
    if len(t1) == 2:
        c=int(t1[0])
        s=int(t1[1])
        return([c,s])

    return([int(channelNumber), 0])

def getLastChannelInfo(kodiObj, chGroup=1):
    p1 = {CHANNELGROUPID: chGroup, PROPERTIES: [CHANNEL, CHANNELNUMBER, SUBCHANNELNUMBER]}

    d1 = [item for item in (kodiObj.PVR.GetChannels(p1)) \
        [RESULT][CHANNELS]]

    numchannels = len(d1)
    x = d1[numchannels -1]
    channel = CHANNELNUMBER, float("{}.{}".format(x[CHANNELNUMBER], x[SUBCHANNELNUMBER]))

    return dict([channel])

def getChannelInfoByChannelNumber(kodiObj,channelNumber,chGroup=1,params=None):
    """
    :param kodiObj: Kodi
    :param channelNumber: float
    :param chGroup: int
    :param params:
    :return: list
    """
    try:
        chanNums = processChannelNumber(channelNumber)
        if chanNums is not None:
            channelNumber, subChanneNumber = chanNums
            try:
                p1={CHANNELGROUPID:chGroup,\
                PROPERTIES:[CHANNEL,CHANNELNUMBER,SUBCHANNELNUMBER]}

                if params is not None:
                    p1.update(params)

                d1=[item for item in (kodiObj.PVR.GetChannels(p1))\
            [RESULT][CHANNELS]if channelNumber == item[CHANNELNUMBER]\
            and subChanneNumber == item[SUBCHANNELNUMBER]]

                z1=[((STATIONID,x[LABEL]),(CHANNELID,x[CHANNELID]),\
                     (CHANNELNUMBER,float("{}.{}".format(x[CHANNELNUMBER],
                       x[SUBCHANNELNUMBER])))) for x in d1]


                return([dict(z) for z in z1])

            except:
                d1=[item for item in (kodiObj.PVR.GetChannels({CHANNELGROUPID:chGroup,\
                PROPERTIES:[CHANNEL]}))[RESULT][CHANNELS]\
                 if channelNumber in item[CHANNELNUMBER]]

                z1=[((LABEL,x[LABEL]),(CHANNELID,x[CHANNELID])) for x in d1]
                return([dict(z) for z in z1])
        else:
            return(None)
    except:
        raise Exception(KODI_OPERATION_FAILED + "Could Not Retrieve Channel Info by Channel Number {}".format(channelNumber))


def getChannelInfoByCallSign(kodiObj,callSign,chGroup=1,params=None):
    """
    :param kodiObj: Kodi
    :param callSign: string
    :param chGroup: int
    :param params:
    :return: list
    """
    try:
        p1={CHANNELGROUPID: chGroup, PROPERTIES:[CHANNEL,CHANNELNUMBER,SUBCHANNELNUMBER]}

        if params is not None:
            p1.update(params)
        
        d1=[item for item in (kodiObj.PVR.GetChannels(p1))[RESULT][CHANNELS]\
         if callSign in item[CHANNEL]]

        z1=[((STATIONID,x[LABEL]),(CHANNELID,x[CHANNELID]),\
             (CHANNELNUMBER,float("{}.{}".format(x[CHANNELNUMBER],
               x[SUBCHANNELNUMBER])))) for x in d1]
        
        return([dict(z) for z in z1])
    
    except:
        d1=[item for item in (kodiObj.PVR.GetChannels({CHANNELGROUPID:chGroup,\
        PROPERTIES:[CHANNEL]}))[RESULT][CHANNELS]\
         if callSign in item[CHANNEL]]

        z1=[((LABEL,x[LABEL]),(CHANNELID,x[CHANNELID])) for x in d1]
        return([dict(z) for z in z1])


def getChannelInfo(kodiObj,chGroup=1,params=None):
    """
    :param kodiObj: Kodi
    :param chGroup: int
    :param params:
    :return: list
    """
    try:
        p1={CHANNELGROUPID:chGroup, PROPERTIES:[CHANNEL,CHANNELNUMBER,SUBCHANNELNUMBER]}
        
        if params is not None:
            p1.update(params)

        d1=[item for item in (kodiObj.PVR.GetChannels(p1))[RESULT][CHANNELS]]
            
        z1=[((STATIONID,x[LABEL]),(CHANNELID,x[CHANNELID]),\
             (CHANNELNUMBER,float("{}.{}".format(x[CHANNELNUMBER],
               x[SUBCHANNELNUMBER])))) for x in d1]
        
        return([dict(z) for z in z1])
    
    except Exception as e:
        d1=[item for item in (kodiObj.PVR.GetChannels({CHANNELGROUPID:chGroup,\
        PROPERTIES:[CHANNEL]}))[RESULT][CHANNELS]\
         if callSign in item[CHANNEL]]

        z1=[((LABEL,x[LABEL]),(CHANNELID,x[CHANNELID])) for x in d1]
        return([dict(z) for z in z1])
    


def getPlayerInfo(kodiObj):
    """
    :param kodiObj: Kodi
    :return:
    """
    pList = kodiObj.Player.GetActivePlayers()[RESULT]
    if len(pList) > 0:
        return(pList[0])
    else:
        return(None)
	    

def playerStop(kodiObj):
    """
    :param kodiObj: Kodi
    :return:
    """
    data=getPlayerInfo(kodiObj)
    if data is not None:
        id = data['playerid']
        kodiObj.Player.Stop({"playerid": id})
    

def changeChannelByChannelID(kodiObj, channelID):
    """
    :param kodiObj: Kodi
    :param channelID: int
    :return:
    """
    kodiObj.Player.Open({ITEM:{CHANNELID:channelID}})


def changeChannelByCallSign(kodiObj, callSign):
    """
    :param kodiObj: Kodi
    :param callSign: string
    :return:
    """
    channelInfo = getChannelInfoByCallSign(kodiObj, callSign)
    kodiObj.Player.Open({ITEM:{CHANNELID:channelInfo[0][CHANNELID]}})


def changeChannelByChannelNumber(kodiObj, channelNumber):
    """
    :param kodiObj: Kodi
    :param channelNumber: float
    :return:
    """
    channelInfo = getChannelInfoByChannelNumber(kodiObj, channelNumber)
    kodiObj.Player.Open({ITEM:{CHANNELID:channelInfo[0][CHANNELID]}})
    
def prettyPrintJSON(txt):
    data=json.dumps(txt, sort_keys=True,indent=4,separators=(',', ': '))
    print(data)


def datetime_utc_to_local(utc_datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    return utc_datetime + offset


def getChannelId(kodiObj, channel):
    info = getChannelInfoByChannelNumber(kodiObj, channel)
    channelid = info[0][CHANNELID]
    return channelid


def getBroadcastIdList(broadcasts, tvshow):
    tvshowlc = tvshow.lower()
    idlist = [broadcast[BROADCASTID] for broadcast in broadcasts if tvshowlc in broadcast[LABEL].lower()]

    return idlist

def getUtcOffset():
    offset = datetime.utcnow() - datetime.now()
    return offset

def getBroadcast_startTimeList(kodiObj, channel, tvshow):
    fmt = '%Y-%m-%d %H:%M:%S'
    startTimeList = []
    try:
        channelid = getChannelId(kodiObj, channel)
    except: startTimeList

    args = {CHANNELID: channelid}
    DbgPrint("tvshow:{}, channel:{}, args:{}".format(tvshow, channel,args))
    broadcastinfo = kodiObj.PVR.GetBroadcasts(args)
    DbgPrint("broadcastinfo:{}".format(broadcastinfo))
    broadcastidList = getBroadcastIdList(broadcastinfo[RESULT][BROADCASTS], tvshow)

    if broadcastidList is not None:
        for broadcastid in broadcastidList:
            pgminfo = kodiObj.PVR.GetBroadcastDetails({BROADCASTID: broadcastid, PROPERTIES: [STARTTIME]})
            DbgPrint("pgmInfo: {}".format(pgminfo['result']))
            starttime = datetime.strptime(pgminfo[RESULT]['broadcastdetails'][STARTTIME], fmt)
            starttime = datetime_utc_to_local(starttime)
            DbgPrint("***startTime: {}".format(starttime))
            startTimeList.append(starttime)

    return startTimeList

def getBroadcastInfo(kodiObj, channel, starttime):
    fmt = '%Y-%m-%d %H:%M:%S'
    offset = getUtcOffset()
    try:
        startTime = str(datetime.strptime(starttime, fmt) + offset)
    except: return

    channelid = getChannelId(kodiObj, channel)
    args = {CHANNELID: channelid, "properties": [STARTTIME]}
    broadcastinfo = kodiObj.PVR.GetBroadcasts(args)[RESULT][BROADCASTS]
    d1 = [x for x in broadcastinfo if x[STARTTIME] == startTime]
    if len(d1) > 0:
        d1=d1[0]
        d1[STARTTIME] = str(datetime.strptime(d1[STARTTIME], fmt) - offset)
        d1.update({CHANNEL:channel, CHANNELID:channelid})

        return d1

def addTimer(kodiObj, channel, starttime):
    broadcastinfo = getBroadcastInfo(kodiObj, channel, starttime)
    if broadcastinfo is not None and len(broadcastinfo) > 0:
        broadcastid=broadcastinfo[BROADCASTID]
        args = {BROADCASTID:broadcastid}
        result = kodiObj.PVR.AddTimer(args)[RESULT]

        return result

def getTimer(kodiObj, channelid, starttime):
    fmt = '%Y-%m-%d %H:%M:%S'
    offset = getUtcOffset()
    startTime = str(datetime.strptime(starttime, fmt) + offset)
    args = {PROPERTIES:[CHANNELID,STARTTIME]}
    result = kodiObj.PVR.GetTimers(args)[RESULT]['timers']
    d1 = [x for x in result if x[CHANNELID]==channelid and x[STARTTIME]== startTime]

    if len(d1)> 0:
        return d1[0]


def deleteTime(kodiObj, channelid,starttime):
    timer = getTimer(kodiObj, channelid, starttime)
    if timer is not None and len(timer)> 0:
        args = {TIMERID:timer[TIMERID]}
        result = kodiObj.PVR.DeleteTimer(args)

        return result[RESULT]


def TvGuideIsPresent(kodiObj, channel):
    try:
        channelid = getChannelId(kodiObj, channel)
        args = {CHANNELID: channelid}
        broadcastinfo = kodiObj.PVR.GetBroadcasts(args)
        DbgPrint("broadcastinfo:{}".format(broadcastinfo))
        broadcastdata = broadcastinfo[RESULT][BROADCASTS]
        if len(broadcastdata) > 0 and type(broadcastdata[0][BROADCASTID]) == int:
            return True
    except: pass

    return False


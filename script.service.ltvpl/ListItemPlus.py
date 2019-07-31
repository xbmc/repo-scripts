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
import locale

__Version__ = "1.1.0"

locale.setlocale(locale.LC_ALL, '')
import copy
import xbmc
import xbmcgui
from utility import myLog
from resources.lib.Utilities.DebugPrint import DbgPrint
#

def strTimeStamp(tData, dataformat="{:%m/%d/%Y}"):
    """
    :type alarmtime: datetime
    :return: tuple(strDate, strTime)
    """
    try:
        strDate = dataformat.format(tData)
        fmt = xbmc.getRegion('time')
        fmt = fmt.replace(':%S', '')
        strTime = "{:" + fmt + "}"
        DbgPrint("***strTime: {}".format(strTime))
        strTime = strTime.format(tData)
    except:
        strDate = strTime = ''

    return (strDate, strTime)

def strDate2TimeStamp(tdata, fmt):
    import time
    ts=datetime (* (time.strptime (tdata, fmt) [0: 6]))
    return ts


class ListItemPlus(xbmcgui.ListItem):
    hdrs = ['alarmtime'   ,'ch'   , 'expiryDate'   , 'id'   , 'recurrenceInterval', 'suspendedFlag', 'title']
    tags = ['alarmtime'   ,'Ch'   , 'Expires'      , 'ID'   , 'Frequency'         , 'suspendedFlag', 'Description']
    dtags = ['Date', 'Time', 'Expires']


    def __new__(cls, other=None, dateformat="%m/%d/%Y", *args, **kwargs):
        if other is not None:
            obj = super(ListItemPlus, cls).__new__(cls, *args, **kwargs)
            if isinstance(other, xbmcgui.ListItem):
                for tag in ListItemPlus.tags:
                    obj.setProperty(tag, other.getProperty(tag))

                for dtag in ListItemPlus.dtags:
                    obj.setProperty(dtag, other.getProperty(dtag))
            return obj
        else:
            return super(ListItemPlus, cls).__new__(cls, *args, **kwargs)


    def __init__(self,other=None, dateformat="%m/%d/%Y", *args, **kwargs):
        super(ListItemPlus, self).__init__(*args, **kwargs)
        self.dateformat = dateformat


    @property
    def Data(self):
        values={}

        for tag in self.tags:
            try:
                tmp = dict([(tag,self.getProperty(tag))])
                DbgPrint("***tmp:{}".format(tmp))
                values.update(tmp)
                DbgPrint("values:{}".format(values))
            except: pass

        for tag in self.dtags:
            tmp = dict([(tag,self.getProperty(tag))])
            values.update(tmp)

        return values

    @Data.setter
    def Data(self, values):
        DESC='Description'
        SF = 'suspendedFlag'
        #
        DbgPrint("Data.Setter Input Values:{}".format(values))
        try:
            keys = copy.copy(values.keys())
            keys.sort()
            for n, key in enumerate(keys):
                if key not in self.dtags:
                    myLog("****key:{} value:{}".format(key,values[key]))
                    self.setProperty(self.tags[n], str(values[key]))

            if values[SF] == 'True':
                self.setProperty(DESC, "*" + values[DESC])

            alarmtime = strDate2TimeStamp(values['alarmtime'], "%Y-%m-%d %H:%M:%S")
            dateformat = "{:" + self.dateformat + "}"
            strDate, strTime = strTimeStamp(alarmtime, dataformat=dateformat)
            self.setProperty('Date',strDate)
            self.setProperty('Time', strTime)
            # self.setInfo('video',{'date':values['alarmtime']})

            if 'expiryDate' in values and  values['expiryDate'] is not None:
                expiryDate = strDate2TimeStamp(values['expiryDate'], "%Y-%m-%d %H:%M:%S")
                strDate, _ = strTimeStamp(expiryDate)
            elif 'Expires' in values and values['Expires'] is not None:
                expiryDate = strDate2TimeStamp(values['Expires'], "%Y-%m-%d %H:%M:%S")
                strDate, _ = strTimeStamp(expiryDate)
            else:
                strDate = ''

            DbgPrint("Expiry Date:{}".format(strDate))
            self.setProperty('Expires', strDate)

        except Exception as e:
            #
            DbgPrint("Data.Setter Error:{}".format(str(e)))
            pass
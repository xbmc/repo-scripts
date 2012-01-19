#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
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
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import datetime
import os
import xbmc
import xbmcgui

from strings import *
from sqlite3 import dbapi2 as sqlite3

class Notification(object):
    NOTIFICATION_DB = 'notification.db'

    def __init__(self, source, addonPath, dataPath):
        self.source = source
        self.addonPath = addonPath
        self.icon = os.path.join(self.addonPath, 'icon.png')

        self.conn = sqlite3.connect(os.path.join(dataPath, self.NOTIFICATION_DB), check_same_thread = False)
        self._createTables()

    def __del__(self):
        self.conn.close()

    def createAlarmClockName(self, program):
        return 'tvguide-%s-%s' % (program.channel.id, program.startDate)

    def scheduleNotifications(self):
        print "[script.tvguide] Scheduling program notifications"
        for channelId, programTitle in self.getPrograms():
            self._processSingleNotification(channelId, programTitle, self._scheduleNotification)

    def _processSingleNotification(self, channelId, programTitle, action):
        now = datetime.datetime.now()
        for channel in self.source.getChannelList():
            for program in self.source.getProgramList(channel, now):
                if channelId == channel.id and programTitle == program.title and self._timeToNotification(program).days in [0,1]:
                    action(program)

    def _scheduleNotification(self, program):
        timeToNotification = self._timeToNotification(program).seconds / 60
        if timeToNotification < 0:
            return

        name = self.createAlarmClockName(program)
        description = strings(NOTIFICATION_TEMPLATE, program.channel.title)

        xbmc.executebuiltin('AlarmClock(%s,Notification(%s,%s,10000,%s),%d,True)' %
            (name.encode('utf-8', 'replace'), program.title.encode('utf-8', 'replace'), description.encode('utf-8', 'replace'), self.icon, timeToNotification - 5))

    def _unscheduleNotification(self, program):
        name = self.createAlarmClockName(program)
        xbmc.executebuiltin('CancelAlarm(%s,True)' % name)

    def _timeToNotification(self, program):
        return program.startDate - datetime.datetime.now()

    def addProgram(self, program):
        """
        @type program: source.program
        """
        c = self.conn.cursor()
        c.execute("INSERT INTO notification(channel, program) VALUES(?, ?)", [program.channel.id, program.title])
        self.conn.commit()
        c.close()

        self._processSingleNotification(program.channel.id, program.title, self._scheduleNotification)

    def delProgram(self, program):
        """
        @type program: source.program
        """
        c = self.conn.cursor()
        c.execute("DELETE FROM notification WHERE channel=? AND program=?", [program.channel.id, program.title])
        self.conn.commit()
        c.close()

        self._processSingleNotification(program.channel.id, program.title, self._unscheduleNotification)


    def getPrograms(self):
        c = self.conn.cursor()
        c.execute("SELECT DISTINCT channel, program FROM notification")
        programs = c.fetchall()
        c.close()

        return programs

    def isNotificationRequiredForProgram(self, program):
        """
        @type program: source.program
        """
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM notification WHERE channel=? AND program=?", [program.channel.id, program.title])
        result = c.fetchone()
        c.close()

        return result

    def clearAllNotifications(self):
        c = self.conn.cursor()
        c.execute('DELETE FROM notification')
        self.conn.commit()
        c.close()

    def _createTables(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS notification (channel TEXT, program TEXT)")
        c.close()


if __name__ == '__main__':
    ADDON = xbmcaddon.Addon(id = 'script.tvguide')
    dataPath = xbmc.translatePath(ADDON.getAddonInfo('profile'))
    n = Notification(None, ADDON.getAddonInfo('path'), dataPath)
    n.clearAllNotifications()

    xbmcgui.Dialog().ok(strings(CLEAR_NOTIFICATIONS), strings(DONE))

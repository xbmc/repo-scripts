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

class Notification(object):
    def __init__(self, source, addonPath):
        self.source = source
        self.addonPath = addonPath
        self.icon = os.path.join(self.addonPath, 'icon.png')

        # reuse conn for now todo less hacky
        self.conn = self.source.conn

    def createAlarmClockName(self, programTitle, startTime):
        return 'tvguide-%s-%s' % (programTitle, startTime)

    def scheduleNotifications(self):
        xbmc.log("[script.tvguide] Scheduling notifications")
        for channelTitle, programTitle, startTime in self.getAllNotifications():
            self._scheduleNotification(channelTitle, programTitle, startTime)

    def _scheduleNotification(self, channelTitle, programTitle, startTime):
        t = startTime - datetime.datetime.now()
        timeToNotification = ((t.days * 86400) + t.seconds) / 60
        if timeToNotification < 0:
            return

        name = self.createAlarmClockName(programTitle, startTime)

        description = strings(NOTIFICATION_5_MINS, channelTitle)
        xbmc.executebuiltin('AlarmClock(%s-5mins,Notification(%s,%s,10000,%s),%d,True)' %
            (name.encode('utf-8', 'replace'), programTitle.encode('utf-8', 'replace'), description.encode('utf-8', 'replace'), self.icon, timeToNotification - 5))

        description = strings(NOTIFICATION_NOW, channelTitle)
        xbmc.executebuiltin('AlarmClock(%s-now,Notification(%s,%s,10000,%s),%d,True)' %
                            (name.encode('utf-8', 'replace'), programTitle.encode('utf-8', 'replace'), description.encode('utf-8', 'replace'), self.icon, timeToNotification))

    def _unscheduleNotification(self, programTitle, startTime):
        name = self.createAlarmClockName(programTitle, startTime)
        xbmc.executebuiltin('CancelAlarm(%s-5mins,True)' % name.encode('utf-8', 'replace'))
        xbmc.executebuiltin('CancelAlarm(%s-now,True)' % name.encode('utf-8', 'replace'))

    def addProgram(self, program):
        """
        @type program: source.program
        """
        c = self.conn.cursor()
        c.execute("INSERT INTO notifications(channel, program_title, source) VALUES(?, ?, ?)", [program.channel.id, program.title, self.source.KEY])
        self.conn.commit()
        c.close()

        self._scheduleNotification(program.channel.title, program.title, program.startDate)

    def delProgram(self, program):
        """
        @type program: source.program
        """
        c = self.conn.cursor()
        c.execute("DELETE FROM notifications WHERE channel=? AND program_title=? AND source=?", [program.channel.id, program.title, self.source.KEY])
        self.conn.commit()
        c.close()

        self._unscheduleNotification(program.title, program.startDate)


    def getAllNotifications(self, daysLimit = 2):
        start = datetime.datetime.now()
        end = start + datetime.timedelta(days = daysLimit)
        c = self.conn.cursor()
        c.execute("SELECT DISTINCT c.title, p.title, p.start_date FROM notifications n, channels c, programs p WHERE n.channel = c.id AND p.channel = c.id AND n.program_title = p.title AND n.source=? AND p.start_date >= ? AND p.end_date <= ?", [self.source.KEY, start, end])
        programs = c.fetchall()
        c.close()

        return programs

    def isNotificationRequiredForProgram(self, program):
        """
        @type program: source.program
        """
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM notifications WHERE channel=? AND program_title=? AND source=?", [program.channel.id, program.title, self.source.KEY])
        result = c.fetchone()
        c.close()

        return result

    def clearAllNotifications(self):
        c = self.conn.cursor()
        c.execute('DELETE FROM notifications')
        self.conn.commit()
        c.close()


if __name__ == '__main__':
    ADDON = xbmcaddon.Addon(id = 'script.tvguide')
    n = Notification(None, ADDON.getAddonInfo('path'))
    n.clearAllNotifications()

    xbmcgui.Dialog().ok(strings(CLEAR_NOTIFICATIONS), strings(DONE))

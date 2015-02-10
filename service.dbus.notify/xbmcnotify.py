'''
    D-Bus notification service for XBMC
    Copyright (C) 2011-2013 Team XBMC
    
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

import xbmc
import dbus

try:
  from gi.repository import Notify
except ImportError:
  Notify = None

class Service(xbmc.Player):
  def __init__(self):
    xbmc.Player.__init__(self)

    if Notify is None:
      self.bus = dbus.SessionBus(private=True)
      self.notify = self.bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
      self.notify = dbus.Interface(self.notify, "org.freedesktop.Notifications")
      self.notifyid = 0
    else:
      Notify.init("XBMC Notifier")

  def onPlayBackStarted(self):
    xbmc.sleep(100)
    if self.isPlaying():
      self.showNotification()

  def onSkipNext(self, notification=None, action=None, data=None):
    self.playnext()

  def showNotification(self):
    if self.isPlayingAudio():
      icon    = "file://%s" % xbmc.translatePath(xbmc.getInfoImage("MusicPlayer.Cover"))
      summary = xbmc.getInfoLabel("MusicPlayer.Artist")
      body    = xbmc.getInfoLabel("MusicPlayer.Title") + "\n" + xbmc.getInfoLabel("MusicPlayer.Album")
    elif self.isPlayingVideo():
      icon    = "file://%s" % xbmc.translatePath(xbmc.getInfoImage("VideoPlayer.Cover"))
      summary = xbmc.getInfoLabel("VideoPlayer.Title")
      body    = xbmc.getInfoLabel("VideoPlayer.Genre")
    else:
      return False

    if not xbmc.getCondVisibility("System.IsFullScreen"):
      if Notify is None:
        self.notifyid = self.notify.Notify("XBMC Media Center", self.notifyid, icon, summary, body, [], {}, 5000)
      else:
        self.notify = Notify.Notification.new(summary, body, icon)
        self.notify.add_action("playnext", 'Skip this item', self.onSkipNext, None, None)
        self.notify.show()

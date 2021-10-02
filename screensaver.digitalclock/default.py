#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Vojislav Vlasic
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import xbmcaddon
import xbmcgui
import xbmc
import xbmcvfs
import random
import os
from datetime import datetime

Addon = xbmcaddon.Addon('screensaver.digitalclock')
path = Addon.getAddonInfo('path')
location = xbmc.getSkinDir()
scriptname = location + '.xml'
Addonversion = Addon.getAddonInfo('version')

class Screensaver(xbmcgui.WindowXMLDialog):

	#setting up zoom
    window = xbmcgui.Window(12900)
    window.setProperty("zoomamount",Addon.getSetting('zoomlevel'))
    del window

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        xbmc.log('Digital Clock Screensaver %s: Initialising' %Addonversion)
        self.abort_requested = False
        self.started = False
        self.exit_monitor = self.ExitMonitor(self.exit)
        self.date_control = self.getControl(30100)
        self.hour_control = self.getControl(30101)
        self.colon_control = self.getControl(30102)
        self.minute_control = self.getControl(30103)
        self.ampm_control = self.getControl(30104)
        self.information_control = self.getControl(30110)
        self.container = self.getControl(30002)
        self.image_control = self.getControl(30020)
        self.image_control2 = self.getControl(30022)
        self.icon_control = self.getControl(30021)
        self.rss_control = self.getControl(30023)
        self.hour_colorcontrol = self.getControl(30105)
        self.colon_colorcontrol = self.getControl(30106)
        self.minute_colorcontrol = self.getControl(30107)
        self.ampm_colorcontrol = self.getControl(30108)
        self.date_colorcontrol = self.getControl(30109)
        self.information_colorcontrol = self.getControl(30111)
        self.shadow_colorcontrol = self.getControl(30112)
        self.waitcounter = 0
        self.switchcounter = 0
        self.iconswitchcounter = 0
        self.logoutcounter = 0
        self.switch = 0
        self.iconswitch = 0
        self.movementtype = int(Addon.getSetting('movementtype'))
        self.movementspeed = int(Addon.getSetting('movementspeed'))
        self.stayinplace = int(Addon.getSetting('stayinplace'))
        self.datef = Addon.getSetting('dateformat')
        self.customdateformat = Addon.getSetting('customdateformat')
        self.colonblink = Addon.getSetting('colonblink')
        self.timef = Addon.getSetting('timeformat')
        self.ampm_control.setVisible(False)
        self.informationshow = Addon.getSetting('additionalinformation')
        self.nowplayinginfoshow = Addon.getSetting('nowplayinginfoshow')
        self.combinesonginfo = Addon.getSetting('combinesonginfo')
        self.showonlynowplaying = Addon.getSetting('showonlynowplaying')
        self.cpuusage = Addon.getSetting('cpuusage')
        self.batterylevel = Addon.getSetting('batterylevel')
        self.freememory = Addon.getSetting('freememory')
        self.cputemp = Addon.getSetting('cputemp')
        self.gputemp = Addon.getSetting('gputemp')
        self.hddtemp = Addon.getSetting('hddtemp')
        self.fps = Addon.getSetting('fps')
        self.cuptime = Addon.getSetting('cuptime')
        self.tuptime = Addon.getSetting('tuptime')
        self.movies = Addon.getSetting('movies')
        self.tvshows = Addon.getSetting('tvshows')
        self.music = Addon.getSetting('music')
        self.weatherinfoshow = Addon.getSetting('weatherinfoshow')
        self.albumartshow = Addon.getSetting('albumartshow')
        self.weathericonf = Addon.getSetting('weathericonformat')
        self.infoswitch = int(Addon.getSetting('infoswitch'))
        self.aspectratio = int(Addon.getSetting('aspectratio'))
        self.background = Addon.getSetting('backgroundchoice')
        self.randomimages = Addon.getSetting('randomimages')
        self.skinhelper = int(Addon.getSetting('skinhelper'))
        self.dimlevel = int(Addon.getSetting('dimlevel'))
        self.hourcolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.hourcolor)")
        self.coloncolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.coloncolor)")
        self.minutecolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.minutecolor)")
        self.ampmcolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.ampmcolor)")
        self.datecolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.datecolor)")
        self.informationcolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.informationcolor)")
        self.iconcolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.iconcolor)")
        self.shadowcolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.shadowcolor)")
        self.backgroundcolor = xbmc.getInfoLabel("Skin.String(screensaver.digitalclock.backgroundcolor)")
        self.trh = Addon.getSetting('hourtr')
        self.trc = Addon.getSetting('colontr')
        self.trm = Addon.getSetting('minutetr')
        self.trampm = Addon.getSetting('ampmtr')
        self.trd = Addon.getSetting('datetr')
        self.tri = Addon.getSetting('informationtr')
        self.trw = Addon.getSetting('icontr')
        self.ch = Addon.getSetting('hourcolor')
        self.cc = Addon.getSetting('coloncolor')
        self.cm = Addon.getSetting('minutecolor')
        self.campm = Addon.getSetting('ampmcolor')
        self.cd = Addon.getSetting('datecolor')
        self.ci = Addon.getSetting('informationcolor')
        self.cw = Addon.getSetting('iconcolor')
        self.zoom = float(Addon.getSetting('zoomlevel'))
        self.logout = Addon.getSetting('logout')
        self.logoutplaying = Addon.getSetting('logoutplaying')
        self.logouttime = int(Addon.getSetting('logouttime'))
        self.rss = Addon.getSetting('rss')
        self.monitor = xbmc.Monitor()

		#setting up colors if they haven't been set up in settings
        if not(self.backgroundcolor):
             self.backgroundcolor = 'FF000000'
        if not(self.shadowcolor):
             self.shadowcolor = '00000000'
        if not(self.hourcolor):
             self.hourcolor = 'FFFFFFFF'
        if not(self.coloncolor):
             self.coloncolor = 'FFFFFFFF'
        if not(self.minutecolor):
             self.minutecolor = 'FFFFFFFF'
        if not(self.ampmcolor):
             self.ampmcolor = 'FFFFFFFF'
        if not(self.datecolor):
             self.datecolor = 'FFFFFFFF'
        if not(self.informationcolor):
             self.informationcolor = 'FFFFFFFF'
        if not(self.iconcolor):
             self.iconcolor = 'FFFFFFFF'

        #setting up aspect ratio
        if self.aspectratio == 0:
            self.image_control2.setVisible(False)
        if self.aspectratio == 1:
            self.image_control.setVisible(False)

		#setting up background and slideshow
        self.timer = ['15','30','60','120','180','240','300','360','420','480','540','600']
        self.dim = ['00000000' ,'03000000','05000000','08000000','0A000000','0D000000','0F000000','12000000','14000000','17000000','1A000000','1C000000','1F000000','21000000','24000000','26000000','29000000','2B000000','2E000000','30000000','33000000','36000000','38000000','3B000000','3D000000','40000000','42000000','45000000','47000000','4A000000','4D000000','4F000000','52000000','54000000','57000000','59000000','5C000000','5E000000','61000000','63000000','66000000','69000000','6B000000','6E000000','70000000','73000000','75000000','78000000','7A000000','7D000000','80000000','82000000','85000000','87000000','8A000000','8C000000','8F000000','91000000','94000000','96000000','99000000','9C000000','9E000000','A1000000','A3000000','A6000000','A8000000','AB000000','AD000000','B0000000','B3000000','B5000000','B8000000','BA000000','BD000000','BF000000','C2000000','C4000000','C7000000','C9000000','CC000000','CF000000','D1000000','D4000000','D6000000','D9000000','DB000000','DE000000','E0000000','E3000000','E6000000','E8000000','EB000000','ED000000','F0000000','F2000000','F5000000','F7000000','FA000000','FC000000','FF000000']
        self.slideshowcounter = 0
        if self.background == '0':
            self.image_control.setImage(os.path.join(path,"resources/media/white.png"))
            self.image_control.setColorDiffuse(self.backgroundcolor)
            self.image_control2.setImage(os.path.join(path,"resources/media/white.png"))
            self.image_control2.setColorDiffuse(self.backgroundcolor)
        elif self.background == '4':
            self.image_control.setImage(os.path.join(path,"resources/media/white.png"))
            self.image_control.setColorDiffuse(self.dim[self.dimlevel])
            self.image_control2.setImage(os.path.join(path,"resources/media/white.png"))
            self.image_control2.setColorDiffuse(self.dim[self.dimlevel])
        elif self.background == '1':
            self.image_control.setImage(Addon.getSetting('file'))
            self.image_control2.setImage(Addon.getSetting('file'))
        elif self.background == '2':
            self.folder = Addon.getSetting('folder')
            self.imagetimer = int(self.timer[int(Addon.getSetting('imagetimer'))])
            self.files = os.walk(self.folder).__next__()[2]
            self.number = len(self.files)-1
            self.files.sort()
            self.nextfile = 0
            if self.randomimages =='true':
                self.nextfile = random.randint(0,self.number)
            self.path = self.folder + self.files[self.nextfile]
            self.nextfile += 1
            if self.nextfile > self.number:
                self.nextfile = 0
            self.image_control.setImage(self.path)
            self.image_control2.setImage(self.path)
        else:
            self.imagetimer = int(self.timer[int(Addon.getSetting('imagetimer'))])
            xbmc.executebuiltin('Skin.SetString(SkinHelper.RandomFanartDelay,%s)' %self.imagetimer)
            if self.skinhelper == 0:
                self.skinhelperimage = "$INFO[Window(Home).Property(SkinHelper.AllMoviesBackground)]"
            elif self.skinhelper == 1:
                self.skinhelperimage = "$INFO[Window(Home).Property(SkinHelper.AllTvShowsBackground)]"
            elif self.skinhelper == 2:
                self.skinhelperimage = "$INFO[Window(Home).Property(SkinHelper.AllMusicBackground)]"
            else:
                self.skinhelperimage = "$INFO[Window(Home).Property(SkinHelper.GlobalFanartBackground)]"
            self.image_control.setImage(xbmc.getInfoLabel(self.skinhelperimage))
            self.image_control2.setImage(xbmc.getInfoLabel(self.skinhelperimage))

		#setting up shadow color
        self.shadow_colorcontrol.setLabel(self.shadowcolor)

        #setting up information
        self.informationlist = []
        if self.informationshow == 'true':
            if self.nowplayinginfoshow == 'true':
                if xbmc.getInfoLabel('MusicPlayer.Artist') or xbmc.getInfoLabel('MusicPlayer.Title'):
                    if self.combinesonginfo == 'true':
                        self.informationlist.append('$INFO[MusicPlayer.Artist] - $INFO[MusicPlayer.Title]')
                    else:
                        self.informationlist.append('$INFO[MusicPlayer.Artist]')
                        self.informationlist.append('$INFO[MusicPlayer.Title]')
                if xbmc.getInfoLabel('VideoPlayer.TVShowTitle'):
                    self.informationlist.append('$INFO[VideoPlayer.TVShowTitle]')
                if xbmc.getInfoLabel('VideoPlayer.Title'):
                    self.informationlist.append('$INFO[VideoPlayer.Title]')
            if self.weatherinfoshow == 'true' and xbmc.getInfoLabel('Weather.Location'):
                self.informationlist.append("$INFO[Weather.Temperature] - $INFO[Weather.Conditions]")
            if self.cpuusage == 'true' and xbmc.getInfoLabel('System.CpuUsage'):
                self.corenumber = xbmc.getInfoLabel('System.CpuUsage').count('%')
                if self.corenumber == 1:
                    self.informationlist.append("$ADDON[screensaver.digitalclock 32280] $INFO[System.CoreUsage(0)]%")
                if self.corenumber == 2:
                    self.informationlist.append("$ADDON[screensaver.digitalclock 32280] $INFO[System.CoreUsage(0)]% $INFO[System.CoreUsage(1)]%")
                if self.corenumber == 4:
                    self.informationlist.append("$ADDON[screensaver.digitalclock 32280] $INFO[System.CoreUsage(0)]% $INFO[System.CoreUsage(1)]% $INFO[System.CoreUsage(2)]% $INFO[System.CoreUsage(3)]%")
                if self.corenumber == 8:
                    self.informationlist.append("$ADDON[screensaver.digitalclock 32280] $INFO[System.CoreUsage(0)]% $INFO[System.CoreUsage(1)]% $INFO[System.CoreUsage(2)]% $INFO[System.CoreUsage(3)]%")
                    self.informationlist.append("$ADDON[screensaver.digitalclock 32280] $INFO[System.CoreUsage(4)]% $INFO[System.CoreUsage(5)]% $INFO[System.CoreUsage(6)]% $INFO[System.CoreUsage(7)]%")
            if self.batterylevel == 'true' and xbmc.getInfoLabel('System.BatteryLevel'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32281] $INFO[System.BatteryLevel]")
            if self.freememory == 'true' and xbmc.getInfoLabel('System.FreeMemory'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32282] $INFO[System.FreeMemory] ($INFO[System.Memory(free.percent)])")
            if self.cputemp == 'true' and xbmc.getInfoLabel('System.CPUTemperature'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32295] $INFO[System.CPUTemperature]")
            if self.gputemp == 'true' and xbmc.getInfoLabel('System.GPUTemperature'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32296] $INFO[System.GPUTemperature]")
            if self.hddtemp == 'true' and xbmc.getInfoLabel('System.HddTemperature'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32297] $INFO[System.HddTemperature]")
            if self.fps == 'true' and xbmc.getInfoLabel('System.FPS'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32298] $INFO[System.FPS]")
            if self.cuptime == 'true' and xbmc.getInfoLabel('System.Uptime'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32299] $INFO[System.Uptime]")
            if self.tuptime == 'true' and xbmc.getInfoLabel('System.TotalUptime'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32300] $INFO[System.TotalUptime]")
            if self.movies == 'true' and xbmc.getInfoLabel('Window(Home).Property(Movies.Count)'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32283] $INFO[Window(Home).Property(Movies.Count)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32284] $INFO[Window(Home).Property(Movies.Watched)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32285] $INFO[Window(Home).Property(Movies.UnWatched)]")
            if self.tvshows == 'true' and xbmc.getInfoLabel('Window(Home).Property(TVShows.Count)'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32286] $INFO[Window(Home).Property(TVShows.Count)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32287] $INFO[Window(Home).Property(Episodes.Count)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32288] $INFO[Window(Home).Property(TVShows.Watched)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32289] $INFO[Window(Home).Property(Episodes.Watched)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32290] $INFO[Window(Home).Property(TVShows.UnWatched)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32291] $INFO[Window(Home).Property(Episodes.UnWatched)]")
            if self.music == 'true' and xbmc.getInfoLabel('Window(Home).Property(Music.SongsCount)'):
                self.informationlist.append("$ADDON[screensaver.digitalclock 32292] $INFO[Window(Home).Property(Music.ArtistsCount)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32293] $INFO[Window(Home).Property(Music.AlbumsCount)]")
                self.informationlist.append("$ADDON[screensaver.digitalclock 32294] $INFO[Window(Home).Property(Music.SongsCount)]")
            if len(self.informationlist) != 0:
                self.information = self.informationlist[0]

		#setting up the date format and positions
        self.dateformat = ['Hide date','$INFO[System.Date(DDD dd. MMM yyyy)]','$INFO[System.Date(dd.mm.yyyy)]','$INFO[System.Date(mm.dd.yyyy)]']
        if self.datef == '0' and not(self.combinesonginfo == 'false' and self.showonlynowplaying == 'true' and self.nowplayinginfoshow == 'true' and xbmc.getInfoLabel('MusicPlayer.Artist')):
            self.date_control.setVisible(False)
            if self.informationshow == 'true':
                if len(self.informationlist) != 0:
                    self.information_control.setPosition(0, 85)
                    if ((self.weatherinfoshow == 'true' and self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')) or (self.nowplayinginfoshow == 'true' and self.albumartshow =='true' and xbmc.getInfoLabel('MusicPlayer.Artist'))):
                        self.icon_control.setPosition(115, 120)
                        self.container.setHeight(int(240 + 30 * (self.zoom / 100 - 1)))
                    else:
                        self.container.setHeight(int(150 + 50 * (self.zoom / 100 - 1)))
                        self.icon_control.setVisible(False)
                else:
                    if ((self.weatherinfoshow == 'true' and self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')) or (self.nowplayinginfoshow == 'true' and self.albumartshow =='true' and xbmc.getInfoLabel('MusicPlayer.Artist'))):
                        self.icon_control.setPosition(115, 90)
                        self.container.setHeight(int(210 + 50 * (self.zoom / 100 - 1)))
                    else:
                        self.container.setHeight(int(90 + 110 * (self.zoom / 100 - 1)))
                        self.icon_control.setVisible(False)
                    self.information_control.setVisible(False)
            else:
                self.container.setHeight(int(100 + 110 * (self.zoom / 100 - 1)))
                self.icon_control.setVisible(False)
                self.information_control.setVisible(False)
        else:
            if self.informationshow == 'true':
                if len(self.informationlist) != 0:
                    if not((self.weatherinfoshow == 'true' and self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')) or (self.nowplayinginfoshow == 'true' and self.albumartshow =='true' and xbmc.getInfoLabel('MusicPlayer.Artist'))):
                        self.container.setHeight(int(180 + 50 * (self.zoom / 100 - 1)))
                        self.icon_control.setVisible(False)
                else:
                    if ((self.weatherinfoshow == 'true' and self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')) or (self.nowplayinginfoshow == 'true' and self.albumartshow =='true' and xbmc.getInfoLabel('MusicPlayer.Artist'))):
                        self.icon_control.setPosition(115, 120)
                        self.container.setHeight(int(240 + 30 * (self.zoom / 100 - 1)))
                    else:
                        self.container.setHeight(int(140 + 50 * (self.zoom / 100 - 1)))
                        self.icon_control.setVisible(False)
                    self.information_control.setVisible(False)
            else:
                self.container.setHeight(int(150 + 50 * (self.zoom / 100 - 1)))
                self.icon_control.setVisible(False)
                self.information_control.setVisible(False)

		#setting up custom format
        if int(self.datef) == 4:
            self.date = ('$INFO[System.Date(%s)]' %self.customdateformat)
        else:
            self.date = self.dateformat[int(self.datef)]

		#setting weather icon set
        self.weathericonset = ['Hide weather icon','set1','set2','set3','set4']

		#setting the icon image
        if self.nowplayinginfoshow == 'true' and self.albumartshow == 'true' and (xbmc.getInfoLabel('MusicPlayer.Artist') or xbmc.getInfoLabel('MusicPlayer.Title')):
            self.icon = xbmc.getInfoLabel('Player.art(thumb)')
        elif self.weatherinfoshow == 'true' and self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location'):
            self.icon = os.path.join(path,"resources/weathericons/",self.weathericonset[int(self.weathericonf)],xbmc.getInfoLabel('Window(Weather).Property(Current.FanartCode)')) + ".png"
        else:
            self.icon_control.setImage(os.path.join(path,"resources/weathericons/",self.weathericonset[int(self.weathericonf)],xbmc.getInfoLabel('Window(Weather).Property(Current.FanartCode)')) + ".png")

		#setting up the time format
        self.timeformat = ['%H','%I','%I','%#I','%#I','%-I','%-I']
        if self.timef == '2' or self.timef == '4' or self.timef == '6':
           self.ampm_control.setVisible(True)
        self.time = self.timeformat[int(self.timef)]

		#setting up movement type and wait timer
        if self.movementtype == 0:
            self.waittimer = 0.5
            self.multiplier = 2
        elif self.movementtype == 1:
            self.waittimer = 0.02
            self.multiplier = 50
            self.dx = random.choice([-(self.movementspeed+1),(self.movementspeed+1)])
            self.dy = random.choice([-(self.movementspeed+1),(self.movementspeed+1)])
        elif self.movementtype == 3:
            self.waittimer = 0.5
            self.multiplier = 2
            self.container.setPosition(int(Addon.getSetting('customx')),int(Addon.getSetting('customy')))
        else:
            self.waittimer = 0.5
            self.multiplier = 2

		#setting up RSS
        if self.rss == 'false':
            self.rss_control.setVisible(False)

		#setting up the screen size
        self.height = self.container.getHeight()
        self.width = self.container.getWidth()
        if self.rss == 'false':
            self.screenye = int(720 + 120 * (self.zoom / 100 - 1) - self.height * self.zoom / 100)
            self.screenys = int(280 * (self.zoom / 100 - 1) - 18 * (self.zoom / 100 - 1))
            self.screenxe = int(1280 - self.width * self.zoom / 100)
            self.screenxs = int(360 * (self.zoom / 100 - 1))
        else:
            self.screenye = int(680 + 120 * (self.zoom / 100 - 1) - self.height * self.zoom / 100)
            self.screenys = int(280 * (self.zoom / 100 - 1) - 18 * (self.zoom / 100 - 1))
            self.screenxe = int(1280 - self.width * self.zoom / 100)
            self.screenxs = int(360 * (self.zoom / 100 - 1))		
		
		#combining transparency and color
        self.setCTR()
        self.Display()

        self.DisplayTime()

    def DisplayTime(self):
        while not self.abort_requested:

            #switching information
            self.Switch()

			#movement
            if self.movementtype == 0:
                #random movement
                self.waitcounter += 1
                if self.waitcounter >= (self.multiplier*self.stayinplace):
                    new_x = random.randint(self.screenxs,self.screenxe)
                    new_y = random.randint(self.screenys,self.screenye)
                    self.container.setPosition(new_x,new_y)
                    self.waitcounter = 0
                    self.setCTR()
            elif self.movementtype == 1:
                #bounce
                self.currentposition = self.container.getPosition()
                new_x = self.currentposition[0] + self.dx
                new_y = self.currentposition[1] + self.dy
                if new_x >= self.screenxe or new_x <= self.screenxs:
                    self.dx = self.dx*-1
                    new_x = self.currentposition[0] + self.dx
                    self.setCTR()
                if new_y >= self.screenye or new_y <= self.screenys:
                    self.dy = self.dy*-1
                    new_y = self.currentposition[1] + self.dy
                    self.setCTR()
                self.container.setPosition(new_x,new_y)

		    #display time
            self.Display()

			#slideshow
            if self.background == '2':
                self.slideshowcounter +=1
                if self.slideshowcounter >= (self.multiplier*self.imagetimer):
                    if self.randomimages =='true':
                        self.nextfile = random.randint(0,self.number)
                    self.path = self.folder + self.files[self.nextfile]
                    self.image_control.setImage(self.path)
                    self.image_control2.setImage(self.path)
                    self.nextfile +=1
                    self.slideshowcounter = 0
                    if self.nextfile > self.number:
                        self.nextfile = 0

			#skin helper
            if self.background == '3':
                self.slideshowcounter +=1
                if self.slideshowcounter >= (self.multiplier*self.imagetimer):
                    self.image_control.setImage(xbmc.getInfoLabel(self.skinhelperimage))
                    self.image_control2.setImage(xbmc.getInfoLabel(self.skinhelperimage))
                    self.slideshowcounter = 0

			#colon blink
            if self.colonblink == 'true':
                if datetime.now().second%2==0:
                    self.colon_control.setVisible(True)
                else:
                    self.colon_control.setVisible(False)
            else:
                self.colon_control.setVisible(True)

			#log out
            if self.logout == 'true' and xbmc.getCondVisibility('Window.Previous(loginscreen)') == 0:
                self.logoutcounter +=1
                if self.logoutcounter >= (self.multiplier*self.logouttime*60):
                    if xbmc.getCondVisibility('Player.HasMedia') == 1:
                        if self.logoutplaying == 'true':
                            xbmc.executebuiltin("PlayerControl(Stop)")
                            xbmc.log('Digital Clock Screensaver %s: Stopping media' %Addonversion)
                            xbmc.executebuiltin("System.LogOff")
                            xbmc.log('Digital Clock Screensaver %s: Logging out' %Addonversion)
                            self.logoutcounter = 0
                    else:
                        xbmc.executebuiltin("System.LogOff")
                        xbmc.log('Digital Clock Screensaver %s: Logging out' %Addonversion)
                        self.logoutcounter = 0
          
            self.monitor.waitForAbort(self.waittimer)

    def setCTR(self):
        self.rc = str("%06x" % random.randint(0, 0xFFFFFF))
        self.rtr = str("%02x" % random.randint(0, 0xFF))
		#random color
        if self.ch == 'true':
            self.hourcolor = self.hourcolor[:2] + self.rc
        if self.cc == 'true':
            self.coloncolor = self.coloncolor[:2] + self.rc
        if self.cm == 'true':
            self.minutecolor = self.minutecolor[:2] + self.rc
        if self.campm == 'true':
            self.ampmcolor = self.ampmcolor[:2] + self.rc
        if self.cd == 'true':
            self.datecolor = self.datecolor[:2] + self.rc
        if self.ci == 'true':
            self.informationcolor = self.informationcolor[:2] + self.rc
        if self.cw == 'true':
            self.iconcolor = self.iconcolor[:2] + self.rc
		#random transparency
        if self.trh == 'true':
            self.hourcolor = self.rtr + self.hourcolor[2:]
            self.shadowcolor = self.rtr + self.shadowcolor[2:]
        if self.trc == 'true':
            self.coloncolor = self.rtr + self.coloncolor[2:]
            self.shadowcolor = self.rtr + self.shadowcolor[2:]
        if self.trm == 'true':
            self.minutecolor = self.rtr + self.minutecolor[2:]
            self.shadowcolor = self.rtr + self.shadowcolor[2:]
        if self.trampm == 'true':
            self.ampmcolor = self.rtr + self.ampmcolor[2:]
            self.shadowcolor = self.rtr + self.shadowcolor[2:]
        if self.trd == 'true':
            self.datecolor = self.rtr + self.datecolor[2:]
            self.shadowcolor = self.rtr + self.shadowcolor[2:]
        if self.tri == 'true':
            self.informationcolor = self.rtr + self.informationcolor[2:]
            self.shadowcolor = self.rtr + self.shadowcolor[2:]
        if self.trw == 'true':
            self.iconcolor = self.rtr + self.iconcolor[2:]
            self.shadowcolor = self.rtr + self.shadowcolor[2:]

    def Display(self):
        self.hour_control.setLabel(datetime.now().strftime(self.time))
        self.colon_control.setLabel(" : ")
        self.minute_control.setLabel(datetime.now().strftime("%M"))
        self.ampm_control.setLabel(datetime.now().strftime("%p"))
        if self.combinesonginfo == 'false' and self.showonlynowplaying == 'true' and self.nowplayinginfoshow == 'true' and xbmc.getInfoLabel('MusicPlayer.Artist'):
            self.date_control.setLabel(xbmc.getInfoLabel('MusicPlayer.Artist'))
        else:
            self.date_control.setLabel(self.date)
        if len(self.informationlist) != 0:
            self.information_control.setLabel(self.information)
        if (self.weatherinfoshow == 'true' and self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')) or (self.nowplayinginfoshow == 'true' and self.albumartshow == 'true' and (xbmc.getInfoLabel('MusicPlayer.Artist') or xbmc.getInfoLabel('MusicPlayer.Title'))):
            self.icon_control.setImage(self.icon)
        self.hour_colorcontrol.setLabel(self.hourcolor)
        self.colon_colorcontrol.setLabel(self.coloncolor)
        self.minute_colorcontrol.setLabel(self.minutecolor)
        self.ampm_colorcontrol.setLabel(self.ampmcolor)
        self.date_colorcontrol.setLabel(self.datecolor)
        self.information_colorcontrol.setLabel(self.informationcolor)
        self.icon_control.setColorDiffuse(self.iconcolor)
        self.shadow_colorcontrol.setLabel(self.shadowcolor)

    def Switch(self):
        if self.combinesonginfo == 'false' and self.showonlynowplaying == 'true' and self.nowplayinginfoshow == 'true' and xbmc.getInfoLabel('MusicPlayer.Title'):
            self.information = xbmc.getInfoLabel('MusicPlayer.Title')
        elif len(self.informationlist) > 1:
            self.switchcounter += 1
            if self.switchcounter == (self.multiplier*self.infoswitch):
                self.switch += 1
                self.switchcounter = 0
                self.information = self.informationlist[self.switch]
                if self.switch == len(self.informationlist)-1:
                    self.switch = -1
        if self.combinesonginfo == 'false' and self.showonlynowplaying == 'true':
            if self.nowplayinginfoshow == 'true' and self.albumartshow == 'true' and xbmc.getInfoLabel('Player.art(thumb)'):
                self.icon = xbmc.getInfoLabel('Player.art(thumb)')
            elif self.weatherinfoshow == 'true' and self.weathericonf != '0':
                self.icon = os.path.join(path,"resources/weathericons/",self.weathericonset[int(self.weathericonf)],xbmc.getInfoLabel('Window(Weather).Property(Current.FanartCode)')) + ".png"
        elif self.weatherinfoshow == 'true' and self.weathericonf != '0' and self.nowplayinginfoshow == 'true' and self.albumartshow == 'true' and xbmc.getInfoLabel('Player.art(thumb)'):
            self.iconswitchcounter += 1
            if self.iconswitchcounter == (self.multiplier*self.infoswitch):
                self.iconswitch += 1
                self.iconswitchcounter = 0
                if self.iconswitch == 2:
                    self.iconswitch = 0
            if self.iconswitch == 0:
                self.icon = xbmc.getInfoLabel('Player.art(thumb)')
            else:
                self.icon = os.path.join(path,"resources/weathericons/",self.weathericonset[int(self.weathericonf)],xbmc.getInfoLabel('Window(Weather).Property(Current.FanartCode)')) + ".png"
        elif self.nowplayinginfoshow == 'true' and self.albumartshow == 'true' and xbmc.getInfoLabel('Player.art(thumb)'):
            self.icon = xbmc.getInfoLabel('Player.art(thumb)')
        elif self.weatherinfoshow == 'true' and self.weathericonf != '0':
            self.icon = os.path.join(path,"resources/weathericons/",self.weathericonset[int(self.weathericonf)],xbmc.getInfoLabel('Window(Weather).Property(Current.FanartCode)')) + ".png"

    def exit(self):
        self.abort_requested = True
        self.exit_monitor = None
        xbmc.log('Digital Clock Screensaver %s: Abort requested' %Addonversion)
        self.close()

if __name__ == '__main__':
    xbmc.log('Digital Clock Screensaver %s: Started' %Addonversion)
    if(os.path.isfile(os.path.join(path,"resources/skins/default/720p/",scriptname))):
        screensaver = Screensaver(scriptname, path, 'default')
    else:
        screensaver = Screensaver('skin.default.xml', path, 'default')
    screensaver.doModal()
    screensaver.close()
    del screensaver
    xbmc.log('Digital Clock Screensaver %s: Stopped' %Addonversion)
    sys.modules.clear()

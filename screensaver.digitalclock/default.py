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
import random
import os
from datetime import datetime

Addon = xbmcaddon.Addon('screensaver.digitalclock')

__scriptname__ = Addon.getAddonInfo('name')
__path__ = Addon.getAddonInfo('path')
__location__ = xbmc.getSkinDir()
#__scriptname__='script-' + __scriptname__ + '-main.xml'
__scriptname__='script-' + __scriptname__ + '-' + __location__+ '.xml'

class Screensaver(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.log('INIT')
        self.abort_requested = False
        self.started = False
        self.exit_monitor = self.ExitMonitor(self.exit)
        self.date_control = self.getControl(30100)
        self.hour_control = self.getControl(30101)
        self.colon_control = self.getControl(30102)
        self.minute_control = self.getControl(30103)
        self.ampm_control = self.getControl(30104)
        self.nowplaying_control = self.getControl(30110)		
        self.container = self.getControl(30002)
        self.image_control = self.getControl(30020)
        self.waitcounter = 0
        self.switchcounter = 0
        self.switch = 1
        self.stayinplace = int(Addon.getSetting('stayinplace'))
        self.datef=Addon.getSetting('dateformat')
        self.timef=Addon.getSetting('timeformat')	
        self.ampm_control.setVisible(False)
        self.nowplayingshow = Addon.getSetting('nowplayingshow')		
        self.infoswitch = int(Addon.getSetting('infoswitch'))				
        self.slideshowenable = Addon.getSetting('slideshow')
        self.randomimages = Addon.getSetting('randomimages')
        self.randomcolor = Addon.getSetting('randomcolor')
        self.randomtr = Addon.getSetting('randomtr')
        self.trh = int(Addon.getSetting('hourtr'))
        self.trc = int(Addon.getSetting('colontr'))
        self.trm = int(Addon.getSetting('minutetr'))
        self.trampm = int(Addon.getSetting('ampmtr'))
        self.trd = int(Addon.getSetting('datetr'))
        self.trnp = int(Addon.getSetting('nowplayingtr'))		
        self.ch = int(Addon.getSetting('hourcolor'))
        self.cc = int(Addon.getSetting('coloncolor'))
        self.cm = int(Addon.getSetting('minutecolor'))
        self.campm = int(Addon.getSetting('ampmcolor'))
        self.cd = int(Addon.getSetting('datecolor'))
        self.cnp = int(Addon.getSetting('nowplayingcolor'))		
        self.hour_colorcontrol = self.getControl(30105)
        self.colon_colorcontrol = self.getControl(30106)
        self.minute_colorcontrol = self.getControl(30107)
        self.ampm_colorcontrol = self.getControl(30108)
        self.date_colorcontrol = self.getControl(30109)
        self.nowplaying_colorcontrol = self.getControl(30111)
			
		#setting up background and slideshow
        if self.slideshowenable == 'false':
            self.image = ['white.png','red.png','green.png','blue.png','yellow.png','black.png']		
            self.image_control.setImage(self.image[int(Addon.getSetting('image'))])
        else:
            self.folder = Addon.getSetting('folder')
            self.timer = ['15','30','60','120','180','240','300','360','420','480','540','600']		
            self.imagetimer = int(self.timer[int(Addon.getSetting('imagetimer'))])
            self.number = len(os.walk(self.folder).next()[2])-1
            self.slideshowcounter = 0
            self.files = os.walk(self.folder).next()[2]
            self.nextfile = 0
            if self.randomimages =='true':
                self.nextfile = random.randint(0,self.number)
            self.path = self.folder + self.files[self.nextfile]
            self.nextfile += 1
            self.image_control.setImage(self.path)
			
		#setting up color transparency
        self.transparency = ['FF','E5','CC','B2','99','7F','66','4C','33','19','00']
		
		#setting up colors
        self.color = ['FFFFFF','FF0000','00FF00','0000FF','FFFF00','000000']
        
        #setting up now playing info
        if xbmc.getInfoLabel('MusicPlayer.Artist') and xbmc.getInfoLabel('MusicPlayer.Title'):
            self.nowplayingtype = 1
            self.nowplaying = '$INFO[MusicPlayer.Artist]'
        elif xbmc.getInfoLabel('VideoPlayer.TVShowTitle') and xbmc.getInfoLabel('VideoPlayer.Title'):
            self.nowplayingtype = 2
            self.nowplaying = '$INFO[MusicPlayer.TVShowTitle]'
        elif xbmc.getInfoLabel('VideoPlayer.Title'):
            self.nowplayingtype = 3
            self.nowplaying = '$INFO[VideoPlayer.Title]'
        elif xbmc.getInfoLabel('MusicPlayer.Title'):
            self.nowplayingtype = 4
            self.split = xbmc.getInfoLabel('MusicPlayer.Title').split(' - ')
            self.nowplaying = self.split[0]			
        else:
            self.nowplayingtype = 0
            self.nowplaying = '$INFO[MusicPlayer.Artist]'
            self.nowplaying_control.setVisible(False)	

		#setting up the date format
        self.dateformat = ['$INFO[System.Date(DDD dd. MMM yyyy)]','$INFO[System.Date(DDD dd. MMM yyyy)]','$INFO[System.Date(dd.mm.yyyy)]','$INFO[System.Date(mm.dd.yyyy)]']		
        if self.datef == '0':
            self.date_control.setVisible(False)
            if self.nowplayingshow == 'true':
                self.nowplaying_control.setPosition(0, 85)
                if self.nowplayingtype != 0:
                    self.container.setHeight(130)
                else:					
                    self.container.setHeight(90)
            else:
                self.container.setHeight(90)
                self.nowplaying_control.setVisible(False)
        else:
            if self.nowplayingshow == 'true':
                if self.nowplayingtype == 0:
                    self.container.setHeight(130)
            else:					
                self.container.setHeight(130)	
                self.nowplaying_control.setVisible(False)
				
        self.date = self.dateformat[int(self.datef)]

		#setting up the time format
        self.timeformat = ['%H','%I','%I']
        if self.timef == '2':
           self.ampm_control.setVisible(True)
        self.time = self.timeformat[int(self.timef)]
		
		#setting up the screen size
        self.screeny = 720 - self.container.getHeight()
        self.screenx = 1280 - self.container.getWidth()
				
		#combining transparency and color
        self.setCTR()
        self.Display()
        
        self.DisplayTime()
        
    def DisplayTime(self):
        while not self.abort_requested:

            #Switching Artist and Title	
            self.Switch()
		
            #Random movement
            self.waitcounter += 1			
            if self.waitcounter == (2*self.stayinplace):
                new_x = random.randint(0,self.screenx)
                new_y = random.randint(0,self.screeny)
                self.container.setPosition(new_x,new_y)
                self.waitcounter = 0
                self.setCTR()

		    #Display time
            self.Display()			
				
			#Slideshow
            if self.slideshowenable == 'true':
                self.slideshowcounter +=1
                if self.slideshowcounter == (2*self.imagetimer):
                    if self.randomimages =='true':
                        self.nextfile = random.randint(0,self.number)
                    self.path = self.folder + self.files[self.nextfile]
                    self.image_control.setImage(self.path)	
                    self.nextfile +=1
                    self.slideshowcounter = 0
                    if self.nextfile > self.number:
                        self.nextfile = 0
				
			#Colon blink
            if datetime.now().second%2==0:
                self.colon_control.setVisible(True)
            else:
                self.colon_control.setVisible(False)

            xbmc.sleep(500)
			
        if self.abort_requested:
            self.log('Digital Clock abort_requested')
            self.exit()
            return
			
    def setCTR(self):
        if self.randomcolor == 'false' and self.randomtr == 'false':
            self.hourcolor = self.transparency[self.trh] + self.color[self.ch]
            self.coloncolor = self.transparency[self.trc] + self.color[self.cc]
            self.minutecolor = self.transparency[self.trm] + self.color[self.cm]
            self.ampmcolor = self.transparency[self.trampm] + self.color[self.campm]
            self.datecolor = self.transparency[self.trd] + self.color[self.cd]
            self.nowplayingcolor = self.transparency[self.trnp] + self.color[self.cnp]
        elif self.randomcolor == 'true' and self.randomtr == 'false':
            self.rc = str("%06x" % random.randint(0, 0xFFFFFF))
            self.hourcolor = self.transparency[self.trh] + self.rc
            self.coloncolor = self.transparency[self.trc] + self.rc
            self.minutecolor = self.transparency[self.trm] + self.rc
            self.ampmcolor = self.transparency[self.trampm] + self.rc
            self.datecolor = self.transparency[self.trd] + self.rc
            self.nowplayingcolor = self.transparency[self.trnp] + self.rc			
        elif self.randomcolor == 'false' and self.randomtr == 'true':
            self.rtr = str("%02x" % random.randint(0x4C, 0xFF))
            self.hourcolor = self.rtr + self.color[self.ch]
            self.coloncolor = self.rtr + self.color[self.cc]
            self.minutecolor = self.rtr + self.color[self.cm]
            self.ampmcolor = self.rtr + self.color[self.campm]
            self.datecolor = self.rtr + self.color[self.cd]
            self.nowplayingcolor = self.rtr + self.color[self.cnp]			
        elif self.randomcolor == 'true' and self.randomtr == 'true':
            self.rc = str("%06x" % random.randint(0, 0xFFFFFF))
            self.rtr = str("%02x" % random.randint(0x4C, 0xFF))
            self.hourcolor = self.rtr + self.rc
            self.coloncolor = self.rtr + self.rc
            self.minutecolor = self.rtr + self.rc
            self.ampmcolor = self.rtr + self.rc
            self.datecolor = self.rtr + self.rc
            self.nowplayingcolor = self.rtr + self.rc

    def Display(self):
        self.hour_control.setLabel(datetime.now().strftime(self.time))
        self.colon_control.setLabel(" : ")   			
        self.minute_control.setLabel(datetime.now().strftime("%M"))
        self.ampm_control.setLabel(datetime.now().strftime("%p"))
        self.date_control.setLabel(self.date)
        self.nowplaying_control.setLabel(self.nowplaying)
        self.hour_colorcontrol.setLabel(self.hourcolor)
        self.colon_colorcontrol.setLabel(self.coloncolor)   			
        self.minute_colorcontrol.setLabel(self.minutecolor)
        self.ampm_colorcontrol.setLabel(self.ampmcolor)
        self.date_colorcontrol.setLabel(self.datecolor)
        self.nowplaying_colorcontrol.setLabel(self.nowplayingcolor)	

    def Switch(self):
        if self.nowplayingtype == 1:
            self.split = xbmc.getInfoLabel('MusicPlayer.Title').split(' (')		
            self.switchcounter += 1
            if self.switchcounter == (2*self.infoswitch):
                self.switch *=-1
                self.switchcounter = 0
            if self.switch == 1:
                self.nowplaying = '$INFO[MusicPlayer.Artist]'
            else:
                self.nowplaying = self.split[0]
        elif self.nowplayingtype == 2:
            self.switchcounter += 1		
            if self.switchcounter == (2*self.infoswitch):
                self.switch *=-1
                self.switchcounter = 0
            if self.switch == 1:
                self.nowplaying = '$INFO[VideoPlayer.TVShowTitle]'
            else:
                self.nowplaying = '$INFO[VideoPlayer.Title]'
        elif self.nowplayingtype == 4:
            self.split = xbmc.getInfoLabel('MusicPlayer.Title').split(' - ')			
            self.switchcounter += 1		
            if self.switchcounter == (2*self.infoswitch):
                self.switch *=-1
                self.switchcounter = 0
            if self.switch == 1:
                self.nowplaying = self.split[0]
            else:
                self.nowplaying = self.split[1]				
		
    def exit(self):
        self.abort_requested = True
        self.exit_monitor = None
        self.log('exit')
        self.close()

    def log(self, msg):
        xbmc.log(u'Digital Clock Screensaver: %s' % msg)

if __name__ == '__main__':
    screensaver = Screensaver(__scriptname__, __path__, 'default')
    screensaver.doModal()
    del screensaver
    sys.modules.clear()
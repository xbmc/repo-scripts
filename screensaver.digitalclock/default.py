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

#__scriptname__ = Addon.getAddonInfo('name')
__path__ = Addon.getAddonInfo('path')
__location__ = xbmc.getSkinDir()
#__scriptname__='main.xml'
__scriptname__ = __location__ + '.xml'

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
        self.information_control = self.getControl(30110)		
        self.container = self.getControl(30002)
        self.image_control = self.getControl(30020)
        self.weathericon_control = self.getControl(30021)	
        self.waitcounter = 0
        self.switchcounter = 0
        self.updateweather = 0
        self.switch = 0
        self.switchlimit = 2		
        self.informationtype = 0
        self.weather = 0
        self.movementtype = int(Addon.getSetting('movementtype'))
        self.movementspeed = int(Addon.getSetting('movementspeed'))
        self.stayinplace = int(Addon.getSetting('stayinplace'))
        self.datef=Addon.getSetting('dateformat')
        self.timef=Addon.getSetting('timeformat')
        self.shadowf=Addon.getSetting('shadowformat')		
        self.ampm_control.setVisible(False)
        self.informationshow = Addon.getSetting('additionalinformation')	
        self.nowplayinginfoshow = Addon.getSetting('nowplayinginfoshow')		
        self.weatherinfoshow = Addon.getSetting('weatherinfoshow')
        self.weathericonf=Addon.getSetting('weathericonformat')		
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
        self.tri = int(Addon.getSetting('informationtr'))
        self.trw = int(Addon.getSetting('weathericontr'))		
        self.ch = int(Addon.getSetting('hourcolor'))
        self.cc = int(Addon.getSetting('coloncolor'))
        self.cm = int(Addon.getSetting('minutecolor'))
        self.campm = int(Addon.getSetting('ampmcolor'))
        self.cd = int(Addon.getSetting('datecolor'))
        self.ci = int(Addon.getSetting('informationcolor'))
        self.cw = int(Addon.getSetting('weathericoncolor'))			
        self.hour_colorcontrol = self.getControl(30105)
        self.colon_colorcontrol = self.getControl(30106)
        self.minute_colorcontrol = self.getControl(30107)
        self.ampm_colorcontrol = self.getControl(30108)
        self.date_colorcontrol = self.getControl(30109)
        self.information_colorcontrol = self.getControl(30111)
        self.shadow_colorcontrol = self.getControl(30112)
        self.monitor = xbmc.Monitor()
			
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
		
		#setting up shadow colors
        self.shadowcolor = ['00000000','FFFFFFFF','FF808080','FF000000']
        self.shadow_colorcontrol.setLabel(self.shadowcolor[int(self.shadowf)])
     
        #setting up information
        if self.informationshow == 'true':		
            if self.nowplayinginfoshow == 'true':
                if xbmc.getInfoLabel('MusicPlayer.Artist') and xbmc.getInfoLabel('MusicPlayer.Title'):
                    self.informationtype = 1
                    self.information = '$INFO[MusicPlayer.Artist]'
                elif xbmc.getInfoLabel('VideoPlayer.TVShowTitle') and xbmc.getInfoLabel('VideoPlayer.Title'):
                    self.informationtype = 2
                    self.information = '$INFO[MusicPlayer.TVShowTitle]'
                elif xbmc.getInfoLabel('VideoPlayer.Title'):
                    self.informationtype = 3
                    self.information = '$INFO[VideoPlayer.Title]'
                elif xbmc.getInfoLabel('MusicPlayer.Title'):
                    self.informationtype = 4
                    self.split = xbmc.getInfoLabel('MusicPlayer.Title').split(' - ')
                    self.information = self.split[0]			
            if self.weatherinfoshow == 'true':
                if xbmc.getInfoLabel('Weather.Location'):
                    self.weather = 1
                    self.switchlimit = 3					
                    self.temperature = xbmc.getInfoLabel('Weather.Temperature')
                    self.conditions = xbmc.getInfoLabel('Weather.Conditions')
                    if self.informationtype == 0:
                        self.informationtype = 5						
                        self.information = self.temperature + ' - ' + self.conditions				

		#setting up the date format and positions
        self.dateformat = ['Hide date','$INFO[System.Date(DDD dd. MMM yyyy)]','$INFO[System.Date(dd.mm.yyyy)]','$INFO[System.Date(mm.dd.yyyy)]']		
        if self.datef == '0':
            self.date_control.setVisible(False)
            if self.informationshow == 'true':
                if self.informationtype != 0:
                    self.information_control.setPosition(0, 85)				
                    if (self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')):
                        self.weathericon_control.setPosition(115, 110)					
                        self.container.setHeight(240)
                    else:
                        self.container.setHeight(130)
                        self.weathericon_control.setVisible(False)						
                else:
                    if (self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')):
                        self.weathericon_control.setPosition(115, 70)					
                        self.container.setHeight(200)
                    else:
                        self.container.setHeight(90)
                        self.weathericon_control.setVisible(False)				
                    self.information_control.setVisible(False)					
            else:
                self.container.setHeight(90)
                self.weathericon_control.setVisible(False)					
                self.information_control.setVisible(False)
        else:
            if self.informationshow == 'true':
                if self.informationtype != 0:
                    if not(self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')):
                        self.container.setHeight(170)
                        self.weathericon_control.setVisible(False)						
                else:
                    if (self.weathericonf != '0' and xbmc.getInfoLabel('Weather.Location')):
                        self.weathericon_control.setPosition(115, 110)					
                        self.container.setHeight(240)
                    else:
                        self.container.setHeight(130)
                        self.weathericon_control.setVisible(False)				
                    self.information_control.setVisible(False)					
            else:
                self.container.setHeight(130)
                self.weathericon_control.setVisible(False)					
                self.information_control.setVisible(False)			
				
        self.date = self.dateformat[int(self.datef)]

		#setting weather icon set
        self.weathericonset = ['Hide weather icon','set1','set2','set3','set4']
        self.weathericon = xbmc.getInfoLabel('Window(Weather).Property(Current.FanartCode)')
        self.weathericon_control.setImage(os.path.join(__path__,"resources/skins/default/weathericons/",self.weathericonset[int(self.weathericonf)],self.weathericon) + ".png")
		
		#setting up the time format
        self.timeformat = ['%H','%I','%I']
        if self.timef == '2':
           self.ampm_control.setVisible(True)
        self.time = self.timeformat[int(self.timef)]
		
		#setting up movement type and wait timer	
        if self.movementtype == 0:
            self.waittimer = 0.5
            self.multiplier = 2
        else:
            self.waittimer = 0.02
            self.multiplier = 50
            self.dx = random.choice([-(self.movementspeed+1),(self.movementspeed+1)])
            self.dy = random.choice([-(self.movementspeed+1),(self.movementspeed+1)])
		
		#setting up the screen size
        self.screeny = 720 - self.container.getHeight()
        self.screenx = 1280 - self.container.getWidth()	
		
		#combining transparency and color
        self.setCTR()
        self.Display()
		
        self.DisplayTime()
        
    def DisplayTime(self):
        while not self.abort_requested:

		    #checking if all weather information is available
            if self.informationshow == 'true':
                if (self.weather == 1 or self.weathericonf != '0'):			
                    if xbmc.getInfoLabel('Weather.Conditions') == 'Busy':
                        self.temperature = xbmc.getInfoLabel('Weather.Temperature')
                        self.conditions = xbmc.getInfoLabel('Weather.Conditions')
                        self.weathericon = xbmc.getInfoLabel('Window(Weather).Property(Current.FanartCode)')		
		
            #switching information	
            self.Switch()

			#movement
            if self.movementtype == 0:			
                #random movement
                self.waitcounter += 1			
                if self.waitcounter == (self.multiplier*self.stayinplace):
                    new_x = random.randint(0,self.screenx)
                    new_y = random.randint(0,self.screeny)
                    self.container.setPosition(new_x,new_y)
                    self.waitcounter = 0
                    self.setCTR()
            else:
                #bounce
                self.currentposition = self.container.getPosition()
                new_x = self.currentposition[0]+self.dx
                new_y = self.currentposition[1]+self.dy
                if new_x >= self.screenx or new_x <= 0:
                    self.dx = self.dx*-1
                    self.setCTR()					
                if new_y >= self.screeny or new_y <= 0:
                    self.dy = self.dy*-1
                    self.setCTR()					
                self.container.setPosition(new_x,new_y)

		    #display time
            self.Display()			
				
			#slideshow
            if self.slideshowenable == 'true':
                self.slideshowcounter +=1
                if self.slideshowcounter == (self.multiplier*self.imagetimer):
                    if self.randomimages =='true':
                        self.nextfile = random.randint(0,self.number)
                    self.path = self.folder + self.files[self.nextfile]
                    self.image_control.setImage(self.path)	
                    self.nextfile +=1
                    self.slideshowcounter = 0
                    if self.nextfile > self.number:
                        self.nextfile = 0
						
            #refresh weather information every 30 minutes
            if (self.weather == 1 or self.weathericonf != '0'):
                self.updateweather += 1			
                if self.updateweather == (self.multiplier*1800):
                    self.temperature = xbmc.getInfoLabel('Weather.Temperature')
                    self.conditions = xbmc.getInfoLabel('Weather.Conditions')
                    self.weathericon = xbmc.getInfoLabel('Window(Weather).Property(Current.FanartCode)')					
                    self.updateweather = 0						
				
			#colon blink
            if datetime.now().second%2==0:
                self.colon_control.setVisible(True)
            else:
                self.colon_control.setVisible(False)

            #xbmc.sleep(500)
            self.monitor.waitForAbort(self.waittimer)
			
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
            self.informationcolor = self.transparency[self.tri] + self.color[self.ci]
            self.weathericoncolor = self.transparency[self.trw] + self.color[self.cw]		
        elif self.randomcolor == 'true' and self.randomtr == 'false':
            self.rc = str("%06x" % random.randint(0, 0xFFFFFF))
            self.hourcolor = self.transparency[self.trh] + self.rc
            self.coloncolor = self.transparency[self.trc] + self.rc
            self.minutecolor = self.transparency[self.trm] + self.rc
            self.ampmcolor = self.transparency[self.trampm] + self.rc
            self.datecolor = self.transparency[self.trd] + self.rc
            self.informationcolor = self.transparency[self.tri] + self.rc
            self.weathericoncolor = self.transparency[self.trw] + self.rc			
        elif self.randomcolor == 'false' and self.randomtr == 'true':
            self.rtr = str("%02x" % random.randint(0x4C, 0xFF))
            self.hourcolor = self.rtr + self.color[self.ch]
            self.coloncolor = self.rtr + self.color[self.cc]
            self.minutecolor = self.rtr + self.color[self.cm]
            self.ampmcolor = self.rtr + self.color[self.campm]
            self.datecolor = self.rtr + self.color[self.cd]
            self.informationcolor = self.rtr + self.color[self.ci]
            self.weathericoncolor = self.rtr + self.color[self.cw]			
        elif self.randomcolor == 'true' and self.randomtr == 'true':
            self.rc = str("%06x" % random.randint(0, 0xFFFFFF))
            self.rtr = str("%02x" % random.randint(0x4C, 0xFF))
            self.hourcolor = self.rtr + self.rc
            self.coloncolor = self.rtr + self.rc
            self.minutecolor = self.rtr + self.rc
            self.ampmcolor = self.rtr + self.rc
            self.datecolor = self.rtr + self.rc
            self.informationcolor = self.rtr + self.rc
            self.weathericoncolor = self.rtr + self.rc		

    def Display(self):
        self.hour_control.setLabel(datetime.now().strftime(self.time))
        self.colon_control.setLabel(" : ")   			
        self.minute_control.setLabel(datetime.now().strftime("%M"))
        self.ampm_control.setLabel(datetime.now().strftime("%p"))
        self.date_control.setLabel(self.date)
        if self.informationtype != 0:
            self.information_control.setLabel(self.information)
        if self.weathericonf != '0': 			
            self.weathericon_control.setImage(os.path.join(__path__,"resources/skins/default/weathericons/",self.weathericonset[int(self.weathericonf)],self.weathericon) + ".png")
        self.hour_colorcontrol.setLabel(self.hourcolor)
        self.colon_colorcontrol.setLabel(self.coloncolor)   			
        self.minute_colorcontrol.setLabel(self.minutecolor)
        self.ampm_colorcontrol.setLabel(self.ampmcolor)
        self.date_colorcontrol.setLabel(self.datecolor)
        self.information_colorcontrol.setLabel(self.informationcolor)
        self.weathericon_control.setColorDiffuse(self.weathericoncolor)		

    def Switch(self):
        if self.informationtype == 1:
            self.split = xbmc.getInfoLabel('MusicPlayer.Title').split(' (')		
            self.switchcounter += 1
            if self.switchcounter == (self.multiplier*self.infoswitch):
                self.switch += 1
                self.switchcounter = 0
                if self.switch == self.switchlimit:
                    self.switch = 0
            if self.switch == 0:
                self.information = '$INFO[MusicPlayer.Artist]'
            elif self.switch == 1:
                self.information = self.split[0]
            else:
                self.information = self.temperature + ' - ' + self.conditions			
        elif self.informationtype == 2:
            self.switchcounter += 1		
            if self.switchcounter == (self.multiplier*self.infoswitch):
                self.switch += 1
                self.switchcounter = 0
                if self.switch == self.switchlimit:
                    self.switch = 0
            if self.switch == 0:
                self.information = '$INFO[VideoPlayer.TVShowTitle]'
            elif self.switch == 1:
                self.information = '$INFO[VideoPlayer.Title]'
            else:
                self.information = self.temperature + ' - ' + self.conditions
        elif self.informationtype == 3:
            if self.switchlimit-1 == 2:		
                self.switchcounter += 1		
                if self.switchcounter == (self.multiplier*self.infoswitch):
                    self.switch += 1
                    self.switchcounter = 0
                    if self.switch == self.switchlimit-1:
                        self.switch = 0
                if self.switch == 0:
                    self.information = '$INFO[VideoPlayer.Title]'
                else:
                    self.information = self.temperature + ' - ' + self.conditions					
        elif self.informationtype == 4:
            self.split = xbmc.getInfoLabel('MusicPlayer.Title').split(' - ')			
            self.switchcounter += 1		
            if self.switchcounter == (self.multiplier*self.infoswitch):
                self.switch += 1
                self.switchcounter = 0
                if self.switch == self.switchlimit:
                    self.switch = 0
            if self.switch == 0:
                self.information = self.split[0]
            elif self.switch == 1:
                self.information = self.split[1]
            else:
                self.information = self.temperature + ' - ' + self.conditions
        elif self.informationtype == 5:
            self.information = self.temperature + ' - ' + self.conditions		
		
    def exit(self):
        self.abort_requested = True
        self.exit_monitor = None
        self.log('exit')
        self.close()

    def log(self, msg):
        xbmc.log(u'Digital Clock Screensaver: %s' % msg)

if __name__ == '__main__':
    if(os.path.isfile(xbmc.translatePath('special://skin/1080i/script-screensaver-digitalclock-custom.xml'))):
        screensaver = Screensaver("script-screensaver-digitalclock-custom.xml", xbmc.translatePath('special://skin/1080i/'), 'default')
    elif(os.path.isfile(xbmc.translatePath('special://skin/720p/script-screensaver-digitalclock-custom.xml'))):
        screensaver = Screensaver("script-screensaver-digitalclock-custom.xml", xbmc.translatePath('special://skin/720p/'), 'default')
    elif(os.path.isfile(xbmc.translatePath('special://skin/21x9/script-screensaver-digitalclock-custom.xml'))):
        screensaver = Screensaver("script-screensaver-digitalclock-custom.xml", xbmc.translatePath('special://skin/21x9/'), 'default')
    elif(os.path.isfile(xbmc.translatePath('special://skin/16x9/script-screensaver-digitalclock-custom.xml'))):
        screensaver = Screensaver("script-screensaver-digitalclock-custom.xml", xbmc.translatePath('special://skin/16x9/'), 'default')
    elif(os.path.isfile(xbmc.translatePath('special://skin/4x3Hirez/script-screensaver-digitalclock-custom.xml'))):
        screensaver = Screensaver("script-screensaver-digitalclock-custom.xml", xbmc.translatePath('special://skin/4x3Hirez/'), 'default')
    elif(os.path.isfile(os.path.join(__path__,"resources/skins/default/720p/",__scriptname__))):
        screensaver = Screensaver(__scriptname__, __path__, 'default')
    else:
        screensaver = Screensaver("skin.default.xml", __path__, 'default')	
    screensaver.doModal()
    del screensaver
    sys.modules.clear()
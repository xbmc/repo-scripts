#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Philip Schmiegelt
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import random
import datetime
import time
import os

import xbmcaddon
import xbmcgui
import xbmc

import controller


addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_path = addon.getAddonInfo('path')
image_dir = xbmc.translatePath( os.path.join( addon_path, 'resources', 'skins', 'default', 'media' ,'').encode("utf-8") ).decode("utf-8")



#lightSizeNormal = 50
#lightPaddingNormal = 2
#blockPaddingLarge = 50
#blockPaddingSmall = 10
blockSizeNormal = 3
blockSizeSeconds = 8


scriptId   = 'screensaver.unaryclock'



class Screensaver(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback, log_callback):
            self.exit_callback = exit_callback
	    self.log_callback = log_callback

        def onScreensaverDeactivated(self):
            #self.log_callback('sending exit_callback')
            self.exit_callback()
        def onAbortRequested(self):
	    #self.log_callback('abort requested')
	    self.exit_callback()


    
    def computeActiveLights(self, size, numberOfLights, randomized): 
        self.flatLightsArray = list()
        for number in range(0,size*size):
            self.flatLightsArray.append(0)
        for number in range(0,numberOfLights):
	    if (randomized):
		rand = random.randint(0,size*size-1)
	    else:
  	        rand = number
            while self.flatLightsArray[rand] == 1:
               rand = (rand+1) % (size*size)
            self.flatLightsArray[rand] = 1
            numberOfLights = numberOfLights-1
            #self.log(self.flatLightsArray)
        return self.flatLightsArray
      
    def drawSinglePart(self, xOffset, yOffset, numberOfLights, blockSize, texture, imageOffset, randomized):
        lightBlock = self.computeActiveLights(blockSize, numberOfLights, randomized)
        lightSize = self.lightSizeNormal
        lightPadding = self.lightPaddingNormal
        #autoscaling
        if (blockSize > blockSizeNormal):
	    #3 lights + 2 spaces
	    lightSize = ((blockSizeNormal*lightSize)+(lightPadding*(blockSizeNormal-1)))  / (blockSize+1)
	    lightPadding = 3
        for cell in range(0,blockSize*blockSize):
	    column = cell%blockSize
            row = cell/blockSize
            t = 'grey.png'
            
            newX = self.topX+xOffset+column*(lightSize+lightPadding)
            newY = self.topY+yOffset+row*(lightSize+lightPadding)
	    if (1 == lightBlock[cell]):
	      t = texture

            if (len(self.allImages)<=imageOffset+cell):
                image = xbmcgui.ControlImage(newX,newY,lightSize,lightSize, image_dir+t, 0)
                image.setVisible(False)
                self.allImages.append(image)
                self.addControl(image)
            else:
                self.allImages[imageOffset+cell].setImage(image_dir+t)
                self.allImages[imageOffset+cell].setPosition(newX,newY)
                self.allImages[imageOffset+cell].setWidth(lightSize)
                self.allImages[imageOffset+cell].setHeight(lightSize)
                

    def showClock(self, onlySeconds):
        now = datetime.datetime.today()
        if (onlySeconds == False):
            for b in self.allImages[:]:
	        b.setVisible(False)
	    
	    #autoscaling
	    self.lightSizeNormal = self.getWidth() / 25
	    self.blockPaddingLarge = self.lightSizeNormal
	    self.blockPaddingSmall = self.blockPaddingLarge / 5
	    self.lightPaddingNormal = 2
	    
	    self.totalClockWidth = 4 * (blockSizeNormal*(self.lightSizeNormal + self.lightPaddingNormal)) + 2*self.blockPaddingSmall + 1*self.blockPaddingLarge
            if (self.showSeconds):
	        self.totalClockWidth = self.totalClockWidth + (blockSizeNormal*(self.lightSizeNormal + self.lightPaddingNormal)) + 1*self.blockPaddingLarge
            self.totalClockHeight = blockSizeNormal*(self.lightSizeNormal + self.lightPaddingNormal)
        
        
            #self.log('clockheigh ' + str(self.totalClockHeight))
            #self.log('clockwidth ' + str(self.totalClockWidth))    
	        
            maxX = self.getWidth()- 100 - self.totalClockWidth
            maxY = self.getHeight()- 100 - self.totalClockHeight
            maxX = max(50, maxX)
            maxY = max(50, maxY)
            #self.log('Screen ' + str(self.getWidth()) + ' ' + str(self.getHeight()))
            #self.log('Max ' + str(maxX) + ' ' + str(maxY))
	    self.topX = random.randint(1, maxX)
            self.topY = random.randint(1, maxY)
            
            
            hour = now.hour
            #self.log(('hour ' + str(hour)))
            self.drawSinglePart(0, 0, (hour/10), blockSizeNormal, self.hour1Color, 0, self.randHourMin)
            self.drawSinglePart(3*(self.lightSizeNormal+self.lightPaddingNormal)+1*self.blockPaddingSmall, 0, (hour%10), blockSizeNormal, self.hour2Color, 9, self.randHourMin)
       
            minute = now.minute
            #self.log(('minute ' + str(minute)))
            self.drawSinglePart(6*(self.lightSizeNormal+self.lightPaddingNormal)+1*self.blockPaddingSmall+self.blockPaddingLarge, 0, (minute/10), blockSizeNormal, self.min1Color, 18, self.randHourMin)
            self.drawSinglePart(9*(self.lightSizeNormal+self.lightPaddingNormal)+2*self.blockPaddingSmall+self.blockPaddingLarge, 0, (minute%10), blockSizeNormal, self.min2Color, 27, self.randHourMin)
        if (self.showSeconds == True):
           second = now.second
           self.drawSinglePart(12*(self.lightSizeNormal+self.lightPaddingNormal)+3*self.blockPaddingSmall+2*self.blockPaddingLarge, 0, second, blockSizeSeconds, self.secondsColor, 36, self.randSec)
        
        if (onlySeconds == False):
            for b in self.allImages[:]:
	        b.setVisible(True)
            

    def onInit(self):
	self.log("Screensaver starting")
        
        self.addon      = xbmcaddon.Addon(scriptId)
        if (self.addon.getSetting('setting_show_seconds') in ['false', 'False']):
            self.showSeconds = False
        else:
	    self.showSeconds = True
	if (self.addon.getSetting('setting_show_random_sec') in ['false', 'False']):
	    self.randSec = False
	else:
	    self.randSec = True        
        if (self.addon.getSetting('setting_show_random_hourmin') in ['false', 'False']):
            self.randHourMin = False
        else:
            self.randHourMin = True
        self.redrawInterval = int(self.addon.getSetting('setting_redraw_interval'))
	self.hour1Color = (self.addon.getSetting('setting_color_col_1')+".png").lower()
	self.hour2Color = (self.addon.getSetting('setting_color_col_2')+".png").lower()
	self.min1Color = (self.addon.getSetting('setting_color_col_3')+".png").lower()
	self.min2Color = (self.addon.getSetting('setting_color_col_4')+".png").lower()
	self.secondsColor = (self.addon.getSetting('setting_color_col_5')+".png").lower()	
	self.monitor = self.ExitMonitor(self.exit, self.log)
	self.allImages = list()
	self.topX = 20
        self.topY = 20
        
        #self.log(addon_path)

        self.showClock(False)
        self.cont = controller.Controller(self.log, self.showClock, self.showSeconds, self.redrawInterval)
        self.cont.start() 
        #self.showClock()
        
        
    

    def exit(self):
        self.log('Exit requested')
	self.cont.stop()
	for b in self.allImages[:]:
	    b.setVisible(False)
	del self.monitor
	del self.cont
	for b in self.allImages[:]:
	    self.removeControl(b)
        del self.allImages[:]
        self.close()
    
    def log(self, msg):
        xbmc.log(u'Unary Clock Screensaver: %s' % msg)
		


#   Copyright (C) 2018 Lunatixz, Anisan
#
#
# This file is part of Flip Clock.
#
# Flip Clock is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Flip Clock is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Flip Clock.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, random, time, datetime, threading
import xbmc, xbmcgui, xbmcvfs, xbmcaddon

# Plugin Info
ADDON_ID       = 'screensaver.flipclock'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
KODI_MONITOR   = xbmc.Monitor()

SKIN_LOC       = os.path.join(ADDON_PATH, 'resources', 'skins', 'default' ,'media')
DIGIT_LOC      = os.path.join(SKIN_LOC, "Digits")
CLOCK_LOC      = os.path.join(SKIN_LOC, "Clock")
BACKGROUND_LOC = os.path.join(SKIN_LOC, "Background")
DEFAULT_IMG    = os.path.join(BACKGROUND_LOC, "1.jpg")
CLOCK_MODE     = REAL_SETTINGS.getSetting("ClockMode")
IMAGE_MODE     = int(REAL_SETTINGS.getSetting("ImageSource"))
USER_IMG       = REAL_SETTINGS.getSetting("BackImage")
USER_IMG       = '' if USER_IMG == 'Default' else USER_IMG
USER_FOLDER    = REAL_SETTINGS.getSetting("BackFolder")
USER_FOLDER    = '' if USER_FOLDER == 'Default' else USER_FOLDER
ANIMATION      = 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope'
EXIT_SCRIPT    = ( 9, 6, 10, 247, 275, 61467, 216, 257, 61448, )
CANCEL_DIALOG  = EXIT_SCRIPT + ( 1, 2, 3, 4, 12, 122, 75, 7, 92, )

#Control IDs
FLIP1    = 210
DIGIT1   = 211
DIGIT11  = 2111
DIGIT12  = 2112
DIGIT110 = 21110
DIGIT120 = 21120
DIGIT2   = 212
DIGIT21  = 2121
DIGIT22  = 2122
DIGIT210 = 21210
DIGIT220 = 21220

FLIP2    = 220
DIGIT3   = 221
DIGIT31  = 2211
DIGIT32  = 2212
DIGIT310 = 22110
DIGIT320 = 22120
DIGIT4   = 222
DIGIT41  = 2221
DIGIT42  = 2222
DIGIT410 = 22210
DIGIT420 = 22220
LABEL    = 224
CLOCK    = 200

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.terminate  =  False


    def onInit( self ):
        counter  =  self.TimeCounter(self)
        counter.start()
        mover  =  self.MoveClock(self)
        mover.start()
            
        
    def onFocus( self, controlId ):
        pass
    
   
    def onClick( self, controlId ):
        pass

        
    def onAction( self, action ):
        self.terminate  =  True
        self.close()
        
        
    class TimeCounter(threading.Thread):
        def __init__(self, ui):
            threading.Thread.__init__(self)
            self.ui =  ui
            self.h1 = 0
            self.h2 = 0
            self.m1 = 0
            self.m2 = 0
            self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
            self.winid.setProperty('flip_animation', ANIMATION)
            self.imgProp    = (USER_IMG     or DEFAULT_IMG)
            self.folderProp = (USER_FOLDER  or BACKGROUND_LOC)
            #either use script, custom user or default background
            
            if IMAGE_MODE == 1:
                self.winid.setProperty("screensaver.flipclock.folder",self.folderProp)
                self.ui.getControl(40000).setVisible(False)
            else:
                self.winid.clearProperty("screensaver.flipclock.folder")
                self.ui.getControl(40000).setVisible(True)
                self.ui.getControl(40000).setImage(self.imgProp)
                      
        def run(self):
            i = 0
            while not KODI_MONITOR.abortRequested() and not self.ui.terminate:
                dtn = datetime.datetime.now()
                
                if CLOCK_MODE == "1":
                    dte = dtn.strftime("%d.%m.%Y %H:%M:%S")
                    h = dtn.strftime("%H")
                else:
                    dte = dtn.strftime("%d.%m.%Y %I:%M:%S")
                    h = dtn.strftime("%I")
                    
                h1 = int(h[0])
                h2 = int(h[1])
                m  = dtn.strftime("%M")
                m1 = int(m[0])
                m2 = int(m[1])
                
                if (self.h1!= h1)|(self.h2!= h2):
                    Flip = self.ui.Fliper(self.ui,1,self.h1,h1,self.h2,h2)
                    Flip.start()
                    self.h1 = h1
                    self.h2 = h2
                    
                if (self.m1!= m1)|(self.m2!= m2):
                    Flip  =  self.ui.Fliper(self.ui,2,self.m1,m1,self.m2,m2)
                    Flip.start()
                    self.m1 = m1
                    self.m2 = m2
                self.ui.getControl( LABEL ).setLabel(dte)
                
                if KODI_MONITOR.waitForAbort(1):
                    break
            
            
    class Fliper(threading.Thread):
        def __init__(self, ui,flip,old1,new1,old2,new2):
            threading.Thread.__init__(self)
            self.ui  =  ui
            self.flip  =  flip
            self.old1  =  old1 
            self.new1  =  new1
            self.old2  =  old2
            self.new2  =  new2

            
        def run (self):
            if (self.flip == 1):
                self.flip1()
            else:
                self.flip2()
        
        
        def flip1(self):
            i = 1
            self.ui.getControl( FLIP1 ).setImage(os.path.join(CLOCK_LOC,"0.png"))
            self.ui.getControl( FLIP1 ).setVisible(1)
            self.ui.getControl( DIGIT11 ).setImage(os.path.join(DIGIT_LOC,str(self.new1)+"(1).png"))
            self.ui.getControl( DIGIT12 ).setImage(os.path.join(DIGIT_LOC,str(self.old1)+"(2).png"))
            self.ui.getControl( DIGIT110 ).setImage(os.path.join(DIGIT_LOC,str(self.old1)+"(1).png"))
            self.ui.getControl( DIGIT21 ).setImage(os.path.join(DIGIT_LOC,str(self.new2)+"(1).png"))
            self.ui.getControl( DIGIT22 ).setImage(os.path.join(DIGIT_LOC,str(self.old2)+"(2).png"))
            self.ui.getControl( DIGIT210 ).setImage(os.path.join(DIGIT_LOC,str(self.old2)+"(1).png"))
            self.ui.getControl( DIGIT110 ).setHeight(40)
            self.ui.getControl( DIGIT110 ).setPosition(15,24)
            self.ui.getControl( DIGIT210 ).setHeight(40)
            self.ui.getControl( DIGIT210 ).setPosition(65,24)
            self.ui.getControl( DIGIT110 ).setVisible(1)
            self.ui.getControl( DIGIT210 ).setVisible(1)
            self.ui.getControl( DIGIT12 ).setVisible(1)
            self.ui.getControl( DIGIT22 ).setVisible(1)
            self.ui.getControl( DIGIT1 ).setVisible(0)
            self.ui.getControl( DIGIT2 ).setVisible(0)
            self.ui.getControl( DIGIT11 ).setVisible(1)
            self.ui.getControl( DIGIT21 ).setVisible(1)
            
            h = 40
            while (i<12):
                KODI_MONITOR.waitForAbort(.01)
                self.ui.getControl( FLIP1 ).setImage(os.path.join(CLOCK_LOC,str(i)+".png"))
                h = h-3
                self.ui.getControl( DIGIT110 ).setPosition(15,24+(40-h))
                self.ui.getControl( DIGIT110 ).setHeight(h)
                self.ui.getControl( DIGIT210 ).setPosition(65,24+(40-h))
                self.ui.getControl( DIGIT210 ).setHeight(h)
                i  =  i +1
            
            h = 43
            self.ui.getControl( DIGIT110 ).setVisible(0)
            self.ui.getControl( DIGIT210 ).setVisible(0)
            self.ui.getControl( DIGIT120 ).setHeight(3)
            self.ui.getControl( DIGIT120 ).setImage(os.path.join(DIGIT_LOC,str(self.new1)+"(2).png"))
            self.ui.getControl( DIGIT220 ).setHeight(3)
            self.ui.getControl( DIGIT220 ).setImage(os.path.join(DIGIT_LOC,str(self.new2)+"(2).png"))
            self.ui.getControl( DIGIT120 ).setVisible(1)
            self.ui.getControl( DIGIT220 ).setVisible(1)
            
            h = 3
            while (i<20):
                KODI_MONITOR.waitForAbort(.01)
                h = h+4
                self.ui.getControl( FLIP1 ).setImage(os.path.join(CLOCK_LOC,str(i)+".png"))
                self.ui.getControl( DIGIT120 ).setHeight(h)
                self.ui.getControl( DIGIT220 ).setHeight(h)
                i  =  i +1
            
            self.ui.getControl( DIGIT1 ).setImage(os.path.join(DIGIT_LOC,str(self.new1)+".png"))
            self.ui.getControl( DIGIT2 ).setImage(os.path.join(DIGIT_LOC,str(self.new2)+".png"))
            self.ui.getControl( DIGIT1 ).setVisible(1)
            self.ui.getControl( DIGIT2 ).setVisible(1)
            self.ui.getControl( DIGIT11 ).setVisible(0)
            self.ui.getControl( DIGIT12 ).setVisible(0)
            self.ui.getControl( DIGIT120 ).setVisible(0)
            self.ui.getControl( DIGIT21 ).setVisible(0)
            self.ui.getControl( DIGIT22 ).setVisible(0)
            self.ui.getControl( DIGIT220 ).setVisible(0)
            self.ui.getControl( FLIP1 ).setVisible(0)
        
        
        def flip2(self):
            i = 1
            self.ui.getControl( FLIP2 ).setImage(os.path.join(CLOCK_LOC,"0.png"))
            self.ui.getControl( FLIP2 ).setVisible(1)
            self.ui.getControl( DIGIT31 ).setImage(os.path.join(DIGIT_LOC,str(self.new1)+"(1).png"))
            self.ui.getControl( DIGIT32 ).setImage(os.path.join(DIGIT_LOC,str(self.old1)+"(2).png"))
            self.ui.getControl( DIGIT310 ).setImage(os.path.join(DIGIT_LOC,str(self.old1)+"(1).png"))
            self.ui.getControl( DIGIT41 ).setImage(os.path.join(DIGIT_LOC,str(self.new2)+"(1).png"))
            self.ui.getControl( DIGIT42 ).setImage(os.path.join(DIGIT_LOC,str(self.old2)+"(2).png"))
            self.ui.getControl( DIGIT410 ).setImage(os.path.join(DIGIT_LOC,str(self.old2)+"(1).png"))
            self.ui.getControl( DIGIT310 ).setHeight(40)
            self.ui.getControl( DIGIT310 ).setPosition(15,24)
            self.ui.getControl( DIGIT410 ).setHeight(40)
            self.ui.getControl( DIGIT410 ).setPosition(65,24)
            self.ui.getControl( DIGIT310 ).setVisible(1)
            self.ui.getControl( DIGIT410 ).setVisible(1)
            self.ui.getControl( DIGIT32 ).setVisible(1)
            self.ui.getControl( DIGIT42 ).setVisible(1)
            self.ui.getControl( DIGIT3 ).setVisible(0)
            self.ui.getControl( DIGIT4 ).setVisible(0)
            self.ui.getControl( DIGIT31 ).setVisible(1)
            self.ui.getControl( DIGIT41 ).setVisible(1)
            
            h = 40
            while (i<12):
                KODI_MONITOR.waitForAbort(.01)
                self.ui.getControl( FLIP2 ).setImage(os.path.join(CLOCK_LOC,str(i)+".png"))
                h = h-3
                self.ui.getControl( DIGIT310 ).setPosition(15,24+(40-h))
                self.ui.getControl( DIGIT310 ).setHeight(h)
                self.ui.getControl( DIGIT410 ).setPosition(65,24+(40-h))
                self.ui.getControl( DIGIT410 ).setHeight(h)
                i  =  i +1
            
            h = 43
            self.ui.getControl( DIGIT310 ).setVisible(0)
            self.ui.getControl( DIGIT410 ).setVisible(0)
            self.ui.getControl( DIGIT320 ).setHeight(3)
            self.ui.getControl( DIGIT320 ).setImage(os.path.join(DIGIT_LOC,str(self.new1)+"(2).png"))
            self.ui.getControl( DIGIT420 ).setHeight(3)
            self.ui.getControl( DIGIT420 ).setImage(os.path.join(DIGIT_LOC,str(self.new2)+"(2).png"))
            self.ui.getControl( DIGIT320 ).setVisible(1)
            self.ui.getControl( DIGIT420 ).setVisible(1)
            
            h = 3
            while (i<20):
                KODI_MONITOR.waitForAbort(.01)
                h = h+4
                self.ui.getControl( FLIP2 ).setImage(os.path.join(CLOCK_LOC,str(i)+".png"))
                self.ui.getControl( DIGIT320 ).setHeight(h)
                self.ui.getControl( DIGIT420 ).setHeight(h)
                i  =  i +1
            
            self.ui.getControl( DIGIT3 ).setImage(os.path.join(DIGIT_LOC,str(self.new1)+".png"))
            self.ui.getControl( DIGIT4 ).setImage(os.path.join(DIGIT_LOC,str(self.new2)+".png"))
            self.ui.getControl( DIGIT3 ).setVisible(1)
            self.ui.getControl( DIGIT4 ).setVisible(1)
            self.ui.getControl( DIGIT31 ).setVisible(0)
            self.ui.getControl( DIGIT32 ).setVisible(0)
            self.ui.getControl( DIGIT320 ).setVisible(0)
            self.ui.getControl( DIGIT41 ).setVisible(0)
            self.ui.getControl( DIGIT42 ).setVisible(0)
            self.ui.getControl( DIGIT420 ).setVisible(0)
            self.ui.getControl( FLIP2 ).setVisible(0)
          
          
    class MoveClock(threading.Thread):
        def __init__(self, ui):
            threading.Thread.__init__(self)
            self.ui  =  ui
            
            
        def run(self):
            i  = 0
            while not KODI_MONITOR.abortRequested() and not self.ui.terminate:
                i = i+1
                if (i>4):
                    i = 0
                    x  =  random.randint(0,990)
                    y  =  random.randint(0,570)
                    self.ui.getControl( CLOCK ).setPosition(x,y)
            
                if KODI_MONITOR.waitForAbort(1):
                    break
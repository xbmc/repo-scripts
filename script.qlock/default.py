
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

import os
import sys
import xbmcaddon, xbmc
from xbmcgui import Window
from xml.dom import minidom
import datetime
import time

__scriptname__ = "Qlock"
__author__     = "Amet"
__settings__   = xbmcaddon.Addon(id='script.qlock')
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')
__layoutDir__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'layout' ) )

if xbmc.getLanguage() in (os.listdir(__layoutDir__)):
  layout = xbmc.getLanguage()
else:
  layout = "English"   

__layoutFile__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'layout',layout,"layout.xml" ) )         
__selfRun__    = 'XBMC.AlarmClock(%s,%s,%i,True)' % (__scriptname__, 'XBMC.RunScript(script.qlock,-update)', 4 )

class Main:
  WINDOW = Window( 10000 )

  def __init__( self ):
      
    self.dom = minidom.parse(__layoutFile__)
    data = self.dom.getElementsByTagName("background")
    self.background = data[0].getAttribute("all").split(",")
    self.now = datetime.datetime.now()

    if (sys.argv[1] == '-startup'):
      self.log("%s -startup" % __scriptname__ )
      self.drawBackground()
      self.drawHighlight()
      self.loop()
      
    if (sys.argv[1] == '-update'):
      self.log( "%s -update" % __scriptname__ )
      self.drawHighlight()
      self.loop()
   
  def waiter(self,seconds):
    for i in range(1, seconds):
      time.sleep(1)
      if xbmc.abortRequested == True:
        sys.exit()

  def loop(self):
    self.log( "Running loop" )
    wait = 3
    while 1:               
      self.log( "Delaying %s secs" % wait )
      self.waiter(wait)
      if datetime.datetime.now().minute >= ((self.now.minute/5) * 5)+5 or (datetime.datetime.now().hour > self.now.hour) or (datetime.datetime.now().hour == 1 and self.now.hour == 12) or (datetime.datetime.now().hour == 0 and self.now.hour == 23) :
        self.drawHighlight()
        xbmc.executebuiltin(__selfRun__)
        self.log( "Set alarm" )
        break
      else:
        diff = ((self.now.minute/5) * 5)+5 - datetime.datetime.now().minute
        if diff > 1:
          wait = (diff-1)*60
        else:
          wait = 3    

  def drawBackground(self):
    for i in range(len(self.background)):
      self.WINDOW.setProperty( "Qlock.%i.Background" % (i+1), self.background[i])
      
  def drawHighlight(self):
    self.now = datetime.datetime.now()   
    for i in range (1,111):
      self.WINDOW.clearProperty("Qlock.%i.Highlight" % i) 
    
    times = self.dom.getElementsByTagName("time")

    minute = "m%.2d" % ((self.now.minute/5) * 5)
    
    if self.now.minute > 19 and self.now.minute != 0 :
      to = int(times[0].getAttribute("shiftOn20"))
      if self.now.minute > 34 and self.now.minute != 0:
        to += int(times[0].getAttribute("shiftOnHalfHour"))
    else:
      to = 0 
    
    if self.now.hour >= 12:
      hour = "h%.2d" % (self.now.hour - 12 + to + int(times[0].getAttribute("shiftHour")))
    else:
      hour = "h%.2d" % (self.now.hour + to + int(times[0].getAttribute("shiftHour")))
    
    if hour == "h00":
      hour = "h12"
           
    highlight = times[0].getAttribute(minute).split(",") + times[0].getAttribute("all").split(",") + times[0].getAttribute(hour).split(",")

    for l in highlight:
     self.WINDOW.setProperty( "Qlock.%s.Highlight" % l.replace(" ",""), self.background[int(l)-1] )

  def log(self,msg):
    xbmc.output("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )

if ( __name__ == "__main__" ):
   Main()

  
  
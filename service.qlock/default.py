
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
__author__     = "amet"
__settings__   = xbmcaddon.Addon()
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')
__layoutDir__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'layout' ) )

WINDOW         = Window( 10000 )
STARTUP        = True

now = datetime.datetime.now()
check_lang = xbmc.getLanguage()

def getLanguage():
  if xbmc.getLanguage() in (os.listdir(__layoutDir__)):
    lang = xbmc.getLanguage()
  else:
    lang = "English"

  __layoutFile__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'layout',lang,"layout.xml" ) )
  dom = minidom.parse(__layoutFile__)
  data = dom.getElementsByTagName("background")
  background = data[0].getAttribute("all").split(",")
  log( "Set new Language - [%s]" % lang )
  return background, dom, lang

def waiter(background, dom, seconds, lang, check_lang):
  log( "Delaying %s secs" % seconds )
  for i in range(1, seconds):
    time.sleep(1)
    if xbmc.abortRequested == True:
      sys.exit()
      
    if check_lang != xbmc.getLanguage(): # check if xbmc language changed while we are waiting
      check_lang = xbmc.getLanguage()  
      background, dom, lang = getLanguage()
      drawBackground(background)
      drawHighlight(background, dom)

  return background, dom, check_lang

def drawBackground(background):
  for i in range(len(background)):
    WINDOW.setProperty( "Qlock.%i.Background" % (i+1), background[i])
    
def drawHighlight(background, dom):
  now = datetime.datetime.now()   
  for i in range (1,111):
    WINDOW.clearProperty("Qlock.%i.Highlight" % i) 
  
  times = dom.getElementsByTagName("time")

  minute = "m%.2d" % ((now.minute/5) * 5)
  
  if now.minute > 19 and now.minute != 0 :
    to = int(times[0].getAttribute("shiftOn20"))
    if now.minute > 34 and now.minute != 0:
      to += int(times[0].getAttribute("shiftOnHalfHour"))
    if now.minute > 24 and now.minute != 0:
      try:
        to += int(times[0].getAttribute("shiftOn25"))
      except:
        pass
  else:
    to = 0 
  
  if now.hour >= 12:
    hour = "h%.2d" % (now.hour - 12 + to + int(times[0].getAttribute("shiftHour")))
  else:
    hour = "h%.2d" % (now.hour + to + int(times[0].getAttribute("shiftHour")))
  
  if hour == "h00":
    hour = "h12"
         
  if xbmc.getLanguage() == "German" and hour == "h01" and minute == "m00":  # German only, at one o'clock
    highlight = ["1","2","4","5","6","45","46","47","108","109","110"]
  else:
    highlight = times[0].getAttribute(minute).split(",") + times[0].getAttribute("all").split(",") + times[0].getAttribute(hour).split(",")

  for l in highlight:
   WINDOW.setProperty( "Qlock.%s.Highlight" % l.replace(" ",""), background[int(l)-1] )

def log(msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )


while (not xbmc.abortRequested):
  if STARTUP:
    background, dom, lang = getLanguage()
    drawBackground(background)
    drawHighlight(background, dom)
    STARTUP = False
    log( "Startup" )
    diff = ((now.minute/5) * 5)+5 - datetime.datetime.now().minute
    if diff > 1:
      wait = (diff-1)*60
      background, dom, check_lang = waiter(background, dom, wait, lang, check_lang)

  if datetime.datetime.now().minute >= ((now.minute/5) * 5)+5 or (datetime.datetime.now().hour > now.hour) or (datetime.datetime.now().hour == 1 and now.hour == 12) or (datetime.datetime.now().hour == 0 and now.hour == 23) :
    drawHighlight(background, dom)
    wait = 240
  else:
    wait = 3
  background, dom, check_lang = waiter(background, dom, wait, lang, check_lang)
  
  
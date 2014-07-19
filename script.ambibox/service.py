# -*- coding: utf-8 -*-
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
# *  along with this program; see the file LICENSE.txt.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *#Modules General
from ambibox import AmbiBox

# Modules XBMC
import xbmcgui, xbmcaddon

__settings__ = xbmcaddon.Addon("script.ambibox")
__language__ = __settings__.getLocalizedString
#########################################################################################################
## BEGIN
#########################################################################################################
ambibox = AmbiBox(__settings__.getSetting("host"), int(__settings__.getSetting("port")))
ambibox.connect()    
showmenu = __settings__.getSetting("show_menu")
menu = ambibox.getProfiles()
menu.append(__language__(32021))  # @[Backlight off] 
menu.append(__language__(32022))  # @[Backlight on] 
if (showmenu == "false"): 
    menu.append(__language__(32023))  # @[Show menu when playing] 
else:
    menu.append(__language__(32024))  # @[Do not show menu when playing] 

off = len(menu)-3 
on = len(menu)-2
show = len(menu)-1
quit = False
selected = xbmcgui.Dialog().select(__language__(32020), menu)  # @[Select profile] 
if selected != -1: 
    if (show == int(selected)):        
        if (showmenu == "false"):
            __settings__.setSetting("show_menu", "true")
        else:
            __settings__.setSetting("show_menu", "false")
    else:
        ambibox.lock()
        if (off == int(selected)):
            ambibox.turnOff() 
        elif (on == int(selected)):
            ambibox.turnOn() 
        else:
            #ambibox.turnOn()
            ambibox.setProfile(menu[selected])
        ambibox.unlock()
ambibox.disconnect()   


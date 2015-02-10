# Copyright (C) 2011 Malte Loepmann (maloep@googlemail.com)
#
# This program is free software; you can redistribute it and/or modify it under the terms 
# of the GNU General Public License as published by the Free Software Foundation; 
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; 
# if not, see <http://www.gnu.org/licenses/>.

import os
import xbmc, xbmcaddon


def checkStartupAction():
	
	#get access to RCB
	rcbAddon = None
	try:
		rcbAddon = xbmcaddon.Addon(id='script.games.rom.collection.browser')
	except:
		print 'RCB Service: Error while accessing "script.games.rom.collection.browser". Make sure the addon is installed.'
		return
		
	launchOnStartup = rcbAddon.getSetting('rcb_launchOnStartup')
	print 'RCB Service: launch RCB on startup = ' +str(launchOnStartup)
	
	if(launchOnStartup.lower() == 'true'):
		startupDelay = int(float(rcbAddon.getSetting('rcb_startupDelay')))
		xbmc.sleep(startupDelay)
		path = os.path.join(rcbAddon.getAddonInfo('path'), 'default.py')
		print 'RCB Service: launch RCB ' +str(path)
		xbmc.executescript("%s" %path)
		return
	
	#check scrape on XBMC startup setting	
	scrapeOnStart = rcbAddon.getSetting('rcb_scrapOnStartUP')
	print 'RCB Service: scrape games on startup = ' +str(scrapeOnStart)
	
	if(scrapeOnStart.lower() == 'true'):
		#launch dbUpdate
		path = os.path.join(rcbAddon.getAddonInfo('path'), 'dbUpLauncher.py')
		print 'RCB Service: Starting DB Update' +str(path)
		xbmc.executescript("%s" %path)
		

print 'RCB Service: Start'
checkStartupAction()
print 'RCB Service: Done'
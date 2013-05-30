
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

import xbmc,xbmcgui
import subprocess,os
import random
import simplejson as json
import xbmcaddon
addon = xbmcaddon.Addon("service.trailer.screensaver")
PATH = addon.getAddonInfo('path')
RESOURCES_PATH = xbmc.translatePath( os.path.join( PATH, 'resources' ) ).decode('utf-8')
MEDIA_PATH = xbmc.translatePath( os.path.join( RESOURCES_PATH, 'media' ) ).decode('utf-8')
OPEN_CURTAIN_PATH = xbmc.translatePath( os.path.join( MEDIA_PATH, 'CurtainOpeningSequence.flv' ) ).decode('utf-8')
CLOSE_CURTAIN_PATH = xbmc.translatePath( os.path.join( MEDIA_PATH, 'CurtainClosingSequence.flv' ) ).decode('utf-8')
PLAYED_TRAILERS = False

def playTrailers():
	DO_CURTIANS = addon.getSetting('do_animation')
	DO_MUTE = addon.getSetting('do_mute')
	NUMBER_TRAILERS =  int(addon.getSetting('number_trailers'))
	xbmc.log('Getting Trailers')
	trailerstring = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "properties": ["trailer"]}, "id": 1}')
	trailerstring = unicode(trailerstring, 'utf-8', errors='ignore')
	trailers = json.loads(trailerstring)
	trailerList =[]
	playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
	playlist.clear()
	for trailer in trailers["result"]["movies"]:
		if not trailer["trailer"] == '':
			trailerList.append(trailer["trailer"])
	random.shuffle(trailerList)
	if DO_CURTIANS == 'true':
		playlist.add(OPEN_CURTAIN_PATH)
	trailercount=0
	for trailer in trailerList:
		trailercount=trailercount+1
		playlist.add(trailer)
		if trailercount == NUMBER_TRAILERS:
			break
	if DO_CURTIANS == 'true':
		playlist.add(CLOSE_CURTAIN_PATH)
	xbmc.Player().play(playlist)
	if DO_MUTE == 'true':
		xbmc.executebuiltin('xbmc.Mute()')
	while(not xbmc.abortRequested):
		if xbmc.Player().isPlayingVideo:
			TIMEOUT = int(addon.getSetting('idle_time_min'))*60
			IDLE_TIME = xbmc.getGlobalIdleTime()
			if IDLE_TIME < TIMEOUT:
				xbmc.executebuiltin('xbmc.PlayerControl(Stop)')
				if DO_MUTE == 'true':
					xbmc.executebuiltin('xbmc.Mute()')
				break
		xbmc.sleep(1000)

class blankScreen(xbmcgui.Window):
	def __init__(self):
		pass

bs = blankScreen()		
IDLE_TIME = 0
while(not xbmc.abortRequested ):
	#Check for User Activity and reset timer
	if xbmc.getGlobalIdleTime() <= 5:
		IDLE_TIME = 0
	TIMEOUT = int(addon.getSetting('idle_time_min'))*60
	if IDLE_TIME < TIMEOUT:
		PLAYED_TRAILERS = False
		del bs
		bs = blankScreen()
	if IDLE_TIME > TIMEOUT:
		if not xbmc.Player().isPlaying():
			if not PLAYED_TRAILERS:
				PLAYED_TRAILERS = True
				bs.show()
				playTrailers()
	#Reset IDLE_TIME if something is playing.
	if xbmc.Player().isPlaying():
		IDLE_TIME=0
	else:
		IDLE_TIME = IDLE_TIME + 1
	xbmc.sleep(1000)


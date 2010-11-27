import os
import sys
import xbmcplugin
import xbmc
import xbmcgui
import traceback
import threading
from datetime import datetime

class tools(object):
	def __init__(self):
		pass
	def loadParameters(self, params):
		self.cmds = {}
		splitCmds = params[params.find('?')+1:].split('&')    
		for cmd in splitCmds: 
			if (len(cmd) > 0):
				splitCmd = cmd.split('=')
				name = splitCmd[0]
				value = splitCmd[1]
				self.cmds[name] = value

	def getCmd(self, cmd):
		if cmd in self.cmds:
			return self.cmds[cmd]
		else:
			return None

__scriptid__ = "script.audio.grooveshark"
__scriptname__ = "GrooveShark"
__author__ = "Solver"
__url__ = "http://code.google.com/p/grooveshark-for-xbmc/"
__svn_url__ = ""
__credits__ = ""
__XBMC_Revision__ = "31000"

try: #It's an XBOX/pre-dharma
	__cwd__ = os.getcwd()
	__settings__ = xbmc.Settings(path=__cwd__)
	__language__ = xbmc.Language(__cwd__.replace( ";", "" )).getLocalizedString
	__debugging__ = __settings__.getSetting("debug")
	__isXbox__ = True
	__version__ = "0.3.1"
	BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib' ))
	print 'GrooveShark: Initialized as a XBOX plugin'

except: #It's post-dharma
	import xbmcaddon
	__settings__ = xbmcaddon.Addon(id=__scriptid__)
	__language__ = __settings__.getLocalizedString
	__debugging__ = __settings__.getSetting("debug")
	__isXbox__ = False
	__version__ = __settings__.getAddonInfo('version')
	BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(__settings__.getAddonInfo('path'), 'resources', 'lib' ))
	__cwd__ = __settings__.getAddonInfo('path')
	print 'GrooveShark: Initialized as a post-dharma plugin'
	#traceback.print_exc()

#__isXbox__ = True

if __isXbox__ == True:
	__settings__.setSetting("xbox", "true")
else:
	__settings__.setSetting("xbox", "false")

if __debugging__ == 'true':
	__debugging__ = True
	print 'GrooveShark: Debugging enabled'
else:
	__debugging__ = False
	print 'GrooveShark: Debugging disabled'

sys.path.append(BASE_RESOURCE_PATH)

def startGUI():
	print "GrooveShark version " + str(__version__)
	w = GrooveClass("grooveshark.xml", __cwd__, "DefaultSkin", isXbox = __isXbox__)
	w.doModal()
	del w
	print 'GrooveShark: Closed'
	sys.modules.clear()

if __isXbox__ == True:
	if __name__ == "__main__":
		from GrooveShark import *
		startGUI()
else: 
	if len(sys.argv) == 3:#Run as a plugin to open datastreams
		from GrooveAPI import *
		import xbmcplugin
		import xbmcgui
		import traceback
		try:
			tools = tools()
			tools.loadParameters(sys.argv[2])
			gs = GrooveAPI()
			get = tools.getCmd
			songId = get('playSong')
			playlist = get('playlist')
			options = get('options')
			radio = get('radio')
			if (playlist != None): # To be implemented...
				#listitem=xbmcgui.ListItem('Playlists')#, iconImage=icon, thumbnailImage=thumbnail )
				#listitem.addContextMenuItems( cm, replaceItems=True )
				#listitem.setProperty( "Folder", "true" )
				#xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url='plugin://script.audio.grooveshark/?playSong=409361', listitem=listitem, isFolder=False, totalItems=1)
				#xbmcplugin.endOfDirectory( handle=int( sys.argv[ 1 ] ), succeeded=True, cacheToDisc=False )
				pass
			
			elif (songId != None):
				print 'GrooveShark: Song ID: ' + str(songId)
				url = gs.getStreamURL(str(songId))
				if url != "":
					listitem=xbmcgui.ListItem(label='music', path=url)
					listitem.setInfo(type='Music', infoLabels = {'url': url})
					listitem.setProperty('mimetype', 'audio/mpeg')
					if options == 'radio':
						print 'GrooveShark: Radio mode'
						gs.radioSetAlreadyListenedSong(songId = songId) # Set this song as listened to
						playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
						playlist.clear()
						song = gs.radioGetNextSong()
						if song != None:
							song = song[0]
							songId = song[1]
							title = song[0]
							albumId = song[4]
							artist = song[6]
							artistId = song[7]
							album = song[3]
							duration = song[2]
							cover = song[9] # Medium image
							try:
								duration = int(duration)
							except:
								duration = 0
							url = 'plugin://%s/?playSong=%s&artistId=%s&options=%s' % (__scriptid__, songId, artistId, 'radio')
							listitemNext=xbmcgui.ListItem(label=title, iconImage=cover, thumbnailImage=cover, path=url)
							listitemNext.setInfo(type='Music', infoLabels = { 'title': title, 'artist': artist, 'album': album , 'url': url})
							listitemNext.setProperty('mimetype', 'audio/mpeg')
							listitemNext.setProperty('IsPlayable', 'true')
							playlist.add(url, listitemNext, 0)
					print 'GrooveShark: Found stream url: (' + url + ')'
					xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=listitem)
				else:
					print 'GrooveShark: No stream url returned for song id'
					listitem=xbmcgui.ListItem(label='music', path='')
					xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, listitem)
			elif (radio != None):
				print 'GrooveShark: Radio'
				song = gs.radioGetNextSong()
				if song != None:
					song = song[0]
					songId = song[1]
					title = song[0]
					albumId = song[4]
					artist = song[6]
					cover = song[9] # Medium image
					url = gs.getStreamURL(str(songId))
					listitem=xbmcgui.ListItem(label=title, iconImage=cover, thumbnailImage=cover, path=url)
					listitem.setInfo(type='Music', infoLabels = { 'title': title, 'artist': artist , 'url': url})
					listitem.setProperty('mimetype', 'audio/mpeg')
					xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=listitem)					
				else:
					xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=None)

			else:
				listitem=xbmcgui.ListItem(label='music', path='')
				xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=listitem)
				print 'GrooveShark: Unknown command'
		except:
			print 'GrooveShark: Exception thrown when determining stream url for song id'
			listitem=xbmcgui.ListItem(label='music', path='')
			xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=listitem)
			traceback.print_exc()
	else:
		if __name__ == "__main__":
			from GrooveShark import *
			startGUI()


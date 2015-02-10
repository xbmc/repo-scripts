from threading import Timer
import xbmc
import xbmcaddon
import os, sys

_settings   = xbmcaddon.Addon()
_name       = _settings.getAddonInfo('name')
_version    = _settings.getAddonInfo('version')
_path       = xbmc.translatePath( _settings.getAddonInfo('path') ).decode('utf-8')
_lib        = xbmc.translatePath( os.path.join( _path, 'resources', 'lib' ) )

sys.path.append (_lib)

from utils import *

_NAME = _name.upper()

class PandaPlayer( xbmc.Player ):

	def __init__( self, core=None, panda=None ):
		xbmc.Player.__init__( self )
		self.panda = panda
		self.timer = None
		self.playNextSong_delay = 0.5

	def playSong( self, item ):
		log( "playSong: item[url] %s" % item[0], xbmc.LOGDEBUG )
		log( "playSong: item[item] %s" % item[1], xbmc.LOGDEBUG )
		self.play( item[0], item[1] )

	def play( self, url, item ):
		# override play() to force use of PLAYER_CORE_MPLAYER
		xbmc.Player( xbmc.PLAYER_CORE_MPLAYER ).play( url, item )

		# NOTE: using PLAYER_CORE_MPLAYER is necessary to play .mp4 streams (low & medium quality from Pandora)
		#   ... unfortunately, using "xbmc.Player([core]) is deprecated [ see URLref: http://forum.xbmc.org/showthread.php?tid=173887&pid=1516662#pid1516662 ]
		#   ... and it may be removed from Gotham [ see URLref: https://github.com/xbmc/xbmc/pull/1427 ]
		# ToDO: discuss with the XBMC Team what the solution to this problem would be

	def onPlayBackStarted( self ):
		log( "onPlayBackStarted: %s" %self.getPlayingFile(), xbmc.LOGDEBUG )
		if self.panda.playing:
			# ToDO: ? remove checks for pandora.com / p-cdn.com (are they needed? could be a maintainence headache if the cdn changes...)
			if not "pandora.com" in self.getPlayingFile():
				if not "p-cdn.com" in self.getPlayingFile():
					self.panda.playing = False
					self.panda.quit()
			else:
				# show visualization (disappears after each song...)
				xbmc.executebuiltin( "ActivateWindow( 12006 )" )

	def onPlayBackEnded( self ):
		log( "onPlayBackEnded", xbmc.LOGDEBUG )
		self.stop()
		log( "playing = %s" %self.panda.playing, xbmc.LOGDEBUG )
		if self.timer and self.timer.isAlive():
			self.timer.cancel()
		if self.panda.skip:
			self.panda.skip = False
		if self.panda.playing:
			self.timer = Timer( self.playNextSong_delay, self.panda.playNextSong )
			self.timer.start()

	def onPlayBackStopped( self ):
		log( "onPlayBackStopped", xbmc.LOGDEBUG )
		self.stop()
		log( "playing = %s" %self.panda.playing, xbmc.LOGDEBUG )
		if self.timer and self.timer.isAlive():
			self.timer.cancel()
		if self.panda.playing and self.panda.skip:
			self.panda.skip = False
			self.timer = Timer( self.playNextSong_delay, self.panda.playNextSong )
			self.timer.start()
		else:
			if xbmc.getCondVisibility('Skin.HasSetting(PandoraVis)'):
				# turn off visualization
				xbmc.executebuiltin('Skin.Reset(PandoraVis)')
			self.panda.stop()

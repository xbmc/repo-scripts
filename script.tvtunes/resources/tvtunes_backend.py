# -*- coding: utf-8 -*-
#Modules General
import threading
from traceback import print_exc
import time
import os
#Modules XBMC
import xbmc
import xbmcgui
import sys
import xbmcvfs
import xbmcaddon

__addon__     = xbmcaddon.Addon(id='script.tvtunes')
__addonid__   = __addon__.getAddonInfo('id')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def normalize_string( text ):
    try: text = unicodedata.normalize( 'NFKD', _unicode( text ) ).encode( 'ascii', 'ignore' )
    except: pass
    return text

try:
    # parse sys.argv for params
    log( sys.argv[ 1 ] )
    try:params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:
        print_exc()
        params = dict( sys.argv[ 1 ].split( "=" ))
except:
    # no params passed
    print_exc()
    params = {} 
class mythread( threading.Thread ):
    def __init__( self ):
        threading.Thread.__init__( self )
        self._stop = False
        log( "### starting TvTunes Backend ###" )
        self.newpath = ""
        self.oldpath = ""
        self.playpath = ""
        self.prevplaypath = ""
        self.loud = False
        self.enable_custom_path = __addon__.getSetting("custom_path_enable")
        if self.enable_custom_path == "true":
            self.custom_path = __addon__.getSetting("custom_path")
        self.base_volume = self.get_volume()
        
        
    def run( self ):
        try:
            while not self._stop:           # the code
                if not xbmc.getCondVisibility( "Window.IsVisible(10025)"): self.stop()      #destroy threading

                if xbmc.getCondVisibility( "Container.Content(Seasons)" ) or xbmc.getCondVisibility( "Container.Content(Episodes)" ) and not xbmc.Player().isPlaying() and "plugin://" not in xbmc.getInfoLabel( "ListItem.Path" ) and not xbmc.getInfoLabel( "container.folderpath" ) == "videodb://5/":
                    if self.enable_custom_path == "true":
                        tvshow = xbmc.getInfoLabel( "ListItem.TVShowTitle" ).replace(":","")
                        tvshow = normalize_string( tvshow )
                        self.newpath = os.path.join(self.custom_path, tvshow).decode("utf-8")
                    else:
                        self.newpath = xbmc.getInfoLabel( "ListItem.Path" )
                    if not self.newpath == self.oldpath and not self.newpath == "" and not self.newpath == "videodb://2/2/":
                        log( "### old path: %s" % self.oldpath )
                        log( "### new path: %s" % self.newpath )
                        self.oldpath = self.newpath
                        if not xbmc.Player().isPlaying() : self.start_playing()
                        else: log( "### player already playing" )

                if xbmc.getInfoLabel( "Window(10025).Property(TvTunesIsAlive)" ) == "true" and not xbmc.Player().isPlaying():
                    log( "### playing ends" )
                    if self.loud: self.raise_volume()
                    xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')

                if xbmc.getCondVisibility( "Container.Content(tvshows)" ) and self.playpath and not xbmc.getCondVisibility( "Window.IsVisible(12003)" ):
                    log( "### reinit condition" )
                    self.newpath = ""
                    self.oldpath = ""
                    self.playpath = ""
                    log( "### stop playing" )
                    if __addon__.getSetting("fade") == 'true':
                        self.fade_out()
                    else:
                        xbmc.Player().stop()
                    if self.loud: self.raise_volume()
                    xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')

                if xbmc.getInfoLabel( "container.folderpath" ) == "videodb://2/2/":
                    # clear the last tune path if we are back at the root of the tvshow library
                    self.prevplaypath = ""

                time.sleep( .5 )
        except:
            print_exc()
            self.stop()

    def get_volume( self ):
        try: volume = int(xbmc.getInfoLabel('player.volume').split(".")[0])
        except: volume = int(xbmc.getInfoLabel('player.volume').split(",")[0])
        log( "### current volume: %s%%" % (( 60 + volume )*(100/60.0)) )
        return volume

    def lower_volume( self ):
        try:
            self.base_volume = self.get_volume()
            self.loud = True
            vol = ((60+self.base_volume-int( params.get("downvolume", 0 )) )*(100/60.0))
            if vol < 0 : vol = 0
            log( "### volume goal: %s%% " % vol )
            xbmc.executebuiltin('XBMC.SetVolume(%d)' % vol)
            log( "### down volume to %d%%" % vol )
        except:
            print_exc()

    def raise_volume( self ):
        self.base_volume = self.get_volume()
        vol = ((60+self.base_volume+int( params.get("downvolume", 0 )) )*(100/60.0))
        log( "### volume goal : %s%% " % vol )
        log( "### raise volume to %d%% " % vol )
        xbmc.executebuiltin( 'XBMC.SetVolume(%d)' % vol )
        self.loud = False

    def fade_out( self ):
        cur_vol = self.get_volume()
        cur_vol_perc = 100 + (cur_vol * (100/60.0))
        vol_step = cur_vol_perc / 10
        # do not mute completely else the mute icon shows up
        for step in range (0,9):
            vol = cur_vol_perc - vol_step
            log( "### vol: %s" % str(vol) )
            xbmc.executebuiltin('XBMC.SetVolume(%d)' % vol)
            cur_vol_perc = vol
            xbmc.sleep(200)
        xbmc.Player().stop()
        # wait till player is stopped before raising the volume
        while xbmc.Player().isPlaying():
            xbmc.sleep(50)
        pre_vol_perc = 100 + (cur_vol * (100/60.0))
        xbmc.executebuiltin('XBMC.SetVolume(%d)' % pre_vol_perc)
        # wait till xbmc has adjusted the volume before continuing
        xbmc.sleep(200)

    def start_playing( self ):
        if params.get("smb", "false" ) == "true" and self.newpath.startswith("smb://") : 
            log( "### Try authentification share" )
            self.newpath = self.newpath.replace("smb://", "smb://%s:%s@" % (params.get("user", "guest" ) , params.get("password", "guest" )) )
            log( "### %s" % self.newpath )

        #######hack for episodes stored as rar files
        if 'rar://' in str(self.newpath):
            self.newpath = self.newpath.replace("rar://","")
        
        #######hack for TV shows stored as ripped disc folders
        if 'VIDEO_TS' in str(self.newpath):
            log( "### FOUND VIDEO_TS IN PATH: Correcting the path for DVDR tv shows" )
            uppedpath = self._updir( self.newpath, 3 )
            if xbmcvfs.exists( os.path.join ( uppedpath , "theme.mp3" )):
                self.playpath = os.path.join ( uppedpath , "theme.mp3" )
            else:
                self.playpath = os.path.join ( self._updir(uppedpath,1) , "theme.mp3" )
        #######end hack

        elif xbmcvfs.exists( os.path.join ( self.newpath , "theme.mp3" ) ):
            self.playpath = os.path.join ( self.newpath , "theme.mp3" )
        elif xbmcvfs.exists(os.path.join(os.path.dirname( os.path.dirname( self.newpath ) ) , "theme.mp3")):
            self.playpath = (os.path.join(os.path.dirname( os.path.dirname( self.newpath ) ) , "theme.mp3"))
        else: self.playpath = False

        if self.playpath:
            if self.playpath == self.prevplaypath: 
                return # don't play the same tune twice (when moving from season to episodes etc)
            self.prevplaypath = self.playpath
            if not self.loud: self.lower_volume()
            xbmcgui.Window( 10025 ).setProperty( "TvTunesIsAlive", "true" )
            log( "### start playing %s" % self.playpath )
            xbmc.Player().play(self.playpath)
            if params.get("loop", "false" ) == "true" : xbmc.executebuiltin('XBMC.PlayerControl(Repeat)')
            else: xbmc.executebuiltin('XBMC.PlayerControl(RepeatOff)')

        else: log( "### no theme found for %s or %s" % ( os.path.join( self.newpath , "theme.mp3" ) , os.path.join ( os.path.dirname( os.path.dirname ( self.newpath ) ) , "theme.mp3" ) ) )

    def _updir(self, thepath, x):
        # move up x directories on thepath
        while x > 0:
            x -= 1
            thepath = (os.path.split(thepath))[0]
        return thepath

    def stop( self ):
        if xbmc.getInfoLabel( "Window(10025).Property(TvTunesIsAlive)" ) == "true" and not xbmc.Player().isPlayingVideo(): 
            log( "### stop playing" )
            xbmc.Player().stop()
        xbmcgui.Window( 10025 ).clearProperty('TvTunesIsRunning')
        xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')
        
        if self.loud: self.raise_volume()
        log( "### Stopping TvTunes Backend ###" )
        self._stop = True


xbmcgui.Window( 10025 ).setProperty( "TvTunesIsRunning", "true" )
thread = mythread()
# start thread
thread.start()

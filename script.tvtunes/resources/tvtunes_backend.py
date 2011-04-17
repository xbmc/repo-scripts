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

try:
    # parse sys.argv for params
    print sys.argv[ 1 ]
    try:params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:
        print_exc()
        params =  dict( sys.argv[ 1 ].split( "=" ))
except:
    # no params passed
    print_exc()
    params = {} 
class mythread( threading.Thread ):
    def __init__( self ):
        threading.Thread.__init__( self )
        self._stop = False
        print "### starting TvTunes Backend ###"
        self.newpath = ""
        self.oldpath = ""
        self.playpath = ""
        self.loud = False
        self.base_volume = self.get_volume()
        
        
    def run( self ):        
        try:             
            while not self._stop:           # le code                
                if not xbmc.getCondVisibility( "Window.IsVisible(10025)"): self.stop()      #destroy threading
                    
                if xbmc.getCondVisibility( "Container.Content(Seasons)" ) or xbmc.getCondVisibility( "Container.Content(Episodes)" ) and not xbmc.Player().isPlaying() and "plugin://" not in xbmc.getInfoLabel( "ListItem.Path" ) and not xbmc.getInfoLabel( "container.folderpath" ) == "videodb://5/":
                    self.newpath = xbmc.getInfoLabel( "ListItem.Path" )
                    if not self.newpath == self.oldpath and not self.newpath == "" and not self.newpath == "videodb://2/2/":
                        print "### old path: %s" % self.oldpath
                        print "### new path: %s" % self.newpath
                        self.oldpath = self.newpath
                        if not xbmc.Player().isPlaying() : self.start_playing()
                        else: print "### player already playing"
                        
                if xbmc.getInfoLabel( "Window(10025).Property(TvTunesIsAlive)" ) == "true" and not xbmc.Player().isPlaying():
                    print "### playing ends"
                    if self.loud: self.raise_volume()
                    xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')
                    
                if xbmc.getCondVisibility( "Container.Content(tvshows)" ) and self.playpath and not xbmc.getCondVisibility( "Window.IsVisible(12003)" ):
                    print "### reinit condition"
                    self.newpath = ""
                    self.oldpath = ""
                    self.playpath = ""
                    print "### stop playing"
                    xbmc.Player().stop()
                    if self.loud: self.raise_volume()
                    xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')
                    
                time.sleep( .5 )
        except:
            print_exc()
            self.stop()
            
    def get_volume( self ):
        try: volume = int(xbmc.getInfoLabel('player.volume').split(".")[0])
        except: volume = int(xbmc.getInfoLabel('player.volume').split(",")[0])
        print "### current volume: %s%%" % (( 60 + volume )*(100/60.0))
        return volume
        
    def lower_volume( self ):
        try:
            self.base_volume = self.get_volume()
            self.loud = True
            vol = ((60+self.base_volume-int( params.get("downvolume", 0 )) )*(100/60.0))
            if vol < 0 : vol = 0
            print "### volume goal: %s%% " % vol
            xbmc.executebuiltin('XBMC.SetVolume(%d)' % vol)
            print "### down volume to %d%%" % vol
        except:
            print_exc()
            
    def raise_volume( self ):
        self.base_volume = self.get_volume()
        vol = ((60+self.base_volume+int( params.get("downvolume", 0 )) )*(100/60.0))
        print "### volume goal : %s%% " % vol
        print "### raise volume to %d%% " % vol
        xbmc.executebuiltin( 'XBMC.SetVolume(%d)' % vol )  
        self.loud = False
        
    def start_playing( self ):     
        if params.get("smb", "false" ) == "true" and self.newpath.startswith("smb://") : 
            print "### Try authentification share"
            self.newpath = self.newpath.replace("smb://", "smb://%s:%s@" % (params.get("user", "guest" ) , params.get("password", "guest" )) )
            print "### %s" % self.newpath
        if os.path.exists( os.path.join (self.newpath , "theme.mp3" ) ):
            self.playpath = os.path.join (self.newpath , "theme.mp3" )
        elif os.path.exists(os.path.join(os.path.dirname( os.path.dirname( self.newpath ) ) , "theme.mp3")):                                
            self.playpath = (os.path.join(os.path.dirname( os.path.dirname( self.newpath ) ) , "theme.mp3"))
        else: self.playpath = False
        if self.playpath:
            if not self.loud: self.lower_volume()
            xbmcgui.Window( 10025 ).setProperty( "TvTunesIsAlive", "true" )
            print "### start playing %s" % self.playpath
            xbmc.Player().play(self.playpath)
            if params.get("loop", "false" ) == "true" : xbmc.executebuiltin('XBMC.PlayerControl(Repeat)')
            else: xbmc.executebuiltin('XBMC.PlayerControl(RepeatOff)')             
        else: print "### no theme found for %s or %s" % ( os.path.join( self.newpath , "theme.mp3" ) , os.path.join ( os.path.dirname( os.path.dirname ( self.newpath ) ) , "theme.mp3" ) )
 
    def stop( self ):
        if xbmc.getInfoLabel( "Window(10025).Property(TvTunesIsAlive)" ) == "true" and not xbmc.Player().isPlayingVideo(): 
            print "### stop playing"
            xbmc.Player().stop()
        xbmcgui.Window( 10025 ).clearProperty('TvTunesIsRunning')
        xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')
        
        if self.loud: self.raise_volume()
        print "### Stopping TvTunes Backend ###"
        self._stop = True
        
xbmcgui.Window( 10025 ).setProperty( "TvTunesIsRunning", "true" )
thread = mythread()
# start thread
thread.start()


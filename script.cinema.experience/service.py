import xbmc, xbmcaddon, xbmcgui, xbmcvfs
import os, sys, traceback

__addon__                = xbmcaddon.Addon( 'script.cinema.experience' )
__version__              = __addon__.getAddonInfo('version')
__scriptID__             = __addon__.getAddonInfo('id')
__script__               = __addon__.getAddonInfo('name')
__addonname__            = __script__
BASE_CACHE_PATH          = os.path.join( xbmc.translatePath( "special://profile" ).decode('utf-8'), "Thumbnails", "Video" )
BASE_CURRENT_SOURCE_PATH = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), os.path.basename( __addon__.getAddonInfo('path') ) )
BASE_RESOURCE_PATH       = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path').decode('utf-8'), 'resources' ) )
home_automation_folder   = os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts" )
home_automation_module   = os.path.join( home_automation_folder, "home_automation.py" )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )

import utils
from settings import *
settings = settings()
original_settings = settings.read_settings_xml()

trivia_settings  = settings.trivia_settings
trailer_settings = settings.trailer_settings
ha_settings      = settings.ha_settings
video_settings   = settings.video_settings
audio_formats    = settings.audio_formats
extra_settings   = settings.extra_settings
_3d_settings     = settings._3d_settings
triggers         = settings.triggers

#Check to see if module is moved to /userdata/addon_data/script.cinema.experience

if not xbmcvfs.exists( os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts", "home_automation.py" ) ) and ha_settings[ "ha_enable" ]:
    source = os.path.join( BASE_RESOURCE_PATH, "ha_scripts", "home_automation.py" )
    destination = os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts", "home_automation.py" )
    xbmcvfs.mkdir( os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts" ) )        
    xbmcvfs.copy( source, destination )
    utils.log( "home_automation.py copied" )

from launch_automation import Launch_automation

class CE_Monitor( xbmc.Monitor ):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.original_settings = settings.read_settings_xml()
        self.enabled = kwargs['enabled']
        self.update_settings = kwargs['update_settings']
        
    def onSettingsChanged( self ):
        try:
            xbmc.sleep( 10000 )
            if not self.original_settings == settings.read_settings_xml():
                self.new_settings = self.update_settings( self.original_settings )
                self.original_settings = self.new_settings
        except:
            traceback.print_exc()
        
class CE_Player( xbmc.Player ):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__( self )
        self.enabled = kwargs['enabled']
    
    def onPlayBackStarted( self ):
        xbmc.sleep( 500 )
        if xbmcgui.Window( 10025 ).getProperty( "CinemaExperienceRunning" ) == "True":
            utils.log( 'Playback Started' )
    
    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        if xbmcgui.Window( 10025 ).getProperty( "CinemaExperienceRunning" ) == "True":
            utils.log( "Playback Ended" )
    
    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        if xbmcgui.Window( 10025 ).getProperty( "CinemaExperienceRunning" ) == "True":
            utils.log( "Playback Stopped" )
    
    def onPlayBackPaused( self ):
        if xbmcgui.Window( 10025 ).getProperty( "CinemaExperienceRunning" ) == "True":
            utils.log( 'Playback Paused' )
            if ha_settings[ "ha_enable" ]:
                Launch_automation().launch_automation( trigger = "Pause", prev_trigger = "Playing", mode = "normal" )
    
    def onPlayBackResumed( self ):
        if xbmcgui.Window( 10025 ).getProperty( "CinemaExperienceRunning" ) == "True":
            utils.log( 'Playback Resumed' )
            if ha_settings[ "ha_enable" ]:
                Launch_automation().launch_automation( trigger = "Resume", prev_trigger = "Paused", mode = "normal" )
    
        pass
        
def _daemon( ):
    settings.start()
    xbmcgui.Window( 10025 ).setProperty( "CinemaExperienceTriggered", "False" )
    while ( not xbmc.abortRequested ):
        CE_Running = xbmcgui.Window( 10025 ).getProperty( "CinemaExperienceRunning" ) == "True"
        CE_Triggered = xbmcgui.Window( 10025 ).getProperty( "CinemaExperienceTriggered" ) == "True"
        if not xbmc.getCondVisibility('VideoPlayer.Content(movies)'):
            xbmc.sleep( 250 )
        else:
            if int( xbmc.PlayList( xbmc.PLAYLIST_VIDEO ).size() ) > 0 and settings.extra_settings[ "override_play" ] and not ( CE_Running or CE_Triggered ):
                #log( 'Something added to playlist.  Cinema Experince Running? %s' % xbmcgui.Window(10025).getProperty( "CinemaExperienceRunning" ) )
                while not int( xbmcgui.getCurrentWindowId() ) == 12005:
                    xbmc.sleep( 100 )
                    #log( 'Waiting for full screen video' )
                xbmc.Player().stop()
                xbmc.executebuiltin( "RunScript(script.cinema.experience,fromplay)" )
                xbmcgui.Window( 10025 ).setProperty( "CinemaExperienceTriggered", "True" )
                xbmc.sleep( 3000 )
            else:
                xbmc.sleep( 250 )

def update_settings( original_settings ):
    utils.log( "service.py - Settings loaded" )
    new_settings = settings.read_settings_xml()
    if not original_settings == new_settings:
        settings.store_settings()
        original_settings = new_settings
        settings.settings_to_log()
        settings.start()
        trivia_settings  = settings.trivia_settings
        trailer_settings = settings.trailer_settings
        ha_settings      = settings.ha_settings
        video_settings   = settings.video_settings
        extra_settings   = settings.extra_settings
        audio_formats    = settings.audio_formats
        _3d_settings     = settings._3d_settings
        triggers         = settings.triggers
    return original_settings
                
if (__name__ == "__main__"):
    utils.log( 'Cinema Experience service script version %s started' % __version__ )
    Player = CE_Player( enabled = True )
    Monitor = CE_Monitor( enabled = True, update_settings = update_settings )
    _daemon()
    del Monitor
    del Player
    utils.log( 'Cinema Experience service script version %s stopped' % __version__ )

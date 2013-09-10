import xbmc, xbmcaddon, xbmcgui, xbmcvfs
import os, sys

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__setting__      = __addon__.getSetting
__scriptID__     = __addonid__

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path').decode('utf-8'), 'resources' ) )
BASE_CURRENT_SOURCE_PATH = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), os.path.basename( __addon__.getAddonInfo('path') ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
home_automation_folder   = os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts" )
home_automation_module   = os.path.join( home_automation_folder, "home_automation.py" )
true = True
false = False
null = None

triggers                    = ( "Script Start", "Trivia Intro", "Trivia", "Trivia Outro", "Coming Attractions Intro", "Movie Trailer", 
                                "Coming Attractions Outro", "Movie Theater Intro", "Countdown", "Feature Presentation Intro", "Audio Format", 
                                "MPAA Rating", "Movie", "Feature Presentation Outro", "Movie Theatre Outro", "Intermission", "Script End", "Pause", "Resume" )

override_play           = eval( __setting__( "override_play" ) )

ha_settings             = {       "ha_enable": eval( __setting__( "ha_enable" ) ),
                           "ha_multi_trigger": eval( __setting__( "ha_multi_trigger" ) ),
                            "ha_script_start": eval( __setting__( "ha_script_start" ) ),
                            "ha_trivia_intro": eval( __setting__( "ha_trivia_intro" ) ),
                            "ha_trivia_start": eval( __setting__( "ha_trivia_start" ) ),
                            "ha_trivia_outro": eval( __setting__( "ha_trivia_outro" ) ),
                               "ha_mte_intro": eval( __setting__( "ha_mte_intro" ) ),
                               "ha_cav_intro": eval( __setting__( "ha_cav_intro" ) ),
                           "ha_trailer_start": eval( __setting__( "ha_trailer_start" ) ),
                               "ha_cav_outro": eval( __setting__( "ha_cav_outro" ) ),
                               "ha_fpv_intro": eval( __setting__( "ha_fpv_intro" ) ),
                             "ha_mpaa_rating": eval( __setting__( "ha_mpaa_rating" ) ),
                         "ha_countdown_video": eval( __setting__( "ha_countdown_video" ) ),
                            "ha_audio_format": eval( __setting__( "ha_audio_format" ) ),
                                   "ha_movie": eval( __setting__( "ha_movie" ) ),
                               "ha_fpv_outro": eval( __setting__( "ha_fpv_outro" ) ),
                               "ha_mte_outro": eval( __setting__( "ha_mte_outro" ) ),
                            "ha_intermission": eval( __setting__( "ha_intermission" ) ),
                              "ha_script_end": eval( __setting__( "ha_script_end" ) ),
                                  "ha_paused": eval( __setting__( "ha_paused" ) ),
                                 "ha_resumed": eval( __setting__( "ha_resumed" ) )
                          }

#Check to see if module is moved to /userdata/addon_data/script.cinema.experience
if not xbmcvfs.exists( os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts", "home_automation.py" ) ) and ha_settings[ "ha_enable" ]:
    source = os.path.join( BASE_RESOURCE_PATH, "ha_scripts", "home_automation.py" )
    destination = os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts", "home_automation.py" )
    xbmcvfs.mkdir( os.path.join( BASE_CURRENT_SOURCE_PATH, "ha_scripts" ) )        
    xbmcvfs.copy( source, destination )
    log( "[ script.cinema.experience ] - home_automation.py copied", level=xbmc.LOGNOTICE )

from launch_automation import Launch_automation
from utils import log

class CE_Monitor( xbmc.Monitor ):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.enabled = kwargs['enabled']
        self.update_settings = kwargs['update_settings']
    
    def onSettingsChanged( self ):
        self.update_settings()
        
class CE_Player( xbmc.Player ):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__( self )
        self.enabled = kwargs['enabled']
    
    def onPlayBackStarted( self ):
        xbmc.sleep( 1000 )
        if xbmcgui.Window(10025).getProperty( "CinemaExperienceRunning" ) == "True":
            log( 'Playback Started' )
    
    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        if xbmcgui.Window(10025).getProperty( "CinemaExperienceRunning" ) == "True":
            log( "Playback Ended" )
    
    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        if xbmcgui.Window(10025).getProperty( "CinemaExperienceRunning" ) == "True":
            log( "Playback Stopped" )
    
    def onPlayBackPaused( self ):
        if xbmcgui.Window(10025).getProperty( "CinemaExperienceRunning" ) == "True":
            log( 'Playback Paused' )
            if ha_settings[ "ha_enable" ]:
                Launch_automation().launch_automation( trigger = "Pause", prev_trigger = "Playing", mode = "normal" )
    
    def onPlayBackResumed( self ):
        if xbmcgui.Window(10025).getProperty( "CinemaExperienceRunning" ) == "True":
            log( 'Playback Resumed' )
            if ha_settings[ "ha_enable" ]:
                Launch_automation().launch_automation( trigger = "Resume", prev_trigger = "Paused", mode = "normal" )
    
class Main():
    def __init__(self):
        self._init_vars()
        self.update_settings
        self._daemon()
        
    def _init_vars(self):
        self.Player = CE_Player( enabled = True )
        self.Monitor = CE_Monitor( enabled = True, update_settings = self.update_settings )
    
    def update_settings( self ):
        log( "service.py - Settings loaded" )
        self.override_play           = eval( __setting__( "override_play" ) )
        self.ha_settings             = {       "ha_enable": eval( __setting__( "ha_enable" ) ),
                                       "ha_multi_trigger": eval( __setting__( "ha_multi_trigger" ) ),
                                        "ha_script_start": eval( __setting__( "ha_script_start" ) ),
                                        "ha_trivia_intro": eval( __setting__( "ha_trivia_intro" ) ),
                                        "ha_trivia_start": eval( __setting__( "ha_trivia_start" ) ),
                                        "ha_trivia_outro": eval( __setting__( "ha_trivia_outro" ) ),
                                           "ha_mte_intro": eval( __setting__( "ha_mte_intro" ) ),
                                           "ha_cav_intro": eval( __setting__( "ha_cav_intro" ) ),
                                       "ha_trailer_start": eval( __setting__( "ha_trailer_start" ) ),
                                           "ha_cav_outro": eval( __setting__( "ha_cav_outro" ) ),
                                           "ha_fpv_intro": eval( __setting__( "ha_fpv_intro" ) ),
                                         "ha_mpaa_rating": eval( __setting__( "ha_mpaa_rating" ) ),
                                     "ha_countdown_video": eval( __setting__( "ha_countdown_video" ) ),
                                        "ha_audio_format": eval( __setting__( "ha_audio_format" ) ),
                                               "ha_movie": eval( __setting__( "ha_movie" ) ),
                                           "ha_fpv_outro": eval( __setting__( "ha_fpv_outro" ) ),
                                           "ha_mte_outro": eval( __setting__( "ha_mte_outro" ) ),
                                        "ha_intermission": eval( __setting__( "ha_intermission" ) ),
                                          "ha_script_end": eval( __setting__( "ha_script_end" ) ),
                                              "ha_paused": eval( __setting__( "ha_paused" ) ),
                                             "ha_resumed": eval( __setting__( "ha_resumed" ) )
                                      }
        override_play = self.override_play
        ha_settings = self.ha_settings
        
    def _daemon( self ):
        while (not xbmc.abortRequested):
            if not xbmc.getCondVisibility('VideoPlayer.Content(movies)'):
                xbmc.sleep( 250 )
            else:
                if int( xbmc.PlayList( xbmc.PLAYLIST_VIDEO ).size() ) > 0 and xbmc.getCondVisibility('VideoPlayer.Content(movies)') and override_play and not xbmcgui.Window(10025).getProperty( "CinemaExperienceRunning" ) == "True":
                    #xbmc.sleep( 100 )
                    xbmc.Player().stop()
                    xbmc.executebuiltin( "RunScript(script.cinema.experience,fromplay)" )
                else:
                    xbmc.sleep( 250 )
                
if (__name__ == "__main__"):
    log('Cinema Experience service script version %s started' % __addonversion__)
    Main()
    del CE_Player
    del CE_Monitor
    del Main
    log('Cinema Experience service script version %s stopped' % __addonversion__)
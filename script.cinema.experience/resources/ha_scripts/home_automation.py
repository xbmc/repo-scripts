# This module's future home should be inside userdata/addon_data/script.cinema.experience/ha_scripts
# to make sure it does not get over written when updating the script

import xbmc, xbmcaddon
import sys, urllib2, os
from threading import Thread
from urllib import urlencode

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
triggers                 = sys.modules[ "__main__" ].triggers
ha_settings              = sys.modules[ "__main__" ].ha_settings
BASE_RESOURCE_PATH       = sys.modules["__main__"].BASE_RESOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
import utils

class Automate:
    def __init__( self ):
        pass
    
    def sab_pause(self, mode):
        """
            This function provides a method to pause and resume SabNZBd downloading, very useful on a limited network or low powered system
            
            Usage:
            
                apikey - Your SabNZBd API key goes here
                ip     - The IP of your SabNZBd Machine, if local, leave as is, if it does not work, put the actual address in
                port   - Normally 5000 but change it to match you SabNZBd program
                
                Pause:
                
                    self.sab_pause( "pause" )
                
                Resume:
                
                    self.sab_pause( "resume" )
        """
        apikey = ""
        ip = "127.0.0.1" # address 
        port = "5000"
        url = "http://%s:%s/sabnzbd/" % ( ip, port )
        query = {}
        query[ "mode" ] = mode
        query["apikey"] = apikey
        response = urllib2.urlopen( urllib2.Request( url + "api?", urlencode( query ) ) )
        response_data = response.read()
      
    def activate_ha( self, trigger = None, prev_trigger = None, mode="normal" ):
        if ha_settings[ "ha_enable" ]:
            if ha_settings[ "ha_multi_trigger" ] and prev_trigger == trigger:
                pass
            elif mode != "thread":
                self.activate_on( trigger )
            else:
                thread = Thread( name='ha_trigger', target=self.activate_on, args=( trigger, ) )
                thread.start()
            prev_trigger = trigger
        return prev_trigger

    def activate_on( self, trigger = None ):
        """
            Scripting to trigger almost anything(HA, other scripts, etc...) when videos start.  
            
            Usage:
                activate_on( "Movie" )
                will trigger code that is set under the Movie heading.
                
        """
        if not trigger:
            utils.log( " - [ home_automation.py ] - No Trigger Sent, Returning", xbmc.LOGNOTICE )
            return
        utils.log( " - [ home_automation.py ] - activate_on( %s ) Triggered" % trigger, xbmc.LOGNOTICE )
        if trigger in triggers:
            utils.log( " - [ home_automation.py ] - Trigger %s" % trigger, xbmc.LOGNOTICE )
        # Script Start
        if trigger == "Script Start" and ha_settings[ "ha_script_start" ]: 
            # place code below this line
            pass
        # Trivia Intro
        elif trigger == "Trivia Intro" and ha_settings[ "ha_trivia_intro" ]: 
            # place code below this line
            pass
        # Trivia
        elif trigger == "Trivia" and ha_settings[ "ha_trivia_start" ]: 
            # place code below this line
            pass
        # Trivia Outro
        elif trigger == "Trivia Outro" and ha_settings[ "ha_trivia_outro" ]:
            # place code below this line
            pass
        # Movie Theatre Intro
        elif trigger == "Movie Theater Intro" and ha_settings[ "ha_mte_intro" ]:
            # place code below this line
            pass
        # Coming Attractions Intro
        elif trigger == "Coming Attractions Intro" and ha_settings[ "ha_cav_intro" ]:
            # place code below this line
            pass
        # Trailer
        elif trigger == "Movie Trailer" and ha_settings[ "ha_trailer_start" ]:
            # place code below this line
            pass
        # Coming Attractions Outro
        elif trigger == "Coming Attractions Outro" and ha_settings[ "ha_cav_outro" ]: 
            # place code below this line
            pass
        # Feature Presentation Intro
        elif trigger == "Feature Presentation Intro" and ha_settings[ "ha_fpv_intro" ]: 
            # place code below this line
            pass
        #3D Intro
        elif trigger == "3D Intro" and ha_setting [ "ha_3d_intro" ]:
            # place code below this line
            pass
        #3D Trailers
        elif trigger == "3D Movie Trailer" and ha_setting [ "ha_3d_trailer" ]:
            # place code below this line
            pass
        #3D Outro
        elif trigger == "3D Outro" and ha_setting [ "ha_3d_outro" ]:
            # place code below this line
            pass
        # MPAA Rating
        elif trigger == "MPAA Rating" and ha_settings[ "ha_mpaa_rating" ]: 
            # place code below this line
            pass
        # Countdown
        elif trigger == "Countdown" and ha_settings[ "ha_countdown_video" ]:
            # place code below this line
            pass
        # Audio Format
        elif trigger == "Audio Format" and ha_settings[ "ha_audio_format" ]:
            # place code below this line
            pass
        # Movie
        elif trigger == "Movie" and ha_settings[ "ha_movie" ]: 
            # place code below this line
            pass
        # Feature Presentation Outro
        elif trigger == "Feature Presentation Outro" and ha_settings[ "ha_fpv_outro" ]:
            # place code below this line
            pass
        # Movie Theatre Intro
        elif trigger == "Movie Theatre Outro" and ha_settings[ "ha_mte_outro" ]: 
            # place code below this line
            pass
        # Intermission
        elif trigger == "Intermission" and ha_settings[ "ha_intermission" ]: 
            # place code below this line
            pass
        # Script End
        elif trigger == "Script End" and ha_settings[ "ha_script_end" ]: 
            # place code below this line
            pass
        # Paused
        elif trigger == "Pause" and ha_settings[ "ha_paused" ]: 
            # place code below this line
            pass
        # Resumed
        elif trigger == "Resume" and ha_settings[ "ha_resumed" ]: 
            # place code below this line
            pass
        else:
            utils.log( " - [ home_automation.py ] - Opps. Something happened", xbmc.LOGNOTICE )

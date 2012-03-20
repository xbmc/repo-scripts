#import modules
import xbmc
import xbmcaddon
import os
import xbmcgui
import sys

### get addon info
__addon__       = xbmcaddon.Addon('script.artwork.downloader')
__addonid__     = ( sys.modules[ "__main__" ].__addonid__ )
__addonname__   = ( sys.modules[ "__main__" ].__addonname__ )
__author__      = ( sys.modules[ "__main__" ].__author__ )
__version__     = ( sys.modules[ "__main__" ].__version__ )
__localize__    = ( sys.modules[ "__main__" ].__localize__ )
__addonprofile__= ( sys.modules[ "__main__" ].__addonprofile__ )
settings_file   = os.path.join(__addonprofile__, "settings.xml")

#import libraries
from resources.lib.utils import *
from resources.lib import language

### Get settings from settings.xml
class settings:
    ### Initial artwork vars
    def _get_artwork(self):
        self.movie_enable           = __addon__.getSetting("movie_enable")          == 'true'
        self.movie_poster           = __addon__.getSetting("movie_poster")          == 'true'
        self.movie_fanart           = __addon__.getSetting("movie_fanart")          == 'true'
        self.movie_extrafanart      = __addon__.getSetting("movie_extrafanart")     == 'true'
        self.movie_extrathumbs      = __addon__.getSetting("movie_extrathumbs")     == 'true'
        self.movie_logo             = __addon__.getSetting("movie_logo")            == 'true'
        self.movie_clearart         = __addon__.getSetting("tvshow_clearart")       == 'true'
        self.movie_discart          = __addon__.getSetting("movie_discart")         == 'true'

        self.tvshow_enable          = __addon__.getSetting("tvshow_enable")         == 'true'
        self.tvshow_poster          = __addon__.getSetting("tvshow_poster")         == 'true'
        self.tvshow_seasonposter    = __addon__.getSetting("tvshow_seasonposter")   == 'true'
        self.tvshow_fanart          = __addon__.getSetting("tvshow_fanart")         == 'true'
        self.tvshow_extrafanart     = __addon__.getSetting("tvshow_extrafanart")    == 'true'
        self.tvshow_clearart        = __addon__.getSetting("tvshow_clearart")       == 'true'
        self.tvshow_logo            = __addon__.getSetting("tvshow_logo")           == 'true'
        self.tvshow_thumb           = __addon__.getSetting("tvshow_thumb")          == 'true'
        self.tvshow_seasonthumb     = __addon__.getSetting("tvshow_seasonthumb")    == 'true'
        self.tvshow_showbanner      = __addon__.getSetting("tvshow_showbanner")     == 'true'
        self.tvshow_seasonbanner    = __addon__.getSetting("tvshow_seasonbanner")   == 'true'
        self.tvshow_characterart    = __addon__.getSetting("tvshow_characterart")   == 'true'

        self.musicvideo_enable      = __addon__.getSetting("musicvideo_enable")     == 'true'
        self.musicvideo_poster      = __addon__.getSetting("musicvideo_poster")     == 'true'
        self.musicvideo_fanart      = __addon__.getSetting("musicvideo_fanart")     == 'true'
        self.musicvideo_extrafanart = __addon__.getSetting("musicvideo_extrafanart")== 'true'
        self.musicvideo_extrathumbs = __addon__.getSetting("musicvideo_extrathumbs")== 'true'
        self.musicvideo_logo        = __addon__.getSetting("musicvideo_logo")       == 'true'
        self.musicvideo_clearart    = __addon__.getSetting("tvshow_clearart")       == 'true'
        self.musicvideo_discart     = __addon__.getSetting("musicvideo_discart")    == 'true'

    ### Initial genral vars
    def _get_general(self):
        self.centralize_enable      = __addon__.getSetting("centralize_enable")     == 'true'
        self.centralfolder_movies   = __addon__.getSetting("centralfolder_movies")
        self.centralfolder_tvshows  = __addon__.getSetting("centralfolder_tvshows")

        self.background             = __addon__.getSetting("background")            == 'true'
        self.notify                 = __addon__.getSetting("notify")                == 'true'
        self.service_startup        = __addon__.getSetting("service_startup")       == 'true'
        self.service_startupdelay   = __addon__.getSetting("service_startupdelay")
        self.service_enable         = __addon__.getSetting("service_enable")        == 'true'
        self.service_runtime        = __addon__.getSetting("service_runtime")
        self.files_overwrite        = __addon__.getSetting("files_overwrite")       == 'true'
        self.xbmc_caching_enabled   = __addon__.getSetting("xbmc_caching_enabled")  == 'true'

        # Disable centralize cause it causes to much confusion
        self.centralize_enable      = False
        
    ### Initial limit vars
    def _get_limit(self):    
        self.limit_artwork              = __addon__.getSetting("limit_artwork") == 'true'
        self.limit_extrafanart_max      = int(__addon__.getSetting("limit_extrafanart_max").rstrip('0').rstrip('.'))
        self.limit_extrafanart_rating   = int(__addon__.getSetting("limit_extrafanart_rating").rstrip('0').rstrip('.'))
        self.limit_size_moviefanart     = int(__addon__.getSetting("limit_size_moviefanart"))
        self.limit_size_tvshowfanart    = int(__addon__.getSetting("limit_size_tvshowfanart"))
        self.limit_extrathumbs          = True
        self.limit_extrathumbs_max      = 4
        self.limit_artwork_max          = 1
        self.limit_preferred_language   = __addon__.getSetting("limit_preferred_language")
        self.limit_notext               = __addon__.getSetting("limit_notext") == 'true'

    ### Initial startup vars
    def _vars(self):
        self.failcount                  = 0     # Initial fail count
        self.failthreshold              = 3     # Abbort when this many fails
        self.xmlfailthreshold           = 5     # Abbort when this many fails
        self.api_timedelay              = 5000  # in msec

    ### Log settings in debug mode
    def _initiallog(self):
        log('## Settings...')
        log('## Preferred language      = %s' % str(self.limit_preferred_language))
        log('## Background Run          = %s' % str(self.background))
        log('## - Notify                = %s' % str(self.notify))
        log('## Run at startup / login  = %s' % str(self.service_startup))
        log('## - Delay in minutes      = %s' % str(self.service_startupdelay))
        log('## Run as service          = %s' % str(self.service_enable))
        log('## - Time                  = %s' % str(self.service_runtime))
        log('## Overwrite all files     = %s' % str(self.files_overwrite))
        log('##')
        log('## Movie Artwork           = %s' % str(self.movie_enable))
        log('## - Poster                = %s' % str(self.movie_poster))
        log('## - Fanart                = %s' % str(self.movie_fanart))
        log('## - ExtraFanart           = %s' % str(self.movie_extrafanart))
        log('## - ExtraThumbs           = %s' % str(self.movie_extrathumbs))
        log('## - Logo                  = %s' % str(self.movie_logo))
        log('## - DiscArt               = %s' % str(self.movie_discart))
        log('##')
        log('## TV Show Artwork         = %s' % str(self.tvshow_enable))
        log('## - Poster                = %s' % str(self.tvshow_poster))
        log('## - Season Poster         = %s' % str(self.tvshow_seasonposter))
        log('## - Fanart                = %s' % str(self.tvshow_fanart))
        log('## - ExtraFanart           = %s' % str(self.tvshow_extrafanart))
        log('## - Clearart              = %s' % str(self.tvshow_clearart))
        log('## - Logo                  = %s' % str(self.tvshow_logo))
        log('## - Showbanner            = %s' % str(self.tvshow_showbanner))
        log('## - Seasonbanner          = %s' % str(self.tvshow_seasonbanner))
        log('## - Thumb                 = %s' % str(self.tvshow_thumb))
        log('## - Show Seasonthumb      = %s' % str(self.tvshow_seasonthumb))
        log('## - Show Characterart     = %s' % str(self.tvshow_characterart))
        log('##')
        log('## Musicvideo Artwork      = %s' % str(self.musicvideo_enable))
        log('## - Poster                = %s' % str(self.musicvideo_poster))
        log('## - Fanart                = %s' % str(self.musicvideo_fanart))
        log('## - ExtraFanart           = %s' % str(self.musicvideo_extrafanart))
        log('## - ExtraThumbs           = %s' % str(self.musicvideo_extrathumbs))
        log('## - Logo                  = %s' % str(self.movie_logo))
        log('## - Clearart              = %s' % str(self.movie_clearart))
        log('## - DiscArt               = %s' % str(self.movie_discart))
        log('##')
        log('## Centralize Extrafanart  = %s' % str(self.centralize_enable))
        log('## - Movies Folder         = %s' % str(self.centralfolder_movies))
        log('## - TV Shows Folder       = %s' % str(self.centralfolder_tvshows))
        log('##')
        log('## Limit Artwork           = %s' % str(self.limit_artwork))
        log('## - Extrafanart Max       = %s' % str(self.limit_extrafanart_max))
        log('## - Fanart Rating         = %s' % str(self.limit_extrafanart_rating))
        log('## - Movie Fanart Size     = %s' % str(self.limit_size_moviefanart))
        log('## - TV Show Fanart Size   = %s' % str(self.limit_size_tvshowfanart))
        log('## - Extrathumbs           = %s' % str(self.limit_extrathumbs))
        log('## - Extrathumbs Max       = %s' % str(self.limit_extrathumbs_max))
        log('## - Language              = %s' % str(self.limit_preferred_language))
        log('## - Fanart with no text   = %s' % str(self.limit_notext))
        log('##')
        log('## XBMC caching enabled    = %s' % str(self.xbmc_caching_enabled))
        log('##')
        log('## End of Settings...')


    ### Create list for Artwork types to download
    def _artype_list(self):
        self.available_arttypes = []
        # create global list
        info = {}
        info['media_type']      = 'movie'
        info['bulk_enabled']    = self.movie_poster
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32128)
        info['art_type']        = 'poster'
        info['filename']        = 'poster.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'movie'
        info['bulk_enabled']    = self.movie_fanart 
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32121)
        info['art_type']        = 'fanart'
        info['filename']        = 'fanart.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'movie'
        info['bulk_enabled']    = self.movie_extrafanart
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32122)
        info['art_type']        = 'extrafanart'
        info['filename']        = ''
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'movie'
        info['bulk_enabled']    = self.movie_extrathumbs
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32131)
        info['art_type']        = 'extrathumbs'
        info['filename']        = 'thumb%s.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'movie'
        info['bulk_enabled']    = self.movie_logo
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32126)
        info['art_type']        = 'clearlogo'
        info['filename']        = 'logo.png'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'movie'
        info['bulk_enabled']    = self.movie_clearart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32125)
        info['art_type']        = 'clearart'
        info['filename']        = 'clearart.png'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'movie'
        info['bulk_enabled']    = self.movie_discart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32132)
        info['art_type']        = 'discart'
        info['filename']        = 'disc.png'
        self.available_arttypes.append(info)

        # append tv show list
        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_poster
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32128)
        info['art_type']        = 'poster'
        info['filename']        = 'poster.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_seasonposter
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32129)
        info['art_type']        = 'seasonposter'
        info['filename']        = 'season%s-poster.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_fanart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32121)
        info['art_type']        = 'fanart'
        info['filename']        = 'fanart.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_extrafanart
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32122)
        info['art_type']        = 'extrafanart'
        info['filename']        = '' 
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_clearart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32125)
        info['art_type']        = 'clearart'
        info['filename']        = 'clearart.png'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_logo
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32126)
        info['art_type']        = 'clearlogo'
        info['filename']        = 'logo.png'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_thumb
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32130)
        info['art_type']        = 'tvthumb'
        info['filename']        = 'landscape.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_seasonthumb
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32134)
        info['art_type']        = 'seasonthumb'
        info['filename']        = 'season%s-landscape.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_showbanner
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32123)
        info['art_type']        = 'banner'
        info['filename']        = 'banner.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_seasonbanner
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32124)
        info['art_type']        = 'seasonbanner'
        info['filename']        = 'season%s-banner.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'tvshow'
        info['bulk_enabled']    = self.tvshow_characterart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32127)
        info['art_type']        = 'characterart'
        info['filename']        = 'character.png'
        self.available_arttypes.append(info)

        # Musicvideo
        info = {}
        info['media_type']      = 'musicvideo'
        info['bulk_enabled']    = self.musicvideo_poster
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32128)
        info['art_type']        = 'poster'
        info['filename']        = 'poster.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'musicvideo'
        info['bulk_enabled']    = self.musicvideo_fanart 
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32121)
        info['art_type']        = 'fanart'
        info['filename']        = 'fanart.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'musicvideo'
        info['bulk_enabled']    = self.musicvideo_extrafanart
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32122)
        info['art_type']        = 'extrafanart'
        info['filename']        = ''
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'musicvideo'
        info['bulk_enabled']    = self.musicvideo_extrathumbs
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32131)
        info['art_type']        = 'extrathumbs'
        info['filename']        = 'thumb%s.jpg'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'musicvideo'
        info['bulk_enabled']    = self.musicvideo_logo
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32126)
        info['art_type']        = 'clearlogo'
        info['filename']        = 'logo.png'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'musicvideo'
        info['bulk_enabled']    = self.musicvideo_clearart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32125)
        info['art_type']        = 'clearart'
        info['filename']        = 'clearart.png'
        self.available_arttypes.append(info)

        info = {}
        info['media_type']      = 'musicvideo'
        info['bulk_enabled']    = self.musicvideo_discart
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32132)
        info['art_type']        = 'cdart'
        info['filename']        = 'disc.png'
        self.available_arttypes.append(info)
        
    ### Check for faulty setting combinations
    def _check(self):
        settings_faulty = True
        while settings_faulty:
            settings_faulty = True
            check_movie = check_tvshow = check_musicvideo = check_centralize = True
            # re-check settings after posible change
            self._get_general()
            self._get_artwork()
            # Check if faulty setting in movie section
            if self.movie_enable:
                if not self.movie_poster and not self.movie_fanart and not self.movie_extrafanart and not self.movie_extrathumbs and not self.movie_logo and not self.movie_clearart and not self.movie_discart:
                    check_movie = False
                    log('Setting check: No subsetting of movies enabled')
                else: check_movie = True
            # Check if faulty setting in tvshow section
            if self.tvshow_enable:
                if not self.tvshow_poster and not self.tvshow_seasonposter and not self.tvshow_fanart and not self.tvshow_extrafanart and not self.tvshow_clearart and not self.tvshow_characterart and not self.tvshow_logo and not self.tvshow_showbanner and not self.tvshow_seasonbanner and not self.tvshow_thumb and not self.tvshow_seasonthumb:
                    check_tvshow = False
                    log('Setting check: No subsetting of tv shows enabled')
                else: check_tvshow = True
            # Check if faulty setting in musicvideo section
            if self.musicvideo_enable:
                if not self.musicvideo_fanart and not self.musicvideo_extrafanart and not self.musicvideo_extrathumbs and not self.musicvideo_poster:
                    check_musicvideo = False
                    log('Setting check: No subsetting of musicvideo enabled')
                else: check_musicvideo = True
            # Check if faulty setting in centralize section
            if self.centralize_enable:
                if self.centralfolder_movies == '' and self.centralfolder_tvshows == '':
                    check_centralize = False
                    log('Setting check: No centralized folder chosen')
                else: check_centralize = True
            # Compare all setting check
            if check_movie and check_tvshow and check_musicvideo and check_centralize:
                settings_faulty = False
            else: settings_faulty = True
            # Faulty setting found
            if settings_faulty:
                log('Faulty setting combination found')
                # when faulty setting detected ask to open the settings window
                if dialog_msg('yesno', line1 = __localize__(32003), line2 = __localize__(32004), background = False, nolabel = __localize__(32026), yeslabel = __localize__(32025)):
                    __addon__.openSettings()
                # if not cancel the script
                else:
                    xbmc.abortRequested = True
                    break
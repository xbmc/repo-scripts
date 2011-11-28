#import modules
import xbmc
import xbmcaddon
import os
import time
import sys
import platform
import xbmcgui

#import libraries
from resources.lib.utils import _log as log
from resources.lib.utils import _dialog as dialog
from resources.lib import language


### get addon info
__addon__       = xbmcaddon.Addon('script.artwork.downloader')
__addonid__     = __addon__.getAddonInfo('id')
__addonname__   = __addon__.getAddonInfo('name')
__author__      = __addon__.getAddonInfo('author')
__version__     = __addon__.getAddonInfo('version')
__localize__    = __addon__.getLocalizedString
__language__    = language.get_abbrev()
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )
settings_file   = os.path.join(__addondir__, "settings.xml")


class _settings:

    ### Get settings from settings.xml
    def _get(self):
        self.movie_enable           = __addon__.getSetting("movie_enable") == 'true'
        self.movie_poster           = __addon__.getSetting("movie_poster") == 'true'
        self.movie_fanart           = __addon__.getSetting("movie_fanart") == 'true'
        self.movie_extrafanart      = __addon__.getSetting("movie_extrafanart") == 'true'
        self.movie_extrathumbs      = __addon__.getSetting("movie_extrathumbs") == 'true'
        self.movie_logo             = __addon__.getSetting("movie_logo") == 'true'
        self.movie_discart          = __addon__.getSetting("movie_discart") == 'true'
        self.movie_defaultthumb     = __addon__.getSetting("movie_defaultthumb") == 'true'
        
        self.tvshow_enable          = __addon__.getSetting("tvshow_enable") == 'true'
        self.tvshow_poster          = __addon__.getSetting("tvshow_poster") == 'true'
        self.tvshow_seasonposter    = __addon__.getSetting("tvshow_seasonposter") == 'true'
        self.tvshow_fanart          = __addon__.getSetting("tvshow_fanart") == 'true'
        self.tvshow_extrafanart     = __addon__.getSetting("tvshow_extrafanart") == 'true'
        self.tvshow_clearart        = __addon__.getSetting("tvshow_clearart") == 'true'
        self.tvshow_logo            = __addon__.getSetting("tvshow_logo") == 'true'
        self.tvshow_thumb           = __addon__.getSetting("tvshow_thumb") == 'true'
        self.tvshow_seasonthumbs    = __addon__.getSetting("tvshow_seasonthumbs") == 'true'
        self.tvshow_showbanner      = __addon__.getSetting("tvshow_showbanner") == 'true'
        self.tvshow_seasonbanner    = __addon__.getSetting("tvshow_seasonbanner") == 'true'
        self.tvshow_characterart    = __addon__.getSetting("tvshow_characterart") == 'true'
        self.tvshow_defaultthumb    = __addon__.getSetting("tvshow_defaultthumb") == 'true'
        self.tvshow_defaultthumb_type    = __addon__.getSetting("tvshow_defaultthumb_type")
        
        self.centralize_enable      = __addon__.getSetting("centralize_enable") == 'true'
        self.centralfolder_split    = __addon__.getSetting("centralfolder_split")
        self.centralfolder_movies   = __addon__.getSetting("centralfolder_movies")
        self.centralfolder_tvshows  = __addon__.getSetting("centralfolder_tvshows")

        self.backup_enabled         = __addon__.getSetting("backup_enabled") == 'true'
        self.backup_path            = __addon__.getSetting("backup_path")
        self.background             = __addon__.getSetting("background") == 'true'
        self.notify                 = __addon__.getSetting("notify") == 'true'
        self.service_startup        = __addon__.getSetting("service_startup") == 'true'
        self.service_enable         = __addon__.getSetting("service_enable") == 'true'
        self.service_time           = __addon__.getSetting("service_time")
        self.files_overwrite        = __addon__.getSetting("files_overwrite") == 'true'
        self.xbmc_caching_enabled   = __addon__.getSetting("xbmc_caching_enabled") == 'true'
        
    def _get_limit(self):    
        self.limit_artwork = __addon__.getSetting("limit_artwork") == 'true'
        self.limit_extrafanart_max      = int(__addon__.getSetting("limit_extrafanart_max").rstrip('0').rstrip('.'))
        self.limit_extrafanart_rating   = int(__addon__.getSetting("limit_extrafanart_rating").rstrip('0').rstrip('.'))
        self.limit_size_moviefanart     = int(__addon__.getSetting("limit_size_moviefanart"))
        self.limit_size_tvshowfanart    = int(__addon__.getSetting("limit_size_tvshowfanart"))
        self.limit_extrathumbs          = self.limit_artwork
        self.limit_extrathumbs_max      = 4
        self.limit_artwork_max          = 1
        self.limit_language             = __addon__.getSetting("limit_language") == 'true'
        self.limit_notext               = __addon__.getSetting("limit_notext") == 'true'



    ### Initial startup vars
    def _vars(self):
        self.failcount                  = 0
        self.failthreshold              = 3
        self.xmlfailthreshold           = 5
        self.api_timedelay              = 5
        self.mediatype                  = ''
        self.medianame                  = ''
        self.count_tvshow_extrafanart   = 0
        self.count_movie_extrafanart    = 0
        self.count_movie_extrathumbs    = 0

    ### Log settings in debug mode
    def _initiallog(self):
        log('## Settings...')
        log('## Language Used           = %s' % str(__language__))
        log('## Background Run          = %s' % str(self.background))
        log('## - Notify                = %s' % str(self.notify))
        log('## Run at startup / login  = %s' % str(self.service_startup))
        log('## Run as service          = %s' % str(self.service_enable))
        log('## - Time interval         = %s' % str(self.service_time))
        log('## Overwrite all files     = %s' % str(self.files_overwrite))
        log('##')
        log('## Movie Artwork           = %s' % str(self.movie_enable))
        log('## - Poster                = %s' % str(self.movie_poster))
        log('## - Fanart                = %s' % str(self.movie_fanart))
        log('## - ExtraFanart           = %s' % str(self.movie_extrafanart))
        log('## - ExtraThumbs           = %s' % str(self.movie_extrathumbs))
        log('## - Logo                  = %s' % str(self.movie_logo))
        log('## - DiscArt               = %s' % str(self.movie_discart))
        log('## - Default Thumb         = %s' % str(self.movie_defaultthumb))
        log('##')
        log('## TV Show Artwork         = %s' % str(self.tvshow_enable))
        log('## - Poster                = %s' % str(self.tvshow_poster))
        log('## - Fanart                = %s' % str(self.tvshow_fanart))
        log('## - ExtraFanart           = %s' % str(self.tvshow_extrafanart))
        log('## - Clearart              = %s' % str(self.tvshow_clearart))
        log('## - Logo                  = %s' % str(self.tvshow_logo))
        log('## - Showbanner            = %s' % str(self.tvshow_showbanner))
        log('## - Seasonbanner          = %s' % str(self.tvshow_seasonbanner))
        log('## - Thumb                 = %s' % str(self.tvshow_thumb))
        log('## - Show Seasonthumbs     = %s' % str(self.tvshow_seasonthumbs))
        log('## - Show Characterart     = %s' % str(self.tvshow_characterart))
        log('## - Default Thumb         = %s' % str(self.tvshow_defaultthumb))
        log('## - Default Thumb Type    = %s' % str(self.tvshow_defaultthumb_type))
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
        log('## - Language              = %s' % str(self.limit_language))
        log('## - Fanart with no text   = %s' % str(self.limit_notext))
        log('##')
        log('## Backup fanart           = %s' % str(self.backup_enabled))
        log('## Backup folder           = %s' % str(self.backup_path))
        log('## XBMC caching enabled    = %s' % str(self.xbmc_caching_enabled))
        log('##')
        log('## End of Settings...')

    ### Check if settings.xml exist and version check
    def _exist(self):
        first_run = True
        while first_run:
            # no settings.xml found
            if not os.path.isfile(settings_file):
                dialog('okdialog', line1 = __localize__(32001), line2 = __localize__(32021))
                log('## Settings.xml file not found. Opening settings window.')
                __addon__.openSettings()
                time.sleep(1)
                __addon__.setSetting(id="addon_version", value=__version__)
            # different version settings.xml found
            if os.path.isfile(settings_file) and __addon__.getSetting("addon_version") <> __version__:
                dialog('okdialog', line1 = __localize__(32002), line2 = __localize__(32021))
                log('## Addon version is different. Opening settings window.')
                __addon__.openSettings()
                __addon__.setSetting(id="addon_version", value=__version__)
            else:
                first_run = False
        __addon__.setSetting(id="addon_version", value=__version__)
        log('## Correct version of settings.xml file found. Continue with initializing.')

    ### Create list for Artwork types to download
    def _artype_list(self):
        self.movie_arttype_list = []
        self.tvshow_arttype_list = []
        # create global list
        info = {}
        info['bulk_enabled']    = self.movie_poster
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32128)
        info['art_type']        = 'poster'
        info['filename']        = 'poster.jpg'
        self.movie_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.movie_fanart 
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32121)
        info['art_type']        = 'fanart'
        info['filename']        = 'fanart.jpg'
        self.movie_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.movie_extrafanart
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32122)
        info['art_type']        = 'extrafanart'
        info['filename']        = ''
        self.movie_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.movie_extrathumbs
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32131)
        info['art_type']        = 'extrathumbs'
        info['filename']        = 'thumb'
        self.movie_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.movie_logo
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32126)
        info['art_type']        = 'clearlogo'
        info['filename']        = 'logo.png'
        self.movie_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.movie_discart
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32132)
        info['art_type']        = 'discart'
        info['filename']        = 'cdart.png'
        self.movie_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.movie_defaultthumb
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32133)
        info['art_type']        = 'poster'
        info['filename']        = 'folder.jpg'
        self.movie_arttype_list.append(info)

        # append tv show list
        info = {}
        info['bulk_enabled']    = self.tvshow_poster
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32128)
        info['art_type']        = 'poster'
        info['filename']        = 'poster.jpg'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_seasonposter
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32129)
        info['art_type']        = 'seasonposter'
        info['filename']        = 'season'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_fanart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32121)
        info['art_type']        = 'fanart'
        info['filename']        = 'fanart.jpg'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_extrafanart
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32122)
        info['art_type']        = 'extrafanart'
        info['filename']        = '' 
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_clearart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32125)
        info['art_type']        = 'clearart'
        info['filename']        = 'clearart.png'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_logo
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32126)
        info['art_type']        = 'clearlogo'
        info['filename']        = 'logo.png'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_thumb
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32130)
        info['art_type']        = 'tvthumb'
        info['filename']        = 'landscape.jpg'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_seasonthumbs
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32134)
        info['art_type']        = 'seasonthumbs'
        info['filename']        = 'seasonthumb'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_showbanner
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32123)
        info['art_type']        = 'banner'
        info['filename']        = 'banner.jpg'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_seasonbanner
        info['solo_enabled']    = 'false'
        info['gui_string']      = __localize__(32124)
        info['art_type']        = 'seasonbanner'
        info['filename']        = 'seasonbanner'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_characterart
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32127)
        info['art_type']        = 'characterart'
        info['filename']        = 'character.png'
        self.tvshow_arttype_list.append(info)
        
        info = {}
        info['bulk_enabled']    = self.tvshow_defaultthumb
        info['solo_enabled']    = 'true'
        info['gui_string']      = __localize__(32133)
        info['art_type']        = 'defaultthumb'
        info['filename']        = 'folder.jpg'
        self.tvshow_arttype_list.append(info)        
        
            
    ### Check for faulty setting combinations
    def _check(self):    
        settings_faulty = True
        check_sections = check_movie = check_tvshow = check_centralize = check_cache = True
        while settings_faulty:
            # re-check settings after posible change
            self._get()        
            # Check if artwork section enabled
            if not (self.movie_enable or self.tvshow_enable):
                check_sections = False
                log('Setting check: No artwork section enabled')
            else: check_sections = True
            # Check if faulty setting in movie section
            if self.movie_enable:
                if not self.movie_fanart and not self.movie_extrafanart and not self.movie_extrathumbs and not self.movie_poster and not self.movie_defaultthumb:
                    check_movie = False
                    log('Setting check: No subsetting of movies enabled')
                else: check_movie = True
            # Check if faulty setting in tvshow section
            if self.tvshow_enable:
                if not self.tvshow_poster and not self.tvshow_fanart and not self.tvshow_extrafanart  and not self.tvshow_showbanner and not self.tvshow_seasonbanner and not self.tvshow_clearart and not self.tvshow_logo and not self.tvshow_showbanner and not self.tvshow_thumb and not self.tvshow_characterart and not self.tvshow_defaultthumb:
                    check_tvshow = False
                    log('Setting check: No subsetting of tv shows enabled')
                else: check_tvshow = True
            # Check if faulty setting in centralize section
            if self.centralize_enable:
                if self.centralfolder_movies == '' and self.centralfolder_tvshows == '':
                    check_centralize = False
                    log('Setting check: No centralized folder chosen')
                else: check_centralize = True
            # Check if faulty setting in cache section
            if self.backup_enabled:
                if self.backup_path == '':
                    check_cache = False
                    log('Setting check: No cache folder chosen')
                else: check_cache = True
            # Compare all setting check
            if check_sections and check_movie and check_tvshow and check_centralize and check_cache:
                settings_faulty = False
            else: settings_faulty = True
            # Faulty setting found
            if settings_faulty:
                log('Faulty setting combination found')
                dialog('okdialog', line1 = __localize__(32003), line2 = __localize__(32004))
                __addon__.openSettings()        
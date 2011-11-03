import re
import os
import time
import sys
import xbmc
import xbmcaddon
import platform

### get addon info
__addon__ = xbmcaddon.Addon('script.extrafanartdownloader')
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')
__localize__ = __addon__.getLocalizedString

addondir = xbmc.translatePath( __addon__.getAddonInfo('profile') )
settings_file = os.path.join(addondir, "settings.xml")
first_run = False

from resources.lib import media_setup
from resources.lib import provider
from resources.lib.utils import _log as log
from resources.lib.utils import _dialog as dialog
from resources.lib.script_exceptions import DownloadError, CreateDirectoryError, HTTP404Error, HTTP503Error, NoFanartError, HTTPTimeout, ItemNotFoundError
from resources.lib import language
from resources.lib.fileops import fileops
from xml.parsers.expat import ExpatError

Media_listing = media_setup.media_listing
__language__ = language.get_abbrev()

### clean up and
def cleanup(self):
    if self.fileops._exists(self.fileops.tempdir):
        dialog('update', percentage = 100, line1 = __localize__(36004), background = self.background)
        log('Cleaning up temp files')
        for x in os.listdir(self.fileops.tempdir):
            tempfile = os.path.join(self.fileops.tempdir, x)
            self.fileops._delete(tempfile)
            if self.fileops._exists(tempfile):
                log('Error deleting temp file: %s' % tempfile, xbmc.LOGERROR)
        self.fileops._rmdir(self.fileops.tempdir)
        if self.fileops._exists(self.fileops.tempdir):
            log('Error deleting temp directory: %s' % self.fileops.tempdir, xbmc.LOGERROR)
        else:
            log('Deleted temp directory: %s' % self.fileops.tempdir, xbmc.LOGNOTICE)
    ### log results and notify user
    log('Finished: Total of %s artwork downloaded' % self.fileops.downloadcount, xbmc.LOGNOTICE)
    summary_tmp = __localize__(36009) + ': %s ' % self.fileops.downloadcount
    summary = summary_tmp + __localize__(36013)
    dialog('close', background = self.background)
    if not self.failcount < self.failthreshold:
        log('Network error detected, script aborted', xbmc.LOGERROR)
        dialog('okdialog', line1 = __localize__(36007), line2 = __localize__(36008), background = self.background)
    if not xbmc.abortRequested:
        dialog('okdialog', line1 = summary, background = self.background)
    else:
        dialog('okdialog', line1 = __localize__(36007), line2 = summary, background = self.background)

### check if settings.xml excist
def settings_excist(self):
    if not os.path.isfile(settings_file):
        dialog('okdialog', line1 = __localize__(36037), line2 = __localize__(36038))
        log('## Settings.xml file not found. Opening settings window.')
        __addon__.openSettings()
        first_run = True
    else:
        log('Settings.xml file found. Continue with initializing.')
  
### get settings from settings.xml
def settings_get(self):
    self.moviefanart = __addon__.getSetting("movie_enable") == 'true'
    self.movie_extrafanart = __addon__.getSetting("movie_extrafanart") == 'true'
    self.movie_extrathumbs = __addon__.getSetting("movie_extrathumbs") == 'true'
    self.tvfanart = __addon__.getSetting("tvshow_enable") == 'true'
    self.tvshow_extrafanart = __addon__.getSetting("tvshow_extrafanart") == 'true'
    self.centralize_enable = __addon__.getSetting("centralize_enable") == 'true'
    self.centralfolder_split = __addon__.getSetting("centralfolder_split")
    self.centralfolder_movies = __addon__.getSetting("centralfolder_movies")
    self.centralfolder_tvshows = __addon__.getSetting("centralfolder_tvshows")
    self.limit_extrafanart = __addon__.getSetting("limit_extrafanart") == 'true'
    self.limit_extrafanart_max = int(float(__addon__.getSetting("limit_extrafanart_max").rstrip('0').rstrip('.')))
    self.limit_extrafanart_rating = int(float(__addon__.getSetting("limit_extrafanart_rating").rstrip('0').rstrip('.')))
    self.limit_extrathumbs = self.limit_extrafanart
    self.limit_extrathumbs_max = 4
    self.limit_extrathumbs_rating = self.limit_extrafanart_rating
    self.limit_language = __addon__.getSetting("limit_language") == 'true'
    self.limit_notext = __addon__.getSetting("limit_notext") == 'true'
    self.use_cache = __addon__.getSetting("use_cache") == 'true'
    self.cache_directory = __addon__.getSetting("cache_directory")
    self.background = __addon__.getSetting("background") == 'true'

### declare some starting variables
def settings_vars(self):
    self.mediatype = ''
    self.medianame = ''
    providers = provider.get_providers()
    self.movie_providers = providers['movie_providers']
    self.tv_providers = providers['tv_providers']
    self.music_providers = providers['music_providers']
    self.failcount = 0
    self.failthreshold = 3
    self.xmlfailthreshold = 5
    self.fanart_centralized = 0        

# Print out settings to log to help with debugging
def settings_log(self):
    log("## Settings...")
    log('## Language Used = %s' % str(__language__))
    log('## Download Movie Artwork= %s' % str(self.moviefanart))
    log('## Download Movie ExtraFanart= %s' % str(self.movie_extrafanart))
    log('## Download Movie ExtraThumbs= %s' % str(self.movie_extrathumbs))
    log('## Download TV Show Artwork = %s' % str(self.tvfanart))
    log('## Download TV Show ExtraFanart = %s' % str(self.tvshow_extrafanart))
    log('## Background Run = %s' % str(self.background))
    log('## Centralize Extrafanart = %s' % str(self.centralize_enable))
    log('## Central Movies Folder = %s' % str(self.centralfolder_movies))
    log('## Central TV Show Folder = %s' % str(self.centralfolder_tvshows))
    log('## Limit Extrafanart = %s' % str(self.limit_extrafanart))
    log('## Limit Extrafanart Max = %s' % str(self.limit_extrafanart_max))
    log('## Limit Extrafanart Rating = %s' % str(self.limit_extrafanart_rating))
    log('## Limit Extrathumbs = %s' % str(self.limit_extrathumbs))
    log('## Limit Extrathumbs Max = %s' % str(self.limit_extrathumbs_max))
    log('## Limit Extrathumbs Rating = %s' % str(self.limit_extrathumbs_rating))
    log('## Limit Language = %s' % str(self.limit_language))
    log('## Limit Fanart with no text = %s' % str(self.limit_notext))
    log('## Backup downloaded fanart= %s' % str(self.use_cache))
    log('## Backup folder = %s' % str(self.cache_directory))
    log("## End of Settings...")

### Check for script starting arguments used by skins
def runmode_args(self):
    log("## Checking for arguments used by skins")
    try: log( "## arg 0: %s" % sys.argv[0] )
    except:   log( "## no arg0" )
    try: log( "## arg 1: %s" % sys.argv[1] )
    except:   log( "## no arg1" )
    try: log( "## arg 2: %s" % sys.argv[2] )
    except:   log( "## no arg2" )
    try: log( "## arg 3: %s" % sys.argv[3] )
    except:   log( "## no arg3" )
    try: log( "## arg 4: %s" % sys.argv[4] )
    except:   log( "## no arg4" )
    try: log( "arg 5: %s" % sys.argv[5] )
    except:   log( "## no arg5" )
    try: log( "## arg 6: %s" % sys.argv[6] )
    except:   log( "## no arg6" )
    try: log( "## arg 7: %s" % sys.argv[7] )
    except:   log( "## no arg7" )
    try: log( "## arg 8: %s" % sys.argv[8] )
    except:   log( "## no arg8" )

### initial check before exicuting
def initialise(self):
    dialog('create', line1 = __localize__(36005), background = self.background)
    for item in sys.argv:
        log("## Checking for downloading mode...")
        match = re.search("mediatype=(.*)" , item)
        if match:
            self.mediatype = match.group(1)
            if self.mediatype == 'tvshow' or self.mediatype == 'movie' or self.mediatype == 'music':
                pass
            else:
                log('Error: invalid mediatype, must be one of movie, tvshow or music', xbmc.LOGERROR)
                return False
        else:
            pass
        match = re.search("medianame=" , item)
        if match:
            self.medianame = item.replace("medianame=" , "")
        else:
            pass
    try:
        self.fileops = fileops()
    except CreateDirectoryError, e:
        log("Could not create directory: %s" % str(e))
        return False
    else:
        return True
class Main:
    def __init__(self):
        settings_excist(self)
        settings_get(self)
        settings_vars(self)
        settings_log(self)
        runmode_args(self)
        if initialise(self):
            if not self.mediatype == '':
                if not self.medianame == '':
                    self.solo_mode(self.mediatype, self.medianame)
                else:
                    if self.mediatype == 'tvshow':
                        self.Medialist = Media_listing('TVShows')
                        log("Bulk mode: TV Shows")
                        self.download_fanart(self.Medialist, self.tv_providers)
                    elif self.mediatype == 'movie':
                        self.Medialist = Media_listing('Movies')
                        log("Bulk mode: Movies")
                        self.download_fanart(self.Medialist, self.movie_providers)
                    elif self.mediatype == 'music':
                        log('Bulk mode: Music not yet implemented', xbmc.LOGNOTICE)
            else:
                if self.tvfanart and self.tvshow_extrafanart:
                    self.Medialist = Media_listing('TVShows')
                    self.mediatype = 'tvshow'
                    self.download_fanart(self.Medialist, self.tv_providers)
                else:
                    log('TV fanart disabled, skipping', xbmc.LOGINFO)
                if self.moviefanart and (self.movie_extrafanart or self.movie_extrathumbs):
                    self.Medialist = Media_listing('Movies')
                    self.mediatype = 'movie'
                    self.download_fanart(self.Medialist, self.movie_providers)
                else:
                    log('Movie fanart disabled, skipping', xbmc.LOGINFO)
        else:
            log('Initialisation error, script aborting', xbmc.LOGERROR)
        cleanup(self)




    ### solo mode
    def solo_mode(self, itemtype, itemname):
        if itemtype == 'movie':
            log("## Solo mode: Movie...")
            self.Medialist = Media_listing('Movies')
        elif itemtype == 'tvshow':
            self.Medialist = Media_listing('TVShows')
            log("## Solo mode: TV Show...")
        elif itemtype == '':
            self.Medialist = Media_listing('Music')
            log("## Solo mode: Music...")
        else:
            log("Error: type must be one of 'movie', 'tvshow' or 'music', aborting", xbmc.LOGERROR)
            return False
        log('Retrieving fanart for: %s' % itemname)
        for currentitem in self.Medialist:
            if itemname == currentitem["name"]:
                if itemtype == 'movie':
                    self.Medialist = []
                    self.Medialist.append(currentitem)
                    self.download_fanart(self.Medialist, self.movie_providers)
                if itemtype == 'tvshow':
                    self.Medialist = []
                    self.Medialist.append(currentitem)
                    self.download_fanart(self.Medialist, self.tv_providers)
                break

    ### download media fanart
    def download_fanart(self, media_list, providers):
        self.processeditems = 0
        for currentmedia in media_list:
            ### check if XBMC is shutting down
            if xbmc.abortRequested:
                log('XBMC abort requested, aborting')
                break
            ### check if script has been cancelled by user
            if dialog('iscanceled', background = self.background):
                break
            if not self.failcount < self.failthreshold:
                break
            try:
                self.media_path = os.path.split(currentmedia["path"])[0].rsplit(' , ', 1)[1]
            except:
                self.media_path = os.path.split(currentmedia["path"])[0]
            self.media_id = currentmedia["id"]
            self.media_name = currentmedia["name"]
            dialog('update', percentage = int(float(self.processeditems) / float(len(media_list)) * 100.0), line1 = __localize__(36005), line2 = self.media_name, line3 = '', background = self.background)
            log('Processing media: %s' % self.media_name, xbmc.LOGNOTICE)
            log('ID: %s' % self.media_id)
            log('Path: %s' % self.media_path)
            targetdirs = []
            targetthumbsdirs = []
            extrafanart_dir = os.path.join(self.media_path, 'extrafanart')
            extrathumbs_dir = os.path.join(self.media_path, 'extrathumbs')
            targetdirs.append(extrafanart_dir)
            targetthumbsdirs.append(extrathumbs_dir)
            ### Check if using the centralize option
            if self.centralize_enable:
                if self.mediatype == 'tvshow':
                    if not self.centralfolder_tvshows == '':
                        targetdirs.append(self.centralfolder_tvshows)
                    else:
                        log('Error: Central fanart enabled but TV Show folder not set, skipping', xbmc.LOGERROR)
                elif self.mediatype == 'movie':
                    if not self.centralfolder_movies == '':
                        targetdirs.append(self.centralfolder_movies)
                    else:
                        log('Error: Central fanart enabled but Movies folder not set, skipping', xbmc.LOGERROR)
            ### Check if using the cache option
            targets = targetdirs[:]
            if self.use_cache and not self.cache_directory == '':
                targets.append(self.cache_directory)
            if self.media_id == '':
                log('%s: No ID found, skipping' % self.media_name, xbmc.LOGNOTICE)
            elif self.mediatype == 'tvshow' and self.media_id.startswith('tt'):
                log('%s: IMDB ID found for TV show, skipping' % self.media_name, xbmc.LOGNOTICE)
            else:
                for provider in providers:
                    if not self.failcount < self.failthreshold:
                        break
                    backdrops_result = ''
                    self.xmlfailcount = 0
                    while not backdrops_result == 'pass' and not backdrops_result == 'skipping':
                        if backdrops_result == 'retrying':
                            time.sleep(10)
                        try:
                            image_list = provider.get_image_list(self.media_id)
                        except HTTP404Error, e:
                            errmsg = '404: File not found'
                            backdrops_result = 'skipping'
                        except HTTP503Error, e:
                            self.xmlfailcount = self.xmlfailcount + 1
                            errmsg = '503: API Limit Exceeded'
                            backdrops_result = 'retrying'
                        except NoFanartError, e:
                            errmsg = 'No fanart found'
                            backdrops_result = 'skipping'
                        except ItemNotFoundError, e:
                            errmsg = '%s not found' % self.media_id
                            backdrops_result = 'skipping'
                        except ExpatError, e:
                            self.xmlfailcount = self.xmlfailcount + 1
                            errmsg = 'Error parsing xml: %s' % str(e)
                            backdrops_result = 'retrying'
                        except HTTPTimeout, e:
                            self.failcount = self.failcount + 1
                            errmsg = 'Timed out'
                            backdrops_result = 'skipping'
                        except DownloadError, e:
                            self.failcount = self.failcount + 1
                            errmsg = 'Possible network error: %s' % str(e)
                            backdrops_result = 'skipping'
                        else:
                            backdrops_result = 'pass'
                        if not self.xmlfailcount < self.xmlfailthreshold:
                            backdrops_result = 'skipping'
                        if not backdrops_result == 'pass':
                            log('Error getting data from %s (%s): %s' % (provider.name, errmsg, backdrops_result))
                    if backdrops_result == 'pass':
                        self.failcount = 0
                        self.current_fanart = 0
                        self.current_extrathumbs = 0
                        self.downloaded_fanart = 0
                        self.downloaded_extrathumbs = 0
                        if (self.limit_extrafanart and self.limit_extrafanart_max < len(image_list)):
                            download_max = self.limit_extrafanart_max
                        else: download_max = len(image_list)
                        if (self.limit_extrathumbs and self.limit_extrathumbs_max < len(image_list)):
                            download_thumbsmax = self.limit_extrathumbs_max
                        else: download_thumbsmax = len(image_list)
                        ### Extrafanart downloading
                        if self.movie_extrafanart or self.tvshow_extrafanart:
                            log('Extrafanart enabled. Processing')
                            for fanart in image_list:
                                size = 'original'
                                fanarturl = fanart['url']
                                if size in fanart['size']:
                                    ### check if script has been cancelled by user
                                    if dialog('iscanceled', background = self.background):
                                        dialog('close', background = self.background)
                                        break
                                    if not self.failcount < self.failthreshold:
                                        break
                                    if self.mediatype == 'movie':
                                        fanartfile = provider.get_filename(fanart['id'])
                                    else:
                                        fanartfile = provider.get_filename(fanarturl)
                                    self.current_fanart = self.current_fanart + 1
                                    ### Check for set limits
                                    if self.limit_extrafanart and self.downloaded_fanart >= self.limit_extrafanart_max:
                                        reason = 'Max number fanart reached: %s' % self.downloaded_fanart
                                        self.fileops._delete_file_in_dirs(fanartfile, targetdirs, reason)
                                    elif self.limit_extrafanart and 'rating' in fanart and fanart['rating'] < self.limit_extrafanart_rating:
                                        reason = 'Rating too low: %s' % fanart['rating']
                                        self.fileops._delete_file_in_dirs(fanartfile, targetdirs, reason)
                                    elif self.limit_extrafanart and 'series_name' in fanart and self.limit_notext and fanart['series_name']:
                                        reason = 'Has text'
                                        self.fileops._delete_file_in_dirs(fanartfile, targetdirs, reason)
                                    elif self.limit_extrafanart and self.limit_language and 'language' in fanart and fanart['language'] != __language__:
                                        reason = "Doesn't match current language: %s" % xbmc.getLanguage()
                                        self.fileops._delete_file_in_dirs(fanartfile, targetdirs, reason)
                                    else:
                                        try:
                                            self.fileops._downloadfile(fanarturl, fanartfile, targets)
                                        except HTTP404Error, e:
                                            log("File does not exist at URL: %s" % str(e), xbmc.LOGWARNING)
                                        except HTTPTimeout, e:
                                            self.failcount = self.failcount + 1
                                            log("Error downloading file: %s, timed out" % str(e), xbmc.LOGERROR)
                                        except CreateDirectoryError, e:
                                            log("Could not create directory, skipping: %s" % str(e), xbmc.LOGWARNING)
                                            break
                                        except DownloadError, e:
                                            self.failcount = self.failcount + 1
                                            log('Error downloading file: %s (Possible network error: %s), skipping' % (fanarturl, str(e)), xbmc.LOGERROR)
                                        else:
                                            self.downloaded_fanart = self.downloaded_fanart + 1
                                    dialog('update', percentage = int(float(self.current_fanart) / float(download_max) * 100.0), line1 = __localize__(36006) + ' ' + __localize__(36102), line2 = self.media_name, line3 = fanartfile, background = self.background)
                        else:    
                            log('Extrafanart disabled. skipping')
                        ### Movie extrathumbs downloading
                        if self.movie_extrathumbs and self.mediatype == 'movie':
                            log('Movie extrathumbs enabled. Processing')
                            for extrathumbs in image_list:
                                size = 'thumb'
                                extrathumbsurl = extrathumbs['url']
                                if size in extrathumbs['size']:
                                    ### check if script has been cancelled by user
                                    if dialog('iscanceled', background = self.background):
                                        dialog('close', background = self.background)
                                        break
                                    if not self.failcount < self.failthreshold:
                                        break
                                    extrathumbsfile = ('thumb%s.jpg' % str(self.current_extrathumbs+1))
                                    self.current_extrathumbs = self.current_extrathumbs + 1
                                    ### Check for set limits
                                    if self.limit_extrathumbs and self.downloaded_extrathumbs >= self.limit_extrathumbs_max:
                                        reason = 'Max number extrathumbs reached: %s' % self.downloaded_extrathumbs
                                        self.fileops._delete_file_in_dirs(extrathumbsfile, targetthumbsdirs, reason)
                                    elif self.limit_extrathumbs and 'rating' in extrathumbs and extrathumbs['rating'] < self.limit_extrathumbs_rating:
                                        reason = 'Rating too low: %s' % extrathumbs['rating']
                                        self.fileops._delete_file_in_dirs(extrathumbsfile, targetthumbsdirs, reason)
                                    elif self.limit_extrathumbs and 'series_name' in extrathumbs and self.limit_notext and extrathumbs['series_name']:
                                        reason = 'Has text'
                                        self.fileops._delete_file_in_dirs(extrathumbsfile, targetthumbsdirs, reason)
                                    elif self.limit_extrathumbs and self.limit_language and 'language' in extrathumbs and extrathumbs['language'] != __language__:
                                        reason = "Doesn't match current language: %s" % xbmc.getLanguage()
                                        self.fileops._delete_file_in_dirs(extrathumbsfile, targetthumbsdirs, reason)
                                    else:
                                        try:
                                            self.fileops._downloadfile(extrathumbsurl, extrathumbsfile, targetthumbsdirs)
                                        except HTTP404Error, e:
                                            log("File does not exist at URL: %s" % str(e), xbmc.LOGWARNING)
                                        except HTTPTimeout, e:
                                            self.failcount = self.failcount + 1
                                            log("Error downloading file: %s, timed out" % str(e), xbmc.LOGERROR)
                                        except CreateDirectoryError, e:
                                            log("Could not create directory, skipping: %s" % str(e), xbmc.LOGWARNING)
                                            break
                                        except DownloadError, e:
                                            self.failcount = self.failcount + 1
                                            log('Error downloading file: %s (Possible network error: %s), skipping' % (extrathumbsurl, str(e)), xbmc.LOGERROR)
                                        else:
                                            self.downloaded_extrathumbs = self.downloaded_extrathumbs + 1
                                    dialog('update', percentage = int(float(self.current_extrathumbs) / float(download_max) * 100.0), line1 = __localize__(36006) + ' ' + __localize__(36110), line2 = self.media_name, line3 = extrathumbsfile, background = self.background)
                        else:    
                            log('Extrathumbs disabled. skipping')
            log('Finished processing media: %s' % self.media_name, xbmc.LOGDEBUG)
            self.processeditems = self.processeditems + 1

if (__name__ == "__main__"):
    log("######## Extrafanart Downloader: Initializing...............................")
    log('## Add-on ID = %s' % str(__addonid__))
    log('## Add-on Name= %s' % str(__addonname__))
    log('## Add-on Version = %s' % str(__addonversion__))
    Main()
    log('script stopped')

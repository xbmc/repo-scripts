#import modules
import re
import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import time

### get addon info
__addon__       = xbmcaddon.Addon(id='script.artwork.downloader')
__addonid__     = __addon__.getAddonInfo('id')
__addonname__   = __addon__.getAddonInfo('name')
__author__      = __addon__.getAddonInfo('author')
__version__     = __addon__.getAddonInfo('version')
__addonpath__   = __addon__.getAddonInfo('path')
__addonprofile__= xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
__icon__        = __addon__.getAddonInfo('icon')
__localize__    = __addon__.getLocalizedString

### import libraries
from urlparse import urlsplit
from traceback import print_exc
from resources.lib import language
from resources.lib import provider
from resources.lib.provider import tmdb # import on behalf of searching when there's no ID
from resources.lib.utils import *
from resources.lib.script_exceptions import *
from resources.lib.fileops import fileops
from resources.lib.apply_filters import apply_filters
from resources.lib.settings import settings
from resources.lib.media_setup import _media_listing as media_listing
from resources.lib.media_setup import _media_unique as media_unique
from xml.parsers.expat import ExpatError
from resources.lib.provider.local import local

### set button actions for GUI
ACTION_PREVIOUS_MENU = (9, 10, 92, 216, 247, 257, 275, 61467, 61448,)


class Main:

    def __init__(self):
        self.initial_vars() 
        self.settings._get_general()    # Get settings from settings.xml
        self.settings._get_artwork()    # Get settings from settings.xml
        self.settings._get_limit()      # Get settings from settings.xml
        self.settings._check()          # Check if there are some faulty combinations present
        self.settings._initiallog()     # Create debug log for settings
        self.settings._vars()           # Get some settings vars
        self.settings._artype_list()    # Fill out the GUI and Arttype lists with enabled options
        if self.initialise():
            # Check for silent background mode
            if self.silent:
                self.settings.background = True
                self.settings.notify = False
            # Check for gui mode
            elif self.mode == 'gui':
                self.settings.background = False
                self.settings.notify = False
                self.settings.files_overwrite = True
            dialog_msg('create', line1 = __localize__(32008), background = self.settings.background)
            # Check if mediatype is specified
            if not self.mediatype == '':
                # Check if dbid is specified
                if not self.dbid == '':
                    self.Medialist = media_unique(self.mediatype,self.dbid)
                    if  self.mediatype == 'movie':
                        self.download_artwork(self.Medialist, self.movie_providers)
                    elif self.mediatype == 'tvshow':
                        self.download_artwork(self.Medialist, self.tv_providers)
                    elif self.mediatype == 'musicvideo':
                        self.download_artwork(self.Medialist, self.musicvideo_providers)
                    if not dialog_msg('iscanceled', background = self.settings.background) and not (self.mode == 'customgui' or self.mode == 'gui'):
                        self._batch_download(self.download_list)
                else:
                    # If no medianame specified
                    # 1. Check what media type was specified, 2. Retrieve library list, 3. Enable the correct type, 4. Do the API stuff
                    self.settings.movie_enable = False
                    self.settings.tvshow_enable = False
                    self.settings.musicvideo_enable = False
                    if self.mediatype == 'movie':
                        self.settings.movie_enable = True
                        self.Medialist = media_listing('movie')
                        self.download_artwork(self.Medialist, self.movie_providers)
                    elif self.mediatype == 'tvshow':
                        self.settings.tvshow_enable = True
                        self.Medialist = media_listing('tvshow')
                        self.download_artwork(self.Medialist, self.tv_providers)
                    elif self.mediatype == 'musicvideo':
                        self.settings.musicvideo_enable = True
                        self.Medialist = media_listing('musicvideo')
                        self.download_artwork(self.Medialist, self.musicvideo_providers)
                    if not dialog_msg('iscanceled', background = self.settings.background):
                        self._batch_download(self.download_list)
            # No mediatype is specified
            else:
                # activate movie/tvshow/musicvideo for custom run
                if self.mode == 'custom':
                    self.settings.movie_enable = True
                    self.settings.tvshow_enable = True
                    self.settings.musicvideo_enable = True
                # Normal oprations check
                # 1. Check if enable, 2. Get library list, 3. Set mediatype, 4. Do the API stuff
                # Do this for each media type
                if self.settings.movie_enable and not dialog_msg('iscanceled', background = True):
                    self.mediatype = 'movie'
                    self.Medialist = media_listing(self.mediatype)
                    self.download_artwork(self.Medialist, self.movie_providers)
                if self.settings.tvshow_enable and not dialog_msg('iscanceled', background = True):
                    self.mediatype = 'tvshow'
                    self.Medialist = media_listing(self.mediatype)
                    self.download_artwork(self.Medialist, self.tv_providers)
                if self.settings.musicvideo_enable and not dialog_msg('iscanceled', background = True):
                    self.mediatype = 'musicvideo'
                    self.Medialist = media_listing(self.mediatype)
                    self.download_artwork(self.Medialist, self.musicvideo_providers)
                # If not cancelled throw the whole downloadlist into the batch downloader
                if not dialog_msg('iscanceled', background = self.settings.background):
                    self._batch_download(self.download_list)
        else:
            log('Initialisation error, script aborting', xbmc.LOGERROR)
        # Make sure that files_overwrite option get's reset after downloading
        __addon__.setSetting(id='files_overwrite', value='false')
        self.cleanup()

    ### Declare standard vars   
    def initial_vars(self):
        providers       = provider.get_providers()
        self.settings   = settings()
        self.filters    = apply_filters()
        self.movie_providers        = providers['movie_providers']
        self.tv_providers           = providers['tv_providers']
        self.musicvideo_providers   = providers['musicvideo_providers']
        self.download_counter       = {}
        self.download_counter['Total Artwork'] = 0
        self.reportdata = '[B]Artwork Downloader:[/B]'
        self.mediatype = ''
        self.medianame = ''
        self.mediapath = ''
        self.dbid = ''
        self.mode = ''
        self.silent = ''
        self.gui_selected_type = ''
        self.failed_items = []
        self.download_list = []
        self.download_art_succes = False
        self.cancelled = False

    ### load settings and initialise needed directories
    def initialise(self):
        log('## Checking for script arguments')
        try:
            log('## arg 0: %s' % sys.argv[0])
            log('## arg 1: %s' % sys.argv[1])
            log('## arg 2: %s' % sys.argv[2])
            log('## arg 3: %s' % sys.argv[3])
        except:
            pass
        log('## Checking for downloading mode...')
        for item in sys.argv:
            # Check for download mode
            match = re.search('silent=(.*)' , item)
            if match:
                self.silent = match.group(1)
            # Check for download mode
            match = re.search('mode=(.*)' , item)
            if match:
                self.mode = match.group(1)
            # Check for mediatype mode
            match = re.search('mediatype=(.*)' , item)
            if match:
                self.mediatype = match.group(1)
                if self.mediatype == 'tvshow' or self.mediatype == 'movie' or self.mediatype == 'musicvideo':
                    pass
                else:
                    log('Error: invalid mediatype, must be one of movie, tvshow or musicvideo', xbmc.LOGERROR)
                    return False
            # Check for download mode
            match = re.search('dbid=(.*)' , item)
            if match:
                self.dbid = match.group(1)
            # Check for medianame
            match = re.search('medianame=(.*)' , item)
            if match:
                self.medianame = match.group(1).lstrip(' " ').rstrip(' " ')
            # Check for mediapath
            match = re.search('mediapath=(.*)' , item)
            if match:
                self.mediapath = match.group(1).lstrip(' " ').rstrip(' "/\ ')
                log('matchgroup: %s' %self.mediapath)
        try:
            # Creates temp folder
            self.fileops = fileops()
        except CreateDirectoryError, e:
            log('Could not create directory: %s' % str(e))
            return False
        else:
            return True 

    def cleanup(self):
        if self.fileops._exists(self.fileops.tempdir):
            dialog_msg('update', percentage = 100, line1 = __localize__(32005), background = self.settings.background)
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
                log('Deleted temp directory: %s' % self.fileops.tempdir)
        
        ### log results and notify user
        # Download totals to log and to download report
        self.reportdata += ('\n - %s: %s' %(__localize__(32148), time.strftime('%d %B %Y - %H:%M')))      # Time of finish
        self.reportdata += ('\n[B]%s:[/B]' %(__localize__(32020)))                                        # Download total header
        self.reportdata += ('\n - %s: %s' % (__localize__(32014), self.download_counter['Total Artwork']))# Total downloaded items
        # Cycle through the download totals
        for artwork_type in self.download_counter:
            if not artwork_type == 'Total Artwork':
                self.reportdata += '\n - %s: %s' % (artwork_type, self.download_counter[artwork_type])
        self.reportdata += '\n[B]%s:[/B]' %__localize__(32016)                                              # Failed items header
        # Cycle through the download totals
        if not self.failed_items:
            self.reportdata += '\n - %s' %__localize__(32149)                                               # No failed or missing items found
        else:
            # use  list(sorted(set(mylist)))  to get unique items
            for item in list(sorted(set(self.failed_items))):
                self.reportdata += '\n - %s' %item
        # Build dialog messages
        summary = __localize__(32012) + ': %s ' % self.download_counter['Total Artwork'] + __localize__(32020)
        summary_notify = ': %s ' % self.download_counter['Total Artwork'] + __localize__(32020)
        provider_msg1 = __localize__(32001)
        provider_msg2 = __localize__(32184) + ' | ' + __localize__(32185) + ' | ' + __localize__(32186)
        # Close dialog in case it was open before doing a notification
        time.sleep(2)
        dialog_msg('close', background = self.settings.background)
        # Print the self.reportdata log message
        #log('Failed items report: %s' % self.reportdata.replace('[B]', '').replace('[/B]', ''))
        # Safe the downloadreport to settings folder using save function
        save_nfo_file(self.reportdata, os.path.join(__addonprofile__ , 'downloadreport.txt'))
        # Some dialog checks
        if self.settings.notify:
            log('Notify on finished/error enabled')
            self.settings.background = False
        if xbmc.Player().isPlayingVideo() or self.silent or self.mode == 'gui' or self.mode == 'customgui' or self.mode == 'custom':
            log('Silent finish because of playing a video or silent mode')
            self.settings.background = True
        if not self.settings.failcount < self.settings.failthreshold:
            log('Network error detected, script aborted', xbmc.LOGERROR)
            dialog_msg('okdialog', line1 = __localize__(32010), line2 = __localize__(32011), background = self.settings.background)
        if not xbmc.abortRequested:
            # Show dialog/notification
            if self.settings.background:
                dialog_msg('okdialog', line0 = summary_notify, line1 = provider_msg1 + ' ' + provider_msg2, background = self.settings.background, cancelled = self.cancelled)
            else:
                # When chosen no in the 'yes/no' dialog execute the viewer.py and parse 'downloadreport'
                if dialog_msg('yesno', line1 = summary, line2 = provider_msg1, line3 = provider_msg2, background = self.settings.background, nolabel = __localize__(32027), yeslabel = __localize__(32028)):
                    runcmd = os.path.join(__addonpath__, 'resources/lib/viewer.py')
                    xbmc.executebuiltin('XBMC.RunScript (%s,%s) '%(runcmd, 'downloadreport'))
                    
        else:
            dialog_msg('okdialog', line1 = __localize__(32010), line2 = summary, background = self.settings.background)
        # Container refresh
        if self.mode in ['gui','customgui']:
            if self.download_art_succes:
                xbmc.executebuiltin('Container.Refresh')
                #xbmc.executebuiltin('XBMC.ReloadSkin()')

    ### download media fanart
    def download_artwork(self, media_list, providers):
        self.processeditems = 0
        for currentmedia in media_list:
            # Declare some vars
            self.media_item = {'id': currentmedia['id'],
                               'dbid': currentmedia['dbid'],
                               'name': currentmedia['name'],
                               'path': currentmedia['path'],
                               'art': currentmedia['art'],
                               'mediatype': currentmedia['mediatype'],
                               'disctype': currentmedia.get('disctype','n/a')}
            ### check if XBMC is shutting down
            if xbmc.abortRequested:
                log('XBMC abort requested, aborting')
                self.reportdata += ('\n - %s: %s' %(__localize__(32150), time.strftime('%d %B %Y - %H:%M')))
                break
            ### check if script has been cancelled by user
            if dialog_msg('iscanceled', background = self.settings.background):
                self.reportdata += ('\n - %s [%s]: %s' %(__localize__(32151), self.media_item['mediatype'], time.strftime('%d %B %Y - %H:%M')))
                break
            # abort script because of to many failures
            if not self.settings.failcount < self.settings.failthreshold:
                self.reportdata += ('\n - %s: %s' %(__localize__(32152), time.strftime('%d %B %Y - %H:%M')))
                break
            dialog_msg('update',
                        percentage = int(float(self.processeditems) / float(len(media_list)) * 100.0),
                        line1 = self.media_item['name'],
                        line2 = __localize__(32008),
                        line3 = '',
                        background = self.settings.background)
            log('########################################################')
            log('Processing media:  %s' % self.media_item['name'])
            # do some id conversions 
            if not self.media_item['mediatype'] == 'tvshow' and self.media_item['id'] in ['','tt0000000','0']:
                log('No IMDB ID found, trying to search themoviedb.org for matching title.')
                self.media_item['id'] = tmdb._search_movie(self.media_item['name'],currentmedia['year'])
            elif self.media_item['mediatype'] == 'movie' and not self.media_item['id'] == '' and not self.media_item['id'].startswith('tt'):
                log('No valid ID found, trying to search themoviedb.org for matching title.')
                self.media_item['id'] = tmdb._search_movie(self.media_item['name'],currentmedia['year'])
            log('Provider ID:       %s' % self.media_item['id'])
            log('Media path:        %s' % self.media_item['path'])
            
            # this part check for local files when enabled
            scan_more = True
            self.image_list = []
            if self.settings.files_local:
                local_list = []
                local_list, scan_more = local().get_image_list(currentmedia)
                # append local artwork
                for item in local_list:
                    self.image_list.append(item)            
            # Declare the target folders
            self.target_extrafanartdirs = []
            self.target_extrathumbsdirs = []
            self.target_artworkdir = []
            for item in self.media_item['path']:
                artwork_dir = os.path.join(item + '/')
                extrafanart_dir = os.path.join(artwork_dir + 'extrafanart' + '/')
                extrathumbs_dir = os.path.join(artwork_dir + 'extrathumbs' + '/')
                self.target_artworkdir.append(artwork_dir.replace('BDMV','').replace('VIDEO_TS',''))
                self.target_extrafanartdirs.append(extrafanart_dir)
                self.target_extrathumbsdirs.append(extrathumbs_dir)
            
            # Check if using the centralize option
            if self.settings.centralize_enable:
                if self.media_item['mediatype'] == 'tvshow':
                    self.target_extrafanartdirs.append(self.settings.centralfolder_tvshows)
                elif self.media_item['mediatype'] == 'movie':
                    self.target_extrafanartdirs.append(self.settings.centralfolder_movies)

            # Check for presence of id used by source sites
            if self.mode == 'gui' and ((self.media_item['id'] == '') or (self.media_item['mediatype'] == 'tvshow' and self.media_item['id'].startswith('tt'))):
                dialog_msg('close', background = self.settings.background)
                dialog_msg('okdialog','' ,self.media_item['name'] , __localize__(32030))
            elif self.media_item['id'] == '':
                log('- No ID found, skipping')
                self.failed_items.append('[%s] ID %s' %(self.media_item['name'], __localize__(32022)))
            elif self.media_item['mediatype'] == 'tvshow' and self.media_item['id'].startswith('tt'):
                log('- IMDB ID found for TV show, skipping')
                self.failed_items.append('[%s]: TVDB ID %s' %(self.media_item['name'], __localize__(32022)))

            # If correct ID found continue
            else:
                self.temp_image_list = []
                # Run through all providers getting their imagelisting
                for self.provider in providers:
                    if not self.settings.failcount < self.settings.failthreshold:
                        break
                    artwork_result = ''
                    xmlfailcount = 0
                    #skip skanning for more if local files have been found and not run in gui / custom mode
                    if not scan_more and not self.mode in ['gui', 'custom']:
                        artwork_result = 'pass'
                    while not artwork_result == 'pass' and not artwork_result == 'skipping':
                        if artwork_result == 'retrying':
                            xbmc.sleep(self.settings.api_timedelay)
                        try:
                            self.temp_image_list = self.provider.get_image_list(self.media_item['id'])
                            #pass
                        except HTTP404Error, e:
                            errmsg = '404: File not found'
                            artwork_result = 'skipping'
                        except HTTP503Error, e:
                            xmlfailcount += 1
                            errmsg = '503: API Limit Exceeded'
                            artwork_result = 'retrying'
                        except NoFanartError, e:
                            errmsg = 'No artwork found'
                            artwork_result = 'skipping'
                            self.failed_items.append('[%s] %s' %(self.media_item['name'], __localize__(32133)))
                        except ItemNotFoundError, e:
                            errmsg = '%s not found' % self.media_item['id']
                            artwork_result = 'skipping'
                        except ExpatError, e:
                            xmlfailcount += 1
                            errmsg = 'Error parsing xml: %s' % str(e)
                            artwork_result = 'retrying'
                        except HTTPTimeout, e:
                            self.settings.failcount += 1
                            errmsg = 'Timed out'
                            artwork_result = 'skipping'
                        except DownloadError, e:
                            self.settings.failcount += 1
                            errmsg = 'Possible network error: %s' % str(e)
                            artwork_result = 'skipping'
                        else:
                            artwork_result = 'pass'
                            for item in self.temp_image_list:
                                self.image_list.append(item)
                        if not xmlfailcount < self.settings.xmlfailthreshold:
                            artwork_result = 'skipping'
                        if not artwork_result == 'pass':
                            log('Error getting data from %s (%s): %s' % (self.provider.name, errmsg, artwork_result))

            if len(self.image_list) > 0:
                if (self.settings.limit_artwork and self.settings.limit_extrafanart_max < len(self.image_list)):
                    self.download_max = self.settings.limit_extrafanart_max
                else:
                    self.download_max = len(self.image_list)
                # Check for GUI mode
                if self.mode == 'gui':
                    log('- Using GUI mode')
                    self._gui_mode()
                elif self.mode == 'custom':
                    log('- Using custom mode')
                    self._custom_mode()
                else:
                    #log('- Using bulk mode')
                    self._download_process()
            self.processeditems += 1

    ### Processes the bulk mode downloading of files
    def _download_process(self):
        if not self.mode == 'custom':
            self.download_arttypes = []
            for item in self.settings.available_arttypes:
                if item['bulk_enabled'] and self.mediatype == item['media_type']:
                    self.download_arttypes.append(item['art_type'])

        for item in self.settings.available_arttypes:
            if item['art_type'] in self.download_arttypes and ((self.settings.movie_enable and self.mediatype == item['media_type']) or (self.settings.tvshow_enable and self.mediatype == item['media_type']) or (self.settings.musicvideo_enable and self.mediatype == item['media_type'])):
                if item['art_type'] == 'extrafanart':
                    self._download_art(item['art_type'], item['filename'], self.target_extrafanartdirs,  item['gui_string'])
                elif item['art_type'] == 'extrathumbs':
                    self._download_art(item['art_type'], item['filename'], self.target_extrathumbsdirs,  item['gui_string'])
                else:
                    self._download_art(item['art_type'], item['filename'], self.target_artworkdir,  item['gui_string'])


    ### Retrieves imagelist for GUI solo mode
    def _gui_imagelist(self, art_type):
        log('- Retrieving image list for GUI')
        filteredlist = []
        #retrieve list
        for artwork in self.image_list:
            if  art_type == artwork['type'][0]:
                filteredlist.append(artwork)
        return filteredlist
 

    ### Artwork downloading
    def _download_art(self, art_type, filename, targetdirs, msg):
        log('* Image type: %s' %art_type)
        self.settings.failcount = 0
        seasonfile_presents = []
        current_artwork = 0                     # Used in progras dialog
        limit_counter = 0                       # Used for limiting on number
        pref_language = language.get_abbrev()   # get abbreviation
        i = 0                                   # Set loop counter
        imagefound = False                      # Set found image false
        imageignore = False                     # Set ignaore image false
        missingfiles = False
        final_image_list = []
        if self.mode in ['gui', 'customgui'] and not art_type in ['extrafanart', 'extrathumbs']:
            final_image_list.append(self.image_item)
        else:
            final_image_list = self.image_list
        if len(final_image_list) == 0:
            log(' - Nothing to download')
        else:
            # This total hack adds temporary ability to use local images that are not on fanart.tv
            # This should be removed asap when rewrite is done
            arttypes = ['clearlogo','clearart','landscape','discart']
            if self.settings.files_local and art_type in arttypes:
                for targetdir in targetdirs:
                    localfile = os.path.join(targetdir, filename).encode('utf-8')
                    if self.fileops._exists(localfile):
                        final_image_list.append({'url': localfile,
                                                 'type': [art_type],
                                                 'language': pref_language,
                                                 'discnumber': '1',
                                                 'disctype': self.media_item['disctype']})
                    break
            # End of hack

            # Do some language shit
            # loop two times than skip
            while (i < 2 and not imagefound):
                # when no image found found after one imagelist loop set to english
                if not imagefound and i == 1:
                    pref_language = 'en'
                    log('! No matching %s artwork found. Searching for English backup' %self.settings.limit_preferred_language)
                # loop through image list
                for artwork in final_image_list:
                    if art_type in artwork['type']:
                        ### check if script has been cancelled by user
                        if dialog_msg('iscanceled', background = self.settings.background):
                            #dialog('close', background = self.settings.background)
                            break
                        if not self.settings.failcount < self.settings.failthreshold:
                            break   
                        # Create an image info list
                        item = {'url': artwork['url'],
                                'targetdirs': targetdirs,
                                'media_name': self.media_item['name'],
                                'mediatype':self.media_item['mediatype'],
                                'artwork_string': msg,
                                'artwork_details': artwork,
                                'dbid':self.media_item['dbid'],
                                'art':self.media_item['art'],
                                'arttype':art_type}
                        # raise artwork counter only on first loop
                        if i != 1:
                            current_artwork += 1

                        # File naming
                        if art_type   == 'extrafanart':
                            item['filename'] = ('%s.jpg'% artwork['id'])
                        elif art_type == 'extrathumbs':
                            item['filename'] = (filename % str(limit_counter + 1))
                        elif art_type in ['seasonposter']:
                            if artwork['season'] == '0':
                                item['filename'] = "season-specials-poster.jpg"
                            elif artwork['season'] == 'all':
                                item['filename'] = "season-all-poster.jpg"
                            elif artwork['season'] == 'n/a':
                                break
                            else:
                                item['filename'] = (filename % int(artwork['season']))
                        elif art_type in ['seasonbanner']:
                            if artwork['season'] == '0':
                                item['filename'] = "season-specials-banner.jpg"
                            elif artwork['season'] == 'all':
                                item['filename'] = "season-all-banner.jpg"
                            elif artwork['season'] == 'n/a':
                                break
                            else:
                                item['filename'] = (filename % int(artwork['season']))
                        elif art_type in ['seasonlandscape']:
                            if artwork['season'] == 'all' or artwork['season'] == '':
                                item['filename'] = "season-all-landscape.jpg"
                            else:
                                item['filename'] = (filename % int(artwork['season']))
                        else:
                            item['filename'] = filename
                        for targetdir in item['targetdirs']:
                            item['localfilename'] = os.path.join(targetdir, item['filename']).encode('utf-8')
                            break

                        # Continue
                        if self.mode in ['gui', 'customgui'] and not art_type in ['extrafanart', 'extrathumbs']:
                            # Add image to download list
                            self.download_list.append(item)
                            # jump out of the loop
                            imagefound = True
                        else:
                            # Check for set limits
                            if self.settings.files_local and not item['url'].startswith('http') and not art_type in ['extrafanart', 'extrathumbs']:
                                # if it's a local file use this first
                                limited = [False, 'This is your local file']
                            elif art_type == 'discart':
                                limited = self.filters.do_filter(art_type, self.mediatype, item['artwork_details'], limit_counter, pref_language, self.media_item['disctype'])
                            else:
                                limited = self.filters.do_filter(art_type, self.mediatype, item['artwork_details'], limit_counter, pref_language)
                            # Delete extrafanart when below settings and parsing the reason message
                            if limited[0] and not i == 1 and art_type in ['extrafanart', 'extrathumbs']:
                                #self.fileops._delete_file_in_dirs(item['filename'], item['targetdirs'], limited[1],self.media_item['name'])
                                pass
                            # Just ignore image when it's below settings
                            elif limited[0]:
                                imageignore = True
                                log(' - Ignoring (%s): %s' % (limited[1], item['filename']))
                            else:
                                # Always add to list when set to overwrite
                                if self.settings.files_overwrite:
                                    log(' - Adding to download list (overwrite enabled): %s' % item['filename'])
                                    self.download_list.append(item)
                                    imagefound = True
                                else:
                                    artcheck = item['art']
                                    # Check if extrathumbs/extrafanart image already exist local
                                    if art_type in ['extrathumbs','extrafanart']:
                                        for targetdir in item['targetdirs']:
                                            if not self.fileops._exists(os.path.join(targetdir, item['filename'])):
                                                missingfiles = True
                                    # Check if image already exist in database
                                    elif not art_type in['seasonlandscape','seasonbanner','seasonposter'] and not artcheck.get(art_type):
                                        missingfiles = True
                                    if missingfiles:
                                        # If missing add to list
                                        imagefound = True 
                                        log(' - Adding to download list (does not exist in all target directories): %s' % item['filename'])
                                        self.download_list.append(item)
                                    else:
                                        imagefound = True
                                        log(' - Ignoring (Exists in all target directories): %s' % item['filename'])
                                # Raise limit counter because image was added to list or it already existed
                                limit_counter += 1
                                # Check if artwork doesn't exist and the ones available are below settings even after searching for English fallback                                   
                                if limited[0] and imageignore and i == 1:
                                    for targetdir in item['targetdirs']:
                                        if not self.fileops._exists(os.path.join (targetdir, item['filename'])) and not art_type in ['extrafanart', 'extrathumbs']:
                                            self.failed_items.append('[%s] %s %s' % (self.media_item['name'], art_type, __localize__(32147)))
                            # Do some special check on season artwork
                            if art_type == 'seasonlandscape' or art_type == 'seasonbanner' or art_type   == 'seasonposter':
                                # If already present in list set limit on 1 so it is skipped
                                limit_counter = 0
                                if artwork['season'] in seasonfile_presents:
                                    log('seasonnumber: %s' %artwork['season'])
                                    limit_counter = 1
                                # If not present in list but found image add it to list and reset counter limit
                                elif imagefound:
                                    seasonfile_presents.append(artwork['season'])
                                    log('Seasons present: %s' %seasonfile_presents)
                                # if not found and not already in list set limit to zero and image found false
                                else:
                                    imagefound = False
                # Counter to make the loop twice when nothing found
                i += 1
                # Not loop when preferred language is English because that the same as the backup
                if pref_language == 'en':
                    i += 2
            # Add to failed items if 0
            if current_artwork == 0:
                self.failed_items.append('[%s] %s %s' % (self.media_item['name'], art_type, __localize__(32022)))
            # Print log message number of found images per art type
            log(' - Found a total of: %s %s' % (current_artwork, art_type))
            # End of language shit

    def _batch_download(self, image_list):
        log('########################################################')
        if not len(image_list) == 0:
            for item in image_list:
                if xbmc.abortRequested:
                    self.reportdata += ('\n - %s: %s' %(__localize__(32150), time.strftime('%d %B %Y - %H:%M')))
                    break
                if dialog_msg('iscanceled', background = self.settings.background):
                    self.reportdata += ('\n - %s: %s' %(__localize__(32153), time.strftime('%d %B %Y - %H:%M')))
                    break
                dialog_msg('update', percentage = int(float(self.download_counter['Total Artwork']) / float(len(image_list)) * 100.0), line1 = item['media_name'], line2 = __localize__(32009) + ' ' + item['artwork_string'], line3 = item['filename'], background = self.settings.background)
                # Try downloading the file and catch errors while trying to
                try:
                    if self.settings.files_local and not item['arttype'] in ['extrafanart', 'extrathumbs']:
                        if (not self.fileops._exists(item['localfilename']) or self.mode == 'customgui' or self.mode == 'gui') and item['url'].startswith('http'):
                            self.fileops._downloadfile(item['url'], item['filename'], item['targetdirs'], item['media_name'], self.mode)
                        item['url'] = item['localfilename'].replace('\\','\\\\')
                    if item['mediatype'] == 'movie':
                        if item['arttype'] == 'poster':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid": %i, "art": { "poster": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'fanart':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid": %i, "art": { "fanart": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'banner':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid": %i, "art": { "banner": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'clearlogo':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid": %i, "art": { "clearlogo": "%s"}}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'clearart':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid": %i, "art": { "clearart": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'landscape':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid": %i, "art": { "landscape": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'discart':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid": %i, "art": { "discart": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        else:
                            self.fileops._downloadfile(item['url'], item['filename'], item['targetdirs'], item['media_name'], self.mode)
                    if item['mediatype'] == 'tvshow':
                        if item['arttype'] == 'poster':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": { "tvshowid": %i, "art": { "poster": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'fanart':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": { "tvshowid": %i, "art": { "fanart": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'banner':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": { "tvshowid": %i, "art": { "banner": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'clearlogo':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": { "tvshowid": %i, "art": { "clearlogo": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'clearart':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": { "tvshowid": %i, "art": { "clearart": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'landscape':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": { "tvshowid": %i, "art": { "landscape": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        elif item['arttype'] == 'characterart':
                            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": { "tvshowid": %i, "art": { "characterart": "%s" }}, "id": 1 }' %(item['dbid'], item['url']))
                        else:
                            self.fileops._downloadfile(item['url'], item['filename'], item['targetdirs'], item['media_name'], self.mode)
                except HTTP404Error, e:
                    log('URL not found: %s' % str(e), xbmc.LOGERROR)
                    self.download_art_succes = False
                except HTTPTimeout, e:
                    self.settings.failcount += 1
                    log('Download timed out: %s' % str(e), xbmc.LOGERROR)
                    self.download_art_succes = False
                except CreateDirectoryError, e:
                    log('Could not create directory, skipping: %s' % str(e), xbmc.LOGWARNING)
                    self.download_art_succes = False
                except CopyError, e:
                    log('Could not copy file (Destination may be read only), skipping: %s' % str(e), xbmc.LOGWARNING)
                    self.download_art_succes = False
                except DownloadError, e:
                    self.settings.failcount += 1
                    log('Error downloading file: %s (Possible network error: %s), skipping' % (item['url'], str(e)), xbmc.LOGERROR)
                    self.download_art_succes = False
                else:
                    try:
                        self.download_counter[item['artwork_string']] += 1
                    except KeyError:
                        self.download_counter[item['artwork_string']] = 1
                    self.download_counter['Total Artwork'] += 1
                    self.download_art_succes = True
            log('Finished download')

    ### Checks imagelist if it has that type of artwork has got images
    def _hasimages(self, art_type):
        found = False
        for artwork in self.image_list:
            if  art_type == artwork['type'][0]:
                found = True
                break
            else: pass
        return found

    ### This handles the GUI image type selector part
    def _gui_mode(self):
        # Close the 'checking for artwork' dialog before opening the GUI list
        dialog_msg('close', background = self.settings.background)
        
        self.download_arttypes = []
        # Look for argument matching artwork types
        for item in sys.argv:
            for type in self.settings.available_arttypes:
                if item == type['art_type'] and self.mediatype == type['media_type']:
                    log('- Custom %s mode arttype: %s' %(type['media_type'],type['art_type']))
                    self.download_arttypes.append(item)
        
        # If only one specified and not extrafanart/extrathumbs
        if (len(self.download_arttypes) == 1) and not self.dbid == '' and not 'extrathumbs' in self.download_arttypes and not 'extrafanart' in self.download_arttypes:
            imagelist = False
            self.gui_selected_type = ''
            for gui_arttype in self.download_arttypes:
                self.gui_selected_type = gui_arttype
                break
            # Add parse the image restraints
            if self.gui_selected_type != '':
                for item in self.settings.available_arttypes:
                    if self.gui_selected_type == item['art_type'] and self.mediatype == item['media_type']:
                        self.gui_selected_filename = item['filename']
                        self.gui_selected_msg = item['gui_string']
                        # Get image list for that specific imagetype
                        imagelist = self._gui_imagelist(self.gui_selected_type)
                        # Some debug log output
                        for item in imagelist:
                            log('- Image put to GUI: %s' %item)
                        break
        else:
            # Create empty list and set bool to false that there is a list
            self.GUI_type_list = []
            imagelist = False
            # Fill GUI art type list
            for item in self.settings.available_arttypes:
                if item['solo_enabled'] == 'true' and self.mediatype == item['media_type'] and self._hasimages(item['art_type']):
                    gui = item['gui_string']
                    self.GUI_type_list.append (gui)
            # Not sure what this does again
            if len(self.GUI_type_list) == 1:
                self.GUI_type_list[0] = 'True'
            # Fills imagelist with image that fit the selected imagetype
            if (len(self.GUI_type_list) == 1) or self._choice_type():
                imagelist = self._gui_imagelist(self.gui_selected_type)
                # Some debug log output
                for item in imagelist:
                    log('- Image put to GUI: %s' %item)
        
        # Download the selected image
        # If there's a list, send the imagelist to the selection dialog
        if imagelist:
            if self._choose_image(imagelist):
                # Create a progress dialog so you can see the progress, Send the selected image for processing, Initiate the batch download
                dialog_msg('create')
                self._download_art(self.gui_selected_type, self.gui_selected_filename, self.target_artworkdir, self.gui_selected_msg)
                self._batch_download(self.download_list)
                # When not succesfull show failure dialog
                if not self.download_art_succes:
                    dialog_msg('okdialog', line1 = __localize__(32006) , line2 = __localize__(32007))
        # When no images found or nothing selected
        if not imagelist and not self.gui_selected_type == '':
            log('- No artwork found')
            dialog_msg('okdialog', line1 = self.media_item['name'] , line2 = self.gui_selected_msg + ' ' + __localize__(32022))
        # When download succesfull
        elif self.download_art_succes:
            log('- Download succesfull')
        # Selection was cancelled
        else:
            log('- Cancelled')
            self.cancelled = True

    # This creates the art type selection dialog. The string id is the selection constraint for what type has been chosen.
    def _choice_type(self):
        # Send the image type list to the selection dialog
        select = xbmcgui.Dialog().select(__addonname__ + ': ' + __localize__(32015) , self.GUI_type_list)
        # Create empty slected image type var
        self.gui_selected_type = ''
        # When nothing is selected from the dialog
        if select == -1: 
            log('### Canceled by user')
            return False
        # If some selection was made
        else:
            # Check what artwork type has been chosen and parse the image restraints
            for item in self.settings.available_arttypes:
                if self.GUI_type_list[select] == item['gui_string'] and self.mediatype == item['media_type']:
                    self.gui_selected_type = item['art_type']
                    self.gui_selected_filename = item['filename']
                    self.gui_selected_msg = item['gui_string']
                    return True
            else:
                return False

    def _custom_mode(self):
        self.download_arttypes = []
        # Look for argument matching artwork types
        for item in sys.argv:
            for type in self.settings.available_arttypes:
                if item == type['art_type'] and self.mediatype == type['media_type']:
                    log('- Custom %s mode arttype: %s' %(type['media_type'],type['art_type']))
                    self.download_arttypes.append(item)

        # If only one specified and not extrafanart/extrathumbs
        if (len(self.download_arttypes) == 1) and not self.dbid == '' and not 'extrathumbs' in self.download_arttypes and not 'extrafanart' in self.download_arttypes:
            # Get image list for that specific imagetype
            for gui_arttype in self.download_arttypes:
                imagelist = self._gui_imagelist(gui_arttype)
            log('- Number of images: %s' %len(imagelist))
            # If more images than 1 found show GUI selection
            if len(imagelist) > 1:
                dialog_msg('close', background = self.settings.background)
                self.mode = 'customgui'
                log('- Image list larger than 1')
                if self._choose_image(imagelist):
                    log('- Chosen: %s'%self.image_item)
                    dialog_msg('create')
                    for item in self.settings.available_arttypes:
                        if gui_arttype == item['art_type']:
                            self._download_art(item['art_type'], item['filename'], self.target_artworkdir, item['gui_string'])
                            break
                    self._batch_download(self.download_list)
                    if not self.download_art_succes:
                        dialog_msg('okdialog', line1 = __localize__(32006) , line2 = __localize__(32007))
                if self.download_art_succes:
                    log('- Download succesfull')
                else:
                    log('- Cancelled')
                    self.cancelled = True
            else:
                self._download_process()
                log('- More than 1 image available')

        # If more than one specified
        else:
            log('- Start custom bulkmode')
            self._download_process()

    # Return the selected url to the GUI part
    def _choose_image(self, imagelist):
        self.image_item = self.MyDialog(imagelist)
        if self.image_item:
            return True
        else:
            return False

    # Pass the imagelist to the dialog and return the selection
    def MyDialog(self, image_list):
        w = MainGui('DialogSelect.xml', __addonpath__, listing=image_list)
        w.doModal()
        try:
            selected_item = False
            # Go through the image list and match the chooosen image id and return the image url
            for item in image_list:
                if w.selected_id == item['id']:
                    selected_item = item
            return selected_item
        except: 
            print_exc()
            return False
        del w

class MainGui(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.listing = kwargs.get('listing')
        self.selected_id = ''

    def onInit(self):
        try :
            self.img_list = self.getControl(6)
            self.img_list.controlLeft(self.img_list)
            self.img_list.controlRight(self.img_list)
            self.getControl(3).setVisible(False)
        except :
            print_exc()
            self.img_list = self.getControl(3)

        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(__localize__(32015))

        for image in self.listing:
            listitem = xbmcgui.ListItem('%s' %(image['generalinfo']))
            listitem.setIconImage(image['preview'])
            listitem.setLabel2(image['id'])
            self.img_list.addItem(listitem)
        self.setFocus(self.img_list)

    def onAction(self, action):
        if action in ACTION_PREVIOUS_MENU:
            self.close()


    def onClick(self, controlID):
        log('# GUI control: %s' % controlID)
        if controlID == 6 or controlID == 3: 
            num = self.img_list.getSelectedPosition()
            log('# GUI position: %s' % num)
            self.selected_id = self.img_list.getSelectedItem().getLabel2()
            log('# GUI selected image ID: %s' % self.selected_id)
            self.close()

    def onFocus(self, controlID):
        pass


### Start of script
if (__name__ == '__main__'):
    log('######## Artwork Downloader: Initializing...............................', xbmc.LOGNOTICE)
    log('## Add-on ID   = %s' % str(__addonid__), xbmc.LOGNOTICE)
    log('## Add-on Name = %s' % str(__addonname__), xbmc.LOGNOTICE)
    log('## Authors     = %s' % str(__author__), xbmc.LOGNOTICE)
    log('## Version     = %s' % str(__version__), xbmc.LOGNOTICE)
    Main()
    log('script stopped', xbmc.LOGNOTICE)
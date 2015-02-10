#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2011-2014 Martijn Kaijser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

#import modules
import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import time
import lib.common

### get addon info
__addon__        = lib.common.__addon__
__addonname__    = lib.common.__addonname__
__addonpath__    = lib.common.__addonpath__
__addonprofile__ = lib.common.__addonprofile__
__localize__     = lib.common.__localize__
__version__      = lib.common.__version__

### import libraries
from lib import language
from lib import provider
from lib.apply_filters import filter
from lib.art_list import arttype_list
from lib.fileops import fileops, cleanup
from lib.gui import choose_image, dialog_msg, choice_type, gui_imagelist, hasimages
from lib.media_setup import _media_listing as media_listing
from lib.media_setup import _media_unique as media_unique
from lib.provider import tmdb # import on behalf of searching when there's no ID
from lib.provider.local import local
from lib.report import create_report
from lib.script_exceptions import *
from lib.settings import get_limit, get, check
from lib.utils import *
from traceback import print_exc
from urlparse import urlsplit
from xml.parsers.expat import ExpatError

arttype_list = arttype_list()
cancelled = False
download_arttypes = []
download_counter = {'Total Artwork': 0}
download_list = []
download_succes = False
failed_items = []
image_list = []
limit = get_limit()
reportdata = '[B]Artwork Downloader:[/B]'
setting = get()
startup = {'mediatype': False,
           'dbid': False,
           'mode': False,
           'silent': False}

class Main:
    def __init__(self):
        if not check():          # Check if there are some faulty combinations present
            sys.exit(1)
        if self.initialise():
            global setting
            global startup
            providers = provider.get_providers()
            # Check for silent background mode
            if startup['silent']:
                setting['background'] = True
                setting['notify'] = False
            # Check for gui mode
            elif startup['mode'] == 'gui':
                setting['background'] = True
                setting['notify'] = False
                setting['files_overwrite'] = True
            dialog_msg('create',
                       line1 = __localize__(32008),
                       background = setting['background'])
            # Check if mediatype is specified
            if startup['mediatype']:
                # Check if dbid is specified
                if startup['dbid']:
                    mediaList = media_unique(startup['mediatype'],startup['dbid'])
                    if startup['mediatype'] == 'movie':
                        self.download_artwork(mediaList, providers['movie_providers'])
                    elif startup['mediatype'] == 'tvshow':
                        self.download_artwork(mediaList, providers['tv_providers'])
                    elif startup['mediatype'] == 'musicvideo':
                        self.download_artwork(mediaList, providers['musicvideo_providers'])
                    if (not dialog_msg('iscanceled', background = setting['background']) and not
                        (startup['mode'] == 'customgui' or
                        startup['mode'] == 'gui')):
                        self._batch_download(download_list)
                else:
                    # If no medianame specified
                    # 1. Check what media type was specified, 2. Retrieve library list, 3. Enable the correct type, 4. Do the API stuff
                    setting['movie_enable'] = False
                    setting['tvshow_enable'] = False
                    setting['musicvideo_enable'] = False
                    if startup['mediatype'] == 'movie':
                        setting['movie_enable'] = True
                        mediaList = media_listing('movie')
                        self.download_artwork(mediaList, providers['movie_providers'])
                    elif startup['mediatype'] == 'tvshow':
                        setting['tvshow_enable'] = True
                        mediaList = media_listing('tvshow')
                        self.download_artwork(mediaList, providers['tv_providers'])
                    elif startup['mediatype'] == 'musicvideo':
                        setting['musicvideo_enable'] = True
                        mediaList = media_listing('musicvideo')
                        self.download_artwork(mediaList, providers['musicvideo_providers'])
                    if not dialog_msg('iscanceled', background = setting['background']):
                        self._batch_download(download_list)
            # No mediatype is specified
            else:
                # activate movie/tvshow/musicvideo for custom run
                if startup['mode'] == 'custom':
                    setting['movie_enable'] = True
                    setting['tvshow_enable'] = True
                    setting['musicvideo_enable'] = True
                # Normal oprations check
                # 1. Check if enable, 2. Get library list, 3. Set mediatype, 4. Do the API stuff
                # Do this for each media type
                if setting['movie_enable'] and not dialog_msg('iscanceled', background = True):
                    startup['mediatype'] = 'movie'
                    mediaList = media_listing(startup['mediatype'])
                    self.download_artwork(mediaList, providers['movie_providers'])
                if setting['tvshow_enable'] and not dialog_msg('iscanceled', background = True):
                    startup['mediatype'] = 'tvshow'
                    mediaList = media_listing(startup['mediatype'])
                    self.download_artwork(mediaList, providers['tv_providers'])
                if setting['musicvideo_enable'] and not dialog_msg('iscanceled', background = True):
                    startup['mediatype'] = 'musicvideo'
                    mediaList = media_listing(startup['mediatype'])
                    self.download_artwork(mediaList, providers['musicvideo_providers'])
                # If not cancelled throw the whole downloadlist into the batch downloader
                if not dialog_msg('iscanceled',
                                  background = setting['background']):
                    self._batch_download(download_list)
        else:
            log('Initialisation error, script aborting', xbmc.LOGERROR)
        # Make sure that files_overwrite option get's reset after downloading
        __addon__.setSetting(id='files_overwrite', value='false')
        cleanup()
        self.report()

    ### load settings and initialise needed directories
    def initialise(self):
        global startup
        log('## Checking for downloading mode...')
        args = ['silent', 'mode', 'mediatype', 'dbid']
        for item in sys.argv:
            arg = item.split('=')
            i = arg[0]
            if arg[0] in args:
                j = arg[1]
                startup.update({arg[0]:arg[1]})
        if startup['mediatype'] and (startup['mediatype'] not in ['tvshow', 'movie', 'musicvideo']):
            log('Error: invalid mediatype, must be one of movie, tvshow or musicvideo', xbmc.LOGERROR)
            return False
        elif startup['dbid'] == '':
            dialog_msg('okdialog',
                       line1 = __localize__(32084))
            log('Error: no valid dbid recieved, item must be scanned into library.', xbmc.LOGERROR)
            return False
        try:
            # Creates temp folder
            self.fileops = fileops()
        except CreateDirectoryError, e:
            log('Could not create directory: %s' % str(e))
            return False
        else:
            return True

    def report(self):
        global setting
        ### log results and notify user
        # Download totals to log and to download report
        create_report(reportdata, download_counter, failed_items)

        # Build dialog messages
        summary = __localize__(32012) + ': %s ' % download_counter['Total Artwork'] + __localize__(32020)
        summary_notify = ': %s ' % download_counter['Total Artwork'] + __localize__(32020)
        provider_msg1 = __localize__(32001)
        provider_msg2 = __localize__(32184) + ' | ' + __localize__(32185) + ' | ' + __localize__(32186)
        # Close dialog in case it was open before doing a notification
        time.sleep(2)
        dialog_msg('close',
                   background = setting['background'])
        # Some dialog checks
        if setting['notify']:
            log('Notify on finished/error enabled')
            setting['background'] = False
        if (xbmc.Player().isPlayingVideo() or startup['silent'] or 
                                              startup['mode'] in ['gui', 'customgui', 'custom']):
            log('Silent finish because of playing a video or silent mode')
            setting['background'] = True
        if not setting['failcount'] < setting['failthreshold']:
            log('Network error detected, script aborted', xbmc.LOGERROR)
            dialog_msg('okdialog',
                       line1 = __localize__(32010),
                       line2 = __localize__(32011),
                       background = setting['background'])
        if not xbmc.abortRequested:
            # Show dialog/notification
            if setting['background']:
                dialog_msg('okdialog',
                           line0 = summary_notify,
                           line1 = provider_msg1 + ' ' + provider_msg2,
                           background = setting['background'],
                           cancelled = cancelled)
            else:
                # When chosen no in the 'yes/no' dialog execute the viewer.py and parse 'downloadreport'
                if dialog_msg('yesno',
                              line1 = summary,
                              line2 = provider_msg1,
                              line3 = provider_msg2,
                              background = setting['background'],
                              nolabel = __localize__(32027),
                              yeslabel = __localize__(32028)):
                    runcmd = os.path.join(__addonpath__, 'lib/viewer.py')
                    xbmc.executebuiltin('XBMC.RunScript (%s,%s) '%(runcmd, 'downloadreport'))
        else:
            dialog_msg('okdialog',
                       line1 = __localize__(32010),
                       line2 = summary,
                       background = setting['background'])
        # Container refresh
        if startup['mode'] in ['gui','customgui']:
            if download_succes:
                xbmc.executebuiltin('Container.Refresh')
                #xbmc.executebuiltin('XBMC.ReloadSkin()')

    ### download media fanart
    def download_artwork(self, media_list, providers):
        global image_list
        global reportdata
        processeditems = 0
        media_list_total = len(media_list)
        for currentmedia in media_list:
            image_list = []
            # Declare some vars
            if not currentmedia.get('disctype'):
                currentmedia['disctype'] = 'n/a'
            ### check if XBMC is shutting down
            if xbmc.abortRequested:
                log('XBMC abort requested, aborting')
                reportdata += ('\n - %s: %s' %(__localize__(32150), time.strftime('%d %B %Y - %H:%M')))
                break
            ### check if script has been cancelled by user
            if dialog_msg('iscanceled',
                          background = setting['background']):
                reportdata += ('\n - %s [%s]: %s' %(__localize__(32151), currentmedia['mediatype'], time.strftime('%d %B %Y - %H:%M')))
                break
            # abort script because of to many failures
            if not setting['failcount'] < setting['failthreshold']:
                reportdata += ('\n - %s: %s' %(__localize__(32152), time.strftime('%d %B %Y - %H:%M')))
                break
            dialog_msg('update',
                        percentage = int(float(processeditems) / float(media_list_total) * 100.0),
                        line1 = currentmedia['name'],
                        line2 = __localize__(32008),
                        line3 = '',
                        background = setting['background'])
            log('########################################################')
            log('Processing media:  %s' % currentmedia['name'])
            # do some id conversions
            if (not currentmedia['mediatype'] == 'tvshow' and
                currentmedia['id'] in ['','tt0000000','0']):
                log('No IMDB ID found, trying to search themoviedb.org for matching title.')
                currentmedia['id'] = tmdb._search_movie(currentmedia['name'],currentmedia['year'])
            elif (currentmedia['mediatype'] == 'movie' and not
                  currentmedia['id'] == '' and not
                  currentmedia['id'].startswith('tt')):
                log('No valid ID found, trying to search themoviedb.org for matching title.')
                currentmedia['id'] = tmdb._search_movie(currentmedia['name'],currentmedia['year'])
            log('Provider ID:       %s' % currentmedia['id'])
            log('Media path:        %s' % currentmedia['path'])
            # Declare the target folders
            artworkdir = []
            extrafanartdirs = []
            extrathumbsdirs = []
            for item in currentmedia['path']:
                artwork_dir = os.path.join(item + '/')
                extrafanart_dir = os.path.join(artwork_dir + 'extrafanart' + '/')
                extrathumbs_dir = os.path.join(artwork_dir + 'extrathumbs' + '/')
                artworkdir.append(artwork_dir.replace('BDMV/','').replace('VIDEO_TS/',''))
                extrafanartdirs.append(extrafanart_dir)
                extrathumbsdirs.append(extrathumbs_dir)
            # Check if using the centralize option
            if setting['centralize_enable']:
                if currentmedia['mediatype'] == 'tvshow':
                    extrafanartdirs.append(setting['centralfolder_tvshows'])
                elif currentmedia['mediatype'] == 'movie':
                    extrafanartdirs.append(setting['centralfolder_movies'])
            currentmedia['artworkdir'] = artworkdir
            currentmedia['extrafanartdirs'] = extrafanartdirs
            currentmedia['extrathumbsdirs'] = extrathumbsdirs
            # this part check for local files when enabled
            scan_more = True
            missing = False
            if setting['files_local']:
                local_list = []
                local_list, scan_more, missing = local().get_image_list(currentmedia)
                # append local artwork
                for item in local_list:
                    image_list.append(item)
            # Check for presence of id used by source sites
            if (startup['mode'] == 'gui' and
                ((currentmedia['id'] == '') or
                (currentmedia['mediatype'] == 'tvshow' and
                currentmedia['id'].startswith('tt')))):
                dialog_msg('close',
                           background = setting['background'])
                dialog_msg('okdialog',
                           '',
                           currentmedia['name'],
                           __localize__(32030))
            elif currentmedia['id'] == '':
                log('- No ID found, skipping')
                failed_items.append('[%s] ID %s' %(currentmedia['name'], __localize__(32022)))
            elif currentmedia['mediatype'] == 'tvshow' and currentmedia['id'].startswith('tt'):
                log('- IMDB ID found for TV show, skipping')
                failed_items.append('[%s]: TVDB ID %s' %(currentmedia['name'], __localize__(32022)))
            #skip scanning for more if local files have been found and not run in gui / custom mode
            elif not scan_more and not startup['mode'] in ['gui', 'custom']:
                log('- Already have all files local')
                pass
            # If correct ID found and don't already have all artwork retrieve from providers
            else:
                log('- Still missing some files')
                log(missing)
                temp_image_list = []
                # Run through all providers getting their imagelisting
                failcount = 0
                for self.provider in providers:
                    if not failcount < setting['failthreshold']:
                        break
                    artwork_result = ''
                    xmlfailcount = 0
                    while not artwork_result == 'pass' and not artwork_result == 'skipping':
                        if artwork_result == 'retrying':
                            xbmc.sleep(setting['api_timedelay'])
                        try:
                            temp_image_list = self.provider.get_image_list(currentmedia['id'])
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
                            failed_items.append('[%s] %s' %(currentmedia['name'], __localize__(32133)))
                        except ItemNotFoundError, e:
                            errmsg = '%s not found' % currentmedia['id']
                            artwork_result = 'skipping'
                        except ExpatError, e:
                            xmlfailcount += 1
                            errmsg = 'Error parsing xml: %s' % str(e)
                            artwork_result = 'retrying'
                        except HTTPTimeout, e:
                            failcount += 1
                            errmsg = 'Timed out'
                            artwork_result = 'skipping'
                        except DownloadError, e:
                            failcount += 1
                            errmsg = 'Possible network error: %s' % str(e)
                            artwork_result = 'skipping'
                        else:
                            artwork_result = 'pass'
                            for item in temp_image_list:
                                image_list.append(item)
                        if not xmlfailcount < setting['xmlfailthreshold']:
                            artwork_result = 'skipping'
                        if not artwork_result == 'pass':
                            log('Error getting data from %s (%s): %s' % (self.provider.name, errmsg, artwork_result))

            if len(image_list) > 0:
                if (limit['limit_artwork'] and limit['limit_extrafanart_max'] < len(image_list)):
                    self.download_max = limit['limit_extrafanart_max']
                else:
                    self.download_max = len(image_list)
                # Check for GUI mode
                if startup['mode'] == 'gui':
                    log('- Using GUI mode')
                    self._gui_mode(currentmedia)
                elif startup['mode'] == 'custom':
                    log('- Using custom mode')
                    self._custom_mode(currentmedia)
                else:
                    #log('- Using bulk mode')
                    self._download_process(currentmedia)
            processeditems += 1

    ### Processes the different modes for downloading of files
    def _download_process(self, currentmedia):
        # with the exception of cutsom mode run through the art_list to see which ones are enabled and create a list with those
        # then call _download_art to process it
        if not startup['mode'] == 'custom':
            global download_arttypes
            download_arttypes = []
            for art_type in arttype_list:
                if art_type['bulk_enabled'] and startup['mediatype'] == art_type['media_type']:
                    download_arttypes.append(art_type['art_type'])
        # do the same but for custom mode
        for art_type in arttype_list:
            if (art_type['art_type'] in download_arttypes and
                ((setting['movie_enable'] and startup['mediatype'] == art_type['media_type']) or
                (setting['tvshow_enable'] and startup['mediatype'] == art_type['media_type']) or
                (setting['musicvideo_enable'] and startup['mediatype'] == art_type['media_type']))):
                if art_type['art_type'] == 'extrafanart':
                    self._download_art(currentmedia, art_type, currentmedia['extrafanartdirs'])
                elif art_type['art_type'] == 'extrathumbs':
                    self._download_art(currentmedia, art_type, currentmedia['extrathumbsdirs'])
                else:
                    self._download_art(currentmedia, art_type, currentmedia['artworkdir'])

    ### Artwork downloading
    def _download_art(self, currentmedia, art_item, targetdirs):
        log('* Image type: %s' %art_item['art_type'])
        seasonfile_presents = []
        current_artwork = 0                     # Used in progras dialog
        limit_counter = 0                       # Used for limiting on number
        pref_language = language.get_abbrev()   # get abbreviation
        i = 0                                   # Set loop counter
        imagefound = False                      # Set found image false
        imageignore = False                     # Set ignaore image false
        missingfiles = False
        global download_list
        final_image_list = []
        if startup['mode'] in ['gui', 'customgui'] and not art_item['art_type'] in ['extrafanart', 'extrathumbs']:
            final_image_list.append(image_list)
        else:
            final_image_list = image_list
        if len(final_image_list) == 0:
            log(' - Nothing to download')
        else:
            # Do some language shit
            # loop two times than skip
            while (i < 2 and not imagefound):
                # when no image found found after one imagelist loop set to english
                if not imagefound and i == 1:
                    pref_language = 'en'
                    log('! No matching %s artwork found. Searching for English backup' %limit['limit_preferred_language'])
                # loop through image list
                for artwork in final_image_list:
                    if art_item['art_type'] in artwork['art_type']:
                        ### check if script has been cancelled by user
                        if dialog_msg('iscanceled',
                                      background = setting['background']):
                            #dialog('close', background = setting['background'])
                            break
                        # Create an image info list
                        item = {'url': artwork['url'],
                                'targetdirs': targetdirs,
                                'media_name': currentmedia['name'],
                                'mediatype':currentmedia['mediatype'],
                                'artwork_string': art_item['gui_string'],
                                'artwork_details': artwork,
                                'dbid':currentmedia['dbid'],
                                'art':currentmedia['art'],
                                'art_type':art_item['art_type']}
                        # raise artwork counter only on first loop
                        if i != 1:
                            current_artwork += 1

                        # File naming
                        if art_item['art_type']   == 'extrafanart':
                            item['filename'] = ('%s.jpg'% artwork['id'])
                        elif art_item['art_type'] == 'extrathumbs':
                            item['filename'] = (art_item['filename'] % str(limit_counter + 1))
                        elif art_item['art_type'] in ['seasonposter']:
                            if artwork['season'] == '0':
                                item['filename'] = "season-specials-poster.jpg"
                            elif artwork['season'] == 'all':
                                item['filename'] = "season-all-poster.jpg"
                            elif artwork['season'] == 'n/a':
                                break
                            else:
                                item['filename'] = (art_item['filename'] % int(artwork['season']))
                        elif art_item['art_type'] in ['seasonbanner']:
                            if artwork['season'] == '0':
                                item['filename'] = "season-specials-banner.jpg"
                            elif artwork['season'] == 'all':
                                item['filename'] = "season-all-banner.jpg"
                            elif artwork['season'] == 'n/a':
                                break
                            else:
                                item['filename'] = (art_item['filename'] % int(artwork['season']))
                        elif art_item['art_type'] in ['seasonlandscape']:
                            if artwork['season'] == 'all' or artwork['season'] == '':
                                item['filename'] = "season-all-landscape.jpg"
                            else:
                                item['filename'] = (art_item['filename'] % int(artwork['season']))
                        else:
                            item['filename'] = art_item['filename']
                        for targetdir in item['targetdirs']:
                            item['localfilename'] = os.path.join(targetdir, item['filename']).encode('utf-8')
                            break

                        # Continue
                        if startup['mode'] in ['gui', 'customgui'] and not art_item['art_type'] in ['extrafanart', 'extrathumbs']:
                            # Add image to download list
                            download_list.append(item)
                            # jump out of the loop
                            imagefound = True
                        else:
                            # Check for set limits
                            if (setting['files_local'] and not
                                item['url'].startswith('http') and not
                                art_item['art_type'] in ['extrafanart', 'extrathumbs']):
                                # if it's a local file use this first
                                limited = [False, 'This is your local file']
                            elif art_item['art_type'] == 'discart':
                                limited = filter(art_item['art_type'],
                                                 startup['mediatype'],
                                                 item['artwork_details'],
                                                 limit_counter,
                                                 pref_language,
                                                 currentmedia['disctype'])
                            else:
                                limited = filter(art_item['art_type'],
                                                 startup['mediatype'],
                                                 item['artwork_details'],
                                                 limit_counter,
                                                 pref_language)
                            # Delete extrafanart when below settings and parsing the reason message
                            if limited[0] and not i == 1 and art_item['art_type'] in ['extrafanart', 'extrathumbs']:
                                #self.fileops._delete_file_in_dirs(item['filename'], item['targetdirs'], limited[1],currentmedia['name'])
                                pass
                            # Just ignore image when it's below settings
                            elif limited[0]:
                                imageignore = True
                                log(' - Ignoring (%s): %s' % (limited[1], item['filename']))
                            else:
                                # Always add to list when set to overwrite
                                if setting['files_overwrite']:
                                    log(' - Adding to download list (overwrite enabled): %s' % item['filename'])
                                    download_list.append(item)
                                    imagefound = True
                                else:
                                    artcheck = item['art']
                                    # Check if extrathumbs/extrafanart image already exist local
                                    if art_item['art_type'] in ['extrathumbs','extrafanart']:
                                        for targetdir in item['targetdirs']:
                                            if not self.fileops._exists(os.path.join(targetdir, item['filename'])):
                                                missingfiles = True
                                    # Check if image already exist in database
                                    elif not art_item['art_type'] in ['seasonlandscape','seasonbanner','seasonposter']:
                                        if setting['files_local']and not self.fileops._exists(item['localfilename']):
                                            missingfiles = True
                                        elif not artcheck.get(art_item['art_type']):
                                            missingfiles = True
                                    if missingfiles:
                                        # If missing add to list
                                        imagefound = True
                                        log(' - Adding to download list (does not exist in all target directories): %s' % item['filename'])
                                        download_list.append(item)
                                    else:
                                        imagefound = True
                                        log(' - Ignoring (Exists in all target directories): %s' % item['filename'])
                                # Raise limit counter because image was added to list or it already existed
                                limit_counter += 1
                                # Check if artwork doesn't exist and the ones available are below settings even after searching for English fallback
                                if limited[0] and imageignore and i == 1:
                                    for targetdir in item['targetdirs']:
                                        if (not self.fileops._exists(os.path.join (targetdir,item['filename'])) and not
                                            art_item['art_type'] in ['extrafanart', 'extrathumbs']):
                                            failed_items.append('[%s] %s %s' % (currentmedia['name'], art_item['art_type'], __localize__(32147)))
                            # Do some special check on season artwork
                            if art_item['art_type'] == 'seasonlandscape' or art_item['art_type'] == 'seasonbanner' or art_item['art_type']   == 'seasonposter':
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
                failed_items.append('[%s] %s %s' % (currentmedia['name'], art_item['art_type'], __localize__(32022)))
            # Print log message number of found images per art type
            log(' - Found a total of: %s %s' % (current_artwork, art_item['art_type']))
            # End of language shit

    def _batch_download(self, image_list):
        log('########################################################')
        global download_counter
        global download_succes
        global reportdata
        image_list_total = len(image_list)
        if not image_list_total == 0:
            failcount = 0
            for item in image_list:
                if xbmc.abortRequested:
                    reportdata += ('\n - %s: %s' %(__localize__(32150), time.strftime('%d %B %Y - %H:%M')))
                    break
                if dialog_msg('iscanceled',
                              background = setting['background']):
                    reportdata += ('\n - %s: %s' %(__localize__(32153), time.strftime('%d %B %Y - %H:%M')))
                    break
                dialog_msg('update',
                           percentage = int(float(download_counter['Total Artwork']) / float(image_list_total) * 100.0),
                           line1 = item['media_name'],
                           line2 = __localize__(32009) + ' ' + __localize__(item['artwork_string']),
                           line3 = item['filename'], background = setting['background'])
                # Try downloading the file and catch errors while trying to
                try:
                    if setting['files_local'] and not item['art_type'] in ['extrafanart', 'extrathumbs']:
                        if ((not self.fileops._exists(item['localfilename']) or
                            startup['mode'] == 'customgui' or
                            startup['mode'] == 'gui') and
                            item['url'].startswith('http')):
                            self.fileops._downloadfile(item)
                        item['url'] = item['localfilename'].replace('\\','\\\\')
                    if item['art_type'] in ['extrathumbs', 'extrafanart']:
                        self.fileops._downloadfile(item)
                    elif item['mediatype'] == 'movie':
                        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": { "movieid": %i, "art": { "%s": "%s" }}, "id": 1 }' %(item['dbid'], item['art_type'], item['url']))
                    elif item['mediatype'] == 'tvshow':
                        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.SetTVShowDetails", "params": { "tvshowid": %i, "art": { "%s": "%s" }}, "id": 1 }' %(item['dbid'], item['art_type'], item['url']))
                except HTTP404Error, e:
                    log('URL not found: %s' % str(e), xbmc.LOGERROR)
                    download_succes = False
                except HTTPTimeout, e:
                    failcount += 1
                    log('Download timed out: %s' % str(e), xbmc.LOGERROR)
                    download_succes = False
                except CreateDirectoryError, e:
                    log('Could not create directory, skipping: %s' % str(e), xbmc.LOGWARNING)
                    download_succes = False
                except CopyError, e:
                    log('Could not copy file (Destination may be read only), skipping: %s' % str(e), xbmc.LOGWARNING)
                    download_succes = False
                except DownloadError, e:
                    failcount += 1
                    log('Error downloading file: %s (Possible network error: %s), skipping' % (item['url'], str(e)), xbmc.LOGERROR)
                    download_succes = False
                else:
                    try:
                        download_counter[__localize__(item['artwork_string'])] += 1
                    except KeyError:
                        download_counter[__localize__(item['artwork_string'])] = 1
                    download_counter['Total Artwork'] += 1
                    download_succes = True
            log('Finished download')

    ### This handles the GUI image type selector part
    def _gui_mode(self, currentmedia):
        global download_arttypes
        global image_list
        # Close the 'checking for artwork' dialog before opening the GUI list
        dialog_msg('close',
                   background = setting['background'])
        # Look for argument matching artwork types
        for item in sys.argv:
            for type in arttype_list:
                if item == type['art_type'] and startup['mediatype'] == type['media_type']:
                    log('- Custom %s mode art_type: %s' %(type['media_type'],type['art_type']))
                    download_arttypes.append(item)
        gui_selected_type = False
        # If only one specified and not extrafanart/extrathumbs
        if ((len(download_arttypes) == 1) and
            startup['dbid'] and not
            'extrathumbs' in download_arttypes and not
            'extrafanart' in download_arttypes):
            imagelist = False
            for gui_arttype in download_arttypes:
                gui_selected_type = gui_arttype
                break
            # Add parse the image restraints
            if gui_selected_type:
                for arttype in arttype_list:
                    if gui_selected_type == arttype['art_type'] and startup['mediatype'] == arttype['media_type']:
                        # Get image list for that specific imagetype
                        imagelist = gui_imagelist(image_list, gui_selected_type)
                        # Some debug log output
                        for image in imagelist:
                            log('- Image put to GUI: %s' %image)
                        break
        else:
            # Create empty list and set bool to false that there is a list
            enabled_type_list = []
            imagelist = False
            # Fill GUI art type list
            for arttype in arttype_list:
                if (arttype['solo_enabled'] == 'true' and
                    startup['mediatype'] == arttype['media_type'] and
                    hasimages(image_list, arttype['art_type'])):
                    gui = __localize__(arttype['gui_string'])
                    enabled_type_list.append(gui)
            # Not sure what this does again
            if len(enabled_type_list) == 1:
                enabled_type_list[0] = 'True'
            # Fills imagelist with image that fit the selected imagetype
            type_list = choice_type(enabled_type_list, startup, arttype_list)
            if (len(enabled_type_list) == 1) or type_list:
                imagelist = gui_imagelist(image_list, type_list['art_type'])
                # Some debug log output
                for image in imagelist:
                    log('- Image put to GUI: %s' %image)

        # Download the selected image
        # If there's a list, send the imagelist to the selection dialog
        if imagelist:
            image_list = choose_image(imagelist)
            if image_list:
                # Create a progress dialog so you can see the progress,
                #Send the selected image for processing, Initiate the batch download
                dialog_msg('create')
                for art_type in arttype_list:
                    if image_list['art_type'][0] == art_type['art_type']:
                        self._download_art(currentmedia, art_type, currentmedia['artworkdir'])
                        self._batch_download(download_list)
                        break
                # When not succesfull show failure dialog
                if not download_succes:
                    dialog_msg('okdialog',
                               line1 = __localize__(32006),
                               line2 = __localize__(32007))
        # When no images found or nothing selected
        if not imagelist and gui_selected_type:
            log('- No artwork found')
            dialog_msg('okdialog',
                       line1 = currentmedia['name'],
                       line2 = __localize__(arttype['gui_string']) + ' ' + __localize__(32022))
        # When download succesfull
        elif download_succes:
            log('- Download succesfull')
        # Selection was cancelled
        else:
            global cancelled
            cancelled = True

    def _custom_mode(self, currentmedia):
        global download_arttypes
        global image_list
        global startup
        # Look for argument matching artwork types
        for item in sys.argv:
            for type in arttype_list:
                if item == type['art_type'] and startup['mediatype'] == type['media_type']:
                    log('- Custom %s mode art_type: %s' %(type['media_type'],type['art_type']))
                    download_arttypes.append(item)

        # If only one specified and not extrafanart/extrathumbs
        if ((len(download_arttypes) == 1) and
            startup['dbid'] and not
            'extrathumbs' in download_arttypes and not
            'extrafanart' in download_arttypes):
            # Get image list for that specific imagetype
            for gui_arttype in download_arttypes:
                imagelist = gui_imagelist(image_list, gui_arttype)
            log('- Number of images: %s' %len(imagelist))
            # If more images than 1 found show GUI selection
            if len(imagelist) > 1:
                dialog_msg('close',
                           background = setting['background'])
                startup['mode'] = 'customgui'
                log('- Image list larger than 1')
                image_list = choose_image(imagelist)
                if image_list:
                    log('- Chosen: %s'% image_list)
                    dialog_msg('create')
                    for item in arttype_list:
                        if gui_arttype == item['art_type']:
                            self._download_art(currentmedia,
                                               item,
                                               currentmedia['artworkdir'])
                            break
                    self._batch_download(download_list)
                    if not download_succes:
                        dialog_msg('okdialog',
                                   line1 = __localize__(32006),
                                   line2 = __localize__(32007))
                if download_succes:
                    log('- Download succesfull')
                else:
                    log('- Cancelled')
                    global cancelled
                    cancelled = True
            else:
                self._download_process(currentmedia)
                log('- More than 1 image available')

        # If more than one specified
        else:
            log('- Start custom bulkmode')
            self._download_process(currentmedia)

### Start of script
if (__name__ == '__main__'):
    log('######## Artwork Downloader: Initializing...............................', xbmc.LOGNOTICE)
    log('## Add-on Name = %s' % str(__addonname__), xbmc.LOGNOTICE)
    log('## Version     = %s' % str(__version__), xbmc.LOGNOTICE)
    Main()
    log('script stopped', xbmc.LOGNOTICE)

#import modules
import sys
import os
import urllib
import xbmcvfs

### import libraries
#from resources.lib.provider.base import BaseProvider
from resources.lib.script_exceptions import NoFanartError
from resources.lib.utils import *
from operator import itemgetter
from resources.lib.settings import settings
from resources.lib.fileops import fileops

### get addon info
__localize__    = ( sys.modules[ "__main__" ].__localize__ )


class local():
    def get_image_list(self,media_item):
        self.settings = settings()
        self.settings._get_general()    # Get settings from settings.xml
        self.settings._get_artwork()    # Get settings from settings.xml
        self.settings._get_limit()      # Get settings from settings.xml
        self.settings._vars()           # Get some settings vars
        self.settings._artype_list()    # Fill out the GUI and Arttype lists with enabled options
        image_list = []
        target_extrafanartdirs = []
        target_extrathumbsdirs = []
        target_artworkdir = []
        for item in media_item['path']:
            target_artworkdir = os.path.join(item + '/').replace('BDMV','').replace('VIDEO_TS','')
            target_extrafanartdirs = os.path.join(item + 'extrafanart' + '/')
            target_extrathumbsdirs = os.path.join(item + 'extrathumbs' + '/')
            break
        file_list = xbmcvfs.listdir(target_artworkdir)[1]
        ### Processes the bulk mode downloading of files
        i = 0
        j = 0
        for item in self.settings.available_arttypes:
            if item['bulk_enabled'] and media_item['mediatype'] == item['media_type']:
                #log('finding: %s, arttype counter: %s'%(item['art_type'], j))
                j += 1
                # File checking
                if item['art_type'] == 'extrafanart':
                    i += 1
                    extrafanart_file_list = ''
                    if xbmcvfs.exists(target_extrafanartdirs):
                        extrafanart_file_list = xbmcvfs.listdir(extrafanart_dir)[1]
                        #log('list of extrafanart files: %s'%file_list)
                    #log('extrafanart found: %s'%len(file_list))
                    if len(extrafanart_file_list) <= self.settings.limit_extrafanart_max:
                        i += 1

                elif item['art_type'] == 'extrathumbs':
                    i += 1
                    extrathumbs_file_list = ''
                    if xbmcvfs.exists(target_extrathumbsdirs):
                        extrathumbs_file_list = xbmcvfs.listdir(extrathumbs_dir)[1]
                        #log('list of extrathumbs files: %s'%file_list)
                    #log('extrathumbs found: %s'%len(file_list))
                    if len(extrathumbs_file_list) <= self.settings.limit_extrathumbs_max:
                        i += 1

                elif item['art_type'] in ['seasonposter']:
                    for season in media_item['seasons']:
                        if season == '0':
                            filename = "season-specials-poster.jpg"
                        elif season == 'all':
                            filename = "season-all-poster.jpg"
                        else:
                            filename = (item['filename'] % int(season))
                        if filename in file_list:
                            url = os.path.join(target_artworkdir, filename).encode('utf-8')
                            i += 1
                            generalinfo = '%s: %s  |  ' %( __localize__(32141), 'n/a')
                            generalinfo += '%s: %s  |  ' %( __localize__(32144), season)
                            generalinfo += '%s: %s  |  ' %( __localize__(32143), 'n/a')
                            generalinfo += '%s: %s  |  ' %( __localize__(32145), 'n/a')
                            # Fill list
                            #log ('found: %s'%url)
                            image_list.append({'url': url,
                                               'preview': url,
                                               'id': filename,
                                               'type': [item['art_type']],
                                               'size': '0',
                                               'season': season,
                                               'language': 'EN',
                                               'votes': '0',
                                               'generalinfo': generalinfo})
                        else:
                            pass

                elif item['art_type'] in ['seasonbanner']:
                    for season in media_item['seasons']:
                        if season == '0':
                            filename = "season-specials-banner.jpg"
                        elif season == 'all':
                            filename = "season-all-banner.jpg"
                        else:
                            filename = (item['filename'] % int(season))
                        if filename in file_list:
                            url = os.path.join(target_artworkdir, filename).encode('utf-8')
                            i += 1
                            generalinfo = '%s: %s  |  ' %( __localize__(32141), 'n/a')
                            generalinfo += '%s: %s  |  ' %( __localize__(32144), season)
                            generalinfo += '%s: %s  |  ' %( __localize__(32143), 'n/a')
                            generalinfo += '%s: %s  |  ' %( __localize__(32145), 'n/a')
                            # Fill list
                            #log ('found: %s'%url)
                            image_list.append({'url': url,
                                               'preview': url,
                                               'id': filename,
                                               'type': [item['art_type']],
                                               'size': '0',
                                               'season': season,
                                               'language': 'EN',
                                               'votes': '0',
                                               'generalinfo': generalinfo})
                        else:
                            pass

                elif item['art_type'] in ['seasonlandscape']:
                    for season in media_item['seasons']:
                        if season == 'all' or season == '':
                            filename = "season-all-landscape.jpg"
                        else:
                            filename = (item['filename'] % int(season))
                        if filename in file_list:
                            url = os.path.join(target_artworkdir, filename).encode('utf-8')
                            i += 1
                            generalinfo = '%s: %s  |  ' %( __localize__(32141), 'n/a')
                            generalinfo += '%s: %s  |  ' %( __localize__(32144), season)
                            generalinfo += '%s: %s  |  ' %( __localize__(32143), 'n/a')
                            generalinfo += '%s: %s  |  ' %( __localize__(32145), 'n/a')
                            # Fill list
                            log ('found: %s'%url)
                            image_list.append({'url': url,
                                               'preview': url,
                                               'id': filename,
                                               'type': [item['art_type']],
                                               'size': '0',
                                               'season': season,
                                               'language': 'EN',
                                               'votes': '0',
                                               'generalinfo': generalinfo})
                        else:
                            pass

                else:
                    filename = item['filename']
                    if filename in file_list:
                        url = os.path.join(target_artworkdir, filename).encode('utf-8')
                        i += 1
                        generalinfo = '%s: %s  |  ' %( __localize__(32141), 'n/a')
                        generalinfo += '%s: %s  |  ' %( __localize__(32143), 'n/a')
                        generalinfo += '%s: %s  |  ' %( __localize__(32145), 'n/a')
                        # Fill list
                        #log ('found: %s'%url)
                        image_list.append({'url': url,
                                           'preview': url,
                                           'id': filename,
                                           'type': [item['art_type']],
                                           'size': '0',
                                           'season': 'n/a',
                                           'language': 'EN',
                                           'votes': '0',
                                           'generalinfo': generalinfo})
        log('total local files needed: %s'%j)
        log('total local files found:  %s'%i)
        if j > i:
            #log('scan providers for more')
            scan_more = True
        else:
            #log('don''t scan for more')
            scan_more = False
        if image_list == []:
            return image_list, scan_more
        else:
            # Sort the list before return. Last sort method is primary
            image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
            image_list = sorted(image_list, key=itemgetter('size'), reverse=False)
            image_list = sorted(image_list, key=itemgetter('language'))
            return image_list, scan_more
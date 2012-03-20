#import modules
import sys
import urllib
import xbmc
### import libraries
from resources.lib.provider.base import BaseProvider
from resources.lib.script_exceptions import NoFanartError, ItemNotFoundError
from resources.lib.utils import *
from elementtree import ElementTree as ET
from operator import itemgetter

### get addon info
__localize__    = ( sys.modules[ "__main__" ].__localize__ )

class FTV_TVProvider():

    def __init__(self):
        self.name = 'fanart.tv - TV API'
        self.api_key = '586118be1ac673f74963cc284d46bd8e'
        self.url = "http://fanart.tv/webservice/series/%s/%s/json/all/1/2"
        self.imagetypes = ['clearlogo', 'clearart', 'tvthumb', 'seasonthumb', 'characterart']

    def get_image_list(self, media_id):
        data = get_json(self.url % (self.api_key,media_id))
        image_list = []
        # Get fanart
        try:
            # split "name" and "data"
            for title, value in data.iteritems():
                # run through specified types
                for art in self.imagetypes:
                    # if type has been found
                    if value.has_key(art):
                        # Run through all the items
                        for item in value[art]:
                            info = {}
                            info['url']         = urllib.quote(item['url'], ':/')   # Original image url
                            info['preview']     = info['url'] + "/preview"          # Create a preview url for later use
                            info['id']          = item['id']
                            info['type']        = art
                            if item.has_key('season'):
                                info['season']  = item['season']
                            else:
                                info['season']  = 'n/a'
                            # language and votes
                            info['language']    = item['lang']
                            info['votes']       = item['likes']
                            
                            # Create Gui string to display
                            info['generalinfo'] = '%s: %s  |  ' %( __localize__(32141), info['language'])
                            if info['season'] != 'n/a':
                                info['generalinfo'] += '%s: %s  |  ' %( __localize__(32144), info['season'] )
                            info['generalinfo'] += '%s: %s  |  ' %( __localize__(32143), info['votes'] )
                            # Add data to list
                            if info:
                                image_list.append(info)
        except: pass
        if image_list == []:
            raise NoFanartError(media_id)
        else:
            # Sort the list before return. Last sort method is primary
            image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
            image_list = sorted(image_list, key=itemgetter('language'))
            return image_list
            
class FTV_MovieProvider():

    def __init__(self):
        self.name = 'fanart.tv - Movie API'
        self.api_key = '586118be1ac673f74963cc284d46bd8e'
        self.url = "http://fanart.tv/webservice/movie/%s/%s/json/all/1/2/"
        self.imagetypes = ['movielogo', 'movieart', 'moviedisc']

    def get_image_list(self, media_id):
        data = get_json(self.url % (self.api_key,media_id))
        image_list = []
        # Get fanart
        try:
            # split "name" and "data"
            for title, value in data.iteritems():
                # run through specified types
                for art in self.imagetypes:
                    # if type has been found
                    if value.has_key(art):
                        # Run through all the items
                        for item in value[art]:
                            info = {}
                            info['url']         = urllib.quote(item['url'], ':/')   # Original image url
                            info['preview']     = info['url'] + "/preview"          # Create a preview url for later use
                            info['id']          = item['id']
                            # Check on what type and use the general tag
                            if art == 'movielogo':
                                info['type']    = 'clearlogo'
                            elif art == 'moviedisc':
                                info['type']    = 'discart'
                            elif art == 'movieart':
                                info['type']    = 'clearart'
                            # Check on disctype
                            if art == 'moviedisc':
                                info['disctype']   = item['disc_type']
                                info['discnumber'] = item['disc']
                            else:
                                info['disctype']   = 'n/a'
                                info['discnumber'] = 'n/a'
                            # language and votes
                            info['language']    = item['lang']
                            info['votes']       = item['likes']
                            # Create Gui string to display
                            info['generalinfo'] = '%s: %s  |  ' %( __localize__(32141), info['language'])
                            if info['disctype'] != 'n/a':
                                info['generalinfo'] += '%s: %s (%s)  |  ' %( __localize__(32146), info['discnumber'], info['disctype'] )
                            info['generalinfo'] += '%s: %s  |  ' %( __localize__(32143), info['votes'] )
                            if info:
                                image_list.append(info)
        except: pass
        if image_list == []:
            raise NoFanartError(media_id)
        else:
            # Sort the list before return. Last sort method is primary
            image_list = sorted(image_list, key=itemgetter('votes'), reverse=True)
            image_list = sorted(image_list, key=itemgetter('language'))
            return image_list
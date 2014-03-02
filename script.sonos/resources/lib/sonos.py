# -*- coding: utf-8 -*-
import cgi

# Load the Soco classes
from soco import SoCo
from soco import SonosDiscovery
from soco import SoCoException



#########################################################################
# Sonos class to add extra support on top of SoCo
#########################################################################
class Sonos(SoCo):

    # Override method so that the album art http reference can be added
    def get_music_library_information(self, search_type, start=0, max_items=100, sub_category=''):
        # Make sure the sub category is valid for the message, escape invalid characters
        sub_category = cgi.escape(sub_category)
        
        # Call the base version
        musicInfo = SoCo.get_music_library_information(self, search_type, start, max_items, sub_category)

        if musicInfo != None:
            for anItem in musicInfo['item_list']:
                # Add on the full album art link, as the URI version does not include the ipaddress
                if (anItem != None) and ('album_art_uri' in anItem.keys()) and (anItem['album_art_uri'] != None) and (anItem['album_art_uri'] != ''):
                    anItem['album_art'] = 'http://' + self.speaker_ip + ':1400' + anItem['album_art_uri']
        
        return musicInfo


    def get_queue(self, start = 0, max_items = 100):
        list = SoCo.get_queue(self, start=start, max_items=max_items)
        
        if list != None:
            for anItem in list:
                # Add on the full album art link, as the URI version does not include the ipaddress
                if (anItem != None) and ('album_art' in anItem.keys()) and (anItem['album_art'] != None) and (anItem['album_art'] != ''):
                    anItem['album_art_real'] = 'http://' + self.speaker_ip + ':1400' + anItem['album_art']
        
        return list

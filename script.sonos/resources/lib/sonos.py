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
    # Format of the meta data (borrowed from sample code)
    meta_template = '&lt;DIDL-Lite xmlns:dc=&quot;http://purl.org/dc/elements/1.1/&quot; xmlns:upnp=&quot;urn:schemas-upnp-org:metadata-1-0/upnp/&quot; xmlns:r=&quot;urn:schemas-rinconnetworks-com:metadata-1-0/&quot; xmlns=&quot;urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/&quot;&gt;&lt;item id=&quot;R:0/0/0&quot; parentID=&quot;R:0/0&quot; restricted=&quot;true&quot;&gt;&lt;dc:title&gt;{title}&lt;/dc:title&gt;&lt;upnp:class&gt;object.item.audioItem.audioBroadcast&lt;/upnp:class&gt;&lt;desc id=&quot;cdudn&quot; nameSpace=&quot;urn:schemas-rinconnetworks-com:metadata-1-0/&quot;&gt;{service}&lt;/desc&gt;&lt;/item&gt;&lt;/DIDL-Lite&gt;'
    tunein_service = 'SA_RINCON65031_'

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

    # Override method so that the album art http reference can be added
    def get_queue(self, start = 0, max_items = 100):
        list = SoCo.get_queue(self, start=start, max_items=max_items)
        
        if list != None:
            for anItem in list:
                # Add on the full album art link, as the URI version does not include the ipaddress
                if (anItem != None) and ('album_art' in anItem.keys()) and (anItem['album_art'] != None) and (anItem['album_art'] != ''):
                    anItem['album_art_real'] = 'http://' + self.speaker_ip + ':1400' + anItem['album_art']
        
        return list

    # For radio playing a title is required
    def play_uri(self, uri='', title=None, metadata=''):

        # Radio stations need to have at least a title to play
        if (metadata == '') and (title != None):
            title_esc = cgi.escape(title)
            metadata = Sonos.meta_template.format(title=title_esc, service=Sonos.tunein_service)

        # Need to replace any special characters in the URI
        uri = cgi.escape(uri)
        # Now play the track
        SoCo.play_uri(self, uri, metadata)
            




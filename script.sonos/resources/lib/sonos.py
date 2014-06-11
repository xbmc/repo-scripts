# -*- coding: utf-8 -*-
import cgi

# Load the Soco classes
from soco import SoCo
from soco import SonosDiscovery
from soco import SoCoException

from soco.data_structures import MusicLibraryItem

#########################################################################
# Sonos class to add extra support on top of SoCo
#########################################################################
class Sonos(SoCo):
    # Format of the meta data (borrowed from sample code)
    meta_template = '<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/" xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"><item id="R:0/0/0" parentID="R:0/0" restricted="true"><dc:title>{title}</dc:title><upnp:class>object.item.audioItem.audioBroadcast</upnp:class><desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">{service}</desc></item></DIDL-Lite>'
    tunein_service = 'SA_RINCON65031_'

    # Converts non complete URIs to complete URIs with IP address
    def _updateAlbumArtToFullUri(self, musicInfo):
        if hasattr(musicInfo, 'album_art_uri'):
            # Add on the full album art link, as the URI version does not include the ipaddress
            if (musicInfo.album_art_uri != None) and (musicInfo.album_art_uri != ""):
                if not musicInfo.album_art_uri.startswith(('http:', 'https:')):
                    musicInfo.album_art_uri = 'http://' + self.ip_address + ':1400' + musicInfo.album_art_uri

    # Override method so that the album art http reference can be added
    def get_music_library_information(self, search_type, start=0, max_items=100, sub_category=''):
        # Make sure the sub category is valid for the message, escape invalid characters
        sub_category = cgi.escape(sub_category)
        
        # Call the base version
        musicInfo = SoCo.get_music_library_information(self, search_type, start, max_items, sub_category)

        if musicInfo != None:
            for anItem in musicInfo['item_list']:
                # Make sure the album art URI is the full path
                self._updateAlbumArtToFullUri(anItem)

        return musicInfo

    # Override method so that the album art http reference can be added
    def get_queue(self, start = 0, max_items = 100):
        list = SoCo.get_queue(self, start=start, max_items=max_items)
        
        if list != None:
            for anItem in list:
                # Make sure the album art URI is the full path
                musicInfo = self._updateAlbumArtToFullUri(anItem)
        
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

    # Need to override the add_to_queue method as in 0.7 it forces you to have
    # metadata - that we do not have
    def add_to_queue(self, uri):
        queueitem = [
            ('InstanceID', 0),
            ('EnqueuedURI', uri),
            ('EnqueuedURIMetaData', ''),
            ('DesiredFirstTrackNumberEnqueued', 0),
            ('EnqueueAsNext', 1)
        ]
        response = self.avTransport.AddURIToQueue(queueitem)

        qnumber = response['FirstTrackNumberEnqueued']
        return int(qnumber)

    # Reads the current Random and repeat status
    def getPlayMode(self):
        isRandom = False
        isLoop = False
        # Check what the play mode is
        playMode = self.play_mode
        if playMode.upper() == "REPEAT_ALL":
            isLoop = True
        elif playMode.upper() == "SHUFFLE":
            isLoop = True
            isRandom = True
        elif playMode.upper() == "SHUFFLE_NOREPEAT":
            isRandom = True
        
        return isRandom, isLoop

    # Sets the current Random and repeat status
    def setPlayMode(self, isRandom, isLoop):
        playMode = "NORMAL"
        
        # Convert the booleans into a playmode
        if isRandom and isLoop:
            playMode = "SHUFFLE"
        elif isRandom and (not isLoop):
            playMode = "SHUFFLE_NOREPEAT"
        elif (not isRandom) and isLoop:
            playMode = "REPEAT_ALL"

        # Now set the playmode on the Sonos speaker
        self.play_mode = playMode
        


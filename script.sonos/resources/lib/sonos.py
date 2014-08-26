# -*- coding: utf-8 -*-
import cgi
import traceback
import logging

# Load the Soco classes
from soco import SoCo
from soco.event_structures import LastChangeEvent
from soco.data_structures import MusicLibraryItem

# Use the SoCo logger
LOGGER = logging.getLogger('soco')


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
            if (musicInfo.album_art_uri is not None) and (musicInfo.album_art_uri != ""):
                if not musicInfo.album_art_uri.startswith(('http:', 'https:')):
                    musicInfo.album_art_uri = 'http://' + self.ip_address + ':1400' + musicInfo.album_art_uri

    # Override method so that the album art http reference can be added
    def get_music_library_information(self, search_type, start=0, max_items=100, sub_category=''):
        # Call the normal view if not browsing deeper
        if (sub_category is None) or (sub_category == ''):
            musicInfo = SoCo.get_music_library_information(self, search_type, start, max_items)
        else:
            # Call the browse version
            musicInfo = self.browse(search_type, sub_category, start, max_items)

        if musicInfo is not None:
            for anItem in musicInfo['item_list']:
                # Make sure the album art URI is the full path
                self._updateAlbumArtToFullUri(anItem)

        return musicInfo

    def browse(self, search_type, sub_category, start=0, max_items=100):
        # Make sure the sub category is valid for the message, escape invalid characters
        sub_category = cgi.escape(sub_category)

        search_translation = {'artists': 'A:ARTIST',
                              'album_artists': 'A:ALBUMARTIST',
                              'albums': 'A:ALBUM',
                              'genres': 'A:GENRE',
                              'composers': 'A:COMPOSER',
                              'tracks': 'A:TRACKS',
                              'playlists': 'A:PLAYLISTS',
                              'share': 'S:',
                              'sonos_playlists': 'SQ:',
                              'categories': 'A:'}
        search = search_translation[search_type]

        search_uri = "#%s%s" % (search, sub_category)
        search_item = MusicLibraryItem(uri=search_uri, title='', parent_id='')

        # Call the base version
        return SoCo.browse(self, search_item, start, max_items)

    # Override method so that the album art http reference can be added
    def get_queue(self, start=0, max_items=100):
        list = SoCo.get_queue(self, start=start, max_items=max_items)

        if list is not None:
            for anItem in list:
                # Make sure the album art URI is the full path
                self._updateAlbumArtToFullUri(anItem)

        return list

    # For radio playing a title is required
    def play_uri(self, uri='', title=None, metadata=''):
        # Radio stations need to have at least a title to play
        if (metadata == '') and (title is not None):
            title_esc = cgi.escape(title)
            metadata = Sonos.meta_template.format(title=title_esc, service=Sonos.tunein_service)

        # Need to replace any special characters in the URI
        uri = cgi.escape(uri)
        # Now play the track
        SoCo.play_uri(self, uri, metadata)

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

    def hasTrackChanged(self, track1, track2):
        if track2 is None:
            return False
        if track1 is None:
            return True
        if track1['uri'] != track2['uri']:
            return True
        # Don't update if the URI is the same but the new version does
        # not have event info
        if (track2['lastEventDetails'] is None) and (track1['lastEventDetails'] is not None):
            return False
        if track1['title'] != track2['title']:
            return True
        if track1['album_art'] != track2['album_art']:
            return True
        if track1['artist'] != track2['artist']:
            return True
        if track1['album'] != track2['album']:
            return True

        return False

    # Gets the most recent event from the event queue
    def getLastEventDetails(self, sub):
        lastChangeDetails = None
        try:
            queueItem = None
            # Get the most recent event received
            while not sub.events.empty():
                try:
                    # Get the next event - but do not block or wait for an event
                    # if there is not already one there
                    queueItem = sub.events.get(False)
                except:
                    LOGGER.debug("Sonos: Queue get failed: %s" % traceback.format_exc())

            # Now get the details of an event if there is one there
            lastChangeDetails = None
            if queueItem is not None:
                lastChangeXmlStr = queueItem.variables['LastChange']
                if lastChangeXmlStr is not None:
                    LOGGER.debug("Event details: %s" % lastChangeXmlStr)
                    # Convert the XML into an object
                    lastChangeDetails = LastChangeEvent.from_xml(lastChangeXmlStr)
        except:
            LOGGER.debug("Sonos: Failed to get latest event details: %s" % traceback.format_exc())

        return lastChangeDetails

    # When given a track info structure and an event, will merge the data
    # together so that it is complete and accurate
    def mergeTrackInfoAndEvent(self, track, eventDetails, previousTrack=None):
        # If there is no event data, then just return the track unchanged
        if eventDetails is None:
            # Check to see if the track has changed, if it has not, then we can
            # safely use the previous event we stored
            if (previousTrack is not None) and (track['uri'] == previousTrack['uri']) and (previousTrack['lastEventDetails'] is not None):
                LOGGER.debug("Sonos: Using previous Event details for merge")
                track['lastEventDetails'] = previousTrack['lastEventDetails']
                eventDetails = previousTrack['lastEventDetails']
            else:
                LOGGER.debug("Sonos: Event details not set for merge")
                track['lastEventDetails'] = None
                return track
        else:
            LOGGER.debug("Sonos: Event details set for merge")
            track['lastEventDetails'] = eventDetails

        # If the track has no album art, use the event one (if it exists)
        if (track['album_art'] is None) or (track['album_art'] == ""):
            if (eventDetails.album_art_uri is not None) and (eventDetails.album_art_uri != ""):
                track['album_art'] = eventDetails.album_art_uri
                # Make sure the Album art is fully qualified
                if not track['album_art'].startswith(('http:', 'https:')):
                    track['album_art'] = 'http://' + self.ip_address + ':1400' + track['album_art']

        if (track['artist'] is None) or (track['artist'] == ""):
            if (eventDetails.album_artist is not None) and (eventDetails.album_artist != ""):
                track['artist'] = eventDetails.album_artist

        # Check if this is radio stream, in which case use that as the title
        if (eventDetails.transport_title is not None) and (eventDetails.transport_title != ""):
            if (track['title'] is None) or (track['title'] == ""):
                track['title'] = eventDetails.transport_title
        # Otherwise treat as a normal title
        elif (track['title'] is None) or (track['title'] == ""):
            if (eventDetails.title is not None) and (eventDetails.title != ""):
                track['title'] = eventDetails.title

        # Check if this is radio stream, in which case use that as the album title
        if (eventDetails.radio_show_md is not None) and (eventDetails.radio_show_md != ""):
            if (track['album'] is None) or (track['album'] == ""):
                track['album'] = eventDetails.radio_show_md
                # This may be something like: Drivetime,p239255 so need to remove the last section
                trimmed = track['album'].rpartition(',p')[0]
                if (trimmed is not None) and (trimmed != ""):
                    track['album'] = trimmed
        # Otherwise treat as a album title
        elif (track['album'] is None) or (track['album'] == ""):
            if (eventDetails.album is not None) and (eventDetails.album != ""):
                track['album'] = eventDetails.album

        return track

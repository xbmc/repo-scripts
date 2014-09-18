# -*- coding: utf-8 -*-
import traceback
import logging

# Load the Soco classes
from soco import SoCo
from soco.event_structures import LastChangeEvent

# Use the SoCo logger
LOGGER = logging.getLogger('soco')


#########################################################################
# Sonos class to add extra support on top of SoCo
#########################################################################
class Sonos(SoCo):
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

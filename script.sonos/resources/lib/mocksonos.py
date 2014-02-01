# -*- coding: utf-8 -*-
import xbmc

#########################################################################
# Mock Sonos class to support testing when there is no live Sonos system
#########################################################################
class TestMockSonos():
    def __init__( self ):
        self.currentPlayState = 'PLAYING'
        self.trackNumber = 100
        self.isMuted = 0 # 0 is unmuted, 1 is muted
        self.currentVolume = 50
        self.duration = "00:05:47"
        self.position = "00:02:25"

    def get_current_track_info(self, forcedTrackNum=None):
        displayTrackNum = self.trackNumber
        if forcedTrackNum != None:
            displayTrackNum = forcedTrackNum
 
        # Test code to test the dialog without a Sonos Speaker connected
        track = {'title': "Title value %d" % displayTrackNum,
                 'artist': "Artist Value %d" % displayTrackNum,
                 'album': "AlbumValue %d" % displayTrackNum,
                 'album_art': '',
                 'position': self.position,
                 'duration': self.duration,
                 'uri': "%d" % self.trackNumber,
                 'playlist_position': "%d" % self.trackNumber }
        return track

    def get_current_transport_info(self):
        playStatus = {'current_transport_state': self.currentPlayState }
        return playStatus

    def play(self):
        self.currentPlayState = 'PLAYING'
        self._displayOperation("Play")

    def pause(self):
        self.currentPlayState = 'PAUSED_PLAYBACK'
        self._displayOperation("Paused")

    def stop(self):
        self.currentPlayState = 'STOPPED'
        self._displayOperation("Stopped")
     
    def next(self):
        self.trackNumber = self.trackNumber + 1
        self._displayOperation("Next Track")

    def previous(self):
        self.trackNumber = self.trackNumber - 1
        self._displayOperation("Previous Track")

    def mute(self, mute=None):
        if mute == None:
            return self.isMuted

        if mute == True:
            self.isMuted = 1
            self._displayOperation("Volume Muted")
        else:
            self.isMuted = 0
            self._displayOperation("Volume Unmuted")
        return True

    def get_queue(self, start = 0, max_items = 100):
        queue = []
        for num in range(start,start + max_items):
            queue.append(self.get_current_track_info(num))
        return queue

    def get_tracks(self, start=0, max_items=100):
        # TODO: THis is not currently returning what the sonos system does
        out = {'item_list': []}
        for num in range(start,start + max_items):
            out['item_list'].append(self.get_current_track_info(self.trackNumber + num + 1))
        return out

    def volume(self, newVolume=None):
        if newVolume != None:
            self.currentVolume = int(newVolume)
            # self._displayOperation("Volume set to %d" % newVolume)
        return self.currentVolume

    def seek(self, timestamp):
        self.position = timestamp
        self._displayOperation("Seek Time to %s" % timestamp)

    def _displayOperation(self, textStr):
        xbmc.executebuiltin('Notification("Test Mock Sonos", %s, %d)' % (textStr, 3))




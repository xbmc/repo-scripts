# -*- coding: utf-8 -*-
import xbmcgui
import re

# Import the common settings
from settings import Settings
from settings import log


######################################################
# Class to control the fetching and setting of lyrics
######################################################
class Lyrics():
    # Create with the track that we need lyrics for and the GUI to be set with the lyrics
    def __init__(self, currentTrack, controlList=None, controlListItemCount=0):
        log("Lyrics: Created with artist(%s) title(%s)" % (currentTrack['artist'], currentTrack['title']))
        self.track = currentTrack
        self.listControl = controlList
        self.lyricListOffset = int(controlListItemCount / 2)

    @staticmethod
    def copyLyricsIfSameTrack(newTrack, oldTrack):
        if (oldTrack is not None) and (newTrack['uri'] == oldTrack['uri']):
            newTrackLyrics = Lyrics(newTrack)
            # Check if the new track already has lyrics, in which case there is nothing to do
            if newTrackLyrics.hasLyrics():
                log("Lyrics: No need to copy lyrics, already exist in track")
                return

            # Check if the old track has any lyrics that can be copied
            oldTrackLyrics = Lyrics(oldTrack)
            if oldTrackLyrics.hasLyrics():
                log("Lyrics: Setting lyrics on new track to existing old lyrics")
                newTrack['lyrics'] = oldTrack['lyrics']
            else:
                log("Lyrics: Old track does not have any lyrics")
        else:
            log("Lyrics: Different tracks, so no need to copy lyrics")
        return newTrack

    # Checks if there are already lyrics attached to the track
    def hasLyrics(self):
        lyricsChecked = False
        if self.track.get('lyrics', None) not in [None, '']:
            lyricsChecked = True
        return lyricsChecked

    def setLyricRequest(self):
        # If we are showing a screen that needs lyrics and we do not have any at the moment
        # then set the properties so that CU LRC looks for them
        if Settings.isLyricsInfoLayout() and not self.hasLyrics():
            log("Lyrics: Setting culrc.artist(%s) culrc.track(%s)" % (self.track['artist'], self.track['title']))
            xbmcgui.Window(10000).setProperty('culrc.manual', 'true')
            xbmcgui.Window(10000).setProperty('culrc.artist', self.track['artist'])
            xbmcgui.Window(10000).setProperty('culrc.track', self.track['title'])

    def clearLyricRequest(self):
        log("Lyrics: Clearing lyric request")
        # Clear the lyrics that were stored so that the lyrics addon does not keep looking
        xbmcgui.Window(10000).clearProperty('culrc.manual')
        xbmcgui.Window(10000).clearProperty('culrc.artist')
        xbmcgui.Window(10000).clearProperty('culrc.track')
        xbmcgui.Window(10000).clearProperty('culrc.lyrics')

    def populateLyrics(self):
        # Check if lyrics are enabled, and set the test if they are
        if Settings.isLyricsInfoLayout() and not self.hasLyrics():
            lyricTxt = xbmcgui.Window(10000).getProperty('culrc.lyrics')
            if lyricTxt not in [None, '']:
                log("Lyrics: Lyrics for artist(%s) track(%s) \n%s" % (self.track['artist'], self.track['title'], lyricTxt))
                # Now persist the lyrics into the currentTrack and clear the current settings
                self.track['lyrics'] = self._parserLyrics(lyricTxt, self.track['duration_seconds'])
                # Clear the lyrics that were stored so that the lyrics addon does not keep looking
                self.clearLyricRequest()

                # Now update the screen
                self._populateListView(self.track['lyrics'])
            else:
                # Disable the lyric display
                self._screenLyricsVisible(False)
        return self.track

    # Uses the supplied lyrics to populate the screen
    def _populateListView(self, lyrics):
        # Make sure there is a valid list control to set
        if self.listControl is None:
            return

        # Now populate the lyrics on the screen
        self.listControl.reset()

        for time, line in lyrics:
            self.listControl.addItem(line)

        self._screenLyricsVisible(True)

    # Toggles if the lyrics section on the screen is to be displayed
    def _screenLyricsVisible(self, areVisible):
        if self.listControl is not None:
            self.listControl.setVisible(areVisible)
            if not areVisible:
                self.listControl.reset()

    # Parses the lyrics that contain the time in square brackets and
    # extracts the time and the text
    def _parserLyrics(self, lyrics, totalDuration):
        timeLines = []
        tag = re.compile('\[(\d+):(\d\d)([\.:]\d+|)\]')
        lyricLineslyrics = lyrics.replace("\r\n", "\n")
        sep = "\n"
        lyricLines = []
        # Now remove any empty lines
        for x in lyricLineslyrics.split(sep):
            if len(x.strip()) > 0:
                lyricLines.append(x)

        # Process each line for lyrics with timestamps attached
        for x in lyricLines:
            match1 = tag.match(x)
            times = []
            if (match1):
                log("Lyrics: Match found for time-stamps, using supplied timestamps")
                while (match1):
                    times.append(float(match1.group(1)) * 60 + float(match1.group(2)))
                    y = 5 + len(match1.group(1)) + len(match1.group(3))
                    x = x[y:]
                    match1 = tag.match(x)
                for time in times:
                    # Skip any empty/blank lines
                    if len(x.strip()) > 0:
                        timeLines.append((time, x))

        # No Lyrics set yet, so must need to set an approximate time for each
        if len(timeLines) < 1:
            log("Lyrics: Generating approximate timestamps")
            # Work out the duration of each line
            timePerLine = totalDuration / len(lyricLines)
            timeSoFar = 0
            for x in lyricLines:
                timeLines.append((timeSoFar, x))
                timeSoFar = timeSoFar + timePerLine

        # Check to see if we processed the data
        timeLines.sort(cmp=lambda x, y: cmp(x[0], y[0]))
        return timeLines

    # Updated the position of the highlighted line in the lyrics display
    def refresh(self):
        # Check if there is anything to do for lyrics
        if not Settings.isLyricsInfoLayout() or (self.listControl is None):
            return

        if not self.hasLyrics():
            return

        timeLines = self.track['lyrics']

        cur_time = self.track['position_seconds']
        nums = self.listControl.size()
        pos = self.listControl.getSelectedPosition()
        # Make sure that we don't exceed the index
        if pos >= len(timeLines):
            log("Lyrics: Current Position exceeds number of entries")
            return

        # Check if we need to roll the lyrics backwards
        if (cur_time < timeLines[pos][0]):
            while ((pos > 0) and (timeLines[pos - 1][0] > cur_time)):
                pos = pos - 1
        else:
            # Going forwards
            while ((pos < nums - 1) and (timeLines[pos + 1][0] < cur_time)):
                pos = pos + 1
            # Now we have the correct position, but we want that to sit in the
            # middle of the dialog, so add on the offset
            if (pos + self.lyricListOffset > nums - 1):
                # As it's near the end - set the focus to the last one
                self.listControl.selectItem(nums - 1)
            else:
                self.listControl.selectItem(pos + self.lyricListOffset)
        self.listControl.selectItem(pos)

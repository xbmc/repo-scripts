# -*- coding: utf-8 -*-
import sys
import os
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

__addon__ = xbmcaddon.Addon(id='script.audiobooks')
__addonid__ = __addon__.getAddonInfo('id')
__fanart__ = __addon__.getAddonInfo('fanart')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")


sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join

from audiobook import AudioBookHandler
from bookplayer import BookPlayer
from database import AudioBooksDB


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

        self.tmpdestination = Settings.getTempLocation()
        self.coverCache = Settings.getCoverCacheLocation()

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # Show all the EBooks that are in the eBook directory
    def showAudiobooks(self, directory=None):
        # Get the setting for the audio book directory
        audioBookFolder = Settings.getAudioBookFolder()

        if audioBookFolder in [None, ""]:
            # Prompt the user to set the eBooks Folder
            audioBookFolder = xbmcgui.Dialog().browseSingle(0, __addon__.getLocalizedString(32005), 'files')

            # Check to make sure the directory is set now
            if audioBookFolder in [None, ""]:
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32006))
                return

            # Save the directory in settings for future use
            log("AudioBooksPlugin: Setting Audio Books folder to %s" % audioBookFolder)
            Settings.setAudioBookFolder(audioBookFolder)

        # We may be looking at a subdirectory
        if directory not in [None, ""]:
            audioBookFolder = directory

        dirs, files = xbmcvfs.listdir(audioBookFolder)

        bookDirs = []
        # For each directory list allow the user to navigate into it
        for dir in dirs:
            if dir.startswith('.'):
                continue

            fullDir = os_path_join(audioBookFolder, dir)

            # Check if this directory is a book directory
            if self._isAudioBookDir(fullDir):
                bookDirs.append(fullDir)
                continue

            log("AudioBooksPlugin: Adding directory %s" % dir)

            displayName = "[%s]" % dir
            try:
                fullDir = fullDir.encode("utf-8")
            except:
                pass

            url = self._build_url({'mode': 'directory', 'directory': fullDir})
            li = xbmcgui.ListItem(displayName, iconImage='DefaultFolder.png')
            li.setProperty("Fanart_Image", __fanart__)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        m4bAudioBooks = []
        for m4bBookFile in files:
            # Check to ensure that this is an eBook
            if not m4bBookFile.lower().endswith('.m4b'):
                log("AudioBooksPlugin: Skipping non audiobook file: %s" % m4bBookFile)
                continue

            fullpath = os_path_join(audioBookFolder, m4bBookFile)

            m4bAudioBooks.append(fullpath)

        # Get all the audiobook in a nicely sorted order
        allAudioBooks = sorted(bookDirs + m4bAudioBooks)

        # Now list all of the books
        for audioBookFile in allAudioBooks:
            log("AudioBooksPlugin: Processing audiobook %s" % audioBookFile)

            audioBookHandler = AudioBookHandler.createHandler(audioBookFile)

            title = audioBookHandler.getTitle()
            coverTargetName = audioBookHandler.getCoverImage(True)

            isRead = False
            if Settings.isMarkCompletedItems():
                if audioBookHandler.isCompleted():
                    isRead = True

            displayString = title
            log("AudioBooksPlugin: Display title is %s for %s" % (displayString, audioBookFile))

            if isRead:
                displayString = '* %s' % displayString

            url = self._build_url({'mode': 'chapters', 'filename': audioBookHandler.getFile(True), 'cover': coverTargetName})
            li = xbmcgui.ListItem(displayString, iconImage=coverTargetName)
            li.setProperty("Fanart_Image", __fanart__)
            li.addContextMenuItems(self._getContextMenu(audioBookHandler), replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

            del audioBookHandler

        xbmcplugin.endOfDirectory(self.addon_handle)

    def _isAudioBookDir(self, fullDir):
        # Check to see if this directory contains audio files (non m4b), if it does then we construct the
        # book using each audio file file as a chapter
        dirs, files = xbmcvfs.listdir(fullDir)

        containsMP3 = False
        for aFile in files:
            if Settings.isPlainAudioFile(aFile):
                log("AudioBooksPlugin: Directory contains MP3 files: %s" % fullDir)
                containsMP3 = True
                break

        return containsMP3

    def listChapters(self, fullpath, defaultImage):
        log("AudioBooksPlugin: Listing chapters for %s" % fullpath)

        audioBookHandler = AudioBookHandler.createHandler(fullpath)

        chapters = audioBookHandler.getChapterDetails()

        if len(chapters) < 1:
            url = self._build_url({'mode': 'play', 'filename': audioBookHandler.getFile(True), 'startTime': 0, 'chapter': 0})

            li = xbmcgui.ListItem(__addon__.getLocalizedString(32018), iconImage=defaultImage)
            li.setProperty("Fanart_Image", __fanart__)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        secondsIn, chapterPosition = audioBookHandler.getPosition()
        if (secondsIn > 0) or (chapterPosition > 1):
            url = self._build_url({'mode': 'play', 'filename': audioBookHandler.getFile(True), 'startTime': secondsIn, 'chapter': chapterPosition})

            displayTime = self._getDisplayTimeFromSeconds(secondsIn)
            displayName = "%s %s" % (__addon__.getLocalizedString(32019), displayTime)

            if chapterPosition > 0:
                displayName = "%s (%s: %d)" % (displayName, __addon__.getLocalizedString(32017), chapterPosition)

            li = xbmcgui.ListItem(displayName, iconImage=defaultImage)
            li.setProperty("Fanart_Image", __fanart__)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        # Add all the chapters to the display
        chapterNum = 0
        for chapter in chapters:
            chapterNum += 1
            url = self._build_url({'mode': 'play', 'filename': audioBookHandler.getFile(True), 'startTime': audioBookHandler.getChapterStart(chapterNum), 'chapter': chapterNum})

            # Check if the current position means that this chapter has already been played
            displayString = chapter['title']

            # Check if we need to add a number at the start of the chapter
            if Settings.autoNumberChapters() and (len(displayString) > 0):
                # Check to make sure that the display chapter does not already
                # start with a number, or end with a number
                if not (displayString[0].isdigit() or displayString[-1].isdigit()):
                    displayString = "%d. %s" % (chapterNum, displayString)

            if Settings.isMarkCompletedItems():
                if (audioBookHandler.isCompleted()) or ((chapter['endTime'] < secondsIn) and (chapter['endTime'] > 0)) or (chapterNum < chapterPosition):
                    displayString = '* %s' % displayString

            li = xbmcgui.ListItem(displayString, iconImage=defaultImage)

            if len(chapters) > 1:
                durationEntry = chapter['startTime']
                # If the duration is set as zero, nothing is displayed
                if (durationEntry < 1) and (chapter['endTime'] > 0):
                    durationEntry = 1
                # Use the start time for the duration display as that will show
                # how far through the book the chapter is
                li.setInfo('music', {'Duration': durationEntry})

            li.setProperty("Fanart_Image", __fanart__)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        del audioBookHandler
        xbmcplugin.endOfDirectory(self.addon_handle)

    def play(self, fullpath, startTime=0, chapter=0):
        log("AudioBooksPlugin: Playing %s" % fullpath)

        audioBookHandler = AudioBookHandler.createHandler(fullpath)

        bookPlayer = BookPlayer()
        bookPlayer.playAudioBook(audioBookHandler, startTime, chapter)
        del bookPlayer
        del audioBookHandler

        # After playing we need to update the screen to reflect our progress
        xbmc.executebuiltin("Container.Refresh")

    # Construct the context menu
    def _getContextMenu(self, bookHandle):
        ctxtMenu = []

        # Play from resume point
        secondsIn, chapterPosition = bookHandle.getPosition()
        if (secondsIn > 0) or (chapterPosition > 1):
            cmd = self._build_url({'mode': 'play', 'filename': bookHandle.getFile(True), 'startTime': secondsIn, 'chapter': chapterPosition})
            displayTime = self._getDisplayTimeFromSeconds(secondsIn)
            displayName = "%s %s" % (__addon__.getLocalizedString(32019), displayTime)

            if chapterPosition > 1:
                displayName = "%s (%s: %d)" % (displayName, __addon__.getLocalizedString(32017), chapterPosition)

            ctxtMenu.append((displayName, 'RunPlugin(%s)' % cmd))

        # Play from start
        cmd = self._build_url({'mode': 'play', 'filename': bookHandle.getFile(True), 'startTime': 0, 'chapter': 0})
        ctxtMenu.append((__addon__.getLocalizedString(32018), 'RunPlugin(%s)' % cmd))

        # If this item is not already complete, allow it to be marked as complete
        if not bookHandle.isCompleted():
            # Mark as complete
            cmd = self._build_url({'mode': 'progress', 'filename': bookHandle.getFile(True), 'isComplete': 1, 'startTime': 0})
            ctxtMenu.append((__addon__.getLocalizedString(32010), 'RunPlugin(%s)' % cmd))

        # Clear History
        cmd = self._build_url({'mode': 'clear', 'filename': bookHandle.getFile(True)})
        ctxtMenu.append((__addon__.getLocalizedString(32011), 'RunPlugin(%s)' % cmd))

        return ctxtMenu

    def progress(self, fullpath, isComplete=True, startTime=0):
        # At the moment the only time progress is called is to mark as complete
        audiobookDB = AudioBooksDB()
        audiobookDB.setPosition(fullpath, startTime, isComplete)
        del audiobookDB

        xbmc.executebuiltin("Container.Refresh")

    def clear(self, fullpath):
        log("AudioBooksPlugin: Clearing history for %s" % fullpath)
        # Remove the item from the database, it will then be rescanned
        audiobookDB = AudioBooksDB()
        audiobookDB.deleteAudioBook(fullpath)
        del audiobookDB

        xbmc.executebuiltin("Container.Refresh")

    def _getDisplayTimeFromSeconds(self, secondsIn):
        seconds = secondsIn % 60
        minutes = 0
        hours = 0
        if secondsIn > 60:
            minutes = ((secondsIn - seconds) % 3600) / 60
        if secondsIn > 3600:
            hours = (secondsIn - (minutes * 60) - seconds) / 3600

        # Build the string up
        displayName = "%d:%02d:%02d" % (hours, minutes, seconds)
        return displayName


################################
# Main of the eBooks Plugin
################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, files in our case
    xbmcplugin.setContent(addon_handle, 'files')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("AudioBooksPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("AudioBooksPlugin: Mode is NONE - showing root menu")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.showAudiobooks()
        del menuNav
    elif mode[0] == 'directory':
        log("AudioBooksPlugin: Mode is Directory")

        directory = args.get('directory', None)

        if (directory is not None) and (len(directory) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.showAudiobooks(directory[0])
            del menuNav

    elif mode[0] == 'chapters':
        log("AudioBooksPlugin: Mode is CHAPTERS")

        # Get the actual folder that was navigated to
        filename = args.get('filename', None)
        cover = args.get('cover', None)

        if (cover is not None) and (len(cover) > 0):
            cover = cover[0]
        else:
            cover = None

        if (filename is not None) and (len(filename) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.listChapters(filename[0], cover)
            del menuNav

    elif mode[0] == 'play':
        log("AudioBooksPlugin: Mode is PLAY")

        # Get the book that we need to play
        filename = args.get('filename', None)
        startTime = args.get('startTime', None)
        chapterPos = args.get('chapter', None)

        startFrom = -1
        if (startTime is not None) and (len(startTime) > 0):
            startFrom = int(startTime[0])

        chapter = 0
        if (chapterPos is not None) and (len(chapterPos) > 0):
            chapter = int(chapterPos[0])

        if (filename is not None) and (len(filename) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.play(filename[0], startFrom, chapter)
            del menuNav

    elif mode[0] == 'progress':
        log("EBooksPlugin: Mode is PROGRESS")

        filename = args.get('filename', None)
        startTime = args.get('startTime', None)
        completeStatus = args.get('isComplete', None)

        startTimeVal = 0
        if (startTime is not None) and (len(startTime) > 0):
            startTimeVal = int(startTime[0])

        isComplete = False
        if (completeStatus is not None) and (len(completeStatus) > 0):
            if completeStatus[0] == '1':
                isComplete = True

        if (filename is not None) and (len(filename) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.progress(filename[0], isComplete, startTimeVal)
            del menuNav

    elif mode[0] == 'clear':
        log("AudioBooksPlugin: Mode is CLEAR")

        # Get the book to remove
        filename = args.get('filename', None)

        if (filename is not None) and (len(filename) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.clear(filename[0])
            del menuNav

# -*- coding: utf-8 -*-
import sys
import os
import cgi
import traceback
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.sonos')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")
__media__ = xbmc.translatePath(os.path.join(__resource__, 'media').encode("utf-8")).decode("utf-8")


sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log

from sonos import Sonos

import soco
from speech import Speech


###################################################################
# Media files used by the plugin
###################################################################
class MediaFiles():
    RadioIcon = 'DefaultAudio.png' if Settings.useSkinIcons() else os.path.join(__media__, 'radio.png')
    MusicLibraryIcon = 'DefaultAudio.png' if Settings.useSkinIcons() else os.path.join(__media__, 'library.png')
    QueueIcon = 'DefaultMusicPlaylists.png' if Settings.useSkinIcons() else os.path.join(__media__, 'playlist.png')

    AlbumsIcon = 'DefaultMusicAlbums.png' if Settings.useSkinIcons() else os.path.join(__media__, 'albums.png')
    ArtistsIcon = 'DefaultMusicArtists.png' if Settings.useSkinIcons() else os.path.join(__media__, 'artists.png')
    ComposersIcon = 'DefaultArtist.png' if Settings.useSkinIcons() else os.path.join(__media__, 'composers.png')
    GenresIcon = 'DefaultMusicGenres.png' if Settings.useSkinIcons() else os.path.join(__media__, 'genres.png')
    TracksIcon = 'DefaultMusicSongs.png' if Settings.useSkinIcons() else os.path.join(__media__, 'tracks.png')
    RadioStationIcon = 'DefaultAudio.png' if Settings.useSkinIcons() else os.path.join(__media__, 'radiostation.png')
    SonosPlaylistIcon = 'DefaultMusicPlaylists.png' if Settings.useSkinIcons() else os.path.join(__media__, 'sonosplaylist.png')


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    # These constants map directly to those in soco.get_music_library_information()
    GENRES = 'genres'
    ARTISTS = 'artists'
    ALBUMARTISTS = 'album_artists'
    ALBUMS = 'albums'
    COMPOSERS = 'composers'
    TRACKS = 'tracks'
    FOLDERS = 'folders'
    IMPORTED_PLAYLISTS = 'playlists'
    SONOS_PLAYLISTS = 'sonos_playlists'

    # Menu items manually set at the root
    ROOT_MENU_MUSIC_LIBRARY = 'Music-Library'
    ROOT_MENU_QUEUE = 'QueueIcon'
    ROOT_MENU_RADIO_STATIONS = 'Radio-Stations'
    ROOT_MENU_RADIO_SHOWS = 'Radio-Shows'
    ROOT_MENU_SONOS_PLAYLISTS = 'Sonos-Playlists'
    ROOT_MENU_SPEECH = 'Speech'

    COMMAND_CONTROLLER = 'launchController'
    COMMAND_SPEECH_INPUT = 'SpeechInput'
    COMMAND_SPEECH_SAVE = 'SpeechSave'

    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

    # Creates a URL for a directory
    def _build_url(self, query):
        # Make sure all of the characters are correctly encoded
        processedQuery = query
        for k, v in processedQuery.iteritems():
            try:
                processedQuery[k] = unicode(v).encode('utf-8')
            except:
                processedQuery[k] = v

        return "%s?%s" % (self.base_url, urllib.urlencode(processedQuery))

    # Display the default list of items in the root menu
    def setRootMenu(self):
        # Sonos Controller Link
        url = self._build_url({'mode': MenuNavigator.COMMAND_CONTROLLER})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32103), iconImage=__icon__)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

#        url = self._build_url({'mode': 'folder', 'foldername': 'Sonos-Favourites'})
#        li = xbmcgui.ListItem('Sonos Favourites (Not Supported Yet)', iconImage='DefaultFolder.png')
#        li.addContextMenuItems([], replaceItems=True) # Clear the Context Menu
#        self._addPlayerToContextMenu(li) # Add the Sonos player to the menu
#        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Music Library
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ROOT_MENU_MUSIC_LIBRARY})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32100), iconImage=MediaFiles.MusicLibraryIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addMusicLibraryContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ROOT_MENU_RADIO_STATIONS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32102), iconImage=MediaFiles.RadioIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

# NOTE: Radio Shows disabled because additional requests need to be added
#       to an external source to get what show episodes are available
#        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ROOT_MENU_RADIO_SHOWS})
#        li = xbmcgui.ListItem('Radio Shows', iconImage=MediaFiles.RadioIcon)
#        li.addContextMenuItems([], replaceItems=True) # Clear the Context Menu
#        self._addPlayerToContextMenu(li) # Add the Sonos player to the menu
#        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.SONOS_PLAYLISTS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32104), iconImage=MediaFiles.QueueIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ROOT_MENU_QUEUE})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32101), iconImage=MediaFiles.QueueIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Custom Speech Options
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ROOT_MENU_SPEECH})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32105), iconImage=__icon__)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Populate the Music menu
    def setMusicLibrary(self):
        # Artists
        # Note: For artists, the sonos system actually calls "Album Artists"
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ALBUMARTISTS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32110), iconImage=MediaFiles.ArtistsIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Albums
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ALBUMS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32111), iconImage=MediaFiles.AlbumsIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Composers
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.COMPOSERS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32112), iconImage=MediaFiles.ComposersIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Genres
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.GENRES})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32113), iconImage=MediaFiles.GenresIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Tracks
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.TRACKS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32114), iconImage=MediaFiles.TracksIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Imported Playlists
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.IMPORTED_PLAYLISTS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32115), iconImage=MediaFiles.SonosPlaylistIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Populets the queue list from the Sonos speaker
    def populateQueueList(self):
        sonosDevice = Sonos.createSonosDevice()

        # Make sure a Sonos speaker was found
        if sonosDevice is not None:
            totalCollected = 0
            numberReturned = Settings.getBatchSize()

            # Need to get all the tracks in batches
            # Only get the next batch if all the items requested were in the last batch
            while (numberReturned == Settings.getBatchSize()) and not self._listLimitReached(totalCollected):
                # Get the items from the sonos system
                list = None
                try:
                    list = sonosDevice.get_queue(totalCollected, Settings.getBatchSize(), True)
                except:
                    log("SonosPlugin: %s" % traceback.format_exc(), xbmc.LOGERROR)
                    xbmcgui.Dialog().ok(__addon__.getLocalizedString(32068), __addon__.getLocalizedString(32070))
                    return

                # Processes the list returned from Sonos, creating the list display on the screen
                numberReturned = len(list)
                log("SonosPlugin: Total queue entries in this batch %d" % numberReturned)

                itemNum = 0

                for item in list:
                    # Get a suitable display title
                    displayTitle = None
                    if (item.creator is not None) and (item.creator != ""):
                        displayTitle = "%s - %s" % (item.title, item.creator)
                    else:
                        displayTitle = item.title

                    # Create the list item for the track
                    if hasattr(item, 'album_art_uri') and (item.album_art_uri is not None) and (item.album_art_uri != ""):
                        li = xbmcgui.ListItem(displayTitle, iconImage=item.album_art_uri, thumbnailImage=item.album_art_uri)
                    else:
                        li = xbmcgui.ListItem(displayTitle, iconImage=MediaFiles.TracksIcon)
                    # Set addition information about the track - will be seen in info view
                    li.setInfo('music', {'title': item.title, 'artist': item.creator, 'album': item.album})

                    # Create the action to be performed when clicking a queue item
                    url = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_QUEUE_PLAY_ITEM, 'itemId': itemNum})

                    # Add the context menu for the queue
                    self._addQueueContextMenu(li, itemNum + totalCollected)
                    itemNum = itemNum + 1

                    xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

                totalCollected = totalCollected + numberReturned
            del sonosDevice

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Process a folder action that requires a lookup from Sonos
    def processFolderMessage(self, folderName, subCategory=''):
        sonosDevice = Sonos.createSonosDevice()

        # Make sure a Sonos speaker was found
        if sonosDevice is not None:
            # Process the sub-category
            if subCategory is None:
                subCategory = ''

            totalCollected = 0
            totalEntries = 1

            isFirstItem = True

            # Need to get all the tracks in batches
            while (totalCollected < totalEntries) and not self._listLimitReached(totalCollected):
                # make the call to get the tracks in batches of 100

                # Get the items from the sonos system
                list = None
                try:
                    if (subCategory is None) or (subCategory == ''):
                        list = sonosDevice.music_library.get_music_library_information(folderName, totalCollected, Settings.getBatchSize(), True)
                    else:
                        # Make sure the sub category is valid for the message, escape invalid characters
                        # subCategory = urllib.quote(subCategory)
                        # Call the browse version
                        list = sonosDevice.music_library.browse_by_idstring(folderName, subCategory, totalCollected, Settings.getBatchSize(), True)
                except:
                    log("SonosPlugin: %s" % traceback.format_exc(), xbmc.LOGERROR)
                    xbmcgui.Dialog().ok(__addon__.getLocalizedString(32068), __addon__.getLocalizedString(32069) % (folderName, subCategory))
                    return

                # Processes the list returned from Sonos, creating the list display on the screen
                totalEntries = list.total_matches
                log("SonosPlugin: Total %s Matches %d" % (folderName, totalEntries))
                numberReturned = list.number_returned
                log("SonosPlugin: Total %s in this batch %d" % (folderName, numberReturned))

                # Makes sure some items are returned
                if numberReturned < 1:
                    numberReturned = len(list)
                    if numberReturned < 1:
                        log("SonosPlugin: Zero items returned from request")
                        break

                for item in list:
                    # Check if this item is a track of a directory
                    if isinstance(item, soco.data_structures.DidlMusicTrack):
                        self._addTrack(item, totalEntries, folderName)
                    else:
                        # Check for the special case where there is an "All" first in the list
                        # For this the id and parent values are the same.  The All item
                        # is a special case and does not handle like a normal directory
                        if ('sameArtist' in item.item_class) or ('albumlist' in item.item_class):
                            log("SonosPlugin: Skipping \"All\" item for %s" % item.title)
                            isFirstItem = False
                            continue

                        # Check to see if we are dealing with a sonos playlist
                        if isinstance(item, soco.data_structures.DidlPlaylistContainer):
                            # Will need to do the search by ID for playlists as the text method
                            # does not work
                            self._addDirectory(item, folderName, totalEntries, subCategory, item.item_id)
                        else:
                            self._addDirectory(item, folderName, totalEntries, subCategory)
                    # No longer the first item
                    isFirstItem = False  # noqa PEP8

                # Add the number returned this time to the running total
                totalCollected = totalCollected + numberReturned
            del sonosDevice

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Gets the Sonos favourite Radio Stations
    def populateRadioStations(self):
        sonosDevice = Sonos.createSonosDevice()

        # Make sure a Sonos speaker was found
        if sonosDevice is not None:
            totalCollected = 0
            totalEntries = 1

            # Need to get all the tracks in batches
            while (totalCollected < totalEntries) and not self._listLimitReached(totalCollected):
                # Get the items from the sonos system
                list = None
                try:
                    list = sonosDevice.get_favorite_radio_stations(start=totalCollected, max_items=Settings.getBatchSize())
                except:
                    log("SonosPlugin: %s" % traceback.format_exc(), xbmc.LOGERROR)
                    xbmcgui.Dialog().ok(__addon__.getLocalizedString(32068), __addon__.getLocalizedString(32071))
                    return

                # Processes the list returned from Sonos, creating the list display on the screen
                totalEntries = int(list['total'])
                log("SonosPlugin: Total Radio Station Matches %d" % totalEntries)
                numberReturned = list['returned']
                log("SonosPlugin: Total Radio Stations in this batch %d" % numberReturned)

                # Makes sure some items are returned
                if numberReturned < 1:
                    numberReturned = len(list['favorites'])
                    if numberReturned < 1:
                        log("SonosPlugin: Zero items returned from request")
                        break

                for item in list['favorites']:
                    # Add the radio station to the list
                    url = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_RADIO_PLAY, 'itemId': item['uri'], 'title': item['title']})

                    li = xbmcgui.ListItem(item['title'], path=url, iconImage=MediaFiles.RadioStationIcon)
                    # Set the right click context menu for the ratio station
                    li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
                    self._addPlayerToContextMenu(li)

                    xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False, totalItems=totalEntries)

                # Add the number returned this time to the running total
                totalCollected = totalCollected + numberReturned
            del sonosDevice

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Gets the Sonos favourite Radio Shows
    def populateRadioShows(self):
        sonosDevice = Sonos.createSonosDevice()

        # Make sure a Sonos speaker was found
        if sonosDevice is not None:
            totalCollected = 0
            totalEntries = 1

            # Need to get all the tracks in batches
            while (totalCollected < totalEntries) and not self._listLimitReached(totalCollected):
                # Get the items from the sonos system
                list = None
                try:
                    list = sonosDevice.get_favorite_radio_shows(start=totalCollected, max_items=Settings.getBatchSize())
                except:
                    log("SonosPlugin: %s" % traceback.format_exc(), xbmc.LOGERROR)
                    xbmcgui.Dialog().ok(__addon__.getLocalizedString(32068), __addon__.getLocalizedString(32072))
                    return

                # Processes the list returned from Sonos, creating the list display on the screen
                totalEntries = int(list['total'])
                log("SonosPlugin: Total Radio Shows Matches %d" % totalEntries)
                numberReturned = list['returned']
                log("SonosPlugin: Total Radio Shows in this batch %d" % numberReturned)

                # Makes sure some items are returned
                if numberReturned < 1:
                    numberReturned = len(list['favorites'])
                    if numberReturned < 1:
                        log("SonosPlugin: Zero items returned from request")
                        break

                for item in list['favorites']:
                    # Add the radio station to the list
                    url = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_RADIO_PLAY, 'itemId': item['uri'], 'title': item['title']})

                    li = xbmcgui.ListItem(item['title'], path=url, iconImage=MediaFiles.RadioStationIcon)
                    # Set the right click context menu for the ratio station
                    li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
                    self._addPlayerToContextMenu(li)

                    xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False, totalItems=totalEntries)

                # Add the number returned this time to the running total
                totalCollected = totalCollected + numberReturned
            del sonosDevice

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Populate the Music menu
    def populateSpeech(self):
        url = self._build_url({'mode': MenuNavigator.COMMAND_SPEECH_INPUT})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32200), iconImage=__icon__)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        url = self._build_url({'mode': MenuNavigator.COMMAND_SPEECH_SAVE})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32203), iconImage=__icon__)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        # Add a blank line before the filters
        li = xbmcgui.ListItem("", iconImage=__icon__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url="", listitem=li, isFolder=False)

        # Create the speech class (Not going to call the Sonos System do no need for the device)
        speech = Speech()
        phrases = speech.loadSavedPhrases()
        del speech

        # Loop through all the phrases and add them to the screen
        for phrase in phrases:
            url = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_SPEECH_SAY_PHRASE, 'itemId': phrase})
            li = xbmcgui.ListItem(phrase, iconImage=__icon__)
            # Add the remove button to the context menu
            cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_SPEECH_REMOVE_PHRASE, 'itemId': phrase})
            ctxtMenu = []
            ctxtMenu.append((__addon__.getLocalizedString(32204), 'RunPlugin(%s)' % cmd))
            li.addContextMenuItems(ctxtMenu, replaceItems=True)  # Clear the Context Menu
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Checks if the limit for the size of the list has been reached
    def _listLimitReached(self, currentEntries):
        queueLimit = Settings.getMaxListEntries()
        # Zero is unlimited
        if queueLimit == 0:
            return False
        return currentEntries >= queueLimit

    # Adds a sub-directory to the display
    def _addDirectory(self, item, folderName, totalEntries=None, subCategory=None, item_id=None):
        if (item is not None) and (folderName is not None):
            # Escape special characters from the title
            # Useful site: http://www.ascii.cl/htmlcodes.htm
            title = item.title.replace('/', "%2F").replace(':', "%3A")
            # If the item ID is set we use that instead of the subcatagory name
            if item_id is not None:
                subCategory = str(item_id)
            # Update the category
            elif subCategory is not None:
                log("SonosPlugin: Adding to existing category %s" % subCategory)
                subCategory += '/' + title.encode("utf-8")
            else:
                subCategory = title.encode("utf-8")
            url = self._build_url({'mode': 'folder', 'foldername': folderName, 'subCategory': subCategory})

            # Get a suitable display title
            displayTitle = None
            if (folderName == MenuNavigator.ALBUMS):  # or (folderName == MenuNavigator.ALBUMARTISTS):
                # Get the display title, adding the track number if available
                if (item.creator is not None) and (item.creator != ""):
                    displayTitle = "%s - %s" % (item.title, item.creator)

            # If the display title hasn't been set yet, default to the title
            if displayTitle is None:
                # Default is to just display the title
                displayTitle = item.title

            # Create the list item for the directory
            if hasattr(item, 'album_art_uri') and (item.album_art_uri is not None) and (item.album_art_uri != ""):
                li = xbmcgui.ListItem(displayTitle, iconImage=item.album_art_uri, thumbnailImage=item.album_art_uri)
            else:
                # Use one of the default icons
                defaultIcon = MediaFiles.TracksIcon
                if (folderName == MenuNavigator.ARTISTS) or (folderName == MenuNavigator.ALBUMARTISTS):
                    defaultIcon = MediaFiles.ArtistsIcon
                elif folderName == MenuNavigator.ALBUMS:
                    defaultIcon = MediaFiles.AlbumsIcon
                elif folderName == MenuNavigator.GENRES:
                    defaultIcon = MediaFiles.GenresIcon
                elif folderName == MenuNavigator.COMPOSERS:
                    defaultIcon = MediaFiles.ComposersIcon
                elif folderName == MenuNavigator.SONOS_PLAYLISTS:
                    defaultIcon = MediaFiles.SonosPlaylistIcon

                li = xbmcgui.ListItem(displayTitle, iconImage=defaultIcon)

            # Set the right click context menu for the directory
            self._addContextMenu(li, item.resources[0].uri)

            if totalEntries is not None:
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True, totalItems=totalEntries)
            else:
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

    # Adds a track to the listing
    def _addTrack(self, item, totalEntries=None, folderName=None):
        if item is not None:
            url = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_PLAY, 'itemId': item.resources[0].uri})

            # Get a suitable display title
            displayTitle = None
            if folderName == MenuNavigator.ALBUMS:
                # Get the display title, adding the track number if available
                if (item.original_track_number is not None) and (item.original_track_number != ""):
                    displayTitle = "%02d. %s" % (item.original_track_number, item.title)
            elif (folderName == MenuNavigator.TRACKS) or (folderName == MenuNavigator.SONOS_PLAYLISTS):
                if (item.creator is not None) and (item.creator != ""):
                    displayTitle = "%s - %s" % (item.title, item.creator)

            # If the display title hasn't been set yet, default to the title
            if displayTitle is None:
                # Default is to just display the title
                displayTitle = item.title

            # Create the list item for the track
            if hasattr(item, 'album_art_uri') and (item.album_art_uri is not None) and (item.album_art_uri != ""):
                li = xbmcgui.ListItem(displayTitle, iconImage=item.album_art_uri, thumbnailImage=item.album_art_uri, path=url)
            else:
                li = xbmcgui.ListItem(displayTitle, path=url, iconImage=MediaFiles.TracksIcon)
            # Set addition information about the track - will be seen in info view
            li.setInfo('music', {'tracknumber': item.original_track_number, 'title': item.title, 'artist': item.creator, 'album': item.album})
            # li.setProperty("IsPlayable","true");

            # Set the right click context menu for the track
            self._addContextMenu(li, item.resources[0].uri)

            if totalEntries is not None:
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False, totalItems=totalEntries)
            else:
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

    def _addContextMenu(self, list_item, itemId):
        ctxtMenu = []
        # Play Now
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_PLAY_NOW, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32154), 'RunPlugin(%s)' % cmd))

#        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_PLAY_NEXT, 'itemId': itemId})
#        ctxtMenu.append(('Play Next', 'RunPlugin(%s)' % cmd))
        # Add To QueueIcon
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_ADD_TO_QUEUE, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32155), 'RunPlugin(%s)' % cmd))
        # Replace QueueIcon
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_REPLACE_QUEUE, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32156), 'RunPlugin(%s)' % cmd))

#        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_ADD_TO_SONOS_FAVOURITES, 'itemId': itemId})
#        ctxtMenu.append(('Add To Sonos Favourites', 'RunPlugin(%s)' % cmd))

#        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_ADD_TO_SONOS_PLAYLIST, 'itemId': itemId})
#        ctxtMenu.append(('Add To Sonos Playlist', 'RunPlugin(%s)' % cmd))

        # Add a link to the player from the context menu
        playerList = self._addPlayerToContextMenu(list_item)
        ctxtMenu.append(playerList.pop())

        list_item.addContextMenuItems(ctxtMenu, replaceItems=True)

    def _addQueueContextMenu(self, list_item, itemId):
        ctxtMenu = []
        # Play Track
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_QUEUE_PLAY_ITEM, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32151), 'RunPlugin(%s)' % cmd))
        # Remove Track
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_QUEUE_REMOVE_ITEM, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32152), 'RunPlugin(%s)' % cmd))
        # Clear QueueIcon
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_QUEUE_CLEAR, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32153), 'RunPlugin(%s)' % cmd))

        # Add a link to the player from the context menu
        playerList = self._addPlayerToContextMenu(list_item)
        ctxtMenu.append(playerList.pop())

        list_item.addContextMenuItems(ctxtMenu, replaceItems=True)

    # Add a link to the player from the context menu
    def _addPlayerToContextMenu(self, list_item):
        ctxtMenu = []
        # Open Sonos Player
        ctxtMenu.append((__addon__.getLocalizedString(32150), 'RunScript(%s)' % os.path.join(__cwd__, "default.py")))
        list_item.addContextMenuItems(ctxtMenu, replaceItems=False)
        return ctxtMenu

    # Add items required for the Music Library
    def _addMusicLibraryContextMenu(self, list_item):
        # Action to update the music library (re-scan)
        # Use a dummy itemid, as it is not really required
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_UPDATE_LIBRARY, 'itemId': -1})

        # Add a link to the player from the context menu
        fullMenu = self._addPlayerToContextMenu(list_item)
        fullMenu.append((__addon__.getLocalizedString(32157), 'RunPlugin(%s)' % cmd))

        list_item.addContextMenuItems(fullMenu, replaceItems=True)


##################################################
# Class to handle all the actions for the plugin
##################################################
class ActionManager():
    ACTION_PLAY = 'play'
    ACTION_PLAY_NOW = 'playNow'
#    ACTION_PLAY_NEXT = 'playNext'
    ACTION_ADD_TO_QUEUE = 'addToQueue'
    ACTION_REPLACE_QUEUE = 'replaceQueue'
#    ACTION_ADD_TO_SONOS_FAVOURITES = 'addToSonosFavourites'
#    ACTION_ADD_TO_SONOS_PLAYLIST = 'addToSonosPlaylist'

    ACTION_UPDATE_LIBRARY = 'updateLibrary'

    ACTION_QUEUE_PLAY_ITEM = 'playQueueItem'
    ACTION_QUEUE_REMOVE_ITEM = 'removeQueueItem'
    ACTION_QUEUE_CLEAR = 'clearQueue'

    ACTION_RADIO_PLAY = 'playRadio'

    ACTION_SPEECH_SAY_PHRASE = 'speechSayPhrase'
    ACTION_SPEECH_REMOVE_PHRASE = 'speechRemovePhrase'

    def __init__(self):
        self.sonosDevice = Sonos.createSonosDevice()

    def performAction(self, actionType, itemId, title):
        try:
            if (actionType == ActionManager.ACTION_PLAY) or (actionType == ActionManager.ACTION_PLAY_NOW):
                self.performPlay(itemId)
            elif actionType == ActionManager.ACTION_ADD_TO_QUEUE:
                self.performAddToQueue(itemId)
            elif actionType == ActionManager.ACTION_REPLACE_QUEUE:
                self.performReplaceQueue(itemId)
            # Operations for the QueueIcon View
            elif actionType == ActionManager.ACTION_QUEUE_PLAY_ITEM:
                self.playQueueItem(int(itemId))
            elif actionType == ActionManager.ACTION_QUEUE_REMOVE_ITEM:
                self.removeQueueItem(int(itemId))
            elif actionType == ActionManager.ACTION_QUEUE_CLEAR:
                self.clearQueueItem(int(itemId))
            # Radio Operations
            elif actionType == ActionManager.ACTION_RADIO_PLAY:
                self.performPlayURI(itemId, title)
            # Speech Operations
            elif actionType == ActionManager.ACTION_SPEECH_SAY_PHRASE:
                self.sayPhrase(itemId)
            elif actionType == ActionManager.ACTION_SPEECH_REMOVE_PHRASE:
                self.removePhrase(itemId)
            elif actionType == ActionManager.ACTION_UPDATE_LIBRARY:
                self.updateLibrary()
            else:
                # This should never be shown, so no need to translate, enabled for debug
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32068), "Operation %s not currently supported" % actionType)
        except:
            log("SonosPlugin: %s" % traceback.format_exc(), xbmc.LOGERROR)
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32068), __addon__.getLocalizedString(32073) % actionType)

    # The default play command for Sonos is to add it to the queue and play that item
    def performPlay(self, itemId):
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            positionInQueue = self.performAddToQueue(itemId)
            # Then play the newly added item
            if positionInQueue > 0:
                positionInQueue = positionInQueue - 1
            self.sonosDevice.play_from_queue(positionInQueue)

    def performPlayURI(self, itemId, title):
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            self.sonosDevice.play_uri(cgi.escape(itemId), title=cgi.escape(title))

    def performAddToQueue(self, itemId):
        positionInQueue = None
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            # Add this one to the queue - it returns the position added
            log("Adding the following URI to the queue: %s" % itemId)
            positionInQueue = self.sonosDevice.add_uri_to_queue(itemId)
        return positionInQueue

    def performReplaceQueue(self, itemId):
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            self.sonosDevice.clear_queue()
            self.performPlay(itemId)

    def playQueueItem(self, itemId):
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            self.sonosDevice.play_from_queue(itemId)

    def removeQueueItem(self, itemId):
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            self.sonosDevice.remove_from_queue(itemId)
            # Refresh the screen now that we have removed one item from it
            xbmc.executebuiltin('Container.Refresh')

    def clearQueueItem(self, itemId):
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            self.sonosDevice.clear_queue()
            # Refresh the screen now that we have removed all the items
            xbmc.executebuiltin('Container.Refresh')

    # Trigger an update of the Library
    def updateLibrary(self):
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            # First check to see if the library is already being updated
            if self.sonosDevice.music_library.library_updating is True:
                # Tell the user that an update is already in progress
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32065))
            else:
                # Perform the update
                self.sonosDevice.music_library.start_library_update()
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32064))

    # SPEECH OPERATIONS
    def sayPhrase(self, phrase):
        # Make sure a Sonos speaker was found
        if self.sonosDevice is not None:
            # Create the speech class and play the message
            speech = Speech(self.sonosDevice)
            # Now get the Sonos Sytem to say the message
            speech.say(phrase)
            del speech

    def removePhrase(self, phrase):
        speech = Speech(self.sonosDevice)
        speech.removePhrase(phrase)
        del speech
        # Refresh the screen now that an item has been removed
        xbmc.executebuiltin('Container.Refresh')


################################
# Main of the Sonos Plugin
################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, audio in our case
    xbmcplugin.setContent(addon_handle, 'audio')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("SonosPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("SonosPlugin: Mode is NONE - showing root menu")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.setRootMenu()
        del menuNav

    elif mode[0] == 'folder':
        log("SonosPlugin: Mode is FOLDER")

        # Get the actual folder that was navigated to
        foldername = args.get('foldername', None)

        if (foldername is not None) and (len(foldername) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            # Check for the special case of manually defined folders
            if foldername[0] == MenuNavigator.ROOT_MENU_MUSIC_LIBRARY:
                menuNav.setMusicLibrary()
            elif foldername[0] == MenuNavigator.ROOT_MENU_QUEUE:
                menuNav.populateQueueList()
            elif foldername[0] == MenuNavigator.ROOT_MENU_RADIO_STATIONS:
                menuNav.populateRadioStations()
            elif foldername[0] == MenuNavigator.ROOT_MENU_RADIO_SHOWS:
                menuNav.populateRadioShows()
            elif foldername[0] == MenuNavigator.ROOT_MENU_SPEECH:
                menuNav.populateSpeech()
            else:
                subCategory = args.get('subCategory', '')
                if subCategory != '':
                    subCategory = subCategory[0]

                log("SonosPlugin: Folder name is %s (%s)" % (foldername[0], subCategory))

                # Populate the menu
                menuNav.processFolderMessage(foldername[0], subCategory)

            del menuNav

    elif mode[0] == 'action':
        log("SonosPlugin: Mode is ACTION")

        # Get the action Type
        actionType = args.get('action', None)
        # Get the item that the action is to be performed on
        itemId = args.get('itemId', None)
        # Get the title if it is supplied
        title = args.get('title', None)
        if title is not None:
            title = title[0]

        if (actionType is not None) and (itemId is not None):
            actionMgr = ActionManager()
            actionMgr.performAction(actionType[0], itemId[0], title)
            del actionMgr

    elif mode[0] == MenuNavigator.COMMAND_CONTROLLER:
        log("SonosPlugin: Mode is launchController")
        xbmc.executebuiltin("ActivateWindow(home)", True)
        xbmc.executebuiltin('RunScript(script.sonos)')

    elif mode[0] == MenuNavigator.COMMAND_SPEECH_INPUT:
        log("SonosPlugin: Mode is Speech Input")
        sonosDevice = Sonos.createSonosDevice()
        # Make sure a Sonos speaker was found
        if sonosDevice is not None:
            # Create the speech class and prompt the user for the message
            speech = Speech(sonosDevice)
            msg = speech.promptForInput()
            if msg is not None:
                # Now get the Sonos Sytem to say the message
                speech.say(msg)
            del speech
            del sonosDevice

    elif mode[0] == MenuNavigator.COMMAND_SPEECH_SAVE:
        log("SonosPlugin: Mode is Speech Save")
        # Create the speech class and prompt the user for the message
        # (No need for a device to save a message)
        speech = Speech()
        speech.addPhrase()
        # Refresh the screen now that an item has been removed
        xbmc.executebuiltin('Container.Refresh')
        del speech

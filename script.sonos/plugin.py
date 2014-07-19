# -*- coding: utf-8 -*-
# Reference:
# http://wiki.xbmc.org/index.php?title=Audio/Video_plugin_tutorial
import sys
import os
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

import soco


###################################################################
# Media files used by the plugin
###################################################################
class MediaFiles():
    RadioIcon = os.path.join(__media__, 'Radio@2x.png')
    MusicLibraryIcon = os.path.join(__media__, 'shMusicLibrary@2x.png')
    QueueIcon = os.path.join(__media__, 'Playlist@2x.png')


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

    # Menu items manually set at the root
    ROOT_MENU_MUSIC_LIBRARY = 'Music-Library'
    ROOT_MENU_QUEUE = 'QueueIcon'
    ROOT_MENU_RADIO_STATIONS = 'Radio-Stations'
    ROOT_MENU_RADIO_SHOWS = 'Radio-Shows'

    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # Display the default list of items in the root menu
    def setRootMenu(self):
        # Sonos Controller Link
        url = self._build_url({'mode': 'launchController'})
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
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
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

#        url = self._build_url({'mode': 'folder', 'foldername': 'Sonos-Playlists'})
#        li = xbmcgui.ListItem('Sonos Playlists (Not Supported Yet)', iconImage='DefaultFolder.png')
#        li.addContextMenuItems([], replaceItems=True) # Clear the Context Menu
#        self._addPlayerToContextMenu(li) # Add the Sonos player to the menu
#        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

#        url = self._build_url({'mode': 'folder', 'foldername': 'Line-In'})
#        li = xbmcgui.ListItem('Line-In (Not Supported Yet)', iconImage='DefaultFolder.png')
#        li.addContextMenuItems([], replaceItems=True) # Clear the Context Menu
#        self._addPlayerToContextMenu(li) # Add the Sonos player to the menu
#        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # QueueIcon
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ROOT_MENU_QUEUE})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32101), iconImage=MediaFiles.QueueIcon)
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Populate the Music menu
    def setMusicLibrary(self):
        # Artists
        # Note: For artists, the sonos system actually calls "Album Artists"
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ALBUMARTISTS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32110), iconImage='DefaultMusicArtists.png')
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Albums
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.ALBUMS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32111), iconImage='DefaultMusicAlbums.png')
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Composers
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.COMPOSERS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32112), iconImage='DefaultArtist.png')
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Genres
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.GENRES})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32113), iconImage='DefaultMusicGenres.png')
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Tracks
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.TRACKS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32114), iconImage='DefaultMusicSongs.png')
        li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
        self._addPlayerToContextMenu(li)  # Add the Sonos player to the menu
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Populets the queue list from the Sonos speaker
    def populateQueueList(self):
        sonosDevice = Settings.getSonosDevice()

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
                    list = sonosDevice.get_queue(start=totalCollected, max_items=Settings.getBatchSize())
                except:
                    log("SonosPlugin: %s" % traceback.format_exc())
                    xbmcgui.Dialog().ok("Error", "Failed to perform queue lookup")
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
                        li = xbmcgui.ListItem(displayTitle, iconImage='DefaultMusicSongs.png')
                    # Set addition information about the track - will be seen in info view
                    li.setInfo('music', {'title': item.title, 'artist': item.creator, 'album': item.album})

                    # Create the action to be performed when clicking a queue item
                    url = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_QUEUE_PLAY_ITEM, 'itemId': itemNum})

                    # Add the context menu for the queue
                    self._addQueueContextMenu(li, itemNum + totalCollected)
                    itemNum = itemNum + 1

                    xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

                totalCollected = totalCollected + numberReturned

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Process a folder action that requires a lookup from Sonos
    def processFolderMessage(self, folderName, subCategory=''):
        sonosDevice = Settings.getSonosDevice()

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
                    list = sonosDevice.get_music_library_information(search_type=folderName, start=totalCollected, max_items=Settings.getBatchSize(), sub_category=subCategory)
                except:
                    log("SonosPlugin: %s" % traceback.format_exc())
                    xbmcgui.Dialog().ok("Error", "Failed to perform lookup %s (%s)" % (folderName, subCategory))
                    return

                # Processes the list returned from Sonos, creating the list display on the screen
                totalEntries = list['total_matches']
                log("SonosPlugin: Total %s Matches %d" % (folderName, totalEntries))
                numberReturned = list['number_returned']
                log("SonosPlugin: Total %s in this batch %d" % (folderName, numberReturned))

                # Makes sure some items are returned
                if numberReturned < 1:
                    numberReturned = len(list['item_list'])
                    if numberReturned < 1:
                        log("SonosPlugin: Zero items returned from request")
                        break

                for item in list['item_list']:
                    # Check if this item is a track of a directory
                    if isinstance(item, soco.data_structures.MLTrack):
                        self._addTrack(item, totalEntries, folderName)
                    else:
                        # Check for the special case where there is an "All" first in the list
                        # For this the id and parent values are the same.  The All item
                        # is a special case and does not handle like a normal directory
                        if ('sameArtist' in item.item_class) or ('albumlist' in item.item_class):
                            log("SonosPlugin: Skipping \"All\" item for %s" % item.title)
                            isFirstItem = False
                            continue

                        self._addDirectory(item, folderName, totalEntries, subCategory)
                    # No longer the first item
                    isFirstItem = False  # noqa PEP8

                # Add the number returned this time to the running total
                totalCollected = totalCollected + numberReturned

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Gets the Sonos favourite Radio Stations
    def populateRadioStations(self):
        sonosDevice = Settings.getSonosDevice()

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
                    log("SonosPlugin: %s" % traceback.format_exc())
                    xbmcgui.Dialog().ok("Error", "Failed to perform radio station lookup")
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

                    li = xbmcgui.ListItem(item['title'], path=url, iconImage='DefaultMusicSongs.png')
                    # Set the right click context menu for the ratio station
                    li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
                    self._addPlayerToContextMenu(li)

                    xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False, totalItems=totalEntries)

                # Add the number returned this time to the running total
                totalCollected = totalCollected + numberReturned

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Gets the Sonos favourite Radio Shows
    def populateRadioShows(self):
        sonosDevice = Settings.getSonosDevice()

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
                    log("SonosPlugin: %s" % traceback.format_exc())
                    xbmcgui.Dialog().ok("Error", "Failed to perform radio shows lookup")
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

                    li = xbmcgui.ListItem(item['title'], path=url, iconImage='DefaultMusicSongs.png')
                    # Set the right click context menu for the ratio station
                    li.addContextMenuItems([], replaceItems=True)  # Clear the Context Menu
                    self._addPlayerToContextMenu(li)

                    xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False, totalItems=totalEntries)

                # Add the number returned this time to the running total
                totalCollected = totalCollected + numberReturned

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Checks if the limit for the size of the list has been reached
    def _listLimitReached(self, currentEntries):
        queueLimit = Settings.getMaxListEntries()
        # Zero is unlimited
        if queueLimit == 0:
            return False
        return currentEntries >= queueLimit

    # Adds a sub-directory to the display
    def _addDirectory(self, item, folderName, totalEntries=None, subCategory=None):
        if (item is not None) and (folderName is not None):
            # Escape special characters from the title
            # Useful site: http://www.ascii.cl/htmlcodes.htm
            title = item.title.replace('/', "%2F").replace(':', "%3A")
            # Update the category
            if subCategory is not None:
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
                defaultIcon = 'DefaultAudio.png'
                if folderName == MenuNavigator.ARTISTS:
                    defaultIcon = 'DefaultMusicArtists.png'
                elif (folderName == MenuNavigator.ALBUMS) or (folderName == MenuNavigator.ALBUMARTISTS):
                    defaultIcon = 'DefaultMusicAlbums.png'
                elif folderName == MenuNavigator.GENRES:
                    defaultIcon = 'DefaultMusicGenres.png'
                elif folderName == MenuNavigator.COMPOSERS:
                    defaultIcon = 'DefaultArtist.png'

                li = xbmcgui.ListItem(displayTitle, iconImage=defaultIcon)

            # Set the right click context menu for the directory
            self._addContextMenu(li, item.uri)

            if totalEntries is not None:
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True, totalItems=totalEntries)
            else:
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

    # Adds a track to the listing
    def _addTrack(self, item, totalEntries=None, folderName=None):
        if item is not None:
            url = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_PLAY, 'itemId': item.uri})

            # Get a suitable display title
            displayTitle = None
            if folderName == MenuNavigator.ALBUMS:
                # Get the display title, adding the track number if available
                if (item.original_track_number is not None) and (item.original_track_number != ""):
                    displayTitle = "%02d. %s" % (item.original_track_number, item.title)
            elif folderName == MenuNavigator.TRACKS:
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
                li = xbmcgui.ListItem(displayTitle, path=url, iconImage='DefaultMusicSongs.png')
            # Set addition information about the track - will be seen in info view
            li.setInfo('music', {'tracknumber': item.original_track_number, 'title': item.title, 'artist': item.creator, 'album': item.album})
            # li.setProperty("IsPlayable","true");

            # Set the right click context menu for the track
            self._addContextMenu(li, item.uri)

            if totalEntries is not None:
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False, totalItems=totalEntries)
            else:
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

    def _addContextMenu(self, list_item, itemId):
        ctxtMenu = []
        # Play Now
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_PLAY_NOW, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32154), 'XBMC.RunPlugin(%s)' % cmd))

#        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_PLAY_NEXT, 'itemId': itemId})
#        ctxtMenu.append(('Play Next', 'XBMC.RunPlugin(%s)' % cmd))
        # Add To QueueIcon
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_ADD_TO_QUEUE, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32155), 'XBMC.RunPlugin(%s)' % cmd))
        # Replace QueueIcon
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_REPLACE_QUEUE, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32156), 'XBMC.RunPlugin(%s)' % cmd))

#        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_ADD_TO_SONOS_FAVOURITES, 'itemId': itemId})
#        ctxtMenu.append(('Add To Sonos Favourites', 'XBMC.RunPlugin(%s)' % cmd))

#        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_ADD_TO_SONOS_PLAYLIST, 'itemId': itemId})
#        ctxtMenu.append(('Add To Sonos Playlist', 'XBMC.RunPlugin(%s)' % cmd))

        # Add a link to the player from the context menu
        self._addPlayerToContextMenu(list_item)

        list_item.addContextMenuItems(ctxtMenu, replaceItems=True)

    def _addQueueContextMenu(self, list_item, itemId):
        ctxtMenu = []
        # Play Track
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_QUEUE_PLAY_ITEM, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32151), 'XBMC.RunPlugin(%s)' % cmd))
        # Remove Track
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_QUEUE_REMOVE_ITEM, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32152), 'XBMC.RunPlugin(%s)' % cmd))
        # Clear QueueIcon
        cmd = self._build_url({'mode': 'action', 'action': ActionManager.ACTION_QUEUE_CLEAR, 'itemId': itemId})
        ctxtMenu.append((__addon__.getLocalizedString(32153), 'XBMC.RunPlugin(%s)' % cmd))

        # Add a link to the player from the context menu
        self._addPlayerToContextMenu(list_item)

        list_item.addContextMenuItems(ctxtMenu, replaceItems=True)

    # Add a link to the player from the context menu
    def _addPlayerToContextMenu(self, list_item):
        ctxtMenu = []
        # Open Sonos Player
        ctxtMenu.append((__addon__.getLocalizedString(32150), 'XBMC.RunScript(%s)' % os.path.join(__cwd__, "default.py")))
        list_item.addContextMenuItems(ctxtMenu, replaceItems=False)


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

    ACTION_QUEUE_PLAY_ITEM = 'playQueueItem'
    ACTION_QUEUE_REMOVE_ITEM = 'removeQueueItem'
    ACTION_QUEUE_CLEAR = 'clearQueue'

    ACTION_RADIO_PLAY = 'playRadio'

    def __init__(self):
        self.sonosDevice = Settings.getSonosDevice()

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
            else:
                # Temp error message - should never be shown - will remove when all features complete
                xbmcgui.Dialog().ok("Error", "Operation %s not currently supported" % actionType)
        except:
            log("SonosPlugin: %s" % traceback.format_exc())
            xbmcgui.Dialog().ok("Error", "Failed to perform action %s" % actionType)

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
            self.sonosDevice.play_uri(itemId, title)

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

    elif mode[0] == 'folder':
        log("SonosPlugin: Mode is FOLDER")

        # Get the actual folder that was navigated to
        foldername = args.get('foldername', None)

        if (foldername is not None) and (len(foldername) > 0):
            # Check for the special case of manually defined folders
            if foldername[0] == MenuNavigator.ROOT_MENU_MUSIC_LIBRARY:
                menuNav = MenuNavigator(base_url, addon_handle)
                menuNav.setMusicLibrary()
            elif foldername[0] == MenuNavigator.ROOT_MENU_QUEUE:
                menuNav = MenuNavigator(base_url, addon_handle)
                menuNav.populateQueueList()
            elif foldername[0] == MenuNavigator.ROOT_MENU_RADIO_STATIONS:
                menuNav = MenuNavigator(base_url, addon_handle)
                menuNav.populateRadioStations()
            elif foldername[0] == MenuNavigator.ROOT_MENU_RADIO_SHOWS:
                menuNav = MenuNavigator(base_url, addon_handle)
                menuNav.populateRadioShows()
            else:
                subCategory = args.get('subCategory', '')
                if subCategory != '':
                    subCategory = subCategory[0]

                log("SonosPlugin: Folder name is %s (%s)" % (foldername[0], subCategory))

                # Populate the menu
                menuNav = MenuNavigator(base_url, addon_handle)
                menuNav.processFolderMessage(foldername[0], subCategory)

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

    elif mode[0] == 'launchController':
        log("SonosPlugin: Mode is launchController")
        xbmc.executebuiltin("xbmc.ActivateWindow(home)", True)
        xbmc.executebuiltin('XBMC.RunScript(script.sonos)')

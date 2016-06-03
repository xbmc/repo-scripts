# -*- coding: utf-8 -*-
import sys
import os
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

# Import the common settings
from resources.lib.settings import Settings
from resources.lib.settings import log
from resources.lib.settings import os_path_join
from resources.lib.database import PinSentryDB

ADDON = xbmcaddon.Addon(id='script.pinsentry')
ICON = ADDON.getAddonInfo('icon')
FANART = ADDON.getAddonInfo('fanart')
CWD = ADDON.getAddonInfo('path').decode("utf-8")
ICON_DIR = xbmc.translatePath(os.path.join(CWD, 'resources', 'media', 'classifications').encode("utf-8")).decode("utf-8")


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    MOVIES = 'movies'
    TVSHOWS = 'tvshows'
    MOVIESETS = 'sets'
    PLUGINS = 'plugins'
    MUSICVIDEOS = 'musicvideos'
    FILESOURCE = 'filesource'

    CLASSIFICATIONS = 'classifications'
    CLASSIFICATIONS_MOVIES = 'classifications-movies'
    CLASSIFICATIONS_TV = 'classifications-tv'

    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # Display the default list of items in the root menu
    def showRootMenu(self):
        # Movies
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MOVIES})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32201), iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems(self._getContextMenu(MenuNavigator.MOVIES), replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # TV Shows
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.TVSHOWS})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32202), iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems(self._getContextMenu(MenuNavigator.TVSHOWS), replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Movie Sets
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MOVIESETS})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32203), iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems(self._getContextMenu(MenuNavigator.MOVIESETS), replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Music Videos
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MUSICVIDEOS})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32205), iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems(self._getContextMenu(MenuNavigator.MUSICVIDEOS), replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Plugins
        if Settings.isActivePlugins():
            url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.PLUGINS})
            li = xbmcgui.ListItem(ADDON.getLocalizedString(32128), iconImage=ICON)
            li.setProperty("Fanart_Image", FANART)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Files
        if Settings.isActiveFileSource():
            url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.FILESOURCE})
            li = xbmcgui.ListItem(ADDON.getLocalizedString(32204), iconImage=ICON)
            li.setProperty("Fanart_Image", FANART)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Classifications
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.CLASSIFICATIONS})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32206), iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Add a blank line before the Operations
        li = xbmcgui.ListItem("", iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url="", listitem=li, isFolder=False)

        # Force Pin Entry
        url = self._build_url({'mode': 'forcepin', 'foldername': 'none'})
        menuItemName = ADDON.getLocalizedString(32213)
        try:
            menuItemName = "[%s]" % menuItemName
        except:
            pass
        li = xbmcgui.ListItem(menuItemName, iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Show the list of videos in a given set
    def showFolder(self, foldername, type="", subType=""):
        # Check for the special case of manually defined folders
        if foldername == MenuNavigator.TVSHOWS:
            self._setList(MenuNavigator.TVSHOWS)
        elif foldername == MenuNavigator.MOVIES:
            self._setList(MenuNavigator.MOVIES)
        elif foldername == MenuNavigator.MOVIESETS:
            self._setList(MenuNavigator.MOVIESETS)
        elif foldername == MenuNavigator.MUSICVIDEOS:
            self._setList(MenuNavigator.MUSICVIDEOS)
        elif foldername == MenuNavigator.PLUGINS:
            self._setList(MenuNavigator.PLUGINS)
        elif foldername == MenuNavigator.FILESOURCE:
            self._setList(MenuNavigator.FILESOURCE)
        elif foldername == MenuNavigator.CLASSIFICATIONS:
            self._setClassificationList(type, subType)

    # Produce the list of videos and flag which ones with security details
    def _setList(self, target):
        items = []
        if target == MenuNavigator.PLUGINS:
            items = self._setPluginList()
        elif target == MenuNavigator.FILESOURCE:
            items = self._setFileSourceList()
        else:
            # Everything other plugins are forms of video
            items = self._getVideos(target)

        # Now add the security details to the list
        items = self._addSecurityFlags(target, items)
        # Update the classifications
        items = self._cleanClassification(target, items)

        for item in items:
            # Create the list-item for this video
            li = xbmcgui.ListItem(item['title'], iconImage=item['thumbnail'])

            # Remove the default context menu
            li.addContextMenuItems([], replaceItems=True)
            # Get the title of the video
            title = item['title']
            try:
                title = item['title'].encode("utf-8")
            except:
                pass

            # Make sure the dbid is coded correctly
            dbid = item['dbid']
            try:
                dbid = item['dbid'].encode("utf-8")
            except:
                pass

            # Check if the classification is restricting this item
            isBlockedByClassification = False
            if 'mpaa' in item:
                if item['mpaa'] not in [None, ""]:
                    isBlockedByClassification = True

            # Add a tick if security is set
            if item['securityLevel'] != 0:
                li.setInfo('video', {'PlayCount': 1})
                # Not the best display format - but the only way that I can get a number to display
                # In the list, the problem is it will display 01:00 - but at least it's something
                if Settings.showSecurityLevelInPlugin():
                    li.setInfo('video', {'Duration': item['securityLevel']})
            elif Settings.isHighlightClassificationUnprotectedVideos():
                # If the user wishes to see which files are not protected by one of the rules
                # currently applied, we put the play signal next to them
                if not isBlockedByClassification:
                    li.setProperty("TotalTime", "")
                    li.setProperty("ResumeTime", "1")

            # Handle the case where we want to turn off security for a video
            if isBlockedByClassification and (item['securityLevel'] == -1):
                # This is the case where the user has forced access to be allowed, this
                # is useful if you have classification enabled and you want to allow a
                # given video for a classification to be unprotected
                li.setProperty("TotalTime", "")
                li.setProperty("ResumeTime", "1")

            li.setProperty("Fanart_Image", item['fanart'])
            url = self._build_url({'mode': 'setsecurity', 'level': item['securityLevel'], 'type': target, 'title': title, 'id': dbid, 'classificationBlocked': str(isBlockedByClassification)})
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Do a lookup in the database for the given type of videos
    def _getVideos(self, target):
        jsonGet = 'GetMovies'
        dbid = 'movieid'
        extraDetails = ', "mpaa"'
        if target == MenuNavigator.TVSHOWS:
            jsonGet = 'GetTVShows'
            dbid = 'tvshowid'
        elif target == MenuNavigator.MOVIESETS:
            jsonGet = 'GetMovieSets'
            dbid = 'setid'
            extraDetails = ""
        elif target == MenuNavigator.MUSICVIDEOS:
            jsonGet = 'GetMusicVideos'
            dbid = 'musicvideoid'
            extraDetails = ""

        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.%s", "params": {"properties": ["title", "thumbnail", "fanart"%s], "sort": { "method": "title" } }, "id": 1}' % (jsonGet, extraDetails))
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log(json_response)
        videolist = []
        if ("result" in json_response) and (target in json_response['result']):
            for item in json_response['result'][target]:
                videoItem = {}

                try:
                    videoItem['title'] = item['title'].encode("utf-8")
                except:
                    log("setVideoList: Failed to encode title %s" % title)
                    videoItem['title'] = item['title']

                if item['thumbnail'] in [None, ""]:
                    videoItem['thumbnail'] = 'DefaultFolder.png'
                else:
                    videoItem['thumbnail'] = item['thumbnail']

                if item['fanart'] in [None, ""]:
                    videoItem['fanart'] = FANART
                else:
                    videoItem['fanart'] = item['fanart']

                videoItem['dbid'] = item[dbid]
                if 'mpaa' in item:
                    videoItem['mpaa'] = item['mpaa']

                videolist.append(videoItem)
        return videolist

    # Adds the current security details to the items
    def _addSecurityFlags(self, type, items):
        # Make sure we have some items to append the details to
        if len(items) < 1:
            return items

        # Make the call to the DB to get all the specific security settings
        pinDB = PinSentryDB()

        securityDetails = {}
        if type == MenuNavigator.TVSHOWS:
            securityDetails = pinDB.getAllTvShowsSecurity()
        elif type == MenuNavigator.MOVIES:
            securityDetails = pinDB.getAllMoviesSecurity()
        elif type == MenuNavigator.MOVIESETS:
            securityDetails = pinDB.getAllMovieSetsSecurity()
        elif type == MenuNavigator.MUSICVIDEOS:
            securityDetails = pinDB.getAllMusicVideosSecurity()
        elif type == MenuNavigator.PLUGINS:
            securityDetails = pinDB.getAllPluginsSecurity()
        elif type == MenuNavigator.FILESOURCE:
            securityDetails = pinDB.getAllFileSourcesSecurity()

        for item in items:
            # Default security to 0 (Not Set)
            securityLevel = 0
            if item['title'] in securityDetails:
                title = item['title']
                securityLevel = securityDetails[title]
                log("PinSentryPlugin: %s has security level %d" % (title, securityLevel))

            item['securityLevel'] = securityLevel

        del pinDB
        return items

    # Update the classifications
    def _cleanClassification(self, target, items):
        securityDetails = {}
        # Make the call to the DB to get all the specific security settings
        if target == MenuNavigator.MOVIES:
            pinDB = PinSentryDB()
            securityDetails = pinDB.getAllMovieClassificationSecurity(True)
            del pinDB
        elif target == MenuNavigator.TVSHOWS:
            pinDB = PinSentryDB()
            securityDetails = pinDB.getAllTvClassificationSecurity(True)
            del pinDB
        else:
            # No Classifications to deal with
            return items

        # Generate a list of certificates to check against
        certValues = securityDetails.keys()

        log("PinSentryPlugin: Allowing certificates for %s" % str(certValues))

        # Check each of the items and add a flag if they are protected by a classification rule
        for item in items:
            if 'mpaa' in item:
                if item['mpaa'] not in [None, ""]:
                    cert = item['mpaa'].strip().split(':')[-1]
                    cert = cert.strip().split()[-1]

                    try:
                        cert = cert.encode("utf-8")
                    except:
                        log("PinSentryPlugin: Failed to encode certificate")

                    # Need to decode the title as it doesn't link it for the logging that follows
                    # if we don't
                    title = item['title']
                    try:
                        title = item['title'].decode("utf-8")
                    except:
                        log("PinSentryPlugin: Failed to decode title")

                    if cert in certValues:
                        item['mpaa'] = cert
                        log("PinSentryPlugin: Setting mpaa for %s to %s" % (title, cert))
                    else:
                        log("PinSentryPlugin: Clearing mpaa for %s (was %s)" % (title, item['mpaa']))
                        item['mpaa'] = ""
        return items

    # get the list of plugins installed on the system
    def _setPluginList(self):
        # Make the call to find out all the addons that are installed
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "type": "xbmc.python.pluginsource", "enabled": true, "properties": ["name", "thumbnail", "fanart"] }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log(json_response)
        plugins = []
        if ("result" in json_response) and ('addons' in json_response['result']):
            # Check each of the plugins that are installed on the system
            for addonItem in json_response['result']['addons']:
                addonId = addonItem['addonid']
                # Need to skip ourselves
                if addonId in ['script.pinsentry']:
                    log("setPluginList: Skipping PinSentry Plugin")
                    continue

                pluginDetails = {}
                pluginDetails['title'] = addonItem['name']
                pluginDetails['dbid'] = addonId

                if addonItem['thumbnail'] in [None, ""]:
                    pluginDetails['thumbnail'] = 'DefaultAddon.png'
                else:
                    pluginDetails['thumbnail'] = addonItem['thumbnail']

                if addonItem['fanart'] in [None, ""]:
                    pluginDetails['fanart'] = FANART
                else:
                    pluginDetails['fanart'] = addonItem['fanart']

                plugins.append(pluginDetails)
        return plugins

    # get the list of plugins installed on the system
    def _setFileSourceList(self):
        # Make the call to find out all the addons that are installed
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetSources", "params": { "media": "video" }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log(json_response)
        fileSources = []
        if ("result" in json_response) and ('sources' in json_response['result']):
            # Check each of the plugins that are installed on the system
            for fileSource in json_response['result']['sources']:
                fileDetails = {}
                fileDetails['title'] = fileSource['label']
                fileDetails['dbid'] = fileSource['file']
                fileDetails['thumbnail'] = 'DefaultFolder.png'
                fileDetails['fanart'] = FANART

                fileSources.append(fileDetails)
        return fileSources

    # Display the classification details
    def _setClassificationList(self, type="", subtype=""):
        classifications = ()
        securityDetails = {}

        # Make the call to the DB to get all the specific security settings
        pinDB = PinSentryDB()

        if type == MenuNavigator.CLASSIFICATIONS_MOVIES:
            classifications = Settings.movieCassificationsNames
            securityDetails = pinDB.getAllMovieClassificationSecurity()
        elif type == MenuNavigator.CLASSIFICATIONS_TV:
            classifications = Settings.tvCassificationsNames
            securityDetails = pinDB.getAllTvClassificationSecurity()

        del pinDB

        # Check if we are showing the root classification listing
        if type in [None, ""]:
            url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.CLASSIFICATIONS, 'type': MenuNavigator.CLASSIFICATIONS_MOVIES})
            li = xbmcgui.ListItem(ADDON.getLocalizedString(32207), iconImage=ICON)
            li.setProperty("Fanart_Image", FANART)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

            url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.CLASSIFICATIONS, 'type': MenuNavigator.CLASSIFICATIONS_TV})
            li = xbmcgui.ListItem(ADDON.getLocalizedString(32208), iconImage=ICON)
            li.setProperty("Fanart_Image", FANART)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)
        elif subtype in [None, ""]:
            # Get all the different language that are supported
            languages = []
            for classification in classifications:
                if classification['lang'] not in languages:
                    languages.append(classification['lang'])

            # Check to see if we can sort all the entries alphabetically for the given language
            try:
                languages = sorted(languages, key=ADDON.getLocalizedString)
            except:
                # If it fails to sort, then we just list them unsorted
                log("PinSentryPlugin: Failed to sort language list")

            # Now print out the item for each language
            for lang in languages:
                url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.CLASSIFICATIONS, 'type': type, 'subtype': str(lang)})

                iconImage = ICON
                for flag in Settings.flags:
                    if flag['lang'] == lang:
                        iconImage = os_path_join(ICON_DIR, flag['icon'])

                li = xbmcgui.ListItem(ADDON.getLocalizedString(lang), iconImage=iconImage)
                li.setProperty("Fanart_Image", FANART)
                li.addContextMenuItems([], replaceItems=True)
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)
        else:
            for classification in classifications:
                # Check if we are looking for a specific country
                if subtype != str(classification['lang']):
                    continue

                fullName = classification['name'] % ADDON.getLocalizedString(classification['lang'])
                idStr = str(classification['id'])
                securityLevel = 0
                if idStr in securityDetails:
                    securityLevel = securityDetails[idStr]
                    log("PinSentryPlugin: Classification %s has security level %d" % (fullName, securityLevel))

                # Set the icon to the certificate one if available
                iconImage = ICON
                if classification['icon'] not in [None, ""]:
                    iconImage = os_path_join(ICON_DIR, classification['icon'])

                li = xbmcgui.ListItem(fullName, iconImage=iconImage)

                # Add a tick if security is set
                if securityLevel > 0:
                    li.setInfo('video', {'PlayCount': 1})

                li.setProperty("Fanart_Image", FANART)
                li.addContextMenuItems([], replaceItems=True)
                url = self._build_url({'mode': 'setsecurity', 'type': type, 'id': classification['id'], 'title': classification['match'], 'level': securityLevel})
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Set the security value for a given video
    def setSecurity(self, type, title, id, oldLevel, classBlocked=False, forceLevel=None):
        log("Setting security for (id:%s) %s" % (id, title))

        level = 1

        # Check if we need to prompt the user or the new security level has been supplied
        if forceLevel is None:
            # Set the new security level to be used
            if oldLevel > 0:
                # Default is to disable it if it was enabled
                level = 0

            numLevels = Settings.getNumberOfLevels()
            if numLevels > 1 or classBlocked:
                # Need to prompt the user to see which pin they are trying to set
                displayNameList = []
                # Add the option to turn it off
                displayNameList.append("%s %s" % (ADDON.getLocalizedString(32211), ADDON.getLocalizedString(32013)))
                for i in range(1, numLevels + 1):
                    secLevStr = str(i)
                    if numLevels < 2:
                        # If there is only one security level, use "On" rather than the number
                        secLevStr = ADDON.getLocalizedString(32014)
                    displayString = "%s %s" % (ADDON.getLocalizedString(32211), secLevStr)
                    displayNameList.append(displayString)

                # Check if we need the option to disable a classification restriction
                if classBlocked:
                    displayNameList.append(ADDON.getLocalizedString(32212))

                select = xbmcgui.Dialog().select(ADDON.getLocalizedString(32001), displayNameList)

                if select != -1:
                    level = select
                    if classBlocked and (select >= (len(displayNameList) - 1)):
                        level = -1
                    log("Setting security level to %d" % level)
                else:
                    log("Exiting set security as no level selected")
                    return
        else:
            level = forceLevel

        # This could take a little time to set the value so show the busy dialog
        xbmc.executebuiltin("ActivateWindow(busydialog)")

        if title not in [None, ""]:
            pinDB = PinSentryDB()
            if type == MenuNavigator.TVSHOWS:
                # Set the security level for this title, setting it to zero
                # will result in the entry being removed from the database
                # as the default for an item is unset
                pinDB.setTvShowSecurityLevel(title, int(id), level)
            elif type == MenuNavigator.MOVIES:
                pinDB.setMovieSecurityLevel(title, int(id), level)
            elif type == MenuNavigator.MOVIESETS:
                pinDB.setMovieSetSecurityLevel(title, int(id), level)
                # As well as setting the security on the Movie set, we need
                # to also set it on each movie in the Movie Set
                self._setSecurityOnMoviesInMovieSets(int(id), level)
            elif type == MenuNavigator.MUSICVIDEOS:
                pinDB.setMusicVideoSecurityLevel(title, int(id), level)
            elif type == MenuNavigator.PLUGINS:
                pinDB.setPluginSecurityLevel(title, id, level)
            elif type == MenuNavigator.FILESOURCE:
                pinDB.setFileSourceSecurityLevel(title, id, level)
            elif type == MenuNavigator.CLASSIFICATIONS_MOVIES:
                pinDB.setMovieClassificationSecurityLevel(id, title, level)
            elif type == MenuNavigator.CLASSIFICATIONS_TV:
                pinDB.setTvClassificationSecurityLevel(id, title, level)
            del pinDB
        else:
            # Handle the bulk operations like set All security for the movies
            self._setBulkSecurity(type, level)

        xbmc.executebuiltin("Dialog.Close(busydialog)")
        xbmc.executebuiltin("Container.Refresh")

    # Sets the security details on all the Movies in a given Movie Set
    def _setSecurityOnMoviesInMovieSets(self, setid, level):
        log("Setting security for movies in movie set %d" % setid)
        # Get all the movies in the movie set
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSetDetails", "params": { "setid": %d, "properties": ["title"] }, "id": 1}' % setid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log(json_response)
        if ("result" in json_response) and ('setdetails' in json_response['result']):
            if 'movies' in json_response['result']['setdetails']:
                for item in json_response['result']['setdetails']['movies']:
                    # Now set the security on the movies in the set
                    self.setSecurity(MenuNavigator.MOVIES, item['label'], item['movieid'], level, forceLevel=level)
        return

    # Performs an operation on all the elements of a given type
    def _setBulkSecurity(self, type, level):
        items = self._getVideos(type)
        for item in items:
            # Get the title of the video
            title = item['title']
            try:
                title = item['title'].encode("utf-8")
            except:
                log("PinSentryPlugin: setBulkSecurity Failed to encode title %s" % title)
            self.setSecurity(type, title, item['dbid'], level, forceLevel=level)

    # Construct the context menu
    def _getContextMenu(self, type):
        ctxtMenu = []

        if type in [MenuNavigator.TVSHOWS, MenuNavigator.MOVIES, MenuNavigator.MOVIESETS, MenuNavigator.MUSICVIDEOS]:
            # Clear All Security
            cmd = self._build_url({'mode': 'setsecurity', 'level': 0, 'type': type, 'forceLevel': 0})
            ctxtMenu.append((ADDON.getLocalizedString(32209), 'RunPlugin(%s)' % cmd))

            # Apply Security To All
            cmd = self._build_url({'mode': 'setsecurity', 'level': 1, 'type': type})
            ctxtMenu.append((ADDON.getLocalizedString(32210), 'RunPlugin(%s)' % cmd))

        return ctxtMenu


################################
# Main of the PinSentry Plugin
################################
if __name__ == '__main__':
    # If we have been called from the settings screen make sure that all the
    # dialogs (like the Addon Information Dialog) are closed
    if xbmc.getCondVisibility("Window.IsActive(10146)"):
        xbmc.executebuiltin("Dialog.Close(all, true)", True)

    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, files in our case
    xbmcplugin.setContent(addon_handle, 'files')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("PinSentryPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("PinSentryPlugin: Mode is NONE - showing root menu")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.showRootMenu()
        del menuNav

    elif mode[0] == 'folder':
        log("PinSentryPlugin: Mode is FOLDER")

        # Get the actual folder that was navigated to
        foldername = args.get('foldername', None)
        type = args.get('type', None)
        subtype = args.get('subtype', None)

        if (foldername is not None) and (len(foldername) > 0):
            type1 = ""
            if (type is not None) and (len(type) > 0):
                type1 = type[0]
            subtype1 = ""
            if (subtype is not None) and (len(subtype) > 0):
                subtype1 = subtype[0]

            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.showFolder(foldername[0], type1, subtype1)
            del menuNav

    elif mode[0] == 'setsecurity':
        log("PinSentryPlugin: Mode is SET SECURITY")

        # Get the actual details of the selection
        type = args.get('type', None)
        title = args.get('title', None)
        level = args.get('level', None)
        id = args.get('id', None)
        classificationBlocked = args.get('classificationBlocked', None)
        forceLevel = args.get('forceLevel', None)

        if (type is not None) and (len(type) > 0):
            log("PinSentryPlugin: Type to set security for %s" % type[0])
            secTitle = ""
            if (title is not None) and (len(title) > 0):
                secTitle = title[0]
            secLevel = 0
            if (level is not None) and (len(level) > 0):
                secLevel = int(level[0])
            dbid = ""
            if (id is not None) and (len(id) > 0):
                dbid = id[0]
            classBlocked = False
            if (classificationBlocked is not None) and (len(classificationBlocked) > 0):
                if classificationBlocked[0] == str(True):
                    classBlocked = True
            forceLevelVal = None
            if (forceLevel is not None) and (len(forceLevel) > 0):
                forceLevelVal = int(forceLevel[0])

            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.setSecurity(type[0], secTitle, dbid, secLevel, classBlocked, forceLevelVal)
            del menuNav

    elif mode[0] == 'forcepin':
        log("PinSentryPlugin: Mode is FORCE PIN")
        xbmcgui.Window(10000).setProperty("PinSentryPrompt", "true")

    elif mode[0] == 'setclassification':
        log("PinSentryPlugin: Mode is SET CLASSIFICATION")

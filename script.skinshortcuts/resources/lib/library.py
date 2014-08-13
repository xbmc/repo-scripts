# coding=utf-8
import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
import thread
from xml.dom.minidom import parse
from xml.sax.saxutils import escape as escapeXML
from traceback import print_exc
from unidecode import unidecode

import datafunctions
DATA = datafunctions.DataFunctions()

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = sys.modules[ "__main__" ].__addon__
__addonid__      = sys.modules[ "__main__" ].__addonid__
__addonversion__ = sys.modules[ "__main__" ].__addonversion__
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ )
__datapathalt__  = os.path.join( "special://profile/", "addon_data", __addonid__ )
__skinpath__     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')
__defaultpath__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'shortcuts').encode("utf-8") ).decode("utf-8")
__language__     = sys.modules[ "__main__" ].__language__
__cwd__          = sys.modules[ "__main__" ].__cwd__
__xbmcversion__  = xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0]

def log(txt):
    if __xbmcversion__ == "13" or __addon__.getSetting( "enable_logging" ) == "true":
        try:
            if isinstance (txt,str):
                txt = txt.decode('utf-8')
            message = u'%s: %s' % (__addonid__, txt)
            xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)
        except:
            pass

class LibraryFunctions():
    def __init__( self, *args, **kwargs ):
        
        # values to mark whether data from different areas of the library have been loaded
        self.loadedCommon = False
        self.loadedMoreCommands = False
        self.loadedVideoLibrary = False
        self.loadedMusicLibrary = False
        self.loadedLibrarySources = False
        self.loadedPVRLibrary = False
        self.loadedRadioLibrary = False
        self.loadedPlaylists = False
        self.loadedAddOns = False
        self.loadedFavourites = False
        self.loadedUPNP = False
        self.loadedSettings = False
        
        self.widgetPlaylistsList = []
        
        # Empty dictionary for different shortcut types
        self.dictionaryGroupings = {"common":None, "commands":None, "video":None, "movie":None, "movie-flat":None, "tvshow":None, "tvshow-flat":None, "musicvideo":None, "musicvideo-flat":None, "customvideonode":None, "customvideonode-flat":None, "videosources":None, "pvr":None, "radio":None, "pvr-tv":None, "pvr-radio":None, "music":None, "musicsources":None, "picturesources":None, "playlist-video":None, "playlist-audio":None, "addon-program":None, "addon-video":None, "addon-audio":None, "addon-image":None, "favourite":None, "settings":None }
        self.folders = {}
        self.foldersCount = 0
        
        self.useDefaultThumbAsIcon = None
        
    def loadLibrary( self ):
        # Load all library data, for use with threading
        self.common()
        self.more()
        self.videolibrary()
        self.musiclibrary()
        self.pvrlibrary()
        self.radiolibrary()
        self.librarysources()
        self.playlists()
        self.addons()                
        self.favourites()
        self.settings()
        
        # Do a JSON query for upnp sources (so that they'll show first time the user asks to see them)
        if self.loadedUPNP == False:
            json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Files.GetDirectory", "params": { "properties": ["title", "file", "thumbnail"], "directory": "upnp://", "media": "files" } }')
            self.loadedUPNP = True

    # ==============================================
    # === BUILD/DISPLAY AVAILABLE SHORTCUT NODES ===
    # ==============================================
    
    def retrieveGroup( self, group, flat = True ):
        trees = [DATA._get_overrides_skin(), DATA._get_overrides_script()]
        nodes = None
        for tree in trees:
            if tree is not None:
                if flat:
                    nodes = tree.find( "flatgroupings" )
                    if nodes is not None:
                        nodes = nodes.findall( "node" )
                else:
                    nodes = tree.find( "groupings" )
            if nodes is not None:
                break                
                
        if nodes is None:
            return [ "Error", [] ]
            
        returnList = []
        
        if flat:
            # Flat groupings
            count = 0
            # Cycle through nodes till we find the one specified
            for node in nodes:
                count += 1
                if "condition" in node.attrib:
                    if not xbmc.getCondVisibility( node.attrib.get( "condition" ) ):
                        group += 1
                        continue
                if "version" in node.attrib:
                    if __xbmcversion__ != node.attrib.get( "version" ):
                        group += 1
                        continue
                if count == group:
                    # We found it :)
                    return( node.attrib.get( "label" ), self.buildNodeListing( node, True ) )
                    for subnode in node:
                        if subnode.tag == "content":
                            returnList = returnList + self.retrieveContent( subnode.text )
                        if subnode.tag == "shortcut":
                            returnList.append( self._create( [subnode.text, subnode.attrib.get( "label" ), subnode.attrib.get( "type" ), {"icon": subnode.attrib.get( "icon" )}] ) )

                    return [node.attrib.get( "label" ), returnList]
                    
            return ["Error", []]
            
        else:
            # Heirachical groupings
            if group == "":
                # We're going to get the root nodes
                return [ __language__(32048), self.buildNodeListing( nodes, False ) ]
            else:
                groups = group.split( "," )
                
                nodes = [ "", nodes ]
                for groupNum in groups:
                    nodes = self.getNode( nodes[1], int( groupNum ) )
                    
                return [ nodes[0], self.buildNodeListing( nodes[1], False ) ]
                        
    def getNode( self, tree, number ):
        count = 0
        for subnode in tree:
            count += 1
            # If not visible, skip it
            if "condition" in subnode.attrib:
                if not xbmc.getCondVisibility( subnode.attrib.get( "condition" ) ):
                    number += 1
                    continue
            if "version" in subnode.attrib:
                if __xbmcversion__ != subnode.attrib.get( "version" ):
                    number += 1
                    continue

            if count == number:
                label = DATA.local( subnode.attrib.get( "label" ) )[2]
                return [ label, subnode ]
                
    def buildNodeListing( self, nodes, flat ):
        returnList = []
        count = 0
        for node in nodes:
            if "condition" in node.attrib:
                if not xbmc.getCondVisibility( node.attrib.get( "condition" ) ):
                    continue
            if "version" in node.attrib:
                if __xbmcversion__ != node.attrib.get( "version" ):
                    continue
            count += 1
            if node.tag == "content":
                returnList = returnList + self.retrieveContent( node.text )
            if node.tag == "shortcut":
                returnList.append( self._create( [node.text, node.attrib.get( "label" ), node.attrib.get( "type" ), {"icon": node.attrib.get( "icon" )}] ) )
            if node.tag == "node" and flat == False:
                returnList.append( self._create( ["||NODE||" + str( count ), node.attrib.get( "label" ), "", {"icon": "DefaultFolder.png"}] ) )
                
        return returnList
                
    def retrieveContent( self, content ):
        if content == "upnp-video":
            items = [ self._create(["||UPNP||", "32070", "32069", {"icon": "DefaultFolder.png"}]) ]
        elif content == "upnp-music":
            items = [ self._create(["||UPNP||", "32070", "32073", {"icon": "DefaultFolder.png"}]) ]
            
        elif self.dictionaryGroupings[ content ] is None:
            # The data hasn't been loaded yet
            items = self.loadGrouping( content )
        else:
            items = self.dictionaryGroupings[ content ]

        if items is not None:
            items = self.checkForFolder( items )
        else:
            items = []
            
        # Check for any icon overrides for these items
        tree = DATA._get_overrides_skin()
        if tree is None:
            return items
            
        for item in items:
            item = self._get_icon_overrides( tree, item, content )
            
        return items
            
    def checkForFolder( self, items ):
        # This function will check for any folders in the listings that are being returned
        # and, if found, move their sub-items into a property
        returnItems = []
        for item in items:
            if isinstance( item, list ):
                self.foldersCount += 1
                self.folders[ str( self.foldersCount ) ] = item[1]
                newItem = item[0]
                newItem.setProperty( "folder", str( self.foldersCount ) )
                returnItems.append( newItem )
            else:
                returnItems.append( item )
            
        return( returnItems )
        
    def loadGrouping( self, content ):
        # We'll be called if the data for a wanted group hasn't been loaded yet
        if content == "common":
            self.common()
        if content  == "commands":
            self.more()
        if content == "video" or content == "movie" or content == "tvshow" or content == "musicvideo" or content == "customvideonode" or content == "movie-flat" or content == "tvshow-flat" or content == "musicvideo-flat" or content == "customvideonode-flat":
            self.videolibrary()
        if content == "videosources" or content == "musicsources" or content == "picturesources":
            self.librarysources()
        if content == "music":
            self.musiclibrary()
        if content == "pvr" or content == "pvr-tv" or content == "pvr-radio":
            self.pvrlibrary()
        if content == "radio":
            self.radiolibrary()
        if content == "playlist-video" or content == "playlist-audio":
            self.playlists()
        if content == "addon-program" or content == "addon-video" or content == "addon-audio" or content == "addon-image":
            self.addons()
        if content == "favourite":
            self.favourites()
        if content == "settings":
            self.settings()
            
        # The data has now been loaded, return it
        return self.dictionaryGroupings[ content ]
        
    def flatGroupingsCount( self ):
        # Return how many nodes there are in the the flat grouping
        tree = DATA._get_overrides_script()
        if tree is None:
            return 1
        groupings = tree.find( "flatgroupings" )
        nodes = groupings.findall( "node" )
        count = 0
        for node in nodes:
            if "condition" in node.attrib:
                if not xbmc.getCondVisibility( node.attrib.get( "condition" ) ):
                    continue
            if "version" in node.attrib:
                if __xbmcversion__ != node.attrib.get( "version" ):
                    continue
                    
            count += 1
                
        return count
        
    
    def addToDictionary( self, group, content ):
        # This function adds content to the dictionaryGroupings - including
        # adding any skin-provided shortcuts to the group
        tree = DATA._get_overrides_skin()
        if tree is None:
            # There are no overrides to check for extra shortcuts
            self.dictionaryGroupings[ group ] = content
            return
            
        # Search for skin-provided shortcuts for this group
        originalGroup = group
        if group.endswith( "-flat" ):
            group = group.replace( "-flat", "" )
            
        if group != "movie" and group != "tvshow" and group != "musicvideo":
            for elem in tree.findall( "shortcut" ):
                if "grouping" in elem.attrib:
                    if group == elem.attrib.get( "grouping" ):
                        # We want to add this shortcut
                        label = elem.attrib.get( "label" )
                        type = elem.attrib.get( "type" )
                        thumb = elem.attrib.get( "thumbnail" )
                        icon = elem.attrib.get( "icon" )
                        
                        action = elem.text
                        
                        #if label.isdigit():
                        #    label = "::LOCAL::" + label
                            
                        if type is None:
                            type = "32024"
                        #elif type.isdigit():
                        #    type = "::LOCAL::" + type
                        
                        if icon is None:
                            icon = ""
                        if thumb is None:
                            thumb = ""

                        listitem = self._create( [action, label, type, {"icon": icon, "thumb": thumb}] )
                        
                        if "condition" in elem.attrib:
                            if xbmc.getCondVisibility( elem.attrib.get( "condition" ) ):
                                content.insert( 0, listitem )
                        else:
                            content.insert( 0, listitem )

                elif group == "common":
                    # We want to add this shortcut
                    label = elem.attrib.get( "label" )
                    type = elem.attrib.get( "type" )
                    thumb = elem.attrib.get( "thumbnail" )
                    icon = elem.attrib.get( "icon" )
                    
                    action = elem.text
                    
                    #if label.isdigit():
                    #    label = "::LOCAL::" + label
                        
                    if type is None:
                        type = "32024"
                    #elif type.isdigit():
                    #    type = "::LOCAL::" + type
                        
                    if type is None or type == "":
                        type = "Skin Provided"
                        
                    if icon is None:
                        icon = ""
                        
                    if thumb is None:
                        thumb = ""

                    listitem = self._create( [action, label, type, {"icon": icon, "thumb":thumb}] )
                    
                    if "condition" in elem.attrib:
                        if xbmc.getCondVisibility( elem.attrib.get( "condition" ) ):
                            content.append( listitem )
                    else:
                        content.append( listitem )
                    
        self.dictionaryGroupings[ originalGroup ] = content
        
    # ================================
    # === BUILD AVAILABLE SHORTCUT ===
    # ================================
    
    def _create ( self, item, allowOverrideLabel = True ):         
        # Retrieve label
        localLabel = DATA.local( item[1] )[0]
        
        # Create localised label2
        displayLabel2 = DATA.local( item[2] )[2]
        shortcutType = DATA.local( item[2] )[0]
        
        if allowOverrideLabel:
            # Check for a replaced label
            replacementLabel = DATA.checkShortcutLabelOverride( item[0] )
            if replacementLabel is not None:
                
                localLabel = DATA.local( replacementLabel[0] )[0]
                    
                if len( replacementLabel ) == 2:
                    # We're also overriding the type
                    displayLabel2 = DATA.local( replacementLabel[1] )[2]
                    shortcutType = DATA.local( replacementLabel[1] )[0]
                    
        
        # Try localising it
        displayLabel = DATA.local( localLabel )[2]
        labelID = DATA.createNiceName( DATA.local( localLabel )[0] )
        
        # Create localised label2
        displayLabel2 = DATA.local( displayLabel2 )[2]
        shortcutType = DATA.local( shortcutType )[0]
            
        # If this launches our explorer, append a notation to the displayLabel
        if item[0].startswith( "||" ):
            displayLabel = displayLabel + "  >"
            
        # Retrieve icon and thumbnail
        if item[3]:
            if "icon" in item[3].keys():
                icon = item[3]["icon"]
            else:
                icon = "DefaultShortcut.png"
            if "thumb" in item[3].keys():
                thumbnail = item[3]["thumb"]
            else:
                thumbnail = None
        else:
            icon = "DefaultShortcut.png"
            thumbnail = None
            
        # Check if the option to use the thumb as the icon is enabled
        if self.useDefaultThumbAsIcon is None:
            # Retrieve the choice from the overrides.xml
            tree = DATA._get_overrides_skin()
            if tree is None:
                self.useDefaultThumbAsIcon = False
            else:
                node = tree.getroot().find( "useDefaultThumbAsIcon" )
                if node is None:
                    self.useDefaultThumbAsIcon = False
                else:
                    if node.text.lower() == "true":
                        self.useDefaultThumbAsIcon = True
                    else:
                        self.useDefaultThumbAsIcon = False
            
        usedDefaultThumbAsIcon = False
        if self.useDefaultThumbAsIcon == True and thumbnail is not None:            
            icon = thumbnail
            thumbnail = None
            usedDefaultThumbAsIcon = True
            
        oldicon = None
        
        # Get a temporary labelID
        DATA._clear_labelID()
        labelID = DATA._get_labelID( labelID, item[0] )
                        
        # If the skin doesn't have the icon, replace it with DefaultShortcut.png
        if not icon or not xbmc.skinHasImage( icon ):
            if not usedDefaultThumbAsIcon:
                icon = "DefaultShortcut.png"
            
        # Build listitem
        if thumbnail is not None:
            listitem = xbmcgui.ListItem(label=displayLabel, label2=displayLabel2, iconImage=icon, thumbnailImage=thumbnail)
            listitem.setProperty( "thumbnail", thumbnail)
        else:
            listitem = xbmcgui.ListItem(label=displayLabel, label2=displayLabel2, iconImage=icon)
        listitem.setProperty( "path", item[0] )
        listitem.setProperty( "localizedString", localLabel )
        listitem.setProperty( "shortcutType", shortcutType )
        listitem.setProperty( "icon", icon )
        listitem.setProperty( "tempLabelID", labelID )
        listitem.setProperty( "defaultLabel", labelID )
        
        return( listitem )
                
    def _get_icon_overrides( self, tree, item, content, setToDefault = True ):
        if tree is None:
            return item
            
        oldicon = None
        newicon = item.getProperty( "icon" )
        for elem in tree.findall( "icon" ):
            if oldicon is None:
                if ("labelID" in elem.attrib and elem.attrib.get( "labelID" ) == item.getProperty( "tempLabelID" )) or ("image" in elem.attrib and elem.attrib.get( "image" ) == item.getProperty( "icon" )):
                    # LabelID matched
                    if "grouping" in elem.attrib:
                        if elem.attrib.get( "grouping" ) == content:
                            # Group also matches - change icon
                            oldicon = item.getProperty( "icon" )
                            newicon = elem.text
                    elif "group" not in elem.attrib:
                        # No group - change icon
                        oldicon = item.getProperty( "icon" )
                        newicon = elem.text
                        
        # If the icon doesn't exist, set icon to default
        setDefault = False
        if not xbmc.skinHasImage( newicon ) and setToDefault == True:
            oldicon = item.getProperty( "icon" )
            icon = "DefaultShortcut.png"
            setDefault == True

        if oldicon is not None:
            # we found an icon override
            item.setProperty( "icon", newicon )
            item.setIconImage( newicon )
            
        if setDefault == True:
            item = self._get_icon_overrides( tree, item, content, False )
            
        return item

    # ===================================
    # === LOAD VIDEO LIBRARY HEIRACHY ===
    # ===================================
    
    def videolibrary( self ):
        if self.loadedVideoLibrary == True:
            # The List has already been populated, return it
            return self.loadedVideoLibrary
        elif self.loadedVideoLibrary == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedVideoLibrary == True:
                    return self.loadedVideoLibrary
        else:
            # We're going to populate the list
            self.loadedVideoLibrary = "Loading"
            
        # Try loading custom nodes first
        try:
            if self._parse_videolibrary( "custom" ) == False:
                self._parse_videolibrary( "default" )
        except:
            log( "Failed to load custom video nodes" )
            print_exc()
            try:
                # Try loading default nodes
                self._parse_videolibrary( "default" )
            except:
                # Empty library
                log( "Failed to load default video nodes" )
                print_exc()
                
        self.loadedVideoLibrary = True
        return self.loadedVideoLibrary
        
    def _parse_videolibrary( self, type ):
        #items = {"video":[], "movies":[], "tvshows":[], "musicvideos":[], "custom":{}}
        items = {}

        rootdir = os.path.join( xbmc.translatePath( "special://profile".decode('utf-8') ), "library", "video" )
        if type == "custom":
            log('Listing custom video nodes...')
        else:
            rootdir = os.path.join( xbmc.translatePath( "special://xbmc".decode('utf-8') ), "system", "library", "video" )
            log( "Listing default video nodes..." )

        # Check the path exists
        if not os.path.exists( rootdir ):
            log( "No nodes found" )
            return False
            
        directories = []
        # Process the root directory (VIDEOS)
        for root, subdirs, files in os.walk( rootdir ):
            type = "video"
            returnVal = self._parse_videonode( rootdir, rootdir, None, True )
            items[ 0 ] = returnVal
            for subdir in subdirs:
                directories.append( os.path.join( rootdir, subdir ) )
            break
                
        for directory in directories:
            returnVal = self._parse_videonode( directory, rootdir )
            
            if returnVal[1] not in items.keys():
                items[ returnVal[1] ] = returnVal
            else:
                count = int( returnVal[1] )
                while count in items.keys():
                    count += 1
                items[ count ] = returnVal
            
        customnodes = None
        customnodesFlat = []
        for item in self._order_dictionary( items ):
            type = item[0]
            
            # item[0] = Type (video, movie, etc)
            # item[1] = The order
            # item[2] = List of items within
            # item[3] = label2
            # item[4] = icon
            
            result = self._create_videonode( self._order_dictionary( item[2] ), item[0], item[3], {"icon": item[4]} )
            
            # Save to the dictionary
            if type == "video":
                self.addToDictionary( "video", result[0] )
            elif type == "movies":
                self.addToDictionary( "movie", result[0] )
                self.addToDictionary( "movie-flat", result[1] )
            elif type == "tvshows":
                self.addToDictionary( "tvshow", result[0] )
                self.addToDictionary( "tvshow-flat", result[1] )
            elif type == "musicvideos":
                self.addToDictionary( "musicvideo", result[0] )
                self.addToDictionary( "musicvideo-flat", result[1] )
            else:
                if customnodes == None:
                    customnodes = result[0]
                    customnodesFlat = result[1]
                else:
                    customnodes = customnodes + result[0]
                    customnodesFlat = customnodesFlat + result[1]
        if customnodes == None:
            customnodes = []
            customnodesFlat = []
        self.addToDictionary( "customvideonode", customnodes )
        self.addToDictionary( "customvideonode-flat", customnodesFlat )
        
    def _parse_videonode( self, directory, rootdir, returnType = None, noSubDirs = False, folderName = None, addShortcuts = False ):
        # This function will iterate through a directory, returning a dictionary of all items, with their
        # key being the order they should be displayed
        returnDict = {}
        unordered = 0
        
        type = returnType
        
        # Add any skin-provided shortcuts for this group (if movies, tv, musicvideo...)
        if addShortcuts and (returnType == "movies" or returnType == "tvshows" or returnType == "musicvideos"):
            if returnType == "movies":
                group = "movie"
            elif returnType == "tvshows":
                group = "tvshow"
            else:
                group = "musicvideo"
                
            tree = DATA._get_overrides_skin()
            if tree is not None:
                for elem in tree.findall( "shortcut" ):
                    if "grouping" in elem.attrib:
                        if group == elem.attrib.get( "grouping" ):
                            # We want to add this shortcut
                            label = elem.attrib.get( "label" )
                            type = elem.attrib.get( "type" )
                            thumb = elem.attrib.get( "thumbnail" )
                            icon = elem.attrib.get( "icon" )
                            
                            action = elem.text
                            
                            if label.isdigit():
                                label = label
                                
                            if type is None:
                                type = "32024"
                            elif type.isdigit():
                                type = type
                                
                            if icon is None:
                                icon = ""
                                
                            if thumb is None:
                                thumb = ""

                            listitem = self._create( [action, label, type, { "icon": icon, "thumb": thumb}] )
                            
                            shouldAdd = False
                            if "condition" in elem.attrib:
                                if xbmc.getCondVisibility( elem.attrib.get( "condition" ) ):
                                    shouldAdd = True
                            else:
                                shouldAdd = True
                                
                            if shouldAdd == True:
                                # Add this listitem to the dictionary we're returning
                                if unordered not in returnDict.keys():
                                    returnDict[ unordered ] = listitem
                                else:
                                    while unordered in returnDict.keys():
                                        unordered += 1
                                    returnDict[ unordered ] = listitem        
        unordered = 100
        
        type = returnType
        
        # Being walking the directory
        for root, subdirs, files in os.walk( directory ):
            if "index.xml" in files:
                tree = xmltree.parse( os.path.join( root, "index.xml" ) )
                label = tree.find( "label" ).text
                
                # If there is no returnType, get the type of links we're looking at
                if returnType is None:
                    if label == "342":
                        # MOVIES
                        type = "movies"
                    elif label == "20343":
                        # TV SHOWS
                        type = "tvshows"
                    elif label == "20389":
                        # MUSIC VIDEOS
                        type = "musicvideos"
                    else:
                        # CUSTOM NODE
                        type = "Custom"
                        
                # Get the label2 (The type of shortcut for items in this directory)
                label2 = label
                #if label.isdigit():
                #    label2 = "::LOCAL::" + label
                #else:
                #    label2 = label
                        
                # Get the order this should appear in
                treeroot = tree.getroot()
                if "order" in treeroot.attrib:
                    order = int( treeroot.attrib.get( "order" ) )
                else:
                    order = unordered
                    unordered += 1
                
                # Get the icon
                icon = tree.find( "icon" ).text
                
                if returnType is None:
                    # If we've not been asked to ignore sub-dirs, we're going to re-call this
                    # directory, which will create links to the files within a directory itself :)
                    returnVal = self._parse_videonode( directory, rootdir, type, addShortcuts = True )
                    if returnVal[0] not in returnDict.keys():
                        returnDict[ returnVal[0] ] = returnVal
                    else:
                        count = int( returnVal[0] )
                        while count in returnDict.keys():
                            count += 1
                            returnDict[ count ] = returnVal
                            
                    return [type, order, returnDict, label2, icon]
            elif noSubDirs == True:
                type = "video"
                label2 = "32014"
                order = unordered
                icon = None
            else:
                # Set some defaults here
                type = "Custom"
                label2 = "custom"
                order = unordered
                icon = None
                        
            for file in files:
                # Parse all the xml files in the directory
                if file.endswith( ".xml" ) and file != "index.xml":
                    try:
                        # Load the file
                        tree = xmltree.parse( os.path.join( root, file ) )
                        treeroot = tree.getroot()
                        
                        # Get the 'order' attribute, or create a new 'order' attribute
                        if "order" in treeroot.attrib:
                            nodeOrder = treeroot.attrib.get( "order" )
                        else:
                            nodeOrder = unordered
                            unordered += 1
                            
                        # Get the label of the item
                        label = tree.find( "label" ).text
                        #if label.isdigit():
                        #    label = "::LOCAL::" + label
                        
                        # Get the itcon
                        nodeicon = tree.find( "icon" ).text
                        
                        # Check if we know a 'pretty' way of accessing this item
                        prettyLink = self._pretty_videonode( file, type, tree )
                        if prettyLink:
                            path = "ActivateWindow(Videos," + prettyLink + ",return)"
                        else:
                            # We don't, create a long path to it
                            path = "ActivateWindow(Videos,library://video/" + os.path.relpath( os.path.join( root, file), rootdir ) + ",return)"
                            path.replace("\\", "/")
                        
                        # Create a listitem to hold this item
                        listitem = self._create( [path, label, label2, { "icon": nodeicon } ] )
                        
                        # Add this listitem to the dictionary we're returning
                        if nodeOrder not in returnDict.keys():
                            returnDict[ nodeOrder ] = listitem
                        else:
                            count = int( nodeOrder )
                            while count in returnDict.keys():
                                count += 1
                            returnDict[ count ] = listitem
                    except:
                        print_exc()
                        pass
                        
            
            if noSubDirs == False:
                for subdir in subdirs:
                    # Call this same function to parse the subdirectory
                    returnVal = self._parse_videonode( os.path.join( directory, subdir ), rootdir, type, folderName = label2 )
                   
                    # Add the result to the dictionary we're returning
                    if returnVal[0] not in returnDict.keys():
                        returnDict[ returnVal[0] ] = returnVal
                    else:
                        count = int( returnVal[0] )
                        while count in returnDict.keys():
                            count += 1
                        returnDict[ count ] = returnVal
                    
            # Break out of the directory walking
            break
            
        # Return our results
        if returnType is None:
            # Include the type
            return [type, order, returnDict, label2, icon]
        else:
            # Don't include the type
            return [order, returnDict, label2, icon]
    
    def _create_videonode( self, inputlist, type, foldername, foldericon, returnList = None, returnListFlat = None ):
        listitemsFlat = returnListFlat
        listitems = []
        if returnList == None:
            # Set up the list we'll save
            listitems = []
            listitemsFlat = []
            
        for item in inputlist:
            if isinstance( item, list ):
                result = self._create_videonode( self._order_dictionary( item[1] ), type, item[2], item[3], listitems, listitemsFlat )
                listitems.append( result[0] )
            else:
                listitems.append( item )
                listitemsFlat.append( item )
                
        if returnList is not None:
            returnList = self._create( ["||FOLDER||", foldername, "", {"icon": foldericon} ] )
            returnList = [returnList, listitems]
        else:
            returnList = listitems
                
        return [returnList, listitemsFlat]
        
    def _pretty_videonode( self, filename, type, tree ):
        # We're going to do lots of matching, to try to figure out the pretty library link
        
        if type == "Custom":
            return False
        
        # Root
        if type == "video":
            if filename == "addons.xml":
                if self._check_videonode( tree, False ):
                    return "Addons"
            elif filename == "files.xml":
                if self._check_videonode( tree, False ):
                    return "Files"
            # elif filename == "inprogressshows.xml": - Don't know a pretty library link for this...
            elif filename == "playlists.xml":
                if self._check_videonode( tree, False ):
                    return "Playlists"
            elif filename == "recentlyaddedepisodes.xml":
                if self._check_videonode( tree, False ):
                    return "RecentlyAddedEpisodes"
            elif filename == "recentlyaddedmovies.xml":
                if self._check_videonode( tree, False ):
                    return "RecentlyAddedMovies"
            elif filename == "recentlyaddedmusicvideos.xml":
                if self._check_videonode( tree, False ):
                    return "RecentlyAddedMusicVideos"
            else:
                return
              
        # For the rest, they should all specify a type, so get that first
        if type == "movies":
            shortcutType = "Movie"
        elif type == "tvshows":
            shortcutType = "TvShow"
        elif type == "musicvideos":
            shortcutType = "MusicVideo"
        else:
            # No shortcut type specified
            return False

        if filename == "actors.xml":    # Movies, TV Shows
            if self._check_videonode( tree, True ):
                return shortcutType + "Actors"
        elif filename == "country.xml":   # Movies
            if self._check_videonode( tree, True ):
                return shortcutType + "Countries"
        elif filename == "directors.xml": # Movies
            if self._check_videonode( tree, True ):
                return shortcutType + "Directors"
        elif filename == "genres.xml":    # Movies, Music Videos, TV Shows
            if self._check_videonode( tree, True ):
                return shortcutType + "Genres"
        elif filename == "sets.xml":      # Movies
            if self._check_videonode( tree, True ):
                return shortcutType + "Sets"
        elif filename == "studios.xml":   # Movies, Music Videos, TV Shows
            if self._check_videonode( tree, True ):
                return shortcutType + "Studios"
        elif filename == "tags.xml":      # Movies, Music Videos, TV Shows
            if self._check_videonode( tree, True ):
                return shortcutType + "Tags"
        elif filename == "titles.xml":    # Movies, Music Videos, TV Shows
            if self._check_videonode( tree, True ):
                return shortcutType + "Titles"
        elif filename == "years.xml":     # Movies, Music Videos, TV Shows
            if self._check_videonode( tree, True ):
                return shortcutType + "Years"
        elif filename == "albums.xml":    # Music Videos
            if self._check_videonode( tree, True ):
                return shortcutType + "Albums"
        elif filename == "artists.xml":   # Music Videos
            if self._check_videonode( tree, True ):
                return shortcutType + "Artists"
        elif filename == "directors.xml": # Music Videos
            if self._check_videonode( tree, True ):
                return shortcutType + "Directors"

        # If we get here, we couldn't find a pretty link
        return False    
    
    def _order_dictionary( self, dictionary ):
        returnArray = []
        for key in sorted(dictionary.iterkeys()):
            returnArray.append( dictionary[ key ] )
            
        return returnArray

    def _check_videonode( self, tree, checkPath ):
        # Check a video node for custom entries
        if checkPath == False:
            if tree.find( 'match' ) is not None or tree.find( 'rule' ) is not None or tree.find( 'limit' ) is not None:
                return False
            else:
                return True
        else:
            if tree.find( 'match' ) is not None or tree.find( 'rule' ) is not None or tree.find( 'limit' ) is not None or tree.find( 'path' ) is not None:
                return False
            else:
                return True
    

    # ============================
    # === LOAD OTHER LIBRARIES ===
    # ============================
                
    def common( self ):
        if self.loadedCommon == True:
            return True
        elif self.loadedCommon == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedCommon == True:
                    return True
        else:
            # We're going to populate the list
            self.loadedCommon = "Loading"
        
        listitems = []
        log('Listing xbmc common items...')
        
        # Videos, Movies, TV Shows, Live TV, Music, Music Videos, Pictures, Weather, Programs,
        # Play dvd, eject tray
        # Settings, File Manager, Profiles, System Info
        try:
            listitems.append( self._create(["ActivateWindow(Videos)", "10006", "32034", {"icon": "DefaultVideo.png"} ]) )
            listitems.append( self._create(["ActivateWindow(Videos,MovieTitles,return)", "342", "32034", {"icon": "DefaultMovies.png"} ]) )
            listitems.append( self._create(["ActivateWindow(Videos,TVShowTitles,return)", "20343", "32034", {"icon": "DefaultTVShows.png"} ]) )

            if __xbmcversion__ == "13":
                listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,34,0 ,13,0)", "32022", "32034", {"icon": "DefaultTVShows.png"} ]) )
            else:
                listitems.append( self._create(["ActivateWindow(TVGuide)", "32022", "32034", {"icon": "DefaultTVShows.png"} ]) )
                listitems.append( self._create(["ActivateWindow(RadioGuide)", "32087", "32034", {"icon": "DefaultTVShows.png"} ]) )
                
            listitems.append( self._create(["ActivateWindow(Music)", "10005", "32034", {"icon": "DefaultMusicAlbums.png"} ]) )
            listitems.append( self._create(["ActivateWindow(Videos,MusicVideos,return)", "20389", "32034", {"icon": "DefaultMusicVideos.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(Pictures)", "10002", "32034", {"icon": "DefaultPicture.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(Weather)", "12600", "32034", {} ]) )
            listitems.append( self._create(["ActivateWindow(Programs,Addons,return)", "10001", "32034", {"icon": "DefaultProgram.png"} ] ) )

            listitems.append( self._create(["XBMC.PlayDVD()", "32032", "32034", {"icon": "DefaultDVDFull.png"} ] ) )
            listitems.append( self._create(["EjectTray()", "32033", "32034", {"icon": "DefaultDVDFull.png"} ] ) )
                    
            listitems.append( self._create(["ActivateWindow(Settings)", "10004", "32034", {} ]) )
            listitems.append( self._create(["ActivateWindow(FileManager)", "7", "32034", {"icon": "DefaultFolder.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(Profiles)", "13200", "32034", {"icon": "UnknownUser.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(SystemInfo)", "10007", "32034", {} ]) )
            
            listitems.append( self._create(["ActivateWindow(Favourites)", "1036", "32034", {} ]) )
        except:
            log( "Failed to load common XBMC shortcuts" )
            print_exc()
            listitems = []
            
        self.addToDictionary( "common", listitems )
        
        self.loadedCommon = True
        
        return self.loadedCommon
        
    def more( self ):
        if self.loadedMoreCommands == True:
            # The List has already been populated, return it
            return True
        elif self.loadedMoreCommands == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedMoreCommands == True:
                    return True
        else:
            # We're going to populate the list
            self.loadedMoreCommands = "Loading"

        try:
            listitems = []
            log( 'Listing more XBMC commands...' )
            
            listitems.append( self._create(["Reboot", "13013", "32054", {} ]) )
            listitems.append( self._create(["ShutDown", "13005", "32054", {} ]) )
            listitems.append( self._create(["PowerDown", "13016", "32054", {} ]) )
            listitems.append( self._create(["Quit", "13009", "32054", {} ]) )
            listitems.append( self._create(["Hibernate", "13010", "32054", {} ]) )
            listitems.append( self._create(["Suspend", "13011", "32054", {} ]) )
            listitems.append( self._create(["ActivateScreensaver", "360", "32054", {} ]) )
            listitems.append( self._create(["Minimize", "13014", "32054", {} ]) )

            listitems.append( self._create(["Mastermode", "20045", "32054", {} ]) )
            
            listitems.append( self._create(["RipCD", "600", "32054", {} ]) )
            
            listitems.append( self._create(["UpdateLibrary(video)", "32046", "32054", {} ]) )
            listitems.append( self._create(["UpdateLibrary(music)", "32047", "32054", {} ]) )
            listitems.append( self._create(["CleanLibrary(video)", "32055", "32054", {} ]) )
            listitems.append( self._create(["CleanLibrary(music)", "32056", "32054", {} ]) )
            
            self.addToDictionary( "commands", listitems )
        except:
            log( "Failed to load more XBMC commands" )
            print_exc()
            
        self.loadedMoreCommands = True
        return self.loadedMoreCommands
        
    def settings( self ):
        if self.loadedSettings == True:
            # The List has already been populated, return it
            return True
        elif self.loadedSettings == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedSettings == True:
                    return True
        else:
            # We're going to populate the list
            self.loadedSettings = "Loading"

        try:
            listitems = []
            log( 'Listing XBMC settings...' )
            
            listitems.append( self._create(["ActivateWindow(Settings)", "10004", "10004", {} ]) )
            
            listitems.append( self._create(["ActivateWindow(AppearanceSettings)", "480", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(VideosSettings)", "3", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(PVRSettings)", "19020", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(MusicSettings)", "2", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(PicturesSettings)", "1", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(WeatherSettings)", "8", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(AddonBrowser)", "24001", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(ServiceSettings)", "14036", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(SystemSettings)", "13000", "10004", {} ]) )
            listitems.append( self._create(["ActivateWindow(SkinSettings)", "20077", "10004", {} ]) )
            
            self.addToDictionary( "settings", listitems )
        except:
            log( "Failed to load more XBMC settings" )
            print_exc()
            
        self.loadedSettings = True
        return self.loadedSettings
        
    
    def pvrlibrary( self ):
        if self.loadedPVRLibrary == True:
            # The List has already been populated, return it
            return self.loadedPVRLibrary
        elif self.loadedPVRLibrary == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedPVRLibrary == True:
                    return self.loadedPVRLibrary
        else:
            # We're going to populate the list
            self.loadedPVRLibrary = "Loading"

        try:
            listitems = []
            log('Listing pvr library...')
            
            # PVR
            if __xbmcversion__ == "13":
                listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,32,0 ,11,0)", "19023", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,33,0 ,12,0)", "19024", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,31,0 ,10,0)", "19069", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,34,0 ,13,0)", "19163", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,35,0 ,14,0)", "32023", "32017", {"icon": "DefaultTVShows.png"} ] ) )

                listitems.append( self._create(["PlayPvrTV", "32066", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["PlayPvrRadio", "32067", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["PlayPvr", "32068", "32017", {"icon": "DefaultTVShows.png"} ] ) )
            else:
                listitems.append( self._create(["ActivateWindow(TVChannels)", "19019", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["ActivateWindow(TVGuide)", "22020", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["ActivateWindow(TVRecordings)", "19163", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["ActivateWindow(TVTimers)", "19040", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["ActivateWindow(TVSearch)", "137", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                
                listitems.append( self._create(["PlayPvrTV", "32066", "32017", {"icon": "DefaultTVShows.png"} ] ) )
                listitems.append( self._create(["PlayPvr", "32068", "32017", {"icon": "DefaultTVShows.png"} ] ) )

            self.addToDictionary( "pvr", listitems )            
            
            # Add tv channels
            listitems = []
            json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "PVR.GetChannels", "params": { "channelgroupid": "alltv", "properties": ["thumbnail", "channeltype", "hidden", "locked", "channel", "lastplayed"] } }')
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            
            # Add all directories returned by the json query
            if json_response.has_key('result') and json_response['result'].has_key('channels') and json_response['result']['channels'] is not None:
                for item in json_response['result']['channels']:
                    listitems.append( self._create(["pvr-channel://" + str( item['channelid'] ), item['label'], "::SCRIPT::32076", {"icon": "DefaultTVShows.png", "thumb": item[ "thumbnail"]}]) )
            
            self.addToDictionary( "pvr-tv", listitems )
            
            # Add radio channels
            listitems = []
            json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "PVR.GetChannels", "params": { "channelgroupid": "allradio", "properties": ["thumbnail", "channeltype", "hidden", "locked", "channel", "lastplayed"] } }')
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            
            # Add all directories returned by the json query
            if json_response.has_key('result') and json_response['result'].has_key('channels') and json_response['result']['channels'] is not None:
                for item in json_response['result']['channels']:
                    listitems.append( self._create(["pvr-channel://" + str( item['channelid'] ), item['label'], "::SCRIPT::32077", {"icon": "DefaultTVShows.png", "thumb": item[ "thumbnail"]}]) )
            
            log( "Found " + str( len( listitems ) ) + " radio channels" )
            self.addToDictionary( "pvr-radio", listitems )

        except:
            log( "Failed to load pvr library" )
            print_exc()

        self.loadedPVRLibrary = True
        return self.loadedPVRLibrary
        
    def radiolibrary( self ):
        if self.loadedRadioLibrary == True:
            # The List has already been populated, return it
            return self.loadedRadioLibrary
        elif self.loadedRadioLibrary == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedRadioLibrary == True:
                    return self.loadedRadioLibrary
        else:
            # We're going to populate the list
            self.loadedRadioLibrary = "Loading"

        try:
            listitems = []
            log('Listing pvr-radio library...')
            
            # PVR
            listitems.append( self._create(["ActivateWindow(RadioChannels)", "19019", "32087", {"icon": "DefaultAudio.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(RadioGuide)", "22020", "32087", {"icon": "DefaultAudio.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(RadioRecordings)", "19163", "32087", {"icon": "DefaultAudio.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(RadioTimers)", "19040", "32087", {"icon": "DefaultAudio.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(RadioSearch)", "137", "32087", {"icon": "DefaultAudio.png"} ] ) )
            
            listitems.append( self._create(["PlayPvrRadio", "32067", "32087", {"icon": "DefaultAudio.png"} ] ) )
            listitems.append( self._create(["PlayPvr", "32068", "32087", {"icon": "DefaultAudio.png"} ] ) )

            self.addToDictionary( "radio", listitems )            

        except:
            log( "Failed to load pvr-radio library" )
            print_exc()

        self.loadedRadioLibrary = True
        return self.loadedRadioLibrary
        
    def musiclibrary( self ):
        if self.loadedMusicLibrary == True:
            # The List has already been populated, return it
            return self.loadedMusicLibrary
        elif self.loadedMusicLibrary == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if loadedMusicLibrary == True:
                    return self.loadedMusicLibrary
        else:
            # We're going to populate the list
            self.loadedMusicLibrary = "Loading"

        try:
            listitems = []
            log('Listing music library...')
                        
            # Music
            listitems.append( self._create(["ActivateWindow(MusicFiles)", "744", "32019", {"icon": "DefaultFolder.png"} ]) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,MusicLibrary,return)", "15100", "32019", {"icon": "DefaultFolder.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Genres,return)", "135", "32019", {"icon": "DefaultMusicGenres.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Artists,return)", "133", "32019", {"icon": "DefaultMusicArtists.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Albums,return)", "132", "32019", {"icon": "DefaultMusicAlbums.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Songs,return)", "134", "32019", {"icon": "DefaultMusicSongs.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Years,return)", "652", "32019", {"icon": "DefaultMusicYears.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Top100,return)", "271", "32019", {"icon": "DefaultMusicTop100.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Top100Songs,return)", "10504", "32019", {"icon": "DefaultMusicTop100Songs.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Top100Albums,return)", "10505", "32019", {"icon": "DefaultMusicTop100Albums.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,RecentlyAddedAlbums,return)", "359", "32019", {"icon": "DefaultMusicRecentlyAdded.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,RecentlyPlayedAlbums,return)", "517", "32019", {"icon": "DefaultMusicRecentlyPlayed.png"} ] ) )
            listitems.append( self._create(["ActivateWindow(MusicLibrary,Playlists,return)", "136", "32019", {"icon": "DefaultMusicPlaylists.png"} ] ) )
            
            # Do a JSON query for upnp sources (so that they'll show first time the user asks to see them)
            if self.loadedUPNP == False:
                json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Files.GetDirectory", "params": { "properties": ["title", "file", "thumbnail"], "directory": "upnp://", "media": "files" } }')
                self.loadedUPNP = True
                
            self.addToDictionary( "music", listitems )
        except:
            log( "Failed to load music library" )
            print_exc()

        self.loadedMusicLibrary = True
        return self.loadedMusicLibrary
    
    def librarysources( self ):
        if self.loadedLibrarySources == True:
            # The List has already been populated, return it
            return self.loadedLibrarySources
        elif self.loadedLibrarySources == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedLibrarySources == True:
                    return self.loadedLibrarySources
        else:
            # We're going to populate the list
            self.loadedLibrarySources = "Loading"
            
        log('Listing library sources...')
        # Add video sources
        listitems = []
        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Files.GetSources", "params": { "media": "video" } }')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
            
        # Add all directories returned by the json query
        if json_response.has_key('result') and json_response['result'].has_key('sources') and json_response['result']['sources'] is not None:
            for item in json_response['result']['sources']:
                listitems.append( self._create(["||SOURCE||" + item['file'], item['label'], "32069", {"icon": "DefaultFolder.png"} ]) )
        self.addToDictionary( "videosources", listitems )
        
        log( " - " + str( len( listitems ) ) + " video sources" )
                
        # Add audio sources
        listitems = []
        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Files.GetSources", "params": { "media": "music" } }')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
            
        # Add all directories returned by the json query
        if json_response.has_key('result') and json_response['result'].has_key('sources') and json_response['result']['sources'] is not None:
            for item in json_response['result']['sources']:
                listitems.append( self._create(["||SOURCE||" + item['file'], item['label'], "32073", {"icon": "DefaultFolder.png"} ]) )
        self.addToDictionary( "musicsources", listitems )
        
        log( " - " + str( len( listitems ) ) + " audio sources" )
        
        # Add picture sources
        listitems = []
        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Files.GetSources", "params": { "media": "pictures" } }')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
            
        # Add all directories returned by the json query
        if json_response.has_key('result') and json_response['result'].has_key('sources') and json_response['result']['sources'] is not None:
            for item in json_response['result']['sources']:
                listitems.append( self._create(["||SOURCE||" + item['file'], item['label'], "32089", {"icon": "DefaultFolder.png"} ]) )
        self.addToDictionary( "picturesources", listitems )
        
        log( " - " + str( len( listitems ) ) + " picture sources" )
        
        self.loadedLibrarySources = True
        return self.loadedLibrarySources
            
    def playlists( self ):
        if self.loadedPlaylists == True:
            # The List has already been populated, return it
            return self.loadedPlaylists
        elif self.loadedPlaylists == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedPlaylists == True:
                    return self.loadedPlaylists
        else:
            # We're going to populate the list
            self.loadedPlaylists = "Loading"
            
        try:
            audiolist = []
            videolist = []
            
            log('Loading playlists...')
            paths = [['special://profile/playlists/video/','32004','VideoLibrary'], ['special://profile/playlists/music/','32005','MusicLibrary'], ['special://profile/playlists/mixed/','32008','MusicLibrary'], [xbmc.translatePath( "special://skin/playlists/" ).decode('utf-8'),'32059',None], [xbmc.translatePath( "special://skin/extras/" ).decode('utf-8'),'32059',None]]
            for path in paths:
                count = 0
                rootpath = xbmc.translatePath( path[0] ).decode('utf-8')
                for root, subdirs, files in os.walk( rootpath ):
                    for file in files:
                        playlist = root.replace( rootpath, path[0] )
                        if not playlist.endswith( '/' ):
                            playlist = playlist + "/"
                        playlist = playlist + file
                        playlistfile = os.path.join( root, file )
                        mediaLibrary = path[2]
                        
                        if file.endswith( '.xsp' ):
                            contents = xbmcvfs.File(playlistfile, 'r')
                            contents_data = contents.read().decode('utf-8')
                            xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                            for line in xmldata.getiterator():
                                if line.tag == "smartplaylist":
                                    mediaType = line.attrib['type']
                                    if mediaType == "movies" or mediaType == "tvshows" or mediaType == "seasons" or mediaType == "episodes" or mediaType == "musicvideos" or mediaType == "sets":
                                        mediaLibrary = "VideoLibrary"
                                    elif mediaType == "albums" or mediaType == "artists" or mediaType == "songs":
                                        mediaLibrary = "MusicLibrary"                                
                                    
                                if line.tag == "name" and mediaLibrary is not None:
                                    name = line.text
                                    if not name:
                                        name = file[:-4]
                                    # Create a list item
                                    listitem = self._create(["::PLAYLIST::", name, path[1], {"icon": "DefaultPlaylist.png"} ])
                                    listitem.setProperty( "action-play", "PlayMedia(" + playlist.encode( 'utf-8' ) + ")" )
                                    listitem.setProperty( "action-show", "ActivateWindow(" + mediaLibrary + "," + playlist.encode( 'utf-8' ) + ", return)".encode( 'utf-8' ) )
                                    
                                    if mediaLibrary == "VideoLibrary":
                                        videolist.append( listitem )
                                    else:
                                        audiolist.append( listitem )
                                    # Save it for the widgets list
                                    self.widgetPlaylistsList.append( [playlist.encode( 'utf-8' ), "(" + __language__( int( path[1] ) ) + ") " + name, name] )
                                    
                                    count += 1
                                    break
                        elif file.endswith( '.m3u' ):
                            name = file[:-4]
                            listitem = self._create( ["::PLAYLIST::", name, "32005", {"icon": "DefaultPlaylist.png"} ] )
                            listitem.setProperty( "action-play", "PlayMedia(" + playlist + ")" )
                            listitem.setProperty( "action-show", "ActivateWindow(MusicLibrary," + playlist + ", return)".encode( 'utf-8' ) )
                            
                            audiolist.append( listitem )
                            
                            count += 1
                            
                log( " - [" + path[0] + "] " + str( count ) + " playlists found" )
            
            self.addToDictionary( "playlist-video", videolist )
            self.addToDictionary( "playlist-audio", audiolist )
            
        except:
            log( "Failed to load playlists" )
            print_exc()
            
        self.loadedPlaylists = True
        return self.loadedPlaylists
                
    def scriptPlaylists( self ):
        # Lazy loading of random source playlists auto-generated by the script
        # (loaded lazily as these can be created/deleted after gui has loaded)
        returnPlaylists = []
        try:
            log('Loading script generated playlists...')
            path = "special://profile/addon_data/" + __addonid__ + "/"
            count = 0
            rootpath = xbmc.translatePath( path ).decode('utf-8')
            for root, subdirs, files in os.walk( rootpath ):
                for file in files:
                    playlist = root.replace( rootpath, path )
                    if not playlist.endswith( '/' ):
                        playlist = playlist + "/"
                    playlist = playlist + file
                    playlistfile = os.path.join( root, file )
                    
                    if file.endswith( '-randomversion.xsp' ):
                        contents = xbmcvfs.File(playlistfile, 'r')
                        contents_data = contents.read().decode('utf-8')
                        xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                        for line in xmldata.getiterator():                               
                            if line.tag == "name":
                                    
                                # Save it for the widgets list
                                # TO-DO - Localize display name
                                returnPlaylists.append( [playlist.encode( 'utf-8' ), "(Source) " + name, name] )
                                
                                count += 1
                                break
                        
            log( " - [" + path[0] + "] " + str( count ) + " playlists found" )
            
        except:
            log( "Failed to load script generated playlists" )
            print_exc()
            
        return returnPlaylists
                
    def favourites( self ):
        if self.loadedFavourites == True:
            # The List has already been populated, return it
            return self.loadedFavourites
        elif self.loadedFavourites == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedFavourites == True:
                    return self.loadedFavourites
        else:
            # We're going to populate the list
            self.loadedFavourites = "Loading"
            
        try:
            log('Loading favourites...')
            
            listitems = []
            listing = None
            
            fav_file = xbmc.translatePath( 'special://profile/favourites.xml' ).decode("utf-8")
            if xbmcvfs.exists( fav_file ):
                doc = parse( fav_file )
                listing = doc.documentElement.getElementsByTagName( 'favourite' )
            else:
                # No favourites file found
                self.addToDictionary( "favourite", [] )
                self.loadedFavourites = True
                return True
                
            for count, favourite in enumerate(listing):
                name = favourite.attributes[ 'name' ].nodeValue
                path = favourite.childNodes [ 0 ].nodeValue
                if ('RunScript' not in path) and ('StartAndroidActivity' not in path) and not (path.endswith(',return)') ):
                    path = path.rstrip(')')
                    path = path + ',return)'

                try:
                    thumb = favourite.attributes[ 'thumb' ].nodeValue
                    
                except:
                    thumb = None
                
                listitems.append( self._create( [ path, name, "32006", { "icon": "DefaultFolder.png", "thumb": thumb} ] ) )
            
            log( " - " + str( len( listitems ) ) + " favourites found" )
            
            self.addToDictionary( "favourite", listitems )
            
        except:
            log( "Failed to load favourites" )
            print_exc()
            
        self.loadedFavourites = True            
        return self.loadedFavourites
        
    def addons( self ):
        if self.loadedAddOns == True:
            # The List has already been populated, return it
            return self.loadedAddOns
        elif self.loadedAddOns == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while count < 20:
                xbmc.sleep( 100 )
                count += 1
                if self.loadedAddOns == True:
                    return self.loadedAddOns
        else:
            # We're going to populate the list
            self.loadedAddOns = "Loading"
            
        try:
            log( 'Loading add-ons' )
                        
            contenttypes = ["executable", "video", "audio", "image"]
            for contenttype in contenttypes:
                listitems = []
                if contenttype == "executable":
                    contentlabel = __language__(32009)
                    shortcutType = "::SCRIPT::32009"
                elif contenttype == "video":
                    contentlabel = __language__(32010)
                    shortcutType = "::SCRIPT::32010"
                elif contenttype == "audio":
                    contentlabel = __language__(32011)
                    shortcutType = "::SCRIPT::32011"
                elif contenttype == "image":
                    contentlabel = __language__(32012)
                    shortcutType = "::SCRIPT::32012"
                    
                json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Addons.Getaddons", "params": { "content": "%s", "properties": ["name", "path", "thumbnail", "enabled"] } }' % contenttype)
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = simplejson.loads(json_query)
                
                if json_response.has_key('result') and json_response['result'].has_key('addons') and json_response['result']['addons'] is not None:
                    for item in json_response['result']['addons']:
                        if item['enabled'] == True:                            
                            path = "RunAddOn(" + item['addonid'].encode('utf-8') + ")"
                            action = None
                            
                            # If this is a plugin, mark that we can browse it
                            if item['addonid'].startswith( "plugin." ):
                                path = "||BROWSE||" + item['addonid'].encode('utf-8')
                                action = "RunAddOn(" + item['addonid'].encode('utf-8') + ")"

                            thumb = "DefaultAddon.png"
                            if item['thumbnail'] != "":
                                thumb = item[ 'thumbnail' ]
                            else:   
                                thumb = None
                                
                            listitem = self._create([path, item['name'], shortcutType, {"icon": "DefaultAddon.png", "thumb": thumb} ])
                            if action is not None:
                                listitem.setProperty( "path", path )
                                listitem.setProperty( "action", action )

                            listitems.append(listitem)
                            
                if contenttype == "executable":
                    self.addToDictionary( "addon-program", listitems )
                    log( " - " + str( len( listitems ) ) + " programs found" )
                elif contenttype == "video":
                    self.addToDictionary( "addon-video", listitems )
                    log( " - " + str( len( listitems ) ) + " video add-ons found" )
                elif contenttype == "audio":
                    self.addToDictionary( "addon-audio", listitems )
                    log( " - " + str( len( listitems ) ) + " audio add-ons found" )
                elif contenttype == "image":
                    self.addToDictionary( "addon-image", listitems )
                    log( " - " + str( len( listitems ) ) + " image add-ons found" )
            
        except:
            log( "Failed to load addons" )
            print_exc()
        
        self.loadedAddOns = True
        return self.loadedAddOns
            
    # =============================
    # === ADDON/SOURCE EXPLORER ===
    # =============================
    
    def explorer( self, history, location, label, thumbnail, itemType ):
        dialogLabel = label[0].replace( "  >", "" )

        # Default action - create shortcut
        listings = []
        
        tree = DATA._get_overrides_skin()
        
        listings.append( self._get_icon_overrides( tree, self._create( ["::CREATE::", "32058", "", {}] ), "" ) )
                
        # If this isn't the root, create a link to go up the heirachy
        if len( label ) is not 1:
        #    listitem = xbmcgui.ListItem( label=".." )
        #    listitem.setProperty( "path", "||BACK||" )
        #    listings.append( listitem )
        #    
            dialogLabel = label[0].replace( "  >", "" ) + " - " + label[ len( label ) - 1 ].replace( "  >", "" )
            
        # Show a waiting dialog, then get the listings for the directory
        dialog = xbmcgui.DialogProgress()
        dialog.create( dialogLabel, __language__( 32063) )
    
        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Files.GetDirectory", "params": { "properties": ["title", "file", "thumbnail"], "directory": "' + location + '", "media": "files" } }')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        
        dialog.close()
            
        # Add all directories returned by the json query
        if json_response.has_key('result') and json_response['result'].has_key('files') and json_response['result']['files'] is not None:
            for item in json_response['result']['files']:
                if item["filetype"] == "directory":
                    thumb = None
                    if item[ "thumbnail" ] is not "":
                        thumb = item[ "thumbnail" ]
                    listitem = self._create( [item[ "file" ], item[ "label" ] + "  >", "", {"icon": "DefaultFolder.png", "thumb": thumb} ] )
                    listings.append( self._get_icon_overrides( tree, listitem, "" ) )
            
        # Show dialog
        w = ShowDialog( "DialogSelect.xml", __cwd__, listing=listings, windowtitle=dialogLabel )
        w.doModal()
        selectedItem = w.result
        del w
        
        if selectedItem != -1:
            selectedAction = listings[ selectedItem ].getProperty( "path" )
            if selectedAction == "::CREATE::":
                # User has chosen the shortcut they want

                # Localize strings
                localItemType = DATA.local( itemType )[2]
                
                # Create a listitem
                listitem = xbmcgui.ListItem(label=label[ len( label ) - 1 ].replace( "  >", "" ), label2=localItemType, iconImage="DefaultShortcut.png", thumbnailImage=thumbnail[ len( thumbnail ) - 1 ])
                
                # Build the action
                if itemType == "32010" or itemType == "32014" or itemType == "32069":
                    action = 'ActivateWindow(10025,"' + location + '",return)'
                    listitem.setProperty( "windowID", "10025" )
                elif itemType == "32011" or itemType == "32019" or itemType == "32073":
                    action = 'ActivateWindow(10501,"' + location + '",return)'
                    listitem.setProperty( "windowID", "10501" )
                elif itemType == "32012" or itemType == "32089":
                    action = 'ActivateWindow(10002,"' + location + '",return)'
                    listitem.setProperty( "windowID", "10002" )
                elif itemType == "32009":
                    action = 'ActivateWindow(10001,"' + location + '",return)'
                else:
                    action = "RunAddon(" + location + ")"

                listitem.setProperty( "path", action )
                listitem.setProperty( "displayPath", action )
                listitem.setProperty( "shortcutType", itemType )
                listitem.setProperty( "icon", "DefaultShortcut.png" )
                if thumbnail[ len( thumbnail ) -1 ] == "":
                    listitem.setProperty( "thumbnail", thumbnail[ 0 ] )
                else:
                    listitem.setProperty( "thumbnail", thumbnail[ len( thumbnail ) - 1 ] )
                listitem.setProperty( "location", location )
                
                return listitem
                
            elif selectedAction == "||BACK||":
                # User is going up the heirarchy, remove current level and re-call this function
                history.pop()
                label.pop()
                thumbnail.pop()
                return self.explorer( history, history[ len( history ) -1 ], label, thumbnail, itemType )
                
            else:
                # User has chosen a sub-level to display, add details and re-call this function
                history.append( selectedAction )
                label.append( listings[ selectedItem ].getLabel() )
                thumbnail.append( listings[ selectedItem ].getProperty( "thumbnail" ) )
                return self.explorer( history, selectedAction, label, thumbnail, itemType )
    
    # ======================
    # === AUTO-PLAYLISTS ===
    # ======================
    
    def _sourcelink_choice( self, selectedShortcut ):
        # The user has selected a source. We're going to give them the choice of displaying it
        # in the files view, or view library content from the source
        dialog = xbmcgui.Dialog()
        
        mediaType = None
        windowID = selectedShortcut.getProperty( "windowID" )
        # Check if we're going to display this in the files view, or the library view
        if windowID == "10025":
            # Video library                                    Files view           Movies                TV Shows             Music videos         !Movies               !TV Shows            !Music Videos
            userChoice = dialog.select( __language__(32078), [__language__(32079), __language__(32015), __language__(32016), __language__(32018), __language__(32081), __language__(32082), __language__(32083) ] )            
            if userChoice == -1:
                return None
            elif userChoice == 0:
                # Escape any backslashes (Windows fix)
                newAction = selectedShortcut.getProperty( "Path" )
                newAction = newAction.replace( "\\", "\\\\" )
                selectedShortcut.setProperty( "Path", newAction )
                selectedShortcut.setProperty( "displayPath", newAction )
                return selectedShortcut
            elif userChoice == 1:
                mediaType = "movies"
                negative = False
            elif userChoice == 2:
                mediaType = "tvshows"
                negative = False
            elif userChoice == 3:
                mediaType = "musicvideo"
                negative = False
            elif userChoice == 4:
                mediaType = "movies"
                negative = True
            elif userChoice == 5:
                mediaType = "tvshows"
                negative = True
            elif userChoice == 6:
                mediaType = "musicvideo"
                negative = True
        elif windowID == "10501":
            # Music library                                    Files view           Songs                          Albums                         Mixed                           !Songs               !Albums               !Mixed
            userChoice = dialog.select( __language__(32078), [__language__(32079), xbmc.getLocalizedString(134), xbmc.getLocalizedString(132), xbmc.getLocalizedString(20395), __language__(32084), __language__(32085), __language__(32086) ] )            
            if userChoice == -1:
                return None
            elif userChoice == 0:
                # Escape any backslashes (Windows fix)
                newAction = selectedShortcut.getProperty( "Path" )
                newAction = newAction.replace( "\\", "\\\\" )
                selectedShortcut.setProperty( "Path", newAction )
                selectedShortcut.setProperty( "displayPath", newAction )
                return selectedShortcut
            elif userChoice == 1:
                mediaType = "songs"
                windowID = "10502"
                negative = False
            elif userChoice == 2:
                mediaType = "albums"
                windowID = "10502"
                negative = False
            elif userChoice == 3:
                mediaType = "mixed"
                windowID = "10502"
                negative = False
            elif userChoice == 4:
                mediaType = "songs"
                windowID = "10502"
                negative = True
            elif userChoice == 5:
                mediaType = "albums"
                windowID = "10502"
                negative = True
            elif userChoice == 6:
                mediaType = "mixed"
                windowID = "10502"
                negative = True
        else:
            # Pictures                                         Files view            Slideshow
            userChoice = dialog.select( __language__(32078), [__language__(32079), xbmc.getLocalizedString(108)])
            if userChoice == -1:
                return None
            elif userChoice == 0:
                # Escape any backslashes (Windows fix)
                newAction = selectedShortcut.getProperty( "Path" )
                newAction = newAction.replace( "\\", "\\\\" )
                selectedShortcut.setProperty( "Path", newAction )
                selectedShortcut.setProperty( "displayPath", newAction )
                return selectedShortcut
            elif userChoice == 1:
                newAction = "SlideShow(" + selectedShortcut.getProperty( "location" ) + ")"
                selectedShortcut.setProperty( "path", newAction )
                selectedShortcut.setProperty( "displayPath", newAction )
                return selectedShortcut
            
        # We're going to display it in the library
        filename = self._build_playlist( selectedShortcut.getProperty( "location" ), mediaType, selectedShortcut.getLabel(), negative )
        newAction = "ActivateWindow(" + windowID + "," +"special://profile/addon_data/" + __addonid__ + "/" + filename + ",return)"
        selectedShortcut.setProperty( "Path", newAction )
        selectedShortcut.setProperty( "displayPath", newAction )
        return selectedShortcut
    
    def _build_playlist( self, target, mediatype, name, negative ):
        # This function will build a playlist that displays the contents of a source in the library view
        # (that is to say, "path" "contains")
        tree = xmltree.ElementTree( xmltree.Element( "smartplaylist" ) )
        root = tree.getroot()
        root.set( "type", mediatype )
        
        if target.startswith ( "multipath://" ):
            temp_path = target.replace( "multipath://", "" ).split( "%2f/" )
            target = []
            for item in temp_path:
                if item is not "":
                    target.append( urllib.url2pathname( item ) )
        else:
            target = [target]
        
        xmltree.SubElement( root, "name").text = name
        if negative == False:
            xmltree.SubElement( root, "match").text = "one"
        else:
            xmltree.SubElement( root, "match").text = "all"
        
        for item in target:
            if negative == False:
                rule = xmltree.SubElement( root, "rule")
                rule.set( "field", "path" )
                rule.set( "operator", "startswith" )
                xmltree.SubElement( rule, "value" ).text = item
            else:
                rule = xmltree.SubElement( root, "rule")
                rule.set( "field", "path" )
                rule.set( "operator", "doesnotcontain" )
                xmltree.SubElement( rule, "value" ).text = item
        
        id = 1
        while xbmcvfs.exists( os.path.join( __datapath__, str( id ) + ".xsp" ) ) :
            id += 1
                
        # Write playlist we'll link to the menu item
        DATA.indent( tree.getroot() )
        tree.write( os.path.join( __datapath__, str( id ) + ".xsp" ), encoding="utf-8" )
        
        # Add a random property, and save this for use in playlists/backgrounds
        order = xmltree.SubElement( root, "order" )
        order.text = "random"
        DATA.indent( tree.getroot() )
        tree.write( os.path.join( __datapath__, str( id ) + "-randomversion.xsp" ), encoding="utf-8" )
        
        return str( id ) + ".xsp"
        
    def _delete_playlist( self, target ):
        # This function will check if the target links to an auto-generated playlist and, if so, delete it
        target = target
        if target.startswith( "ActivateWindow(" ):
            try:
                elements = target.split( "," )
                if len( elements ) > 1:
                    if elements[1].startswith( "special://profile/addon_data/" + __addonid__ + "/" ) and elements[1].endswith( ".xsp" ):
                        xbmcvfs.delete( xbmc.translatePath( elements[1] ) )
                        xbmcvfs.delete( xbmc.translatePath( elements[1].replace( ".xsp", "-randomversion.xsp" ) ) )                        
            except:
                return

    def _rename_playlist( self, target, newLabel ):
        # This function changes the label tag of an auto-generated playlist
        
        # First we will check that this is a playlist
        target = target
        if target.startswith( "ActivateWindow(" ):
            try:
                elements = target.split( "," )
            except:
                return
                    
            try:
                if elements[1].startswith( "special://profile/addon_data/" + __addonid__ + "/" ) and elements[1].endswith( ".xsp" ):
                    filename =  xbmc.translatePath( elements[1] )
                else:
                    return
            except:
                return
                    
            # Load the tree and change the name
            tree = xmltree.parse( filename )
            name = tree.getroot().find( "name" )
            name.text = newLabel
            
            # Write the tree
            DATA.indent( tree.getroot() )
            tree.write( filename, encoding="utf-8" )
                    
            # Load the random tree and change the name
            tree = xmltree.parse( filename.replace( ".xsp", "-randomversion.xsp" ) )
            name = tree.getroot().find( "name" )
            name.text = newLabel
            
            # Write the random tree
            DATA.indent( tree.getroot() )
            tree.write( filename.replace( ".xsp", "-randomversion.xsp" ), encoding="utf-8" )

# =====================================
# === COMMON SELECT SHORTCUT METHOD ===
# =====================================

    def selectShortcut( self, group = "", custom = False, availableShortcuts = None, windowTitle = None ):
        # This function allows the user to select a shortcut
        
        # If group is empty, start background loading of shortcuts
        if group == "":
            thread.start_new_thread( self.loadLibrary, () )
        
        if availableShortcuts is None:
            nodes = self.retrieveGroup( group, False )
            availableShortcuts = nodes[1]
            windowTitle = nodes[0]
        else:
            availableShortcuts = self.checkForFolder( availableShortcuts )
            
        if custom is not False:
            availableShortcuts.append( self._create(["||CUSTOM||", "Custom shortcut", "", {}] ) )
        
        # Check a shortcut is available
        if len( availableShortcuts ) == 0:
            log( "No available shortcuts found" )
            xbmcgui.Dialog().ok( __language__(32064), __language__(32065) )
            return
                                
        w = ShowDialog( "DialogSelect.xml", __cwd__, listing=availableShortcuts, windowtitle=windowTitle )
        w.doModal()
        number = w.result
        del w
        
        if number != -1:
            selectedShortcut = availableShortcuts[ number ]
            path = selectedShortcut.getProperty( "Path" )
            if path.startswith( "||NODE||" ):
                if group == "":
                    group = path.replace( "||NODE||", "" )
                else:
                    group = group + "," + path.replace( "||NODE||", "" )
                return self.selectShortcut( group = group )
            elif path.startswith( "||BROWSE||" ):
                selectedShortcut = self.explorer( ["plugin://" + path.replace( "||BROWSE||", "" )], "plugin://" + path.replace( "||BROWSE||", "" ), [selectedShortcut.getLabel()], [selectedShortcut.getProperty("thumbnail")], selectedShortcut.getProperty("shortcutType") )
                # Convert backslashes to double-backslashes (windows fix)
                if selectedShortcut is not None:
                    newAction = selectedShortcut.getProperty( "Path" )
                    newAction = newAction.replace( "\\", "\\\\" )
                    selectedShortcut.setProperty( "Path", newAction )
                    selectedShortcut.setProperty( "displayPath", newAction )
            elif path == "||FOLDER||":
                # The next set of shortcuts are within the listitem property folder-contents
                shortcuts = self.folders[ selectedShortcut.getProperty( "folder" ) ]
                return self.selectShortcut( group=group, availableShortcuts=shortcuts, windowTitle = selectedShortcut.getLabel() )
            elif path == "||UPNP||":
                selectedShortcut = self.explorer( ["upnp://"], "upnp://", [selectedShortcut.getLabel()], [selectedShortcut.getProperty("thumbnail")], selectedShortcut.getProperty("shortcutType")  )
                path = selectedShortcut.getProperty( "Path" )
            elif path.startswith( "||SOURCE||" ):
                selectedShortcut = self.explorer( [path.replace( "||SOURCE||", "" )], path.replace( "||SOURCE||", "" ), [selectedShortcut.getLabel()], [selectedShortcut.getProperty("thumbnail")], selectedShortcut.getProperty("shortcutType")  )
                if selectedShortcut is None or "upnp://" in selectedShortcut.getProperty( "Path" ):
                    return selectedShortcut
                selectedShortcut = self._sourcelink_choice( selectedShortcut )
                #path = urllib.unquote( selectedShortcut.getProperty( "Path" ) )
            elif path == "::PLAYLIST::" :
                # Give the user the choice of playing or displaying the playlist
                dialog = xbmcgui.Dialog()
                userchoice = dialog.yesno( __language__( 32040 ), __language__( 32060 ), "", "", __language__( 32061 ), __language__( 32062 ) )
                # False: Display
                # True: Play
                if userchoice == False:
                    selectedShortcut.setProperty( "chosenPath", selectedShortcut.getProperty( "action-show" ) )
                else:
                    selectedShortcut.setProperty( "chosenPath", selectedShortcut.getProperty( "action-play" ) )
                   
            elif path == "||CUSTOM||":
                # Let the user type a command
                keyboard = xbmc.Keyboard( "", __language__(32027), False )
                keyboard.doModal()
                
                if ( keyboard.isConfirmed() ):
                    action = keyboard.getText()
                    if action != "":
                        # Create a really simple listitem to return
                        selectedShortcut = xbmcgui.ListItem( None, __language__(32024) )
                        selectedShortcut.setProperty( "Path", action )
                    else:
                        selectedShortcut = None
                            
                else:
                    selectedShortcut = None

            return selectedShortcut
        else:
            return None

# ============================
# === PRETTY SELECT DIALOG ===
# ============================
            
class ShowDialog( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.listing = kwargs.get( "listing" )
        self.windowtitle = kwargs.get( "windowtitle" )
        self.result = -1

    def onInit(self):
        try:
            self.fav_list = self.getControl(6)
            self.getControl(3).setVisible(False)
        except:
            print_exc()
            self.fav_list = self.getControl(3)

        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(self.windowtitle)

        for item in self.listing :
            listitem = xbmcgui.ListItem(label=item.getLabel(), label2=item.getLabel2(), iconImage=item.getProperty( "icon" ), thumbnailImage=item.getProperty( "thumbnail" ))
            listitem.setProperty( "Addon.Summary", item.getLabel2() )
            self.fav_list.addItem( listitem )

        self.setFocus(self.fav_list)

    def onAction(self, action):
        if action.getId() in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.result = -1
            self.close()

    def onClick(self, controlID):
        if controlID == 6 or controlID == 3:
            num = self.fav_list.getSelectedPosition()
            self.result = num
        else:
            self.result = -1

        self.close()

    def onFocus(self, controlID):
        pass

# coding=utf-8
import os, sys, datetime, unicodedata, re, types
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
import hashlib, hashlist
import cPickle as pickle
from xml.dom.minidom import parse
from traceback import print_exc
from htmlentitydefs import name2codepoint
from unidecode import unidecode
from unicodeutils import try_decode

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id').decode( 'utf-8' )
__addonversion__ = __addon__.getAddonInfo('version')
__xbmcversion__  = xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0]
__language__     = __addon__.getLocalizedString
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__addonname__    = __addon__.getAddonInfo('name').decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ )
__profilepath__  = xbmc.translatePath( "special://profile/" ).decode('utf-8')
__skinpath__     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')
__defaultpath__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'shortcuts').encode("utf-8") ).decode("utf-8")

# character entity reference
CHAR_ENTITY_REXP = re.compile('&(%s);' % '|'.join(name2codepoint))

# decimal character reference
DECIMAL_REXP = re.compile('&#(\d+);')

# hexadecimal character reference
HEX_REXP = re.compile('&#x([\da-fA-F]+);')

REPLACE1_REXP = re.compile(r'[\']+')
REPLACE2_REXP = re.compile(r'[^-a-z0-9]+')
REMOVE_REXP = re.compile('-{2,}')

def log(txt):
    if __addon__.getSetting( "enable_logging" ) == "true":
        try:
            if isinstance (txt,str):
                txt = txt.decode('utf-8')
            message = u'%s: %s' % (__addonid__, txt)
            xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)
        except:
            pass
    
class NodeFunctions():
    def __init__(self):
        self.indexCounter = 0
        
    ##############################################
    # Functions used by library.py to list nodes #
    ##############################################
        
    def get_nodes( self, path, prefix ):
        dirs, files = xbmcvfs.listdir( path )
        nodes = {}
        
        try:
            for dir in dirs:
                self.parse_node( os.path.join( path, dir ), dir, nodes, prefix )
            for file in files:
                self.parse_view( os.path.join( path, file.decode( "utf-8" ) ), nodes, origPath = "%s/%s" % ( prefix, file ), prefix = prefix )
        except:
            print_exc()
            return False
        
        return nodes
        
    def parse_node( self, node, dir, nodes, prefix ):
        # If the folder we've been passed contains an index.xml, send that file to be processed
        if xbmcvfs.exists( os.path.join( node, "index.xml" ) ):
            self.parse_view( os.path.join( node, "index.xml" ), nodes, True, "%s/%s/" % ( prefix, dir ), node, prefix = prefix )
    
    def parse_view( self, file, nodes, isFolder = False, origFolder = None, origPath = None, prefix = None ):
        if not isFolder and file.endswith( "index.xml" ):
            return
        try:
            # Load the xml file
            tree = xmltree.parse( file )
            root = tree.getroot()
            
            # Get the item index
            if "order" in root.attrib:
                index = root.attrib.get( "order" )
                origIndex = index
                while int( index ) in nodes:
                    index = int( index )
                    index += 1
                    index = str( index )
            else:
                self.indexCounter -= 1
                index = str( self.indexCounter )
                origIndex = "-"

            # Try to get media type from visibility condition
            mediaType = None
            if "visible" in root.attrib:
                visibleAttrib = root.attrib.get( "visible" )
                if not xbmc.getCondVisibility( visibleAttrib ):
                    # The node isn't visible
                    return
                if "Library.HasContent(" in visibleAttrib and "+" not in visibleAttrib and "|" not in visibleAttrib:
                    mediaType = visibleAttrib.split( "(" )[ 1 ].split( ")" )[ 0 ].lower()

            # Try to get media type from content node
            contentNode = root.find( "content" )
            if contentNode is not None:
                mediaType = contentNode.text

            # Get label and icon
            label = root.find( "label" ).text
            
            icon = root.find( "icon" )
            if icon is not None:
                icon = icon.text
            else:
                icon = ""

            if isFolder:
                # Add it to our list of nodes
                nodes[ int( index ) ] = [ label, icon, origFolder, "folder", origIndex, mediaType ]
            else:
                # Check for a path
                path = root.find( "path" )
                if path is not None:
                    # Change the origPath (the url used as the shortcut address) to it
                    origPath = path.text
                    
                # Check for a grouping
                group = root.find( "group" )
                if group is None:
                    # Add it as an item
                    nodes[ int( index ) ] = [ label, icon, origPath, "item", origIndex, mediaType ]
                else:
                    # Add it as grouped
                    nodes[ int( index ) ] = [ label, icon, origPath, "grouped", origIndex, mediaType ]
        except:
            print_exc()
            
    def isGrouped( self, path ):        
        customPathVideo = path.replace( "library://video", os.path.join( xbmc.translatePath( "special://profile".decode('utf-8') ), "library", "video" ) )[:-1]
        defaultPathVideo = path.replace( "library://video", os.path.join( xbmc.translatePath( "special://xbmc".decode('utf-8') ), "system", "library", "video" ) )[:-1]
        customPathAudio = path.replace( "library://music", os.path.join( xbmc.translatePath( "special://profile".decode('utf-8') ), "library", "music" ) )[:-1]
        defaultPathAudio = path.replace( "library://music", os.path.join( xbmc.translatePath( "special://xbmc".decode('utf-8') ), "system", "library", "music" ) )[:-1]
        
        paths = [ customPathVideo, defaultPathVideo, customPathAudio, defaultPathAudio ]
        foundPath = False

        for tryPath in paths:
            if xbmcvfs.exists( tryPath ):
                path = tryPath
                foundPath = True
                break
        if foundPath == False:
            return False
        
        # Open the file
        try:
            # Load the xml file
            tree = xmltree.parse( path )
            root = tree.getroot()

            group = root.find( "group" )
            if group is None:
                return False
            else:
                return True
        except:
            return False

    #####################################
    # Function used by DataFunctions.py #
    #####################################
            
    def get_visibility( self, path ):
        path = path.replace( "videodb://", "library://video/" )
        path = path.replace( "musicdb://", "library://music/" )
        if path.endswith( ".xml" ):
            path = path[ :-3 ]
        if path.endswith( ".xml/" ):
            path = path[ :-4 ]

        if "library://video" in path:
            pathStart = "library://video"
            pathEnd = "video"
        elif "library://music" in path:
            pathStart = "library://music"
            pathEnd = "music"
        else:
            return ""

        customPath = path.replace( pathStart, os.path.join( xbmc.translatePath( "special://profile".decode('utf-8') ), "library", pathEnd ) ) + "index.xml"
        customFile = path.replace( pathStart, os.path.join( xbmc.translatePath( "special://profile".decode('utf-8') ), "library", pathEnd ) )[:-1] + ".xml"
        defaultPath = path.replace( pathStart, os.path.join( xbmc.translatePath( "special://xbmc".decode('utf-8') ), "system", "library", pathEnd ) ) + "index.xml"
        defaultFile = path.replace( pathStart, os.path.join( xbmc.translatePath( "special://xbmc".decode('utf-8') ), "system", "library", pathEnd ) )[:-1] + ".xml"

        # Check whether the node exists - either as a parent node (with an index.xml) or a view node (append .xml)
        # in first custom video nodes, then default video nodes
        if xbmcvfs.exists( customPath ):
            path = customPath
        elif xbmcvfs.exists( customFile ):
            path = customFile
        elif xbmcvfs.exists( defaultPath ):
            path = defaultPath
        elif xbmcvfs.exists( defaultFile ):
            path = defaultFile
        else:
            return ""
            
        # Open the file
        try:
            # Load the xml file
            tree = xmltree.parse( path )
            root = tree.getroot()

            if "visible" in root.attrib:
                return root.attrib.get( "visible" )
            else:
                return ""
        except:
            return False

    def get_mediaType( self, path ):
        path = path.replace( "videodb://", "library://video/" )
        path = path.replace( "musicdb://", "library://music/" )
        if path.endswith( ".xml" ):
            path = path[ :-3 ]
        if path.endswith( ".xml/" ):
            path = path[ :-4 ]

        if "library://video" in path:
            pathStart = "library://video"
            pathEnd = "video"
        elif "library://music" in path:
            pathStart = "library://music"
            pathEnd = "music"
        else:
            return "unknown"

        customPath = path.replace( pathStart, os.path.join( xbmc.translatePath( "special://profile".decode('utf-8') ), "library", pathEnd ) ) + "index.xml"
        customFile = path.replace( pathStart, os.path.join( xbmc.translatePath( "special://profile".decode('utf-8') ), "library", pathEnd ) )[:-1] + ".xml"
        defaultPath = path.replace( pathStart, os.path.join( xbmc.translatePath( "special://xbmc".decode('utf-8') ), "system", "library", pathEnd ) ) + "index.xml"
        defaultFile = path.replace( pathStart, os.path.join( xbmc.translatePath( "special://xbmc".decode('utf-8') ), "system", "library", pathEnd ) )[:-1] + ".xml"
        
        # Check whether the node exists - either as a parent node (with an index.xml) or a view node (append .xml)
        # in first custom video nodes, then default video nodes
        if xbmcvfs.exists( customPath ):
            path = customPath
        elif xbmcvfs.exists( customFile ):
            path = customFile
        elif xbmcvfs.exists( defaultPath ):
            path = defaultPath
        elif xbmcvfs.exists( defaultFile ):
            path = defaultFile
        else:
            return "unknown"
            
        # Open the file
        try:
            # Load the xml file
            tree = xmltree.parse( path )
            root = tree.getroot()

            mediaType = "unknown"
            if "visible" in root.attrib:
                visibleAttrib = root.attrib.get( "visible" )
                if "Library.HasContent(" in visibleAttrib and "+" not in visibleAttrib and "|" not in visibleAttrib:
                    mediaType = visibleAttrib.split( "(" )[ 1 ].split( ")" )[ 0 ].lower()

            contentNode = root.find( "content" )
            if contentNode is not None:
                mediaType = contentNode.text

            return mediaType

        except:
            return "unknown"
            
    ############################################
    # Functions used to add a node to the menu #
    ############################################

    def addToMenu( self, path, label, icon, content, window, DATA ):
        log( repr( window ) )
        log( repr( label ) )
        log( repr( path ) )
        log( repr( content ) )
        # Show a waiting dialog
        dialog = xbmcgui.DialogProgress()
        dialog.create( path, __language__( 32063 ) )

        # Work out if it's a single item, or a node
        isNode = False
        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Files.GetDirectory", "params": { "properties": ["title", "file", "thumbnail"], "directory": "' + path + '", "media": "files" } }')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)

        labels = []
        paths = []
        nodePaths = []

        # Now we've retrieved the path, decode everything for writing
        path = try_decode( path )
        label = try_decode( label )
        icon = try_decode( icon )
        
        # Add all directories returned by the json query
        if json_response.has_key('result') and json_response['result'].has_key('files') and json_response['result']['files'] is not None:
            labels = [ __language__(32058) ]
            paths = [ "ActivateWindow(%s,%s,return)" %( window, path ) ]
            for item in json_response['result']['files']:
                if item[ "filetype" ] == "directory":
                    isNode = True
                    labels.append( item[ "label" ] )
                    nodePaths.append( "ActivateWindow(%s,%s,return)" %( window, item[ "file" ] ) )
        else:
            log( "Invalid JSON response returned" )

        # Add actions based on content
        if content == "albums":
            labels.append( "Play" )
            paths.append( "RunScript(script.skinshortcuts,type=launchalbum&album=%s)" %( self.extractID( path ) ) )
        if window == 10002:
            labels.append( "Slideshow" )
            paths.append( "SlideShow(%s,notrandom)" %( path ) )
            labels.append( "Slideshow (random)" )
            paths.append( "SlideShow(%s,random)" %( path ) )
            labels.append( "Slideshow (recursive)" )
            paths.append( "SlideShow(%s,recursive,notrandom)" %( path ) )
            labels.append( "Slideshow (recursive, random)" )
            paths.append( "SlideShow(%s,recursive,random)" %( path ) )
        if path.endswith( ".xsp" ):
            labels.append( "Play" )
            paths.append( "PlayMedia(%s)" %( path ) )

        allMenuItems = [ xbmcgui.ListItem(label=__language__( 32112 )) ] # Main menu
        allLabelIDs = [ "mainmenu" ]
        if isNode:
            allMenuItems.append( xbmcgui.ListItem(label=__language__( 32113 ) ) ) # Main menu + autofill submenu
            allLabelIDs.append( "mainmenu" )

        # Get main menu items
        menuitems = DATA._get_shortcuts( "mainmenu", processShortcuts = False )
        DATA._clear_labelID()
        for menuitem in menuitems.findall( "shortcut" ):
            # Get existing items labelID's
            allMenuItems.append( xbmcgui.ListItem(label=DATA.local( menuitem.find( "label" ).text )[2], iconImage=menuitem.find( "icon" ).text) )
            allLabelIDs.append( DATA._get_labelID( DATA.local( menuitem.find( "label" ).text )[3], menuitem.find( "action" ).text ) )

        # Close progress dialog
        dialog.close()

        # Show a select dialog so the user can pick where in the menu to add the item
        w = ShowDialog( "DialogSelect.xml", __cwd__, listing=allMenuItems, windowtitle=__language__( 32114 ) )
        w.doModal()
        selectedMenu = w.result
        del w
        
        if selectedMenu == -1 or selectedMenu is None:
            # User cancelled
            return

        action = paths[ 0 ]
        if isNode and selectedMenu == 1:
            # We're auto-filling submenu, so add all sub-nodes as possible default actions
            paths = paths + nodePaths

        if len( paths ) > 1:
            # There are multiple actions to choose from
            selectedAction = xbmcgui.Dialog().select( __language__( 32095 ), labels )
            
            if selectedAction == -1 or selectedAction is None:
                # User cancelled
                return True

            action = paths[ selectedAction ]

        # Add the shortcut to the menu the user has selected
        # Load existing main menu items
        menuitems = DATA._get_shortcuts( allLabelIDs[ selectedMenu ], processShortcuts = False )
        DATA._clear_labelID()
            
        # Generate a new labelID
        newLabelID = DATA._get_labelID( label, action )
        
        # Write the updated mainmenu.DATA.xml
        newelement = xmltree.SubElement( menuitems.getroot(), "shortcut" )
        xmltree.SubElement( newelement, "label" ).text = label
        xmltree.SubElement( newelement, "label2" ).text = "32024" # Custom shortcut
        xmltree.SubElement( newelement, "icon" ).text = icon
        xmltree.SubElement( newelement, "thumb" )
        xmltree.SubElement( newelement, "action" ).text = action
        
        DATA.indent( menuitems.getroot() )
        path = xbmc.translatePath( os.path.join( "special://profile", "addon_data", __addonid__, "%s.DATA.xml" %( DATA.slugify( allLabelIDs[ selectedMenu ], True ) ) ).encode('utf-8') )
        menuitems.write( path, encoding="UTF-8" )

        if isNode and selectedMenu == 1:
            # We're also going to write a submenu
            menuitems = xmltree.ElementTree( xmltree.Element( "shortcuts" ) )
            
            for item in json_response['result']['files']:
                if item[ "filetype" ] == "directory":
                    newelement = xmltree.SubElement( menuitems.getroot(), "shortcut" )
                    xmltree.SubElement( newelement, "label" ).text = item[ "label" ]
                    xmltree.SubElement( newelement, "label2" ).text = "32024" # Custom shortcut
                    xmltree.SubElement( newelement, "icon" ).text = item[ "thumbnail" ]
                    xmltree.SubElement( newelement, "thumb" )
                    xmltree.SubElement( newelement, "action" ).text = "ActivateWindow(%s,%s,return)" %( window, item[ "file" ] )
                
            DATA.indent( menuitems.getroot() )
            path = xbmc.translatePath( os.path.join( "special://profile", "addon_data", __addonid__, DATA.slugify( newLabelID, True ) + ".DATA.xml" ).encode('utf-8') )
            menuitems.write( path, encoding="UTF-8" )
        
        # Mark that the menu needs to be rebuilt
        xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-reloadmainmenu", "True" )
        
        # And tell the user it all worked
        xbmcgui.Dialog().ok( __addon__.getAddonInfo( "name" ), __language__(32090) )

    def extractID( self, path ):
        # Extract the ID of an item from its path
        itemID = path
        if "?" in itemID:
            itemID = itemID.rsplit( "?", 1 )[ 0 ]
        if itemID.endswith( "/" ): itemID = itemID[ :-1 ]
        itemID = itemID.rsplit( "/", 1 )[ 1 ]
        return itemID

# ============================
# === PRETTY SELECT DIALOG ===
# ============================
            
class ShowDialog( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.listing = kwargs.get( "listing" )
        self.windowtitle = kwargs.get( "windowtitle" )
        self.getmore = kwargs.get( "getmore" )
        self.result = -1

    def onInit(self):
        try:
            self.fav_list = self.getControl(6)
            self.getControl(3).setVisible(False)
        except:
            print_exc()
            self.fav_list = self.getControl(3)

        if self.getmore == True:
            self.getControl(5).setLabel(xbmc.getLocalizedString(21452))
        else:
            self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(self.windowtitle)

        # Set Cancel label (Kodi 17+)
        if int( __xbmcversion__ ) >= 17:
            try:
                self.getControl(7).setLabel(xbmc.getLocalizedString(222))
            except:
                log( "Unable to set label for control 7" )

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
        if controlID == 5:
            self.result = -2
        elif controlID == 6 or controlID == 3:
            num = self.fav_list.getSelectedPosition()
            self.result = num
        else:
            self.result = -1

        self.close()

    def onFocus(self, controlID):
        pass


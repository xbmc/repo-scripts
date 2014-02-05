# coding=utf-8
import os, sys
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, urllib, xbmcvfs
import xml.etree.ElementTree as xmltree
import cPickle as pickle
import cProfile
import pstats
import random
import time
from time import gmtime, strftime
from datetime import datetime
from traceback import print_exc

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id').decode( 'utf-8' )
__addonversion__ = __addon__.getAddonInfo('version')
__language__     = __addon__.getLocalizedString
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__addonname__    = __addon__.getAddonInfo('name').decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).encode('utf-8'), __addonid__.encode( 'utf-8' ) ).decode('utf-8')
__profilepath__  = xbmc.translatePath( "special://profile/" ).decode('utf-8')
__skinpath__     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')
__defaultpath__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'shortcuts').encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode('utf-8')
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)
        
class Main:
    # MAIN ENTRY POINT
    def __init__(self):
        self._parse_argv()
        self.WINDOW = xbmcgui.Window(10000)
        
        # Check if the user has changed skin or profile
        if self.WINDOW.getProperty("skinsettings-currentSkin-Path") and self.WINDOW.getProperty("skinsettings-currentProfile-Path"):
            if self.WINDOW.getProperty("skinsettings-currentSkin-Path") != xbmc.getSkinDir() or self.WINDOW.getProperty("skinsettings-currentProfile-Path") != __profilepath__:
                self.reset_window_properties()
                self.WINDOW.setProperty("skinsettings-currentSkin-Path", xbmc.getSkinDir() )
                self.WINDOW.setProperty("skinsettings-currentProfile-Path", __profilepath__ )
        else:
            self.WINDOW.setProperty("skinsettings-currentSkin-Path", xbmc.getSkinDir() )
            self.WINDOW.setProperty("skinsettings-currentProfile-Path", __profilepath__ )
                
        
        # Create datapath if not exists
        if not xbmcvfs.exists(__datapath__):
            xbmcvfs.mkdir(__datapath__)
        
        # Perform action specified by user
        if not self.TYPE:
            line1 = "This addon is for skin developers, and requires skin support"
            xbmcgui.Dialog().ok(__addonname__, line1)
            
        if self.TYPE=="launch":
            self._launch_shortcut( self.PATH )
        if self.TYPE=="manage":
            self._manage_shortcuts( self.GROUP )
        if self.TYPE=="list":
            self._list_shortcuts( self.GROUP )
        if self.TYPE=="submenu":
            self._list_submenu( self.MENUID, self.LEVEL )
        if self.TYPE=="settings":
            self._manage_shortcut_links() 
        if self.TYPE=="resetall":
            self._reset_all_shortcuts()

    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
            self.TYPE = params.get( "type", "" )
        except:
            #print_exc()
            try:
                params = dict( arg.split( "=" ) for arg in sys.argv[ 2 ].split( "&" ) )
                self.TYPE = params.get( "?type", "" )
            except:
                self.TYPE = ""
                params = {}
        
        self.GROUP = params.get( "group", "" )
        self.PATH = params.get( "path", "" )
        self.MENUID = params.get( "mainmenuID", "0" )
        self.LEVEL = params.get( "level", "" )
        self.CUSTOMID = params.get( "customid", "" )
    
    
    # -----------------
    # PRIMARY FUNCTIONS
    # -----------------

    def _launch_shortcut( self, path ):
        log( "### Launching shortcut" )
        
        runDefaultCommand = True
        action = urllib.unquote( self.PATH )
        
        # Load overrides
        trees = [self._load_overrides_skin(), self._load_overrides_user()]
        
        for tree in trees:
            if runDefaultCommand == True:
                if tree is not None:
                    #tree = xmltree.parse( path )
                    # Search for any overrides
                    elems = tree.findall( 'override' )
                    for elem in elems:
                        if elem.attrib.get( 'action' ) == action:
                            runCustomCommand = True
                            
                            # Check any conditions
                            conditions = elem.findall('condition')
                            for condition in conditions:
                                if xbmc.getCondVisibility( condition.text ) == False:
                                    runCustomCommand = False
                                    break
                            
                            # If any and all conditions have been met, run actions
                            if runCustomCommand == True:
                                actions = elem.findall( 'action' )
                                for action in actions:
                                    runDefaultCommand = False
                                    log( "Launching: " + action.text )
                                    xbmc.executebuiltin( action.text )
                                break
                                
        # If we haven't overridden the command, run the original
        if runDefaultCommand == True:
            log( "Launching: " + urllib.unquote(self.PATH) )
            xbmc.executebuiltin( urllib.unquote(self.PATH) )
            
        # Tell XBMC not to try playing any media
        xbmcplugin.setResolvedUrl( handle=int( sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem() )
        
    
    def _manage_shortcuts( self, group ):
        import gui
        ui= gui.GUI( "script-skinshortcuts.xml", __cwd__, "default", group=group )
        ui.doModal()
        del ui
        
        # Update home window property (used to automatically refresh type=settings)
        xbmcgui.Window( 10000 ).setProperty( "skinshortcuts",strftime( "%Y%m%d%H%M%S",gmtime() ) )
        
        # Clear window properties for this group, and for backgrounds, widgets, properties
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-" + group )        
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsWidgets" )        
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsCustomProperties" )        
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsBackgrounds" )        
        

    def _list_shortcuts( self, group ):
        log( "### Listing shortcuts ..." )
        if group == "":
            log( "### - NO GROUP PASSED")
            # Return an empty list
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
            return None
        
        # Load shortcuts and overrides
        listitems = self._get_shortcuts( group )
        saveItems = []
        
        i = 0
        
        for item in listitems:
            i += 1
            # Generate a listitem
            path = sys.argv[0].decode( 'utf-8' ) + "?type=launch&path=" + item[4] + "&group=" + self.GROUP
            
            listitem = xbmcgui.ListItem(label=item[0], label2=item[1], iconImage=item[2], thumbnailImage=item[3])
            listitem.setProperty( 'IsPlayable', 'True')
            listitem.setProperty( "labelID", item[5].encode('utf-8') )
            listitem.setProperty( "action", urllib.unquote( item[4] ) )
            listitem.setProperty( "group", group )
            listitem.setProperty( "path", path )
            
            # Set an additional property to use for inbuilt submenu visibility
            listitem.setProperty( "submenuVisibility", str( i ) )
            
            # Localize label2 (type of shortcut)
            if not item[1].find( "::SCRIPT::" ) == -1:
                listitem.setLabel2( __language__( int( item[1][10:] ) ) )
                            
            # Add additional properties
            if len( item[6] ) != 0:
                for property in item[6]:
                    listitem.setProperty( property[0], property[1] )
                    log( "Additional property: " + property[0] + " = " + property[1] )
            
            saveItems.append( ( path, listitem ) )
        
        # Return the list
        xbmcplugin.addDirectoryItems( handle=int(sys.argv[1]), items=saveItems )
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
                
    def _list_submenu( self, mainmenuID, levelInt ):
        log( "### Listing submenu ..." )
        if mainmenuID == "0":
            log( "### - NO MAIN MENU ID PASSED")
            # Return an empty list
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
            return None
            
        fullMenu = True
        mainmenuListItems = []
        if self.GROUP:
            # Retrieve passed main menu items
            groups = self.GROUP.split( ",")
            for group in groups:
                mainmenuListItems.append( group )
            fullMenu = False
        else:
            # Load shortcuts for the main menu
            mainmenuListItems = self._get_shortcuts( "mainmenu" )
            
        log( repr( mainmenuListItems ) )
        saveItems = []
        
        i = 0
        
        for mainmenuItem in mainmenuListItems:
            i += 1
            # Load menu for each labelID
            mainmenuLabelID = mainmenuItem
            log( mainmenuLabelID )
            if fullMenu == True:
                mainmenuLabelID = mainmenuItem[5].encode( 'utf-8' )
                
            if levelInt == "":
                listitems = self._get_shortcuts( mainmenuLabelID )
            else:
                listitems = self._get_shortcuts( mainmenuLabelID + "." + levelInt )
            for item in listitems:
                path = sys.argv[0].decode('utf-8') + "?type=launch&path=" + item[4].encode('utf-8') + "&group=" + mainmenuLabelID.decode('utf-8')
                
                listitem = xbmcgui.ListItem(label=item[0], label2=item[1], iconImage=item[2], thumbnailImage=item[3])
                
                listitem.setProperty('IsPlayable', 'True')
                listitem.setProperty( "labelID", item[5].encode('utf-8') )
                listitem.setProperty( "action", urllib.unquote( item[4] ) )
                listitem.setProperty( "group", mainmenuLabelID.decode('utf-8') )
                listitem.setProperty( "path", path )
                
                if fullMenu == True:
                    listitem.setProperty( "node.visible", "StringCompare(Container(" + mainmenuID + ").ListItem.Property(submenuVisibility)," + str( i ) + ")" )
                else:
                    listitem.setProperty( "node.visible", "StringCompare(Container(" + mainmenuID + ").ListItem.Property(submenuVisibility)," + mainmenuLabelID + ")" )
                
                # Localize label2 (type of shortcut)
                if not listitem.getLabel2().find( "::SCRIPT::" ) == -1:
                    listitem.setLabel2( __language__( int( listitem.getLabel2()[10:] ) ) )
                
                # Add additional properties
                if len( item[6] ) != 0:
                    for property in item[6]:
                        listitem.setProperty( property[0], property[1] )
                        log( "Additional property: " + property[0] + " = " + property[1] )
                
                saveItems.append( ( path, listitem ) )
        
        # Return the list
        xbmcplugin.addDirectoryItems( handle=int(sys.argv[1]), items=saveItems )
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    

    def _reset_all_shortcuts( self ):
        log( "### Resetting all shortcuts" )
        dialog = xbmcgui.Dialog()
        
        # Ask the user if they're sure they want to do this
        if dialog.yesno(__language__(32037), __language__(32038)):
            for files in xbmcvfs.listdir( __datapath__ ):
                # Try deleting all shortcuts
                if files:
                    for file in files:
                        file_path = os.path.join( __datapath__, file.decode( 'utf-8' ) ).encode( 'utf-8' )
                        if xbmcvfs.exists( file_path ):
                            try:
                                xbmcvfs.delete( file_path )
                            except:
                                print_exc()
                                log( "### ERROR could not delete file %s" % file[0] )
        
            # Update home window property (used to automatically refresh type=settings)
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts",strftime( "%Y%m%d%H%M%S",gmtime() ) )   
            
            # Reset all window properties (so menus will be reloaded)
            self.reset_window_properties()
                
        # Tell XBMC not to try playing any media
        try:
            xbmcplugin.setResolvedUrl( handle=int( sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem() )
        except:
            log( "Not launched from a list item" )
    
    
    # ---------
    # LOAD DATA
    # ---------
    
    def _get_shortcuts( self, group ):
        # This will load the shortcut file, and save it as a window property
        # Additionally, if the override files haven't been loaded, we'll load them too
        try:
            returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-" + group )
            return pickle.loads( returnVal )
        except:
        
            paths = [os.path.join( __datapath__ , group.decode( 'utf-8' ) + ".shortcuts" ).encode('utf-8'), os.path.join( __skinpath__ , group.decode( 'utf-8' ) + ".shortcuts").encode('utf-8'), os.path.join( __defaultpath__ , group.decode( 'utf-8' ) + ".shortcuts" ).encode('utf-8') ]
            
            for path in paths:
                try:
                    # Try loading shortcuts
                    unprocessedList = eval( xbmcvfs.File( path ).read() )
                    processedList = self._process_shortcuts( unprocessedList, group )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-" + group, pickle.dumps( processedList ) )
                    return processedList
                except:
                    log( "No file %s" % path )    
                
        # No file loaded
        xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-" + group, pickle.dumps( [] ) )
        return [] 
                
            
    def _process_shortcuts( self, listitems, group ):
        # This function will process any graphics overrides provided by the skin, and return a set of listitems ready to be stored
        tree = self._load_overrides_skin()
        returnitems = []
        
        for item in listitems:
            # Generate the labelID
            label = item[0]
            labelID = item[0].replace(" ", "").lower()
            
            # Localize label & labelID
            if not label.find( "::SCRIPT::" ) == -1:
                labelID = self.createNiceName( label[10:] )
                label = __language__(int( label[10:] ) )
            elif not label.find( "::LOCAL::" ) == -1:
                labelID = self.createNiceName( label[9:] )
                label = xbmc.getLocalizedString(int( label[9:] ) )
            
            # If the user hasn't overridden the thumbnail, check for skin override
            if not len(item) == 6 or (len(item) == 6 and item[5] == "True"):
                if tree is not None:
                    elems = tree.findall('thumbnail')
                    for elem in elems:
                        if elem is not None and elem.attrib.get( 'labelID' ) == labelID:
                            item[3] = elem.text
                        if elem is not None and elem.attrib.get( 'image' ) == item[3]:
                            item[3] = elem.text
                        if elem is not None and elem.attrib.get( 'image' ) == item[2]:
                            item[2] = elem.text
                            
            # Get additional mainmenu properties
            additionalProperties = []
            if group == "mainmenu":
                visibilityCheck = self.checkVisibility( labelID )
                if visibilityCheck != "":
                    additionalProperties.append( ["node.visible", visibilityCheck] )
                widgetCheck = self.checkWidget( labelID )
                if widgetCheck != "":
                    additionalProperties.append( ["widget", widgetCheck] )
                backgroundCheck = self.checkBackground( labelID )
                if backgroundCheck != "":
                    additionalProperties.append( ["background", backgroundCheck] )
            customProperties = self.checkCustomProperties( labelID )
            if len( customProperties ) != 0:
                for customProperty in customProperties:
                    additionalProperties.append( [customProperty[0], customProperty[1]] )

            # Add item
            returnitems.append( [label, item[1], item[2], item[3], item[4], labelID, additionalProperties] )
            #returnitems.append( item )
                
        return returnitems            
      
      
    def _load_overrides_skin( self ):
        # If we haven't already loaded skin overrides, or if the skin has changed, load the overrides file
        if not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-skin-data" ) or not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-skin" ) == __skinpath__:
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-skin", __skinpath__ )
            overridepath = os.path.join( __skinpath__ , "overrides.xml" )
            if xbmcvfs.exists(overridepath):
                try:
                    tree = xmltree.parse( overridepath )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-skin-data", pickle.dumps( tree ) )
                    return tree
                except:
                    print_exc()
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-skin-data", "No overrides" )
                    return None
            else:
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-skin-data", "No overrides" )
                return None
   
        # Return the overrides
        returnData = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-skin-data" )
        if returnData == "No overrides":
            return None
        else:
            return pickle.loads( returnData )


    def _load_overrides_user( self ):
        # If we haven't already loaded user overrides
        if not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user-data" ) or not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user" ) == __profilepath__:
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user", __profilepath__ )
            overridepath = os.path.join( __profilepath__ , "overrides.xml" )
            if xbmcvfs.exists(overridepath):
                try:
                    tree = xmltree.parse( overridepath )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user-data", pickle.dumps( tree ) )
                    return tree
                    #file = xbmcvfs.File( overridepath )
                    #xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user-data", pickle.dumps( file.read().encode( 'utf-8' ) ) )
                    #file.close
                except:
                    print_exc()
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user-data", "No overrides" )
            else:
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user-data", "No overrides" )
                
        # Return the overrides
        returnData = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user-data" )
        if returnData == "No overrides":
            return None
        else:
            #return xmltree.parse( pickle.loads( returnData ) )
            return pickle.loads( returnData )
    
    
    # ----------------
    # SKINSETTINGS.XML
    # ----------------
    
    def _manage_shortcut_links ( self ):
        log( "### Generating list for skin settings" )
        pathAddition = ""
        
        # Create link to manage main menu
        if self.LEVEL == "":
            path = sys.argv[0].decode('utf-8') + "?type=launch&path=" + urllib.quote( "RunScript(script.skinshortcuts,type=manage&group=mainmenu)" )
            displayLabel = self._get_customised_settings_string("main")
            listitem = xbmcgui.ListItem(label=displayLabel, label2="", iconImage="DefaultShortcut.png", thumbnailImage="DefaultShortcut.png")
            listitem.setProperty('isPlayable', 'False')
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=listitem, isFolder=False)
        else:
            pathAddition = "." + self.LEVEL
        
        # Set path based on user defined mainmenu, then skin-provided, then script-provided
        if xbmcvfs.exists( os.path.join( __datapath__ , "mainmenu.shortcuts" ) ):
            # User defined shortcuts
            path = os.path.join( __datapath__ , "mainmenu.shortcuts" )
        elif xbmcvfs.exists( os.path.join( __skinpath__ , "mainmenu.shortcuts" ) ):
            # Skin-provided defaults
            path = os.path.join( __skinpath__ , "mainmenu.shortcuts" )
        elif xbmcvfs.exists( os.path.join( __defaultpath__ , "mainmenu.shortcuts" ) ):
            # Script-provided defaults
            path = os.path.join( __defaultpath__ , "mainmenu.shortcuts" )
        else:
            # No custom shortcuts or defaults available
            path = ""
            
        if not path == "":
            try:
                # Try loading shortcuts
                file = xbmcvfs.File( path )
                loaditems = eval( file.read() )
                file.close()
                
                listitems = []
                
                for item in loaditems:
                    itemEncoded = item[0].encode( 'utf-8' )
                    path = sys.argv[0].decode('utf-8') + "?type=launch&path=" + urllib.quote( "RunScript(script.skinshortcuts,type=manage&group=" + itemEncoded + pathAddition + ")" )
                    
                    # Get localised label
                    if not item[0].find( "::SCRIPT::" ) == -1:
                        localLabel = __language__(int( item[0][10:] ) )
                        path = sys.argv[0].decode('utf-8') + "?type=launch&path=" + urllib.quote( "RunScript(script.skinshortcuts,type=manage&group=" + self.createNiceName( item[0][10:] ).encode("ascii", "xmlcharrefreplace") + pathAddition + ")" )
                    elif not item[0].find( "::LOCAL::" ) == -1:
                        localLabel = xbmc.getLocalizedString(int( item[0][9:] ) )
                        path = sys.argv[0].decode('utf-8') + "?type=launch&path=" + urllib.quote( "RunScript(script.skinshortcuts,type=manage&group=" + self.createNiceName( item[0][9:] ).encode("ascii", "xmlcharrefreplace") + pathAddition + ")" )
                    else:
                        localLabel = item[0]
                        
                    # Get display label
                    displayLabel = self._get_customised_settings_string("submenu").replace("::MENUNAME::", localLabel)
                    
                    #listitem = xbmcgui.ListItem(label=__language__(32036) + item[0], label2="", iconImage="", thumbnailImage="")
                    listitem = xbmcgui.ListItem(label=displayLabel, label2="", iconImage="", thumbnailImage="")
                    listitem.setProperty('isPlayable', 'True')
                        
                    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=listitem)

            except:
                print_exc()
                log( "### ERROR could not load file %s" % path )
        
        # Add a link to reset all shortcuts
        if self.LEVEL == "":
            path = sys.argv[0].decode('utf-8') + "?type=resetall"
            displayLabel = self._get_customised_settings_string("reset")
            listitem = xbmcgui.ListItem(label=displayLabel, label2="", iconImage="DefaultShortcut.png", thumbnailImage="DefaultShortcut.png")
            listitem.setProperty('isPlayable', 'True')
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=listitem)
        
        # Save the list
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    
    def _get_customised_settings_string( self, group ):
        # This function will return the customised settings string for the given group
        tree = self._load_overrides_skin()
        if tree is not None:
            elems = tree.findall('settingslabel')
            for elem in elems:
                if elem is not None and elem.attrib.get( 'type' ) == group:
                    if self.LEVEL != "":
                        if elem.attrib.get( 'level' ) == self.LEVEL:
                            if elem.text.isdigit():
                                return xbmc.getLocalizedString( int( elem.text ) )
                            else:
                                return elem.text
                    else:
                        if 'level' not in elem.attrib:
                            if elem.text.isdigit():
                                return xbmc.getLocalizedString( int( elem.text ) )
                            else:
                                return elem.text
                                
        # If we get here, no string has been specified in overrides.xml
        if group == "main":
            return __language__(32035)
        elif group == "submenu" and self.LEVEL == "":
            return __language__(32036)
        elif group == "submenu" and self.LEVEL != "":
            return "::MENUNAME::"
        elif group == "reset":
            return __language__(32037)
        return "::MENUNAME::"
    
    
    # ----------------
    # WIDGET FUNCTIONS
    # ----------------    
    
    def _get_widgets( self ):
        # This will load the shortcut file, and save it as a window property
        # Additionally, if the override files haven't been loaded, we'll load them too
        
        try:
            returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcutsWidgets" )
            return pickle.loads( returnVal )
        except:
            # Try to load user-defined widgets
            if xbmcvfs.exists( os.path.join( __datapath__ , xbmc.getSkinDir() + ".widgets" ) ):
                path = os.path.join( __datapath__ , xbmc.getSkinDir() + ".widgets" )
                try:
                    # Try loading widgets
                    contents = eval( xbmcvfs.File( path ).read() )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsWidgets", pickle.dumps( contents ) )
                    return contents
                except:
                    print_exc()
                    log( "### ERROR could not load file %s" % path )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsWidgets", pickle.dumps( [] ) )
                    return []

            else:
                # User hasn't set any widgets, so we'll load them from the
                # skins overrides.xml instead
                tree = self._load_overrides_skin()
                widgets = []
                
                if tree is not None:
                    elems = tree.findall('widgetdefault')
                    for elem in elems:
                        widgets.append( [ elem.attrib.get( 'labelID' ), elem.text ] )
                
                # Save the widgets to a window property               
                xbmcgui.Window( 10000 ).setProperty( "skinshortcutsWidgets", pickle.dumps( widgets ) )
                return widgets


    def _get_customproperties( self ):
        # This will load the shortcut file, and save it as a window property
        # Additionally, if the override files haven't been loaded, we'll load them too
        
        try:
            returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcutsCustomProperties" )
            return pickle.loads( returnVal )
        except:
            # Try to load user-defined custom properties
            if xbmcvfs.exists( os.path.join( __datapath__ , xbmc.getSkinDir() + ".customproperties" ) ):
                path = os.path.join( __datapath__ , xbmc.getSkinDir() + ".customproperties" )
                try:
                    # Try loading custom properties
                    contents = eval( xbmcvfs.File( path ).read() )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsCustomProperties", pickle.dumps( contents ) )
                    return contents
                except:
                    print_exc()
                    log( "### ERROR could not load file %s" % path )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsCustomProperties", pickle.dumps( [] ) )
                    return []

            else:
                # User hasn't set any custom properties, so we'll load them from the
                # skins overrides.xml instead
                tree = self._load_overrides_skin()
                properties = []
                
                if tree is not None:
                    elems = tree.findall('propertydefault')
                    for elem in elems:
                        properties.append( [ elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text ] )
                
                # Save the custom properties to a window property               
                xbmcgui.Window( 10000 ).setProperty( "skinshortcutsCustomProperties", pickle.dumps( properties ) )
                return properties
    
    
    # --------------------
    # BACKGROUND FUNCTIONS
    # --------------------    
    
    def _get_backgrounds( self ):
        # This function will load users backgrounds settings
        try:
            returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcutsBackgrounds" )
            return pickle.loads( returnVal )
        except:
            # Try to load user-defined widgets
            if xbmcvfs.exists( os.path.join( __datapath__ , xbmc.getSkinDir() + ".backgrounds" ) ):
                path = os.path.join( __datapath__ , xbmc.getSkinDir() + ".backgrounds" )
                try:
                    # Try loading widgets
                    contents = eval( xbmcvfs.File( path ).read() )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsBackgrounds", pickle.dumps( contents ) )
                    return contents
                except:
                    print_exc()
                    log( "### ERROR could not load file %s" % path )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsBackgrounds", pickle.dumps( [] ) )
                    return []

            else:
                # User hasn't set any widgets, so we'll load them from the
                # skins overrides.xml instead
                tree = self._load_overrides_skin()
                backgrounds = []
                
                if tree is not None:
                    elems = tree.findall('backgrounddefault')
                    for elem in elems:
                        backgrounds.append( [ elem.attrib.get( 'labelID' ), elem.text ] )
                
                # Save the widgets to a window property               
                xbmcgui.Window( 10000 ).setProperty( "skinshortcutsBackgrounds", pickle.dumps( backgrounds ) )
                return backgrounds
                
    
    # ----------------
    # HELPER FUNCTIONS
    # ----------------
    
    def checkVisibility ( self, item ):
        # Return whether mainmenu items should be displayed
        if item == "movies":
            return "Library.HasContent(Movies)"
        elif item == "tvshows":
            return "Library.HasContent(TVShows)"
        if item == "livetv":
            return "System.GetBool(pvrmanager.enabled)"
        elif item == "musicvideos":
            return "Library.HasContent(MusicVideos)"
        elif item == "music":
            return "Library.HasContent(Music)"
        elif item == "weather":
            return "!IsEmpty(Weather.Plugin)"
        elif item == "dvd":
            return "System.HasMediaDVD"
        else:
            return ""
            
    
    def checkWidget( self, item ):
        # Return any widget for mainmenu items
        currentWidgets = ( self._get_widgets() )
        
        # Loop through current widgets, looking for the current item
        for currentWidget in currentWidgets:
            if currentWidget[0].encode('utf-8') == item:
                return currentWidget[1]
                
        return ""
        
    
    def checkBackground( self, item ):
        # Return any widget for mainmenu items
        currentBackgrounds = ( self._get_backgrounds() )
        
        # Loop through current widgets, looking for the current item
        for currentBackground in currentBackgrounds:
            if currentBackground[0].encode('utf-8') == item:
                return currentBackground[1]
                
        return ""
        
    
    def checkCustomProperties( self, item ):
        # Return any custom properties for mainmenu items
        currentProperties = ( self._get_customproperties() )
        
        # Loop through current properties, looking for the current item
        returnVals = []
        for currentProperty in currentProperties:
            if currentProperty[0].encode('utf-8') == item:
                returnVals.append( [currentProperty[1], currentProperty[2]] )
                
        return returnVals

     
    def createNiceName ( self, item ):
        # Translate certain localized strings into non-localized form for labelID
        if item == "10006":
            return "videos"
        if item == "342":
            return "movies"
        if item == "20343":
            return "tvshows"
        if item == "32022":
            return "livetv"
        if item == "10005":
            return "music"
        if item == "20389":
            return "musicvideos"
        if item == "10002":
            return "pictures"
        if item == "12600":
            return "weather"
        if item == "10001":
            return "programs"
        if item == "32032":
            return "dvd"
        if item == "10004":
            return "settings"
        else:
            return item
                        
    
    def reset_window_properties( self ):
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-skin" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsWidgets" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsBackgrounds" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-mainmenu" )
        listitems = self._get_shortcuts( "mainmenu" )
        for item in listitems:
            # Get labelID so we can check shortcuts for this menu item
            groupName = item[0].replace(" ", "").lower().encode('utf-8')
            
            # Localize strings
            if not item[0].find( "::SCRIPT::" ) == -1:
                groupName = self.createNiceName( item[0][10:] ).encode('utf-8')
            elif not item[0].find( "::LOCAL::" ) == -1:
                groupName = self.createNiceName( item[0][9:] ).encode('utf-8')
                
            # Clear the property
            xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-" + groupName )
            
            # Clear any additional submenus
            i = 0
            finished = False
            while finished == False:
                i = i + 1
                if xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-" + groupName + "." + str( i ) ):
                    xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-" + groupName + "." + str( i ) )
                else:
                    finished = True

                    
if ( __name__ == "__main__" ):
    log('script version %s started' % __addonversion__)
    
    # Profiling
    #filename = os.path.join( __datapath__, strftime( "%Y%m%d%H%M%S",gmtime() ) + "-" + str( random.randrange(0,100000) ) + ".log" )
    #cProfile.run( 'Main()', filename )
    
    #stream = open( filename + ".txt", 'w')
    #p = pstats.Stats( filename, stream = stream )
    #p.sort_stats( "cumulative" )
    #p.print_stats()
    
    # No profiling
    Main()

    
    log('script stopped')
# coding=utf-8
import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
from xml.dom.minidom import parse
from xml.sax.saxutils import escape as escapeXML
import thread
from traceback import print_exc
from unicodeutils import try_decode
import calendar
from time import gmtime, strftime
import random

import datafunctions
DATA = datafunctions.DataFunctions()

import library
LIBRARY = library.LibraryFunctions()

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

ADDON        = sys.modules[ "__main__" ].ADDON
ADDONID      = sys.modules[ "__main__" ].ADDONID
CWD          = sys.modules[ "__main__" ].CWD
DATAPATH     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), ADDONID )
SKINPATH     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')
DEFAULTPATH  = xbmc.translatePath( os.path.join( CWD, 'resources', 'shortcuts').encode("utf-8") ).decode("utf-8")
LANGUAGE     = ADDON.getLocalizedString
KODIVERSION  = xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0]

ACTION_CANCEL_DIALOG = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
ACTION_CONTEXT_MENU = ( 117, )

ISEMPTY = "IsEmpty"
if int( KODIVERSION ) >= 17:
    ISEMPTY = "String.IsEmpty"

if not xbmcvfs.exists(DATAPATH):
    xbmcvfs.mkdir(DATAPATH)

def log(txt):
    if ADDON.getSetting( "enable_logging" ) == "true":
        try:
            if isinstance (txt,str):
                txt = txt.decode('utf-8')
            message = u'%s: %s' % (ADDONID, txt)
            xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)
        except:
            pass

def is_hebrew(text):
    if type(text) != unicode:
        text = text.decode('utf-8')
    for chr in text:
        if ord(chr) >= 1488 and ord(chr) <= 1514:
            return True
    return False

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        self.group = kwargs[ "group" ]
        try:
            self.defaultGroup = kwargs[ "defaultGroup" ]
            if self.defaultGroup == "":
                self.defaultGroup = None
        except:
            self.defaultGroup = None
        self.nolabels = kwargs[ "nolabels" ]
        self.groupname = kwargs[ "groupname" ]
        self.shortcutgroup = 1
        
        # Empty arrays for different shortcut types
        self.thumbnailBrowseDefault = None
        self.thumbnailNone = None
        self.backgroundBrowse = None
        self.backgroundBrowseDefault = None
        self.widgetPlaylists = False
        self.widgetPlaylistsType = None
        self.widgetRename = True
        
        # Variables for overrides
        self.onBack = {}
        self.saveWithProperty = []

        # Has skin overriden GUI 308
        self.alwaysReset = False
        self.alwaysRestore = False
        
        self.allListItems = []

        # Additional button ID's we'll handle for setting custom properties
        self.customPropertyButtons = {}
        self.customToggleButtons = {}

        # Context menu
        self.contextControls = []
        self.contextItems = []

        # Onclicks
        self.customOnClick = {}

        self.windowProperties = {}
        
        self.changeMade = False
        
        log( 'Management module loaded' )
        
    def onInit( self ):
        if self.group == '':
            self._close()
        else:
            self.window_id = xbmcgui.getCurrentWindowDialogId()
            self.currentWindow = xbmcgui.Window( xbmcgui.getCurrentWindowDialogId() )
            xbmcgui.Window(self.window_id).setProperty('groupname', self.group)
            if self.groupname is not None:
                xbmcgui.Window( self.window_id ).setProperty( 'groupDisplayName', self.groupname )
            
            # Load widget and background names
            self._load_overrides()

            # Load context menu options
            self._load_overrides_context()

            # Load additional onclick overrides
            self._load_overrides_onclick()

            # Load additional button ID's we'll handle for custom properties
            self._load_customPropertyButtons()

            # Load current shortcuts
            self.load_shortcuts()
                        
            # Set window title label
            try:
                if self.getControl( 500 ).getLabel() == "":
                    if self.group == "mainmenu":
                        self.getControl( 500 ).setLabel( LANGUAGE(32071) )
                    elif self.groupname is not None:
                        self.getControl( 500 ).setLabel( LANGUAGE(32080).replace( "::MENUNAME::", self.groupname ) )
                    else:
                        self.getControl( 500 ).setLabel( LANGUAGE(32072) )
            except:
                pass
                
            # Set enabled condition for various controls
            has111 = True
            try:
                self.getControl( 111 ).setEnableCondition( "%s(Container(211).ListItem.Property(LOCKED))" %( ISEMPTY ) )
            except:
                has111 = False
            try:
                self.getControl( 302 ).setEnableCondition( "%s(Container(211).ListItem.Property(LOCKED))" %( ISEMPTY ) )
            except:
                pass
            try:
                self.getControl( 307 ).setEnableCondition( "%s(Container(211).ListItem.Property(LOCKED))" %( ISEMPTY ) )
            except:
                pass
            try:
                self.getControl( 401 ).setEnableCondition( "%s(Container(211).ListItem.Property(LOCKED))" %( ISEMPTY ) )
            except:
                pass
            
            # Set button labels
            if self.nolabels == "false":
                try:
                    if self.getControl( 301 ).getLabel() == "":
                        self.getControl( 301 ).setLabel( LANGUAGE(32000) )
                except:
                    log( "No add shortcut button on GUI (id 301)" )
                try:
                    if self.getControl( 302 ).getLabel() == "":
                        self.getControl( 302 ).setLabel( LANGUAGE(32001) )
                except:
                    log( "No delete shortcut button on GUI (id 302)" )
                try:
                    if self.getControl( 303 ).getLabel() == "":
                        self.getControl( 303 ).setLabel( LANGUAGE(32002) )
                except:
                    log( "No move shortcut up button on GUI (id 303)" )
                try:
                    if self.getControl( 304 ).getLabel() == "":
                        self.getControl( 304 ).setLabel( LANGUAGE(32003) )
                except:
                    log( "No move shortcut down button on GUI (id 304)" )
                
                try:
                    if self.getControl( 305 ).getLabel() == "":
                        self.getControl( 305 ).setLabel( LANGUAGE(32025) )
                except:
                    log( "Not set label button on GUI (id 305)" )
                    
                try:
                    if self.getControl( 306 ).getLabel() == "":
                        self.getControl( 306 ).setLabel( LANGUAGE(32026) )
                except:
                    log( "No edit thumbnail button on GUI (id 306)" )
                    
                try:
                    if self.getControl( 307 ).getLabel() == "":
                        self.getControl( 307 ).setLabel( LANGUAGE(32027) )
                except:
                    log( "Not edit action button on GUI (id 307)" )
                    
                try:
                    if self.getControl( 308 ).getLabel() == "":
                        self.getControl( 308 ).setLabel( LANGUAGE(32028) )
                except:
                    log( "No reset shortcuts button on GUI (id 308)" )
                    
                try:
                    if self.getControl( 309 ).getLabel() == "":
                        self.getControl( 309 ).setLabel( LANGUAGE(32044) )
                    log( "Warning: Deprecated widget button (id 309)" )
                except:
                    pass
                try:
                    if self.getControl( 310 ).getLabel() == "":
                        self.getControl( 310 ).setLabel( LANGUAGE(32045) )
                except:
                    log( "No background button on GUI (id 310)" )
                try:
                    if self.getControl( 312 ).getLabel() == "":
                        self.getControl( 312 ).setLabel( LANGUAGE(32044) )
                except:
                    log( "No widget button on GUI (id 309)" )
                    
                try:
                    if self.getControl( 401 ).getLabel() == "":
                        self.getControl( 401 ).setLabel( LANGUAGE(32048) )
                except:
                    log( "No widget button on GUI (id 401)" )
                    
            # Load library shortcuts in thread
            thread.start_new_thread( LIBRARY.loadAllLibrary, () )
            
            if has111:
                try:
                    self._display_shortcuts()
                except:
                    pass

            # Clear window property indicating we're loading
            xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-loading" )


                
    # ======================
    # === LOAD/SAVE DATA ===
    # ======================

    
    def load_shortcuts( self, includeUserShortcuts = True, addShortcutsToWindow = True ):
        log( "Loading shortcuts" )
        DATA._clear_labelID()

        isSubLevel = False
        if "." in self.group and self.group.rsplit( ".", 1)[ 1 ].isdigit() and int( self.group.rsplit( ".", 1 )[ 1 ] ) in range( 1, 6 ):
            isSubLevel = True
        
        if includeUserShortcuts:
            shortcuts = DATA._get_shortcuts( self.group, defaultGroup = self.defaultGroup, isSubLevel = isSubLevel )
        else:
            shortcuts = DATA._get_shortcuts( self.group, defaultGroup = self.defaultGroup, defaultsOnly = True )
        
        #listitems = []
        for shortcut in shortcuts.getroot().findall( "shortcut" ):
            # Parse the shortcut, and add it to the list of shortcuts
            item = self._parse_shortcut( shortcut )
            self.allListItems.append( item[1] )
        
        # Add all visible shortcuts to control 211
        self._display_listitems()
        
    def _display_listitems( self, focus = None ):
        # Displays listitems that are visible from self.allListItems
        
        # Initial properties
        count = 0
        visible = False
        DATA._clear_labelID()
        listitems = []
        
        for listitem in self.allListItems:
            # Get icon overrides
            self._get_icon_overrides( listitem )
            
            # Set order index in case its changed
            listitem.setProperty( "skinshortcuts-orderindex", str( count ) )
            
            shouldDisplay = True
            # Check for a visibility condition
            if listitem.getProperty( "visible-condition" ):
                shouldDisplay = xbmc.getCondVisibility( listitem.getProperty( "visible-condition" ) )
                
            if shouldDisplay == True:
                visible = True
                listitems.append( listitem )
                
            # Increase our count
            count += 1

        # If there are no shortcuts, add a blank one
        if visible == False:
            listitem = xbmcgui.ListItem( LANGUAGE(32013), iconImage = "DefaultShortcut.png" )
            listitem.setProperty( "Path", 'noop' )
            listitem.setProperty( "icon", "DefaultShortcut.png" )
            listitem.setProperty( "skinshortcuts-orderindex", str( count ) )
            listitems.append( listitem )
            self.allListItems.append( listitem )

        self.getControl( 211 ).reset()
        self.getControl( 211 ).addItems( listitems )
        if focus is not None:
            self.getControl( 211 ).selectItem( focus )
        self._add_additional_properties()
              
    def _parse_shortcut( self, item ):
        # Parse a shortcut node
        localLabel = DATA.local( item.find( "label" ).text )
        localLabel2 = DATA.local( item.find( "label2" ).text )
        
        # Get icon and thumb (and set to None if there isn't any)
        icon = item.find( "icon" )
        
        if icon is not None and icon.text:
            icon = icon.text
        else:
            icon = "DefaultShortcut.png"
            
        thumb = item.find( "thumb" )
        if thumb is not None and thumb.text:
            thumb = thumb.text
        else:
            thumb = ""
            
        # If either localLabel[ 2 ] starts with a $, ask Kodi to parse it for us
        if localLabel[ 2 ].startswith( "$" ):
            localLabel[ 2 ] = xbmc.getInfoLabel( localLabel[ 2 ] )
        if localLabel2[ 2 ].startswith( "$" ):
            localLabel2[ 2 ] = xbmc.getInfoLabel( localLabel2[ 2 ] )
        
        # Create the list item
        listitem = xbmcgui.ListItem( label=localLabel[2], label2 = localLabel2[2], iconImage = xbmc.getInfoLabel(icon), thumbnailImage = xbmc.getInfoLabel(thumb) )
        listitem.setProperty( "localizedString", localLabel[0] )
        listitem.setProperty( "icon", icon )
        listitem.setProperty( "thumbnail", thumb )
        
        # Set the action
        action = item.find( "action" ).text
        self._add_additionalproperty( listitem, "translatedPath", action )
        if "special://skin/" in action:
            translate = xbmc.translatePath( "special://skin/" ).decode( "utf-8" )
            action = action.replace( "special://skin/", translate )
        
        listitem.setProperty( "path", action )
        listitem.setProperty( "displayPath", action )

        # Set the disabled property
        if item.find( "disabled" ) is not None:
            listitem.setProperty( "skinshortcuts-disabled", "True" )
        else:
            listitem.setProperty( "skinshortcuts-disabled", "False" )
        
        # If there's an overriden icon, use it
        overridenIcon = item.find( "override-icon" )
        if overridenIcon is not None:
            listitem.setIconImage( overridenIcon.text )
            listitem.setProperty( "icon", overridenIcon.text )
            listitem.setProperty( "original-icon", icon )
            
        # Set the labelID, displayID, shortcutType
        listitem.setProperty( "labelID", item.find( "labelID" ).text )
        listitem.setProperty( "defaultID", item.find( "defaultID" ).text )
        listitem.setProperty( "shortcutType", localLabel2[0] )
        
        # Set any visible condition
        isVisible = True
        visibleCondition = item.find( "visible" )
        if visibleCondition is not None:
            listitem.setProperty( "visible-condition", visibleCondition.text )
            isVisible = xbmc.getCondVisibility( visibleCondition.text )
        
        # Check if the shortcut is locked
        locked = item.find( "lock" )
        if locked is not None:
            if locked.text.lower() == "true" or locked.text == xbmc.getSkinDir():
                listitem.setProperty( "LOCKED", locked.text )
                
        # Additional properties
        additionalProperties = item.find( "additional-properties" )
        if additionalProperties is not None:
            listitem.setProperty( "additionalListItemProperties", additionalProperties.text )
        else:
            listitem.setProperty( "additionalListItemProperties", "[]" )
        self._add_additional_properties( listitem )
                
        return [ isVisible, listitem ]

    def _add_additional_properties( self, listitem = None ):
        allProps = {}
        backgroundName = None
        backgroundPlaylistName = None

        # If the listitem is None, grab the current listitem from 211
        if listitem is None:
            listitem = self.getControl( 211 ).getSelectedItem()

        # Process current properties
        currentProperties = listitem.getProperty( "skinshortcuts-allproperties" )
        if currentProperties != "":
            currentProperties = eval( currentProperties )
        else:
            currentProperties = {}

        # Process all custom properties
        customProperties = listitem.getProperty( "additionalListItemProperties" )
        if customProperties != "":
            customProperties = eval( customProperties )
            for customProperty in customProperties:
                if customProperty[1].startswith("$") and not customProperty[ 1 ].startswith( "$SKIN" ):
                    #Translate some listItem properties if needed so they're displayed correctly in the gui
                    allProps[ customProperty[ 0 ] ] = xbmc.getInfoLabel( customProperty[ 1 ] )
                else:
                    allProps[ customProperty[ 0 ] ] = DATA.local( customProperty[ 1 ] )[ 2 ]
                    if customProperty[ 1 ].isdigit():
                        allProps[ "%s-NUM" %( customProperty[ 0 ] ) ] = customProperty[ 1 ]
                
                # if this is backgroundName or backgroundPlaylistName, keep them so we can localise them properly
                if customProperty[0] == "backgroundName":
                    backgroundName = customProperty[1]
                if customProperty[1] == "backgroundPlaylistName":
                    backgroundPlaylistName = customProperty[1]
                
        # If we've kept backgroundName, localise it with the updated playlist name
        if backgroundName is not None and backgroundPlaylistName is not None:
            allProps[ "backgroundName" ] = DATA.local( backgroundName )[2].replace( "::PLAYLIST::", backgroundPlaylistName )

        # Get fallback properties
        fallbackProperties, fallbacks = DATA._getCustomPropertyFallbacks( self.group )

        # Add fallback properties
        for key in fallbackProperties:
            if key not in allProps.keys():
                # Check whether we have a fallback for the value
                for propertyMatch in fallbacks[ key ]:
                    matches = False
                    if propertyMatch[ 1 ] is None:
                        # This has no conditions, so it matched
                        matches = True
                    elif propertyMatch[ 1 ] in allProps.keys() and allProps[ propertyMatch[ 1 ] ] == propertyMatch[ 2 ]:
                        matches = True

                    if matches:
                        allProps[ key ] = propertyMatch[ 0 ]
                        break

        # Get property requirements
        otherProperties, requires, templateOnly = DATA._getPropertyRequires()

        # Remove any properties whose requirements haven't been met
        for key in otherProperties:
            if key in allProps.keys() and key in requires.keys() and requires[ key ] not in allProps.keys():
                # This properties requirements aren't met
                allProps.pop( key )
                if "%s-NUM" %( key ) in allProps.keys():
                    allProps.pop( "%s-NUM" %( key ) )

        # Save the new properties to the listitem
        listitem.setProperty( "skinshortcuts-allproperties", repr( allProps ) )
        added, removed, changed = self.DictDiffer( allProps, currentProperties )
        for key in added:
            listitem.setProperty( key, allProps[ key ] )
        for key in removed:
            if key not in allProps.keys(): continue
            listitem.setProperty( key, None )
        for key in changed:
            listitem.setProperty( key, allProps[ key ] )
        
        # Save the new properties to the window
        added, removed, changed = self.DictDiffer( allProps, self.windowProperties )
        for key in added:
            self.currentWindow.setProperty( key, allProps[ key ] )
        for key in removed:
            self.currentWindow.clearProperty( key )
        for key in changed:
            self.currentWindow.setProperty( key, allProps[ key ] )
        self.windowProperties = allProps

    def DictDiffer( self, current_dict, past_dict ):
        # Get differences between dictionaries
        self.current_dict, self.past_dict = current_dict, past_dict
        set_current, set_past = set(current_dict.keys()), set(past_dict.keys())
        intersect = set_current.intersection(set_past)

        #       Added                    Removed               Changed
        return( set_current - intersect, set_past - intersect, set(o for o in intersect if past_dict[o] != current_dict[o]) )

    def _get_icon_overrides( self, listitem, setToDefault = True, labelID = None ):
        # Start by getting the labelID
        if not labelID:
            labelID = listitem.getProperty( "localizedString" )
            if labelID == None or labelID == "":
                labelID = listitem.getLabel()
            labelID = DATA._get_labelID( DATA.local( labelID )[3], listitem.getProperty( "path" ) )
        
        # Retrieve icon
        icon = listitem.getProperty( "icon" )
        oldicon = None
        iconIsVar = False
        
        if listitem.getProperty( "untranslatedIcon" ):
            iconIsVar = True
        
        # If the icon is a VAR or an INFO, we're going to translate it and set the untranslatedIcon property
        if icon.startswith( "$" ):
            listitem.setProperty( "untranslatedIcon", icon )
            icon = xbmc.getInfoLabel( icon )
            listitem.setProperty( "icon", icon )
            listitem.setIconImage( icon )
            iconIsVar = True
        if icon.startswith("resource://"):
            iconIsVar = True
        
        # Check for overrides
        tree = DATA._get_overrides_skin()
        for elem in tree.findall( "icon" ):
            if oldicon is None:
                if ("labelID" in elem.attrib and elem.attrib.get( "labelID" ) == labelID) or ("image" in elem.attrib and elem.attrib.get( "image" ) == icon):
                    # LabelID matched
                    if "group" in elem.attrib:
                        if elem.attrib.get( "group" ) == self.group:
                            # Group also matches - change icon
                            oldicon = icon
                            icon = elem.text
                            
                    elif "grouping" not in elem.attrib:
                        # No group - change icon
                        oldicon = icon
                        icon = elem.text
                            
        # If the skin doesn't have the icon, replace it with DefaultShortcut.png
        setDefault = False
        if ( not xbmc.skinHasImage( icon ) and setToDefault == True ) and not iconIsVar:
            if oldicon == None:
                oldicon = icon
            setDefault = True
            icon = "DefaultShortcut.png"
                
        # If we changed the icon, update the listitem
        if oldicon is not None:
            listitem.setIconImage( icon )
            listitem.setProperty( "icon", icon )
            listitem.setProperty( "original-icon", oldicon )
            
        if setDefault == True and setToDefault == True:
            # We set this to the default icon, so we need to check if /that/ icon is overriden
            self._get_icon_overrides( listitem, False, labelID )
        
    def _save_shortcuts( self, weEnabledSystemDebug = False, weEnabledScriptDebug = False ):
        # Entry point to save shortcuts - we will call the _save_shortcuts_function and, if it
        # fails, enable debug options (if not enabled) + recreate the error, then offer to upload
        # debug log (if relevant add-on is installed)

        # Save the shortcuts
        try:
            self._save_shortcuts_function()
            return
        except:
            print_exc()
            log( "Failed to save shortcuts" )

        # We failed to save the shortcuts
        
        if weEnabledSystemDebug or weEnabledScriptDebug:
            # Disable any logging we enabled
            if weEnabledSystemDebug:
                json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method":"Settings.setSettingValue", "params": {"setting":"debug.showloginfo", "value":false} } ' )
            if weEnabledScriptDebug:
                ADDON.setSetting( "enable_logging", "false" )

            if xbmc.getCondVisibility( "System.HasAddon( script.kodi.loguploader)" ):
                # Offer to upload a debug log
                ret = xbmcgui.Dialog().yesno( ADDON.getAddonInfo( "name" ), LANGUAGE( 32097 ), LANGUAGE( 32093 ) )
                if ret:
                    xbmc.executebuiltin( "RunScript(script.kodi.loguploader)" )
            else:
                # Inform user menu couldn't be saved
                xbmcgui.Dialog().ok( ADDON.getAddonInfo( "name" ), LANGUAGE( 32097 ), LANGUAGE( 32094 ) )

            # We're done
            return

        # Enable any debug logging needed                        
        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Settings.getSettings" }')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        
        enabledSystemDebug = False
        enabledScriptDebug = False
        if json_response.has_key('result') and json_response['result'].has_key('settings') and json_response['result']['settings'] is not None:
            for item in json_response['result']['settings']:
                if item["id"] == "debug.showloginfo":
                    if item["value"] == False:
                        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method":"Settings.setSettingValue", "params": {"setting":"debug.showloginfo", "value":true} } ' )
                        enabledSystemDebug = True
        
        if ADDON.getSetting( "enable_logging" ) != "true":
            ADDON.setSetting( "enable_logging", "true" )
            enabledScriptDebug = True
            
        if enabledSystemDebug or enabledScriptDebug:
            # We enabled one or more of the debug options, re-run this function
            self._save_shortcuts( enabledSystemDebug, enabledScriptDebug )
        else:
            if xbmc.getCondVisibility( "System.HasAddon( script.kodi.loguploader )" ):
                # Offer to upload a debug log
                ret = xbmcgui.Dialog().yesno( ADDON.getAddonInfo( "name" ), LANGUAGE( 32097 ), LANGUAGE( 32093 ) )
                if ret:
                    xbmc.executebuiltin( "RunScript(script.kodi.loguploader)" )
            else:
                # Inform user menu couldn't be saved
                xbmcgui.Dialog().ok( ADDON.getAddonInfo( "name" ), LANGUAGE( 32097 ), LANGUAGE( 32094 ) )                 
            
    def _save_shortcuts_function( self ):
        # Save shortcuts
        if self.changeMade == True:
            log( "Saving changes" )
            
            # Create a new tree
            tree = xmltree.ElementTree( xmltree.Element( "shortcuts" ) )
            root = tree.getroot()
            
            properties = []
            
            labelIDChanges = []
            labelIDChangesDict = {}
           
            DATA._clear_labelID()
            
            for listitem in self.allListItems:
                
                # If the item has a label or an action, or a specified property from the override is present
                if try_decode( listitem.getLabel() ) != LANGUAGE(32013) or listitem.getProperty( "path" ) != "noop" or self.hasSaveWithProperty( listitem ):
                    # Generate labelID, and mark if it has changed
                    labelID = listitem.getProperty( "labelID" )
                    newlabelID = labelID

                    # defaultID
                    defaultID = try_decode( listitem.getProperty( "defaultID" ) )
                    
                    localizedString = listitem.getProperty( "localizedString" )
                    if localizedString is None or localizedString == "":
                        localLabel = DATA.local( listitem.getLabel() )
                    else:
                        localLabel = DATA.local( localizedString )
                    newlabelID = DATA._get_labelID( localLabel[3], listitem.getProperty( "path" ) )     
                    if self.group == "mainmenu":
                        labelIDChanges.append( [labelID, newlabelID, defaultID] )
                        labelIDChangesDict[ labelID ] = newlabelID
                        
                    # We want to save this
                    shortcut = xmltree.SubElement( root, "shortcut" )
                    xmltree.SubElement( shortcut, "defaultID" ).text = defaultID
                    
                    # Label and label2
                    xmltree.SubElement( shortcut, "label" ).text = localLabel[0]
                    xmltree.SubElement( shortcut, "label2" ).text = DATA.local( listitem.getLabel2() )[0]
                    
                    # Icon and thumbnail
                    if listitem.getProperty( "untranslatedIcon" ):
                        icon = listitem.getProperty( "untranslatedIcon" )
                    else:
                        if listitem.getProperty( "original-icon" ):
                            icon = listitem.getProperty( "original-icon" )
                        else:
                            icon = listitem.getProperty( "icon" )

                    thumb = listitem.getProperty( "thumbnail" )
                    
                    xmltree.SubElement( shortcut, "icon" ).text = try_decode( icon )
                    xmltree.SubElement( shortcut, "thumb" ).text = try_decode( thumb )
                    
                    # Action
                    xmltree.SubElement( shortcut, "action" ).text = try_decode( listitem.getProperty( "path" ) )
                    
                    # Visible
                    if listitem.getProperty( "visible-condition" ):
                        xmltree.SubElement( shortcut, "visible" ).text = listitem.getProperty( "visible-condition" )

                    # Disabled
                    if listitem.getProperty( "skinshortcuts-disabled" ) == "True":
                        xmltree.SubElement( shortcut, "disabled" ).text = "True"
                    
                    # Locked
                    if listitem.getProperty( "LOCKED" ):
                        xmltree.SubElement( shortcut, "lock" ).text = listitem.getProperty( "LOCKED" )
                    
                    # Additional properties
                    if listitem.getProperty( "additionalListItemProperties" ):
                        additionalProperties = eval( listitem.getProperty( "additionalListItemProperties" ) )
                        if icon != "":
                            additionalProperties.append( [ "icon", icon ] )
                        if thumb != "":
                            additionalProperties.append( [ "thumb", thumb ] )
                        properties.append( [ newlabelID, additionalProperties ] )
                        
            # Check whether this is an additional level
            isSubLevel = False
            if "." in self.group and self.group.rsplit( ".", 1 )[ 1 ].isdigit() and int( self.group.rsplit( ".", 1 )[ 1 ] ) in range( 1, 6 ):
                isSubLevel = True

            # Save the shortcuts
            DATA.indent( root )
            path = os.path.join( DATAPATH , DATA.slugify( self.group, True, isSubLevel = isSubLevel ) + ".DATA.xml" )
            path = try_decode( path )
            
            tree.write( path.replace( ".shortcuts", ".DATA.xml" ), encoding="UTF-8"  )
            
            # Now make any labelID changes
            copyDefaultProperties = []
            while not len( labelIDChanges ) == 0:
                # Get the first labelID change, and check that we're not changing anything from that
                labelIDFrom = labelIDChanges[0][0]
                labelIDTo = labelIDChanges[0][1]
                defaultIDFrom = labelIDChanges[0][2]
                
                # If labelIDFrom is empty. this is a new item so we want to set the From the same as the To
                # (this will ensure any default .shortcuts file is copied across)
                if labelIDFrom == "" or labelIDFrom is None:
                    labelIDFrom = labelIDTo
                
                # Check that there isn't another item in the list whose 'From' is the same as our 'To'
                # - if so, we're going to move our items elsewhere, and move 'em to the correct place later
                # (This ensures we don't overwrite anything incorrectly)
                if not len( labelIDChanges ) == 1:
                    for x in range( 1, len( labelIDChanges ) ):
                        if labelIDChanges[x][0] == labelIDTo:
                            tempLocation = str( random.randrange(0,9999999999999999) )
                            labelIDChanges[0][1] = tempLocation
                            labelIDChanges.append( [tempLocation, labelIDTo, defaultIDFrom] )
                            labelIDTo = tempLocation
                            break
                            
                # Make the change (0 - the main sub-menu, 1-5 - additional submenus )
                for i in range( 0, 6 ):
                    if i == 0:
                        groupName = labelIDFrom
                        paths = [[os.path.join( DATAPATH, DATA.slugify( labelIDFrom, True ) + ".DATA.xml" ).encode( "utf-8" ), "Move"], [os.path.join( SKINPATH, DATA.slugify( defaultIDFrom ) + ".DATA.xml" ).encode( "utf-8" ), "Copy"], [os.path.join( DEFAULTPATH, DATA.slugify( defaultIDFrom ) + ".DATA.xml" ).encode( "utf-8" ), "Copy"], [None, "New"]]
                        target = os.path.join( DATAPATH, DATA.slugify( labelIDTo, True ) + ".DATA.xml" ).encode( "utf-8" )
                    else:
                        groupName = "%s.%s" %( labelIDFrom, str( i ) )
                        paths = [[os.path.join( DATAPATH, DATA.slugify( "%s.%s" %( labelIDFrom, str( i )), True, isSubLevel = True ) + ".DATA.xml" ).encode( "utf-8" ), "Move"], [os.path.join( SKINPATH, DATA.slugify( "%s.%s" %( defaultIDFrom, str( i ) ), isSubLevel = True ) + ".DATA.xml" ).encode( "utf-8" ), "Copy"], [os.path.join( DEFAULTPATH, DATA.slugify( "%s.%s" %( defaultIDFrom, str( i ) ), isSubLevel = True ) + ".DATA.xml" ).encode( "utf-8" ), "Copy"]]
                        target = os.path.join( DATAPATH, DATA.slugify( "%s.%s" %( labelIDTo, str( i ) ), True, isSubLevel = True ) + ".DATA.xml" ).encode( "utf-8" )
                        
                    target = try_decode( target )
                    
                    for path in paths:
                        path[0] = try_decode( path[0] )
                        path[1] = try_decode( path[1] )
                            
                        if path[1] == "New":
                            tree = xmltree.ElementTree( xmltree.Element( "shortcuts" ) )
                            tree.write( target, encoding="UTF-8"  )
                            log( "Creating empty file - %s" %( target ) )
                            break
                            
                        elif xbmcvfs.exists( path[0] ):
                            # The XML file exists
                            if path[1] == "Move":
                                if path[0] != target:
                                    # Move the original to the target path
                                    log( "Moving " + path[0] + " > " + target )
                                    xbmcvfs.rename( path[0], target )
                            else:
                                # We're copying the file (actually, we'll re-write the file without
                                # any LOCKED elements and with icons/thumbs adjusted to absolute paths)
                                newtree = xmltree.parse( path[0] )
                                for newnode in newtree.getroot().findall( "shortcut" ):
                                    searchNode = newnode.find( "locked" )
                                    if searchNode is not None:
                                        newnode.remove( searchNode )
                                        
                                # Write it to the target
                                DATA.indent( newtree.getroot() )
                                newtree.write( target, encoding="utf-8" )
                                log( "Copying " + path[0] + " > " + target )

                                # We'll need to import it's default properties, so save the groupName
                                copyDefaultProperties.append( groupName )
                            break
                        
                labelIDChanges.pop( 0 )
                
            # Save widgets, backgrounds and custom properties
            self._save_properties( properties, labelIDChangesDict, copyDefaultProperties )
            
            # Note that we've saved stuff
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-reloadmainmenu", "True" )

    def hasSaveWithProperty( self, listitem ):
        for propertyName in self.saveWithProperty:
            if listitem.getProperty( propertyName ) != "":
                return True
        return False
                    
    def _save_properties( self, properties, labelIDChanges, copyDefaults ):
        # Save all additional properties (widgets, backgrounds, custom)
        log( "Saving properties" )
        
        currentProperties = []
        
        # Get previously loaded properties
        path = os.path.join( DATAPATH , xbmc.getSkinDir().decode('utf-8') + ".properties" )
        if xbmcvfs.exists( path ):
            # The properties file exists, load from it
            listProperties = eval( xbmcvfs.File( path ).read() )
            for listProperty in listProperties:
                # listProperty[0] = groupname
                # listProperty[1] = labelID
                # listProperty[2] = property name
                # listProperty[3] = property value
                currentProperties.append( [listProperty[0], listProperty[1], listProperty[2], listProperty[3]] )
        
        # Copy any items not in the current group to the array we'll save, and
        # make any labelID changes whilst we're at it
        saveData = []
        for property in currentProperties:
            #[ groupname, itemLabelID, property, value ]
            if not property[0] == self.group:
                if property[0] in labelIDChanges.keys():
                    property[0] = labelIDChanges[property[0]]
                elif "." in property[0] and property[ 0 ].rsplit( ".", 1 )[ 1 ].isdigit():
                    # Additional menu
                    groupName, groupValue = property[ 0 ].rsplit( ".", 1 )
                    if groupName in labelIDChanges.keys() and int( groupValue ) in range( 1, 6 ):
                        property[0] = "%s.%s" %( labelIDChanges[ groupName ], groupValue )
                saveData.append( property )
        
        # Add all the properties we've been passed
        for property in properties:
            # property[0] = labelID
            for toSave in property[1]:
                # toSave[0] = property name
                # toSave[1] = property value
                
                saveData.append( [ self.group, property[0], toSave[0], toSave[1] ] )

        # Add any default properties
        for group in copyDefaults:
            for defaultProperty in DATA.defaultProperties:
                #[ groupname, itemLabelID, property, value ]
                if defaultProperty[ 0 ] == group:
                    saveData.append( [ group, defaultProperty[ 1 ], defaultProperty[ 2 ], defaultProperty[ 3 ] ] )
        
        # Try to save the file
        try:
            f = xbmcvfs.File( os.path.join( DATAPATH , xbmc.getSkinDir().decode('utf-8') + ".properties" ), 'w' )
            f.write( repr( saveData ).replace( "],", "],\n" ) )
            f.close()
        except:
            print_exc()
            log( "### ERROR could not save file %s" % DATAPATH )

        # Clear saved properties in DATA, so it will pick up any new ones next time we load a file
        DATA.currentProperties = None
    
    def _load_overrides( self ):
        # Load various overrides from the skin, most notably backgrounds and thumbnails
        self.backgrounds = "LOADING"
        self.thumbnails = "LOADING"
        
        # Load skin overrides
        tree = DATA._get_overrides_skin()
                
        # Should we allow the user to select a playlist as a widget...
        elem = tree.find('widgetPlaylists')
        if elem is not None and elem.text == "True":
            self.widgetPlaylists = True
            if "type" in elem.attrib:
                self.widgetPlaylistsType = elem.attrib.get( "type" )
                
        # Get backgrounds and thumbnails - we do this in a separate thread as the json used to load VFS paths
        # is very expensive
        thread.start_new_thread( self._load_backgrounds_thumbnails, () )

        # Should we allow the user to browse for background images...
        elem = tree.find('backgroundBrowse')
        if elem is not None and elem.text.lower() in ("true", "single", "multi"):
            self.backgroundBrowse = elem.text.lower()
            if "default" in elem.attrib:
                self.backgroundBrowseDefault = elem.attrib.get( "default" )

        # Find the default thumbnail browse directory
        elem = tree.find("thumbnailBrowseDefault")
        if elem is not None and len(elem.text) > 0:
            self.thumbnailBrowseDefault = elem.text

        # Should we allow the user to rename a widget?
        elem = tree.find( "widgetRename" )
        if elem is not None and elem.text.lower() == "false":
            self.widgetRename = False

        # Does the skin override GUI 308?
        elem = tree.find( "alwaysReset" )
        if elem is not None and elem.text.lower() == "true":
            self.alwaysReset = True
        elem = tree.find( "alwaysRestore" )
        if elem is not None and elem.text.lower() == "true":
            self.alwaysRestore = True

        # Do we enable 'Get More...' button when browsing Skin Helper widgets
        elem = tree.find( "defaultwidgetsGetMore" )
        if elem is not None and elem.text.lower() == "false":
            LIBRARY.skinhelperWidgetInstall = False

        # Are there any controls we don't close the window on 'back' for?
        for elem in tree.findall( "onback" ):
            self.onBack[ int( elem.text ) ] = int( elem.attrib.get( "to" ) )

        # Are there any custom properties that shortcuts should be saved if present
        for elem in tree.findall( "saveWithProperty" ):
            self.saveWithProperty.append( elem.text )
            

    def _load_overrides_context( self ):
        # Load context menu settings from overrides

        # Check we're running Krypton or later - we don't support the context menu on earlier versions
        if int( KODIVERSION ) <= 16:
            return
        
        for overrideType in [ "skin", "script" ]:
            # Load overrides
            if overrideType == "skin":
                tree = DATA._get_overrides_skin()
            else:
                tree = DATA._get_overrides_script()

            # Check if context menu overrides in tree
            elem = tree.find( "contextmenu" )
            if elem is None:
                # It isn't
                continue

            # Get which controls the context menu is enabled on
            for control in elem.findall( "enableon" ):
                self.contextControls.append( int( control.text ) )

            # Get the context menu items
            for item in elem.findall( "item" ):
                if "control" not in item.attrib:
                    # There's no control specified, so it's no use to us
                    continue

                condition = None
                if "condition" in item.attrib:
                    condition = item.attrib.get( "condition" )

                self.contextItems.append( ( int( item.attrib.get( "control" ) ), condition, item.text ) )

            # If we get here, we've loaded context options, so we're done
            return

    def _load_overrides_onclick( self ):
        # Load additional onlcicks from overrides

        # Get overrides
        tree = DATA._get_overrides_skin()

        # Get additional onclick handlers
        for control in tree.findall( "onclick" ):
            self.customOnClick[ int( control.get( "id" ) ) ] = control.text

    def _load_backgrounds_thumbnails( self ):
        # Load backgrounds (done in background thread)
        backgrounds = []
        thumbnails = []

        # Load skin overrides
        tree = DATA._get_overrides_skin()
        
        # Get backgrounds
        elems = tree.findall('background')
        for elem in elems:
            if "condition" in elem.attrib:
                if not xbmc.getCondVisibility( elem.attrib.get( "condition" ) ):
                    continue
            
            if elem.text.startswith("||BROWSE||"):
                #we want to include images from a VFS path...
                images = LIBRARY.getImagesFromVfsPath(elem.text.replace("||BROWSE||",""))
                for image in images:
                    backgrounds.append( [image[0], image[1] ] )
            elif "icon" in elem.attrib:
                backgrounds.append( [elem.attrib.get( "icon" ), DATA.local( elem.attrib.get( 'label' ) )[2] ] )
            else:
                backgrounds.append( [elem.text, DATA.local( elem.attrib.get( 'label' ) )[2] ] )

        self.backgrounds = backgrounds

        # Get thumbnails
        elems = tree.findall('thumbnail')
        for elem in elems:
            if "condition" in elem.attrib:
                if not xbmc.getCondVisibility( elem.attrib.get( "condition" ) ):
                    continue
                    
            if elem.text.startswith("||BROWSE||"):
                #we want to include images from a VFS path...
                images = LIBRARY.getImagesFromVfsPath(elem.text.replace("||BROWSE||",""))
                for image in images:
                    thumbnails.append( [image[0], image[1] ] )
            elif elem.text == "::NONE::":
                if "label" in elem.attrib:
                    self.thumbnailNone = elem.attrib.get( "label" )
                else:
                    self.thumbnailNone = "231"
            else:
                thumbnails.append( [elem.text, DATA.local( elem.attrib.get( 'label' ) )[2] ] )

        self.thumbnails = thumbnails

    def _load_customPropertyButtons( self ):
        # Load a list of addition button IDs we'll handle for setting additional properties

        # Load skin overrides
        tree = DATA._get_overrides_skin()

        for elem in tree.findall( "propertySettings" ):
            if "buttonID" in elem.attrib and "property" in elem.attrib:
                self.customPropertyButtons[ int( elem.attrib.get( "buttonID" ) ) ] = elem.attrib.get( "property" )
            elif "buttonID" in elem.attrib and "toggle" in elem.attrib:
                self.customToggleButtons[ int( elem.attrib.get( "buttonID" ) ) ] = elem.attrib.get( "toggle" )
                
    # ========================
    # === GUI INTERACTIONS ===
    # ========================

    def onClick(self, controlID):
        if controlID == 102:
            # Move to previous type of shortcuts
            self.shortcutgroup = self.shortcutgroup - 1
            if self.shortcutgroup == 0:
                self.shortcutgroup = LIBRARY.flatGroupingsCount()
            
            self._display_shortcuts()

        elif controlID == 103:
            # Move to next type of shortcuts
            self.shortcutgroup = self.shortcutgroup + 1
            if self.shortcutgroup > LIBRARY.flatGroupingsCount():
                self.shortcutgroup = 1
            
            self._display_shortcuts()
            
        elif controlID == 111:
            # User has selected an available shortcut they want in their menu
            log( "Select shortcut (111)" )
            listControl = self.getControl( 211 )
            itemIndex = listControl.getSelectedPosition()
            orderIndex = int( listControl.getListItem( itemIndex ).getProperty( "skinshortcuts-orderindex" ) )
            altAction = None
            
            if self.warnonremoval( listControl.getListItem( itemIndex ) ) == False:
                return
            
            # Copy the new shortcut
            selectedItem = self.getControl( 111 ).getSelectedItem()
            listitemCopy = self._duplicate_listitem( selectedItem, listControl.getListItem( itemIndex ) )
            
            path = listitemCopy.getProperty( "path" )
            if path.startswith( "||BROWSE||" ):
                # If this is a plugin, call our plugin browser
                returnVal = LIBRARY.explorer( ["plugin://" + path.replace( "||BROWSE||", "" )], "plugin://" + path.replace( "||BROWSE||", "" ), [self.getControl( 111 ).getSelectedItem().getLabel()], [self.getControl( 111 ).getSelectedItem().getProperty("thumbnail")], self.getControl( 111 ).getSelectedItem().getProperty("shortcutType")  )
                if returnVal is not None:
                    # Convert backslashes to double-backslashes (windows fix)
                    newAction = returnVal.getProperty( "Path" )
                    newAction = newAction.replace( "\\", "\\\\" )
                    returnVal.setProperty( "path", newAction )
                    returnVal.setProperty( "displayPath", newAction )
                    listitemCopy = self._duplicate_listitem( returnVal, listControl.getListItem( itemIndex ) )
                else:
                    listitemCopy = None
            elif path == "||UPNP||":
                returnVal = LIBRARY.explorer( ["upnp://"], "upnp://", [self.getControl( 111 ).getSelectedItem().getLabel()], [self.getControl( 111 ).getSelectedItem().getProperty("thumbnail")], self.getControl( 111 ).getSelectedItem().getProperty("shortcutType")  )
                if returnVal is not None:
                    listitemCopy = self._duplicate_listitem( returnVal, listControl.getListItem( itemIndex ) )
                else:
                    listitemCopy = None
            elif path.startswith( "||SOURCE||" ):
                returnVal = LIBRARY.explorer( [path.replace( "||SOURCE||", "" )], path.replace( "||SOURCE||", "" ), [self.getControl( 111 ).getSelectedItem().getLabel()], [self.getControl( 111 ).getSelectedItem().getProperty("thumbnail")], self.getControl( 111 ).getSelectedItem().getProperty("shortcutType")  )
                if returnVal is not None:
                    if "upnp://" in returnVal.getProperty( "Path" ):
                        listitemCopy = self._duplicate_listitem( returnVal, listControl.getListItem( itemIndex ) )
                    else:
                        returnVal = LIBRARY._sourcelink_choice( returnVal )
                        if returnVal is not None:
                            listitemCopy = self._duplicate_listitem( returnVal, listControl.getListItem( itemIndex ) )
                        else:
                            listitemCopy = None
                else:
                    listitemCopy = None
            elif path.startswith( "::PLAYLIST" ):
                log( "Selected playlist" )
                if not ">" in path or "VideoLibrary" in path:
                    # Give the user the choice of playing or displaying the playlist
                    dialog = xbmcgui.Dialog()
                    userchoice = dialog.yesno( LANGUAGE( 32040 ), LANGUAGE( 32060 ), "", "", LANGUAGE( 32061 ), LANGUAGE( 32062 ) )
                    # False: Display
                    # True: Play
                    if not userchoice:
                        listitemCopy.setProperty( "path", selectedItem.getProperty( "action-show" ) )
                        listitemCopy.setProperty( "displayPath", selectedItem.getProperty( "action-show" ) )
                    else:
                        listitemCopy.setProperty( "path", selectedItem.getProperty( "action-play" ) )
                        listitemCopy.setProperty( "displayPath", selectedItem.getProperty( "action-play" ) )
                elif ">" in path:
                    # Give the user the choice of playing, displaying or party more for the playlist
                    dialog = xbmcgui.Dialog()
                    userchoice = dialog.select( LANGUAGE( 32060 ), [ LANGUAGE( 32061 ), LANGUAGE( 32062 ), xbmc.getLocalizedString( 589 ) ] )
                    # 0 - Display
                    # 1 - Play
                    # 2 - Party mode
                    if not userchoice or userchoice == 0:
                        listitemCopy.setProperty( "path", selectedItem.getProperty( "action-show" ) )
                        listitemCopy.setProperty( "displayPath", selectedItem.getProperty( "action-show" ) )
                    elif userchoice == 1:
                        listitemCopy.setProperty( "path", selectedItem.getProperty( "action-play" ) )
                        listitemCopy.setProperty( "displayPath", selectedItem.getProperty( "action-play" ) )
                    else:
                        listitemCopy.setProperty( "path", selectedItem.getProperty( "action-party" ) )
                        listitemCopy.setProperty( "displayPath", selectedItem.getProperty( "action-party" ) )
             
            if listitemCopy is None:
                # Nothing was selected in the explorer
                return
                
            self.changeMade = True
            
            # Replace the allListItems listitem with our new list item
            self.allListItems[ orderIndex ] = listitemCopy
            
            # Delete playlist (TO BE REMOVED!)
            LIBRARY._delete_playlist( listControl.getListItem( itemIndex ).getProperty( "path" ) )
            
            # Display list items
            self._display_listitems( focus = itemIndex )
        
        elif controlID in [301, 1301]:
            # Add a new item
            log( "Add item (301)" )
            self.changeMade = True
            listControl = self.getControl( 211 )
            num = listControl.getSelectedPosition()
            orderIndex = int( listControl.getListItem( num ).getProperty( "skinshortcuts-orderindex" ) ) + 1
            
            # Set default label and action
            listitem = xbmcgui.ListItem( LANGUAGE(32013) )
            listitem.setProperty( "Path", 'noop' )
            listitem.setProperty( "additionalListItemProperties", "[]" )

            # Add fallback custom property values
            self._add_additional_properties( listitem )
            
            # Add new item to both displayed list and list kept in memory
            self.allListItems.insert( orderIndex, listitem )
            self._display_listitems( num + 1 )
            
            # If Control 1301 is used we want to add a new item and immediately select a shortcut
            if controlID == 1301:
                xbmc.executebuiltin('SendClick(401)')
            
        elif controlID == 302:
            # Delete an item
            log( "Delete item (302)" )
            
            listControl = self.getControl( 211 )
            num = listControl.getSelectedPosition()
            orderIndex = int( listControl.getListItem( num ).getProperty( "skinshortcuts-orderindex" ) )
            
            if self.warnonremoval( listControl.getListItem( num ) ) == False:
                return
            
            LIBRARY._delete_playlist( listControl.getListItem( num ).getProperty( "path" ) )
            
            self.changeMade = True
            
            # Remove item from memory list, and reload all list items
            self.allListItems.pop( orderIndex )
            self._display_listitems( num )
            
        elif controlID == 303:
            # Move item up in list
            log( "Move up (303)" )
            listControl = self.getControl( 211 )
            
            itemIndex = listControl.getSelectedPosition()
            orderIndex = int( listControl.getListItem( itemIndex ).getProperty( "skinshortcuts-orderindex" ) )
            if itemIndex == 0:
                # Top item, can't move it up
                return
                
            self.changeMade = True
                
            while True:
                # Move the item one up in the list
                self.allListItems[ orderIndex - 1 ], self.allListItems[ orderIndex ] = self.allListItems[ orderIndex ], self.allListItems[ orderIndex - 1 ]
                
                # If we've just moved to the top of the list, break
                if orderIndex == 1:
                    break
                    
                # Check if the item we've just swapped is visible
                shouldBreak = True
                if self.allListItems[ orderIndex ].getProperty( "visible-condition" ):
                    shouldBreak = xbmc.getCondVisibility( self.allListItems[ orderIndex ].getProperty( "visible-condition" ) )
                    
                if shouldBreak:
                    break
                    
                orderIndex -= 1
                    
            # Display the updated order
            self._display_listitems( itemIndex - 1 )
            
        elif controlID == 304:
            # Move item down in list
            log( "Move down (304)" )
            listControl = self.getControl( 211 )
            
            itemIndex = listControl.getSelectedPosition()
            orderIndex = int( listControl.getListItem( itemIndex ).getProperty( "skinshortcuts-orderindex" ) )
            
            log( str( itemIndex ) + " : " + str( listControl.size() ) )
            
            if itemIndex == listControl.size() - 1:
                return
                
            self.changeMade = True
            
            while True:
                # Move the item one up in the list
                self.allListItems[ orderIndex + 1 ], self.allListItems[ orderIndex ] = self.allListItems[ orderIndex ], self.allListItems[ orderIndex + 1 ]
                
                # If we've just moved to the top of the list, break
                if orderIndex == len( self.allListItems ) - 1:
                    break
                    
                # Check if the item we've just swapped is visible
                shouldBreak = True
                if self.allListItems[ orderIndex ].getProperty( "visible-condition" ):
                    shouldBreak = xbmc.getCondVisibility( self.allListItems[ orderIndex ].getProperty( "visible-condition" ) )
                    
                if shouldBreak:
                    break
                    
                orderIndex += 1
                    
            # Display the updated order
            self._display_listitems( itemIndex + 1 )

        elif controlID == 305:
            # Change label
            log( "Change label (305)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            # Retreive current label and labelID
            label = listitem.getLabel()
            oldlabelID = listitem.getProperty( "labelID" )
            
            # If the item is blank, set the current label to empty
            if try_decode( label ) == LANGUAGE(32013):
                label = ""
                
            # Get new label from keyboard dialog
            if is_hebrew(label):
                label = label.decode('utf-8')[::-1]
            keyboard = xbmc.Keyboard( label, xbmc.getLocalizedString(528), False )
            keyboard.doModal()
            if ( keyboard.isConfirmed() ):
                label = keyboard.getText()
                if label == "":
                    label = LANGUAGE(32013)
            else:
                return
                
            self.changeMade = True
            self._set_label( listitem, label )

        elif controlID == 306:
            # Change thumbnail
            log( "Change thumbnail (306)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            # Get new thumbnail from browse dialog
            dialog = xbmcgui.Dialog()
            custom_thumbnail = dialog.browse( 2 , xbmc.getLocalizedString(1030), 'files', '', True, False, self.thumbnailBrowseDefault)
            
            if custom_thumbnail:
                # Update the thumbnail
                self.changeMade = True
                listitem.setThumbnailImage( custom_thumbnail )
                listitem.setProperty( "thumbnail", custom_thumbnail )
            else:
                return
            
        elif controlID == 307:
            # Change Action
            log( "Change action (307)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            if self.warnonremoval( listitem ) == False:
                return
            
            # Retrieve current action
            action = listitem.getProperty( "path" )
            if action == "noop":
                action = ""
            
            if self.currentWindow.getProperty( "custom-grouping" ):
                selectedShortcut = LIBRARY.selectShortcut(custom = True, currentAction = listitem.getProperty("path"), grouping = self.currentWindow.getProperty( "custom-grouping" )) 
                self.currentWindow.clearProperty( "custom-grouping" )
            else:
                selectedShortcut = LIBRARY.selectShortcut(custom = True, currentAction = listitem.getProperty("path")) 

            if not selectedShortcut:
                # User cancelled
                return

            if selectedShortcut.getProperty( "chosenPath" ):
                action = try_decode( selectedShortcut.getProperty( "chosenPath" ) )
            elif selectedShortcut.getProperty( "path" ):
                action = try_decode(selectedShortcut.getProperty( "path" ))
            
            if action == "":
                action = "noop"

            if listitem.getProperty( "path" ) == action:
                return
                
            self.changeMade = True
            LIBRARY._delete_playlist( listitem.getProperty( "path" ) )
            
            # Update the action
            listitem.setProperty( "path", action )
            listitem.setProperty( "displaypath", action )
            listitem.setLabel2( LANGUAGE(32024) )
            listitem.setProperty( "shortcutType", "32024" )
            
        elif controlID == 308:
            # Reset shortcuts
            log( "Reset shortcuts (308)" )

            # Ask the user if they want to restore a shortcut, or reset to skin defaults
            if self.alwaysReset:
                # The skin has disable the restore function, so set response as if user has chose the reset to
                # defaults option
                response = 1
            elif self.alwaysRestore:
                # The skin has disabled the reset function, so set response as if the user has chosen to restore
                # a skin-default shortcut
                response = 0
            else:
                # No skin override, so let user decide to restore or reset
                if not DATA.checkIfMenusShared():
                    # Also offer to import from another skin
                    response = xbmcgui.Dialog().select( LANGUAGE(32102), [ LANGUAGE(32103), LANGUAGE(32104), "Import from compatible skin" ] )
                else:
                    response = xbmcgui.Dialog().select( LANGUAGE(32102), [ LANGUAGE(32103), LANGUAGE(32104) ] )
            
            if response == -1:
                # User cancelled
                return

            elif response == 0:
                # We're going to restore a particular shortcut
                restorePretty = []
                restoreItems = []

                # Save the labelID list from DATA
                originalLabelIDList = DATA.labelIDList
                DATA.labelIDList = []

                # Get a list of all shortcuts that were originally in the menu and restore labelIDList
                DATA._clear_labelID()
                shortcuts = DATA._get_shortcuts( self.group, defaultGroup = self.defaultGroup, defaultsOnly = True )
                DATA.labelIDList = originalLabelIDList

                for shortcut in shortcuts.getroot().findall( "shortcut" ):
                    # Parse the shortcut
                    item = self._parse_shortcut( shortcut )

                    # Check if a shortcuts labelID is already in the list
                    if item[1].getProperty( "labelID" ) not in DATA.labelIDList:
                        restorePretty.append( LIBRARY._create(["", item[ 1 ].getLabel(), item[1].getLabel2(), { "icon": item[1].getProperty( "icon" ) }] ) )
                        restoreItems.append( item[1] )

                if len( restoreItems ) == 0:
                    xbmcgui.Dialog().ok( LANGUAGE(32103), LANGUAGE(32105) )
                    return

                # Let the user select a shortcut to restore
                w = library.ShowDialog( "DialogSelect.xml", CWD, listing=restorePretty, windowtitle=LANGUAGE(32103) )
                w.doModal()
                restoreShortcut = w.result
                del w

                if restoreShortcut == -1:
                    # User cancelled
                    return

                # We now have our shortcut to return. Add it to self.allListItems and labelID list
                self.allListItems.append( restoreItems[ restoreShortcut ] )
                DATA.labelIDList.append( restoreItems[ restoreShortcut ].getProperty( "labelID" ) )

                self.changeMade = True
                self._display_listitems()

            elif response == 1:
                # We're going to reset all the shortcuts
                self.changeMade = True
                
                # Delete any auto-generated source playlists
                for x in range(0, self.getControl( 211 ).size()):
                    LIBRARY._delete_playlist( self.getControl( 211 ).getListItem( x ).getProperty( "path" ) )

                self.getControl( 211 ).reset()
                
                self.allListItems = []
                
                # Call the load shortcuts function, but add that we don't want
                # previously saved user shortcuts
                self.load_shortcuts( False )

            else:
                # We're going to offer to import menus from another compatible skin
                skinList, sharedFiles = DATA.getSharedSkinList()
                
                if len( skinList ) == 0:
                    xbmcgui.Dialog().ok( LANGUAGE(32110), LANGUAGE(32109) )
                    return

                # Let the user select a shortcut to restore
                importMenu = xbmcgui.Dialog().select( LANGUAGE(32110), skinList )

                if importMenu == -1:
                    # User cancelled
                    return

                # Delete any auto-generated source playlists
                for x in range(0, self.getControl( 211 ).size()):
                    LIBRARY._delete_playlist( self.getControl( 211 ).getListItem( x ).getProperty( "path" ) )

                if importMenu == 0 and not len( sharedFiles ) == 0:
                    # User has chosen to import the shared menu
                    DATA.importSkinMenu( sharedFiles )
                else:
                    # User has chosen to import from a particular skin
                    DATA.importSkinMenu( DATA.getFilesForSkin( skinList[ importMenu ] ), skinList[ importMenu ] )

                self.getControl( 211 ).reset()
                
                self.allListItems = []
                
                # Call the load shortcuts function
                self.load_shortcuts( True )
     
        elif controlID == 309:
            # Choose widget
            log( "Warning: Deprecated control 309 (Choose widget) selected")
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()

            # Check that widgets have been loaded
            LIBRARY.loadLibrary( "widgets" )
            
            # If we're setting for an additional widget, get it's number
            widgetID = ""
            if self.currentWindow.getProperty( "widgetID" ):
                widgetID += "." + self.currentWindow.getProperty( "widgetID" )
                self.currentWindow.clearProperty( "widgetID" )
            
            # Get the default widget for this item
            defaultWidget = self.find_default( "widget", listitem.getProperty( "labelID" ), listitem.getProperty( "defaultID" ) )
            
            # Generate list of widgets for select dialog
            widget = [""]
            widgetLabel = [LANGUAGE(32053)]
            widgetName = [""]
            widgetType = [ None ]
            for key in LIBRARY.dictionaryGroupings[ "widgets-classic" ]:
                widget.append( key[0] )
                widgetName.append( "" )
                widgetType.append( key[2] )
                
                if key[0] == defaultWidget:
                    widgetLabel.append( key[1] + " (%s)" %( LANGUAGE(32050) ) )
                else:
                    widgetLabel.append( key[1] )
                
            # If playlists have been enabled for widgets, add them too
            if self.widgetPlaylists:
                # Ensure playlists are loaded
                LIBRARY.loadLibrary( "playlists" )

                # Add them
                for playlist in LIBRARY.widgetPlaylistsList:
                    widget.append( "::PLAYLIST::" + playlist[0] )
                    widgetLabel.append( playlist[1] )
                    widgetName.append( playlist[2] )
                    widgetType.append( self.widgetPlaylistsType )
                for playlist in LIBRARY.scriptPlaylists():
                    widget.append( "::PLAYLIST::" + playlist[0] )
                    widgetLabel.append( playlist[1] )
                    widgetName.append( playlist[2] )
                    widgetType.append( self.widgetPlaylistsType )
                    
            # Show the dialog
            selectedWidget = xbmcgui.Dialog().select( LANGUAGE(32044), widgetLabel )
            
            if selectedWidget == -1:
                # User cancelled
                return
            elif selectedWidget == 0:
                # User selected no widget
                self._remove_additionalproperty( listitem, "widget" + widgetID )
                self._remove_additionalproperty( listitem, "widgetName" + widgetID )
                self._remove_additionalproperty( listitem, "widgetType" + widgetID )
                self._remove_additionalproperty( listitem, "widgetPlaylist" + widgetID )
                
            else:
                if widget[selectedWidget].startswith( "::PLAYLIST::" ):
                    self._add_additionalproperty( listitem, "widget" + widgetID, "Playlist" )
                    self._add_additionalproperty( listitem, "widgetName" + widgetID, widgetName[selectedWidget] )
                    self._add_additionalproperty( listitem, "widgetPlaylist" + widgetID, widget[selectedWidget].strip( "::PLAYLIST::" ) )
                    if self.currentWindow.getProperty( "useWidgetNameAsLabel" ) == "true" and widgetID == "":
                        self._set_label( listitem, widgetName[selectedWidget] )
                        self.currentWindow.clearProperty( "useWidgetNameAsLabel" )
                else:
                    self._add_additionalproperty( listitem, "widgetName" + widgetID, widgetLabel[selectedWidget].replace( " (%s)" %( LANGUAGE(32050) ), "" ) )
                    self._add_additionalproperty( listitem, "widget" + widgetID, widget[selectedWidget] )
                    self._remove_additionalproperty( listitem, "widgetPlaylist" + widgetID )
                    if self.currentWindow.getProperty( "useWidgetNameAsLabel" ) == "true" and widgetID == "":
                        self._set_label( listitem, widgetLabel[selectedWidget].replace( " (%s)" %( LANGUAGE(32050) ), "" ) )
                        self.currentWindow.clearProperty( "useWidgetNameAsLabel" )
                
                if widgetType[ selectedWidget ] is not None:
                    self._add_additionalproperty( listitem, "widgetType" + widgetID, widgetType[ selectedWidget] )
                else:
                    self._remove_additionalproperty( listitem, "widgetType" + widgetID )
                
            self.changeMade = True

        elif controlID == 312:
            # Alternative widget select
            log( "Choose widget (312)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()

            # If we're setting for an additional widget, get its number
            widgetID = ""
            if self.currentWindow.getProperty( "widgetID" ):
                widgetID = "." + self.currentWindow.getProperty( "widgetID" )
                self.currentWindow.clearProperty( "widgetID" )

            # Get the default widget for this item
            defaultWidget = self.find_default( "widget", listitem.getProperty( "labelID" ), listitem.getProperty( "defaultID" ) )

            # Ensure widgets are loaded
            LIBRARY.loadLibrary( "widgets" )

            # Let user choose widget
            if listitem.getProperty( "widgetPath" ) == "":
                selectedShortcut = LIBRARY.selectShortcut( grouping = "widget", showNone = True )
            else:
                selectedShortcut = LIBRARY.selectShortcut( grouping = "widget", showNone = True, custom = True, currentAction = listitem.getProperty( "widgetPath" ) )

            if selectedShortcut is None:
                # User cancelled
                return

            if selectedShortcut.getProperty( "Path" ) and selectedShortcut.getProperty( "custom" ) == "true":
                # User has manually edited the widget path, so we'll update that property only
                self._add_additionalproperty( listitem, "widgetPath" + widgetID, selectedShortcut.getProperty( "Path" ) )
                self.changeMade = True

            elif selectedShortcut.getProperty( "Path" ):
                # User has chosen a widget

                # Let user edit widget title, if they want & skin hasn't disabled it
                widgetName = selectedShortcut.getProperty( "widgetName" )
                if self.widgetRename:
                    if widgetName.startswith("$"):
                        widgetTempName = xbmc.getInfoLabel(widgetName)
                    else:
                        widgetTempName = DATA.local( widgetName )[2]
                    if is_hebrew(widgetTempName):
                        widgetTempName = widgetTempName[::-1]
                    keyboard = xbmc.Keyboard( widgetTempName, xbmc.getLocalizedString(16105), False )
                    keyboard.doModal()
                    if ( keyboard.isConfirmed() ) and keyboard.getText() != "":
                        if widgetTempName != try_decode( keyboard.getText() ):
                            widgetName = try_decode( keyboard.getText() )

                # Add any necessary reload parameter
                widgetPath = LIBRARY.addWidgetReload( selectedShortcut.getProperty( "widgetPath" ) )
                
                self._add_additionalproperty( listitem, "widget" + widgetID, selectedShortcut.getProperty( "widget" ) )
                self._add_additionalproperty( listitem, "widgetName" + widgetID, widgetName )
                self._add_additionalproperty( listitem, "widgetType" + widgetID, selectedShortcut.getProperty( "widgetType" ) )
                self._add_additionalproperty( listitem, "widgetTarget" + widgetID, selectedShortcut.getProperty( "widgetTarget" ) )
                self._add_additionalproperty( listitem, "widgetPath" + widgetID, widgetPath )
                if self.currentWindow.getProperty( "useWidgetNameAsLabel" ) == "true" and widgetID == "":
                    self._set_label( listitem, selectedShortcut.getProperty( ( "widgetName" ) ) )
                    self.currentWindow.clearProperty( "useWidgetNameAsLabel" )
                self.changeMade = True

            else:
                # User has selected 'None'
                self._remove_additionalproperty( listitem, "widget" + widgetID )
                self._remove_additionalproperty( listitem, "widgetName" + widgetID )
                self._remove_additionalproperty( listitem, "widgetType" + widgetID )
                self._remove_additionalproperty( listitem, "widgetTarget" + widgetID )
                self._remove_additionalproperty( listitem, "widgetPath" + widgetID )
                if self.currentWindow.getProperty( "useWidgetNameAsLabel" ) == "true" and widgetID == "":
                    self._set_label( listitem, selectedShortcut.getProperty( ( "widgetName" ) ) )
                    self.currentWindow.clearProperty( "useWidgetNameAsLabel" )
                self.changeMade = True

                return
       
        elif controlID == 310:
            # Choose background
            log( "Choose background (310)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            usePrettyDialog = False
            
            # Create lists for the select dialog, with image browse buttons if enabled
            if self.backgroundBrowse == "true":
                log( "Adding both browse options" )
                background = ["", "", ""]         
                backgroundLabel = [LANGUAGE(32053), LANGUAGE(32051), LANGUAGE(32052)]
                backgroundPretty = [ LIBRARY._create(["", LANGUAGE(32053), "", { "icon": "DefaultAddonNone.png" }] ), LIBRARY._create(["", LANGUAGE(32051), "", { "icon": "DefaultFile.png" }] ), LIBRARY._create(["", LANGUAGE(32052), "", { "icon": "DefaultFolder.png" }] ) ]
            elif self.backgroundBrowse == "single":
                log( "Adding single browse option" )
                background = ["", ""]         
                backgroundLabel = [LANGUAGE(32053), LANGUAGE(32051)]
                backgroundPretty = [ LIBRARY._create(["", LANGUAGE(32053), "", { "icon": "DefaultAddonNone.png" }] ), LIBRARY._create(["", LANGUAGE(32051), "", { "icon": "DefaultFile.png" }] ) ]
            elif self.backgroundBrowse == "multi":
                log( "Adding multi browse option" )
                background = ["", ""]         
                backgroundLabel = [LANGUAGE(32053), LANGUAGE(32052)]
                backgroundPretty = [ LIBRARY._create(["", LANGUAGE(32053), "", { "icon": "DefaultAddonNone.png" }] ), LIBRARY._create(["", LANGUAGE(32052), "", { "icon": "DefaultFolder.png" }] ) ]
            else:
                background = [""]                         
                backgroundLabel = [LANGUAGE(32053)]
                backgroundPretty = [ LIBRARY._create(["", LANGUAGE(32053), "", { "icon": "DefaultAddonNone.png" }] ) ]

            # Wait to ensure that all backgrounds are loaded
            count = 0
            while self.backgrounds == "LOADING" and count < 20:
                if xbmc.Monitor().waitForAbort(0.1):
                    return
                count = count + 1
            if self.backgrounds == "LOADING":
                self.backgrounds = []

            # Get the default background for this item
            defaultBackground = self.find_default( "background", listitem.getProperty( "labelID" ), listitem.getProperty( "defaultID" ) )
            
            # Generate list of backgrounds for the dialog
            for key in self.backgrounds:
                if "::PLAYLIST::" in key[1]:
                    for playlist in LIBRARY.widgetPlaylistsList:
                        background.append( [ key[0], playlist[0], playlist[1] ] )
                        backgroundLabel.append( key[1].replace( "::PLAYLIST::", playlist[1] ) )
                        backgroundPretty.append( LIBRARY._create(["", key[1].replace( "::PLAYLIST::", playlist[1] ), "", {}] ) )
                    for playlist in LIBRARY.scriptPlaylists():
                        background.append( [ key[0], playlist[0], playlist[1] ] )
                        backgroundLabel.append( key[1].replace( "::PLAYLIST::", playlist[1] ) )
                        backgroundPretty.append( LIBRARY._create(["", key[1].replace( "::PLAYLIST::", playlist[1] ), "", {}] ) )
                else:
                    background.append( key[0] )
                    virtualImage = None
                    if key[0].startswith("$INFO") or key[0].startswith("$VAR"):
                        virtualImage = key[0].replace("$INFO[","").replace("$VAR[","").replace("]","")
                        virtualImage = xbmc.getInfoLabel(virtualImage)
                    
                    #fix for resource addon images
                    if key[0].startswith("resource://"):
                        virtualImage = key[0]

                    label = key[ 1 ]
                    if label.startswith( "$INFO" ) or label.startswith( "$VAR" ):
                        label = xbmc.getInfoLabel( label )

                    if defaultBackground == key[ 0 ]:
                        label = "%s (%s)" %( label, LANGUAGE( 32050 ) )

                    backgroundLabel.append( label )
                    if xbmc.skinHasImage( key[ 0 ] ) or virtualImage:
                        usePrettyDialog = True
                        backgroundPretty.append( LIBRARY._create(["", label, "", { "icon":  key[ 0 ] } ] ) )
                    else:
                        backgroundPretty.append( LIBRARY._create(["", label, "", {} ] ) )
            
            if usePrettyDialog:
                w = library.ShowDialog( "DialogSelect.xml", CWD, listing=backgroundPretty, windowtitle=LANGUAGE(32045) )
                w.doModal()
                selectedBackground = w.result
                del w
            else:
                # Show the dialog
                selectedBackground = xbmcgui.Dialog().select( LANGUAGE(32045), backgroundLabel )
            
            if selectedBackground == -1:
                # User cancelled
                return
            elif selectedBackground == 0:
                # User selected no background
                self._remove_additionalproperty( listitem, "background" )
                self._remove_additionalproperty( listitem, "backgroundName" )
                self._remove_additionalproperty( listitem, "backgroundPlaylist" )
                self._remove_additionalproperty( listitem, "backgroundPlaylistName" )
                self.changeMade = True
                return

            elif self.backgroundBrowse and (selectedBackground == 1 or (self.backgroundBrowse == "true" and selectedBackground == 2)):
                # User has chosen to browse for an image/folder
                imagedialog = xbmcgui.Dialog()
                if selectedBackground == 1 and self.backgroundBrowse != "multi": # Single image
                    custom_image = imagedialog.browse( 2 , xbmc.getLocalizedString(1030), 'files', '', True, False, self.backgroundBrowseDefault)
                else: # Multi-image
                    custom_image = imagedialog.browse( 0 , xbmc.getLocalizedString(1030), 'files', '', True, False, self.backgroundBrowseDefault)
                
                if custom_image:
                    self._add_additionalproperty( listitem, "background", custom_image )
                    self._add_additionalproperty( listitem, "backgroundName", custom_image )
                    self._remove_additionalproperty( listitem, "backgroundPlaylist" )
                    self._remove_additionalproperty( listitem, "backgroundPlaylistName" )
                else:
                    # User cancelled
                    return

            else:
                if isinstance( background[selectedBackground], list ):
                    # User has selected a playlist backgrounds
                    self._add_additionalproperty( listitem, "background", background[selectedBackground][0] )
                    self._add_additionalproperty( listitem, "backgroundName", backgroundLabel[selectedBackground].replace("::PLAYLIST::", background[selectedBackground][1]) )
                    self._add_additionalproperty( listitem, "backgroundPlaylist", background[selectedBackground][1] )
                    self._add_additionalproperty( listitem, "backgroundPlaylistName", background[selectedBackground][2] )
                    
                else:
                    # User has selected a normal background
                    self._add_additionalproperty( listitem, "background", background[selectedBackground] )
                    self._add_additionalproperty( listitem, "backgroundName", backgroundLabel[selectedBackground].replace( " (%s)" %( LANGUAGE(32050) ), "" ) )
                    self._remove_additionalproperty( listitem, "backgroundPlaylist" )
                    self._remove_additionalproperty( listitem, "backgroundPlaylistName" )
            
            self.changeMade = True
        
        elif controlID == 311:
            # Choose thumbnail
            log( "Choose thumbnail (311)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            # Create lists for the select dialog
            thumbnail = [""]                     
            thumbnailLabel = [LIBRARY._create(["", LANGUAGE(32096), "", {}] )]

            # Add a None option if the skin specified it
            if self.thumbnailNone:
                thumbnail.append( "" )
                thumbnailLabel.insert( 0, LIBRARY._create(["", self.thumbnailNone, "", {}] ) )

            # Ensure thumbnails have been loaded
            count = 0
            while self.thumbnails == "LOADING" and count < 20:
                if xbmc.Monitor().waitForAbort(0.1):
                    return
                count = count + 1
            if self.thumbnails == "LOADING":
                self.thumbnails = []
            
            # Generate list of thumbnails for the dialog
            for key in self.thumbnails:
                log( repr( key[ 0 ] ) + " " + repr( key[ 1 ] ) )
                thumbnail.append( key[0] )
                thumbnailLabel.append( LIBRARY._create(["", key[ 1 ], "", {"icon": key[ 0 ] }] ) )
            
            # Show the dialog
            w = library.ShowDialog( "DialogSelect.xml", CWD, listing=thumbnailLabel, windowtitle="Select thumbnail" )
            w.doModal()
            selectedThumbnail = w.result
            del w
            
            if selectedThumbnail == -1:
                # User cancelled
                return

            elif self.thumbnailNone and selectedThumbnail == 0:
                # User has chosen 'None'
                listitem.setThumbnailImage( None )
                listitem.setProperty( "thumbnail", None )

            elif (not self.thumbnailNone and selectedThumbnail == 0) or (self.thumbnailNone and selectedThumbnail == 1):
                # User has chosen to browse for an image
                imagedialog = xbmcgui.Dialog()
                
                if self.thumbnailBrowseDefault:
                    custom_image = imagedialog.browse( 2 , xbmc.getLocalizedString(1030), 'files', '', True, False, self.thumbnailBrowseDefault)
                else:
                    custom_image = imagedialog.browse( 2 , xbmc.getLocalizedString(1030), 'files', '', True, False, self.backgroundBrowseDefault)
                
                if custom_image:
                    listitem.setThumbnailImage( custom_image )
                    listitem.setProperty( "thumbnail", custom_image )
                else:
                    # User cancelled
                    return

            else:
                # User has selected a normal thumbnail
                listitem.setThumbnailImage( thumbnail[ selectedThumbnail ] )
                listitem.setProperty( "thumbnail", thumbnail[ selectedThumbnail ] )
            self.changeMade = True

        elif controlID == 313:
            # Toggle disabled
            log( "Toggle disabled (313)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()

            # Retrieve and toggle current disabled state
            disabled = listitem.getProperty( "skinshortcuts-disabled" )
            if disabled == "True":
                listitem.setProperty( "skinshortcuts-disabled", "False" )
            else:
                # Display any warning  
                if self.warnonremoval( listitem ) == False:
                    return
                
                # Toggle to true, add highlighting to label
                listitem.setProperty( "skinshortcuts-disabled", "True" )
                
            self.changeMade = True
        
        elif controlID == 401:
            # Select shortcut
            log( "Select shortcut (401)" )
            num = self.getControl( 211 ).getSelectedPosition()
            orderIndex = int( self.getControl( 211 ).getListItem( num ).getProperty( "skinshortcuts-orderindex" ) )
            
            if self.warnonremoval( self.getControl( 211 ).getListItem( num ) ) == False:
                return

            if self.currentWindow.getProperty( "custom-grouping" ):
                selectedShortcut = LIBRARY.selectShortcut( grouping = self.currentWindow.getProperty( "custom-grouping" ) )
                self.currentWindow.clearProperty( "custom-grouping" )
            else:
                selectedShortcut = LIBRARY.selectShortcut()
            
            if selectedShortcut is not None:
                listitemCopy = self._duplicate_listitem( selectedShortcut, self.getControl( 211 ).getListItem( num ) )
                
                #add a translated version of the path as property
                self._add_additionalproperty( listitemCopy, "translatedPath", selectedShortcut.getProperty( "path" ) )
                
                if selectedShortcut.getProperty( "smartShortcutProperties" ):
                    for listitemProperty in eval( selectedShortcut.getProperty( "smartShortcutProperties" ) ):
                        self._add_additionalproperty( listitemCopy, listitemProperty[0], listitemProperty[1] )
                               
                #set default background for this item (if any)
                defaultBackground = self.find_defaultBackground( listitemCopy.getProperty( "labelID" ), listitemCopy.getProperty( "defaultID" ) )
                if defaultBackground:
                    self._add_additionalproperty( listitemCopy, "background", defaultBackground["path"] )
                    self._add_additionalproperty( listitemCopy, "backgroundName", defaultBackground["label"] )
            
                #set default widget for this item (if any)
                defaultWidget = self.find_defaultWidget( listitemCopy.getProperty( "labelID" ), listitemCopy.getProperty( "defaultID" ) )
                if defaultWidget:
                    self._add_additionalproperty( listitemCopy, "widget", defaultWidget["widget"] )
                    self._add_additionalproperty( listitemCopy, "widgetName", defaultWidget["name"] )
                    self._add_additionalproperty( listitemCopy, "widgetType", defaultWidget["type"] )
                    self._add_additionalproperty( listitemCopy, "widgetPath", defaultWidget["path"] )
                    self._add_additionalproperty( listitemCopy, "widgetTarget", defaultWidget["target"] )
                        
                if selectedShortcut.getProperty( "chosenPath" ):
                    listitemCopy.setProperty( "path", selectedShortcut.getProperty( "chosenPath" ) )
                    listitemCopy.setProperty( "displayPath", selectedShortcut.getProperty( "chosenPath" ) )
                LIBRARY._delete_playlist( self.getControl( 211 ).getListItem( num ).getProperty( "path" ) )
            
                self.changeMade = True
                
                self.allListItems[ orderIndex ] = listitemCopy
                self._display_listitems( num )
            else:
                return

        elif controlID == 405 or controlID == 406 or controlID == 407 or controlID == 408 or controlID == 409 or controlID == 410:
            # Launch management dialog for submenu
            if xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-loading" ) and int( calendar.timegm( gmtime() ) ) - int( xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-loading" ) ) <= 5:
                return

            log( "Launching management dialog for submenu/additional menu (" + str( controlID ) + ")" )
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-loading", str( calendar.timegm( gmtime() ) ) )
            
            # Get the group we're about to edit
            launchGroup = self.getControl( 211 ).getSelectedItem().getProperty( "labelID" )
            launchDefaultGroup = self.getControl( 211 ).getSelectedItem().getProperty( "defaultID" )
            groupName = self.getControl( 211 ).getSelectedItem().getLabel()
            
            if launchDefaultGroup == None:
                launchDefaultGroup = ""
                            
            # If the labelID property is empty, we need to generate one
            if launchGroup is None or launchGroup == "":
                DATA._clear_labelID()
                num = self.getControl( 211 ).getSelectedPosition()
                orderIndex = self.getControl( 211 ).getListItem( num )
                
                # Get the labelID's of all other menu items
                for listitem in self.allListItems:
                    if listitem != orderIndex:
                        DATA._get_labelID( listitem.getProperty( "labelID" ), listitem.getProperty( "path" ) )
                
                # Now generate labelID for this menu item, if it doesn't have one
                labelID = self.getControl( 211 ).getListItem( num ).getProperty( "localizedString" )
                if labelID is None or labelID == "":
                    launchGroup = DATA._get_labelID( self.getControl( 211 ).getListItem( num ).getLabel(), self.getControl( 211 ).getListItem( num ).getProperty( "path" ) )
                else:
                    launchGroup = DATA._get_labelID( labelID, self.getControl( 211 ).getListItem( num ).getProperty( "path" ) )
                self.getControl( 211 ).getListItem( num ).setProperty( "labelID", launchGroup )                                        
            
            # Check if we're launching a specific additional menu
            if controlID == 406:
                launchGroup = launchGroup + ".1"
                launchDefaultGroup = launchDefaultGroup + ".1"
            elif controlID == 407:
                launchGroup = launchGroup + ".2"
                launchDefaultGroup = launchDefaultGroup + ".2"
            elif controlID == 408:
                launchGroup = launchGroup + ".3"
                launchDefaultGroup = launchDefaultGroup + ".3"
            elif controlID == 409:
                launchGroup = launchGroup + ".4"
                launchDefaultGroup = launchDefaultGroup + ".4"
            elif controlID == 410:
                launchGroup = launchGroup + ".5"
                launchDefaultGroup = launchDefaultGroup + ".5"
            # Check if 'level' property has been set
            elif self.currentWindow.getProperty("level"):
                launchGroup = launchGroup + "." + self.currentWindow.getProperty("level")
                self.currentWindow.clearProperty("level")
                
            # Check if 'groupname' property has been set
            if self.currentWindow.getProperty( "overrideName" ):
                groupName = self.currentWindow.getProperty( "overrideName" )
                self.currentWindow.clearProperty( "overrideName" )
                
            # Execute the script
            self.currentWindow.setProperty( "additionalDialog", "True" )
            import gui
            ui= gui.GUI( "script-skinshortcuts.xml", CWD, "default", group=launchGroup, defaultGroup=launchDefaultGroup, nolabels=self.nolabels, groupname=groupName )
            ui.doModal()
            del ui
            self.currentWindow.clearProperty( "additionalDialog" )

        if controlID in self.customToggleButtons:
            # Toggle a custom property
            log( "Toggling custom property (%s)" %( str( controlID ) ) )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()

            propertyName = self.customToggleButtons[ controlID ]
            self.changeMade = True

            if listitem.getProperty( propertyName ) == "True":
                self._remove_additionalproperty( listitem, propertyName )
            else:
                self._add_additionalproperty( listitem, propertyName, "True" )
                    
        if controlID == 404 or controlID in self.customPropertyButtons:
            # Set custom property
            # We do this last so that, if the skinner has specified a default Skin Shortcuts control is used to set the
            # property, that is completed before we get here.
            log( "Setting custom property (%s)" %( str( controlID ) ) )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            propertyName = ""
            propertyValue = ""

            usePrettyDialog = False
            
            # Retrieve the custom property
            if self.currentWindow.getProperty( "customProperty" ):
                propertyName = self.currentWindow.getProperty( "customProperty" )
                self.currentWindow.clearProperty( "customProperty" )
                propertyValue = self.currentWindow.getProperty( "customValue" )
                self.currentWindow.clearProperty( "customValue" )
            
                if propertyName == "thumb":
                    # Special treatment if we try to set the thumb with the property method
                    listitem.setThumbnailImage( xbmc.getInfoLabel(propertyValue) )
                    listitem.setIconImage( xbmc.getInfoLabel(propertyValue) )
                    listitem.setProperty( "thumbnail", propertyValue )
                    listitem.setProperty( "icon", propertyValue )
                    if not propertyValue:
                        listitem.setProperty( "original-icon", None )
                elif not propertyValue:
                    # No value set, so remove it from additionalListItemProperties
                    self._remove_additionalproperty( listitem, propertyName )
                else:
                    # Set the property
                    self._add_additionalproperty( listitem, propertyName, propertyValue )
                
                # notify that we have changes
                self.changeMade = True

            elif controlID != 404 or self.currentWindow.getProperty( "chooseProperty" ):
                if controlID == 404:
                    # Button 404, so we get the property from the window property
                    propertyName = self.currentWindow.getProperty( "chooseProperty" )
                    self.currentWindow.clearProperty( "chooseProperty" )
                else:
                    # Custom button, so we get the property from the dictionary
                    propertyName = self.customPropertyButtons[ controlID ]

                # Get the overrides
                tree = DATA._get_overrides_skin()

                # Set options
                dialogTitle = LANGUAGE(32101)
                showNone = True
                imageBrowse = False
                browseSingle = False
                browseMulti = False
                for elem in tree.findall( "propertySettings" ):
                    # Get property settings based on property value matching
                    if "property" in elem.attrib and elem.attrib.get( "property" ) == propertyName:
                        if "title" in elem.attrib:
                            dialogTitle = elem.attrib.get( "title" )
                        if "showNone" in elem.attrib and elem.attrib.get( "showNone" ).lower() == "false":
                            showNone = False
                        if "imageBrowse" in elem.attrib and elem.attrib.get( "imageBrowse" ).lower() == "true":
                            imageBrowse = True


                # Create lists for the select dialog
                property = []
                propertyLabel = []
                propertyPretty = []

                if showNone:
                    # Add a 'None' option to the list
                    property.append( "" )
                    propertyLabel.append( LANGUAGE(32053) )
                    propertyPretty.append( LIBRARY._create(["", LANGUAGE(32053), "", { "icon": "DefaultAddonNone.png" }] ) )
                if imageBrowse:
                    # Add browse single/multi options to the list
                    property.extend( [ "", "" ] )
                    propertyLabel.extend( [ LANGUAGE(32051), LANGUAGE(32052) ] )
                    propertyPretty.extend( [ LIBRARY._create(["", LANGUAGE(32051), "", { "icon": "DefaultFile.png" }] ), LIBRARY._create(["", LANGUAGE(32052), "", { "icon": "DefaultFolder.png" }] ) ] )
                
                # Get all the skin-defined properties
                for elem in tree.findall( "property" ):
                    if "property" in elem.attrib and elem.attrib.get( "property" ) == propertyName:
                        if "condition" in elem.attrib and not xbmc.getCondVisibility( elem.attrib.get( "condition" ) ):
                            continue
                        foundProperty = elem.text
                        property.append( foundProperty )
                        if "icon" in elem.attrib:
                            usePrettyDialog = True
                            iconImage = { "icon": elem.attrib.get( "icon" ) }
                        else:
                            iconImage = {}

                        if "label" in elem.attrib:
                            labelValue = elem.attrib.get( "label" )
                            if labelValue.startswith( "$INFO" ) or labelValue.startswith( "$VAR" ):
                                propertyLabel.append( xbmc.getInfoLabel( labelValue ) )
                                propertyPretty.append( LIBRARY._create( [ "", xbmc.getInfoLabel( labelValue ), "", iconImage ] ) )
                            else:
                                propertyLabel.append( DATA.local( labelValue )[ 2 ] )
                                propertyPretty.append( LIBRARY._create( [ "", labelValue, "", iconImage ] ) )
                        else:
                            propertyLabel.append( DATA.local( foundProperty )[2] )
                            propertyPretty.append( LIBRARY._create( [ "", foundProperty, "", iconImage ] ) )
                
                # Show the dialog
                if usePrettyDialog:
                    w = library.ShowDialog( "DialogSelect.xml", CWD, listing=propertyPretty, windowtitle=dialogTitle )
                    w.doModal()
                    selectedProperty = w.result
                    del w
                else:
                    selectedProperty = xbmcgui.Dialog().select( dialogTitle, propertyLabel )
                
                if selectedProperty == -1:
                    # User cancelled
                    return
                elif selectedProperty == 0 and showNone:
                    # User selected no property
                    self.changeMade = True
                    self._remove_additionalproperty( listitem, propertyName )
                elif ( selectedProperty == 0 and not showNone and imageBrowse ) or ( selectedProperty == 1 and showNone and imageBrowse ):
                    # User has selected to browse for a single image
                    browseSingle = True
                elif ( selectedProperty == 1 and not showNone and imageBrowse ) or ( selectedProperty == 2 and showNone and imageBrowse ):
                    # User has selected to browse for a multi-image
                    browseMulti = True
                else:
                    self.changeMade = True
                    self._add_additionalproperty( listitem, propertyName, property[ selectedProperty ] )

                if browseSingle or browseMulti:
                    # User has chosen to browse for an image/folder
                    imagedialog = xbmcgui.Dialog()
                    if browseSingle: # Single image
                        custom_image = imagedialog.browse( 2 , xbmc.getLocalizedString(1030), 'files', '', True, False, None )
                    else: # Multi-image
                        custom_image = imagedialog.browse( 0 , xbmc.getLocalizedString(1030), 'files', '', True, False, None )
                    
                    if custom_image:
                        self.changeMade = True
                        self._add_additionalproperty( listitem, propertyName, custom_image )
                    else:
                        # User cancelled
                        return
                
            else:
                # The customProperty or chooseProperty window properties needs to be set, so return
                self.currentWindow.clearProperty( "customValue" )
                return

        # Custom onclick actions
        if controlID in self.customOnClick:
            xbmc.executebuiltin( self.customOnClick[ controlID ] )
            



    # ========================
    # === HELPER FUNCTIONS ===
    # ========================
    
            
    def _display_shortcuts( self ):
        # Load the currently selected shortcut group
        newGroup = LIBRARY.retrieveGroup( self.shortcutgroup )
        
        label = DATA.local( newGroup[0] )[2]
        
        self.getControl( 111 ).reset()
        for item in newGroup[1]:
            newItem = self._duplicate_listitem( item )
            if item.getProperty( "action-show" ):
                newItem.setProperty( "action-show", item.getProperty( "action-show" ) )
                newItem.setProperty( "action-play", item.getProperty( "action-play" ) )
                newItem.setProperty( "action-party", item.getProperty( "action-party" ) )
            self.getControl( 111 ).addItem( newItem )
        self.getControl( 101 ).setLabel( label + " (%s)" %self.getControl( 111 ).size() )
        
    def _duplicate_listitem( self, listitem, originallistitem = None ):
        # Create a copy of an existing listitem
        listitemCopy = xbmcgui.ListItem(label=listitem.getLabel(), label2=listitem.getLabel2(), iconImage=listitem.getProperty("icon"), thumbnailImage=listitem.getProperty("thumbnail"))
        listitemCopy.setProperty( "path", listitem.getProperty("path") )
        listitemCopy.setProperty( "displaypath", listitem.getProperty("path") )
        listitemCopy.setProperty( "icon", listitem.getProperty("icon") )
        listitemCopy.setProperty( "thumbnail", listitem.getProperty("thumbnail") )
        listitemCopy.setProperty( "localizedString", listitem.getProperty("localizedString") )
        listitemCopy.setProperty( "shortcutType", listitem.getProperty("shortcutType") )
        listitemCopy.setProperty( "skinshortcuts-disabled", listitem.getProperty( "skinshortcuts-disabled" ) )
                
        if listitem.getProperty( "LOCKED" ):
            listitemCopy.setProperty( "LOCKED", listitem.getProperty( "LOCKED" ) )
            
        if listitem.getProperty( "defaultID" ):
            listitemCopy.setProperty( "defaultID", listitem.getProperty( "defaultID" ) )
        elif listitem.getProperty( "labelID" ):
            listitemCopy.setProperty( "defaultID", listitem.getProperty( "labelID" ) )
        else:
            listitemCopy.setProperty( "defaultID", DATA._get_labelID( DATA.local( listitem.getProperty( "localizedString" ) )[3],  listitem.getProperty( "path" ), True ) )
            
        # If the item has an untranslated icon, set the icon image to it
        if listitem.getProperty( "untranslatedIcon" ):
            icon = listitem.getProperty( "untranslatedIcon" )
            listitemCopy.setIconImage( icon )
            listitemCopy.setProperty( "icon", icon )
            
        # Revert to original icon (because we'll override it again in a minute!)
        if listitem.getProperty( "original-icon" ):
            icon = listitem.getProperty( "original-icon" )
            if icon == "":
                icon = None
            listitemCopy.setIconImage( icon )
            listitemCopy.setProperty( "icon", icon )
        
        # If we've haven't been passed an originallistitem, set the following from the listitem we were passed
        foundProperties = []
        if originallistitem is None:
            listitemCopy.setProperty( "labelID", listitem.getProperty("labelID") )
            if listitem.getProperty( "visible-condition" ):
                listitemCopy.setProperty( "visible-condition", listitem.getProperty( "visible-condition" ) )
            if listitem.getProperty( "additionalListItemProperties" ):
                listitemCopy.setProperty( "additionalListItemProperties", listitem.getProperty( "additionalListItemProperties" ) )
        else:
            # Set these from the original item we were passed (this will keep original labelID and additional properties
            # in tact)
            listitemCopy.setProperty( "labelID", originallistitem.getProperty( "labelID" ) )
            if originallistitem.getProperty( "visible-condition" ):
                listitemCopy.setProperty( "visible-condition", originallistitem.getProperty( "visible-condition" ) )
            if originallistitem.getProperty( "additionalListItemProperties" ):
                listitemCopy.setProperty( "additionalListItemProperties", originallistitem.getProperty( "additionalListItemProperties" ) )

        # Add custom properties
        self._add_additional_properties( listitemCopy )
                
        return listitemCopy
                
    def _add_additionalproperty( self, listitem, propertyName, propertyValue ):
        # Add an item to the additional properties of a user items
        properties = []
        if listitem.getProperty( "additionalListItemProperties" ):
            properties = eval( listitem.getProperty( "additionalListItemProperties" ) )
                
        foundProperty = False
        for property in properties:
            if property[0] == propertyName:
                foundProperty = True
                property[1] = DATA.local( propertyValue )[0]
                
        if foundProperty == False:
            properties.append( [propertyName, DATA.local( propertyValue )[0] ] )
        
        #translate any INFO labels (if needed) so they will be displayed correctly in the gui
        if propertyValue:
            if propertyValue.startswith("$") and not propertyValue.startswith( "$SKIN" ):
                listitem.setProperty( propertyName, xbmc.getInfoLabel(propertyValue) )
            else:
                listitem.setProperty( propertyName, DATA.local( propertyValue )[2] )
                if propertyValue.isdigit():
                    listitem.setProperty( "%s-NUM" %( propertyName ), propertyValue )
            
        listitem.setProperty( "additionalListItemProperties", repr( properties ) )

        self._add_additional_properties( listitem )
        
    def _remove_additionalproperty( self, listitem, propertyName ):
        # Remove an item from the additional properties of a user item
        properties = []
        hasProperties = False
        if listitem.getProperty( "additionalListItemProperties" ):
            properties = eval( listitem.getProperty( "additionalListItemProperties" ) )
            hasProperties = True
        
        for property in properties:
            if property[0] == propertyName or "%s-NUM" %( property[0] ) == "%s-NUM" %( propertyName ):
                properties.remove( property )
                listitem.setProperty( property[0], None )
        
        listitem.setProperty( "additionalListItemProperties", repr( properties ) )

        self._add_additional_properties( listitem )
    
    def warnonremoval( self, item ):
        # This function will warn the user before they modify a settings link
        # (if the skin has enabled this function)
        tree = DATA._get_overrides_skin()
            
        for elem in tree.findall( "warn" ):
            if elem.text.lower() == item.getProperty( "displaypath" ).lower():
                # We want to show the message :)
                message = DATA.local( elem.attrib.get( "message" ) )[2]
                    
                heading = DATA.local( elem.attrib.get( "heading" ) )[2]
                
                dialog = xbmcgui.Dialog()
                return dialog.yesno( heading, message )
                
        return True
    
    def find_defaultBackground( self, labelID, defaultID ):
        # This function finds the default background, including properties
        count = 0
        while self.backgrounds == "LOADING" and count < 20:
            if xbmc.Monitor().waitForAbort(0.1):
                return
            count = count + 1
        if self.backgrounds == "LOADING":
            self.backgrounds = []
        result = {}
        defaultBackground = self.find_default( "background", labelID, defaultID )
        if defaultBackground:
            for key in self.backgrounds:
                if defaultBackground == key[ 0 ]:
                    result["path"] = key[ 0 ]
                    result["label"] = key[ 1 ]
                elif defaultBackground == key[ 1 ]:
                    result["path"] = key[ 0 ]
                    result["label"] = key[ 1 ]
        
        return result

    def find_defaultWidget( self, labelID, defaultID ):
        # This function finds the default widget, including properties
        result = {}
        
        #first look for any widgetdefaultnodes
        defaultWidget = self.find_default( "widgetdefaultnode", labelID, defaultID )
        if defaultWidget is not None:
            result["path"] = defaultWidget.get( "path" )
            result["name"] = defaultWidget.get( "label" )
            result["widget"] = defaultWidget.text
            result["type"] = defaultWidget.get( "type" )
            result["target"] = defaultWidget.get( "target" )
        else:
            #find any classic widgets
            defaultWidget = self.find_default( "widget", labelID, defaultID )
            for key in LIBRARY.dictionaryGroupings[ "widgets-classic" ]:
                if key[0] == defaultWidget:
                    result["widget"] = key[ 0 ]
                    result["name"] = key[ 1 ]
                    result["type"] = key[ 2 ]
                    result["path"] = key[ 3 ]
                    result["target"] = key[ 5 ]
                    break
        return result
       
    def find_default( self, backgroundorwidget, labelID, defaultID ):
        # This function finds the id of an items default background or widget
        
        if labelID == None:
            labelID = defaultID
        
        tree = DATA._get_overrides_skin()
        if backgroundorwidget == "background":
            elems = tree.getroot().findall( "backgrounddefault" )
        elif backgroundorwidget == "widgetdefaultnode":
            elems = tree.getroot().findall( "widgetdefaultnode" )
        else:
            elems = tree.getroot().findall( "widgetdefault" )
            
        if elems is not None:
            for elem in elems:
                if elem.attrib.get( "labelID" ) == labelID or elem.attrib.get( "defaultID" ) == defaultID:
                    if "group" in elem.attrib:
                        if elem.attrib.get( "group" ) == self.group:
                            if backgroundorwidget == "widgetdefaultnode":
                                #if it's a widgetdefaultnode, return the whole element
                                return elem
                            else:
                                return elem.text
                        else:
                            continue
                    else:
                        return elem.text
                                    
        return None
        
    def _set_label( self, listitem, label ):
        # Update the label, local string and labelID
        listitem.setLabel( label )
        listitem.setProperty( "localizedString", None )
            
        LIBRARY._rename_playlist( listitem.getProperty( "path" ), label )
            
        # If there's no label2, set it to custom shortcut
        if not listitem.getLabel2():
            listitem.setLabel2( LANGUAGE(32024) )
            listitem.setProperty( "shortcutType", "32024" )
    
    def onAction( self, action ):
        currentFocus = self.getFocusId()
        if action.getId() in ACTION_CANCEL_DIALOG:
            # Close action

            if currentFocus and currentFocus in self.onBack:
                # Action overriden to return to a control
                self.setFocusId( self.onBack[ currentFocus ] )
                return

            # Close window
            self._save_shortcuts()
            xbmcgui.Window(self.window_id).clearProperty('groupname')
            self._close()

        elif currentFocus in self.contextControls and action.getId() in ACTION_CONTEXT_MENU:
            # Context menu action
            self._display_Context_Menu()

        if currentFocus == 211:
            # Changed highlighted item, update window properties
            self._add_additional_properties()

    def _display_Context_Menu( self ):
        # Displays a context menu

        contextActions = []
        contextItems = []

        # Find active context menu items
        for item in self.contextItems:
            # Check any condition
            if item[ 1 ] is None or xbmc.getCondVisibility( item[ 1 ] ):
                # Add the items
                contextActions.append( item[ 0 ] )
                contextItems.append( item[ 2 ] )

        # Check that there are some items to display
        if len( contextItems ) == 0:
            log( "Context menu called, but no items to display" )
            return

        # Display the context menu
        selectedItem = xbmcgui.Dialog().contextmenu( list=contextItems )

        if selectedItem == -1:
            # Nothing selected
            return

        # Call the control associated with the selected item
        self.onClick( contextActions[ selectedItem ] )

    def _close( self ):
        self.close()
            
# coding=utf-8
import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
from xml.dom.minidom import parse
from xml.sax.saxutils import escape as escapeXML
import thread
from traceback import print_exc
from unidecode import unidecode
import random

import datafunctions
DATA = datafunctions.DataFunctions()

import library
LIBRARY = library.LibraryFunctions()

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = sys.modules[ "__main__" ].__addon__
__addonid__      = sys.modules[ "__main__" ].__addonid__
__addonversion__ = sys.modules[ "__main__" ].__addonversion__
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ )
__skinpath__     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')
__defaultpath__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'shortcuts').encode("utf-8") ).decode("utf-8")
__language__     = sys.modules[ "__main__" ].__language__
__cwd__          = sys.modules[ "__main__" ].__cwd__

ACTION_CANCEL_DIALOG = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )

if not xbmcvfs.exists(__datapath__):
    xbmcvfs.mkdir(__datapath__)

def log(txt):
    try:
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)
    except:
        pass

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        self.group = kwargs[ "group" ]
        self.nolabels = kwargs[ "nolabels" ]
        self.groupname = kwargs[ "groupname" ]
        self.shortcutgroup = 1
        
        # Empty arrays for different shortcut types
        self.backgroundBrowse = False
        self.widgetPlaylists = False
        self.widgetPlaylistsType = None
        
        self.currentProperties = []
        self.defaultProperties = []
        
        self.changeMade = False
        
        log( 'Management module loaded' )

    def onInit( self ):
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-script" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-script-data" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-skin" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-skin-data" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-user" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-user-data" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsAdditionalProperties" )
        if self.group == '':
            self._close()
        else:
            self.window_id = xbmcgui.getCurrentWindowDialogId()
            xbmcgui.Window(self.window_id).setProperty('groupname', self.group)
            if self.groupname is not None:
                xbmcgui.Window( self.window_id ).setProperty( 'groupDisplayName', self.groupname )
                
            log( "### " + repr( self.groupname ) )

            # Load library shortcuts in thread
            thread.start_new_thread( LIBRARY.loadLibrary, () )
            
            # Load widget and background names
            self._load_widgetsbackgrounds()
            
            # Load saved and default properties
            self._load_properties()
            
            # Load current shortcuts
            self.load_shortcuts()

            # Load default shortcuts for group in thread
            LIBRARY.loadedMenuDefaults = "Loading"
            thread.start_new_thread( self._load_defaults, () )
                        
            # Set window title label
            try:
                if self.getControl( 500 ).getLabel() == "":
                    if self.group == "mainmenu":
                        self.getControl( 500 ).setLabel( __language__(32071) )
                    elif self.groupname is not None:
                        self.getControl( 500 ).setLabel( __language__(32080).replace( "::MENUNAME::", self.groupname ) )
                    else:
                        self.getControl( 500 ).setLabel( __language__(32072) )
            except:
                pass
                
            # Set enabled condition for various controls
            try:
                self.getControl( 111 ).setEnableCondition( "IsEmpty(Container(211).ListItem.Property(LOCKED))" )
            except:
                pass
            try:
                self.getControl( 302 ).setEnableCondition( "IsEmpty(Container(211).ListItem.Property(LOCKED))" )
            except:
                pass
            try:
                self.getControl( 307 ).setEnableCondition( "IsEmpty(Container(211).ListItem.Property(LOCKED))" )
            except:
                pass
            try:
                self.getControl( 401 ).setEnableCondition( "IsEmpty(Container(211).ListItem.Property(LOCKED))" )
            except:
                pass
            
            # Set button labels
            if self.nolabels == "false":
                try:
                    if self.getControl( 301 ).getLabel() == "":
                        self.getControl( 301 ).setLabel( __language__(32000) )
                except:
                    log( "No add shortcut button on GUI (id 301)" )
                try:
                    if self.getControl( 302 ).getLabel() == "":
                        self.getControl( 302 ).setLabel( __language__(32001) )
                except:
                    log( "No delete shortcut button on GUI (id 302)" )
                try:
                    if self.getControl( 303 ).getLabel() == "":
                        self.getControl( 303 ).setLabel( __language__(32002) )
                except:
                    log( "No move shortcut up button on GUI (id 303)" )
                try:
                    if self.getControl( 304 ).getLabel() == "":
                        self.getControl( 304 ).setLabel( __language__(32003) )
                except:
                    log( "No move shortcut down button on GUI (id 304)" )
                
                try:
                    if self.getControl( 305 ).getLabel() == "":
                        self.getControl( 305 ).setLabel( __language__(32025) )
                except:
                    log( "Not set label button on GUI (id 305)" )
                    
                try:
                    if self.getControl( 306 ).getLabel() == "":
                        self.getControl( 306 ).setLabel( __language__(32026) )
                except:
                    log( "No edit thumbnail button on GUI (id 306)" )
                    
                try:
                    if self.getControl( 307 ).getLabel() == "":
                        self.getControl( 307 ).setLabel( __language__(32027) )
                except:
                    log( "Not edit action button on GUI (id 307)" )
                    
                try:
                    if self.getControl( 308 ).getLabel() == "":
                        self.getControl( 308 ).setLabel( __language__(32028) )
                except:
                    log( "No reset shortcuts button on GUI (id 308)" )
                    
                try:
                    if self.getControl( 309 ).getLabel() == "":
                        self.getControl( 309 ).setLabel( __language__(32044) )
                except:
                    log( "No widget button on GUI (id 309)" )
                try:
                    if self.getControl( 310 ).getLabel() == "":
                        self.getControl( 310 ).setLabel( __language__(32045) )
                except:
                    log( "No background button on GUI (id 310)" )
                    
                try:
                    if self.getControl( 401 ).getLabel() == "":
                        self.getControl( 401 ).setLabel( __language__(32048) )
                except:
                    log( "No widget button on GUI (id 401)" )
            
            try:
                self._display_shortcuts()
            except:
                log( "No list of shortcuts to choose from on GUI" )

    def _load_defaults( self ):
        # This function loads the default shortcuts for the selected menu
        LIBRARY.loadedMenuDefaults = "Loading"
        LIBRARY.addToDictionary( "menudefault", self.load_shortcuts( False, False ) )
        LIBRARY.loadedMenuDefaults = True
        
    def _load_widgetsbackgrounds( self ):
        self.widgets = []
        self.widgetsPretty = {}
        self.backgrounds = []
        self.backgroundsPretty = {}
        
        # Load skin overrides
        path = os.path.join( __skinpath__ , "overrides.xml" )
        tree = None
        if xbmcvfs.exists( path ):
            try:
                tree = xmltree.fromstring( xbmcvfs.File( path ).read().encode( 'utf-8' ) )
            except:
                print_exc()
        
        # Get widgets
        if tree is not None:
            elems = tree.findall('widget')
            for elem in elems:
                widgetType = None
                if "type" in elem.attrib:
                    widgetType = elem.attrib.get( "type" )
                if elem.attrib.get( 'label' ).isdigit():
                    self.widgets.append( [elem.text, xbmc.getLocalizedString( int( elem.attrib.get( 'label' ) ) ), widgetType ] )
                    self.widgetsPretty[elem.text] = xbmc.getLocalizedString( int( elem.attrib.get( 'label' ) ) )
                else:
                    self.widgets.append( [elem.text, elem.attrib.get( 'label' ), widgetType ] )
                    self.widgetsPretty[elem.text] = elem.attrib.get( 'label' )
                    
        # Get backgrounds
        if tree is not None:
            elems = tree.findall('background')
            for elem in elems:
                if elem.attrib.get( 'label' ).isdigit():
                    self.backgrounds.append( [elem.text, xbmc.getLocalizedString( int( elem.attrib.get( 'label' ) ) )] )
                    self.backgroundsPretty[elem.text] = xbmc.getLocalizedString( int( elem.attrib.get( 'label' ) ) )
                else:
                    self.backgrounds.append( [elem.text, elem.attrib.get( 'label' ) ] )
                    self.backgroundsPretty[elem.text] = elem.attrib.get( 'label' )


    def onClick(self, controlID):
        if controlID == 102:
            # Move to previous type of shortcuts
            self.shortcutgroup = self.shortcutgroup - 1
            if self.shortcutgroup == 0:
                self.shortcutgroup = LIBRARY.flatGroupingsCount()
            
            self._display_shortcuts()

        if controlID == 103:
            # Move to next type of shortcuts
            self.shortcutgroup = self.shortcutgroup + 1
            if self.shortcutgroup > LIBRARY.flatGroupingsCount():
                self.shortcutgroup = 1
            
            self._display_shortcuts()
            
        if controlID == 111:
            # User has selected an available shortcut they want in their menu
            log( "Select shortcut (111)" )
            listControl = self.getControl( 211 )
            itemIndex = listControl.getSelectedPosition()
            altAction = None
            
            if self.warnonremoval( listControl.getListItem( itemIndex ) ) == False:
                return
            
            # Copy the new shortcut
            selectedItem = self.getControl( 111 ).getSelectedItem()
            listitemCopy = self._duplicate_listitem( selectedItem, listControl.getListItem( itemIndex ) )
            
            path = urllib.unquote( listitemCopy.getProperty( "Path" ) )
            if path.startswith( "||BROWSE||" ):
                # If this is a plugin, call our plugin browser
                returnVal = LIBRARY.explorer( ["plugin://" + path.replace( "||BROWSE||", "" )], "plugin://" + path.replace( "||BROWSE||", "" ), [self.getControl( 111 ).getSelectedItem().getLabel()], [self.getControl( 111 ).getSelectedItem().getProperty("thumbnail")], self.getControl( 111 ).getSelectedItem().getProperty("shortcutType")  )
                if returnVal is not None:
                    # Convert backslashes to double-backslashes (windows fix)
                    newAction = urllib.unquote( returnVal.getProperty( "Path" ) )
                    newAction = newAction.replace( "\\", "\\\\" )
                    returnVal.setProperty( "Path", urllib.quote( newAction ) )
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
                    if "upnp://" in urllib.unquote( returnVal.getProperty( "Path" ) ):
                        listitemCopy = self._duplicate_listitem( returnVal, listControl.getListItem( itemIndex ) )
                    else:
                        returnVal = LIBRARY._sourcelink_choice( returnVal )
                        if returnVal is not None:
                            listitemCopy = self._duplicate_listitem( returnVal, listControl.getListItem( itemIndex ) )
                        else:
                            listitemCopy = None
                else:
                    listitemCopy = None
            elif path == "::PLAYLIST::":
                # Give the user the choice of playing or displaying the playlist
                dialog = xbmcgui.Dialog()
                userchoice = dialog.yesno( __language__( 32040 ), __language__( 32060 ), "", "", __language__( 32061 ), __language__( 32062 ) )
                # False: Display
                # True: Play
                if userchoice == False:
                    listitemCopy.setProperty( "path", selectedItem.getProperty( "action-show" ) )
                    listitemCopy.setProperty( "displayPath", urllib.unquote( selectedItem.getProperty( "action-show" ) ) )
                else:
                    listitemCopy.setProperty( "path", selectedItem.getProperty( "action-play" ) )
                    listitemCopy.setProperty( "displayPath", urllib.unquote( selectedItem.getProperty( "action-play" ) ) )
             
            if listitemCopy is None:
                # Nothing was selected in the explorer
                return
                
            self.changeMade = True
            
            # Update the list
            listitems = []
            DATA._clear_labelID()
            for x in range( 0, listControl.size() ):
                if x == itemIndex:
                    # Where the new shortcut should go
                    LIBRARY._delete_playlist(listControl.getListItem( itemIndex ).getProperty( "path" ) )
                    self._get_icon_overrides( listitemCopy )
                    listitems.append( listitemCopy )
                else:
                    listitemOriginal = self._duplicate_listitem( listControl.getListItem( x ) )
                    self._get_icon_overrides( listitemOriginal )
                    listitems.append( listitemOriginal )
            
            listControl.reset()
            listControl.addItems( listitems )
            listControl.selectItem( itemIndex )
            
        
        if controlID == 301:
            # Add a new item
            log( "Add item (301)" )
            self.changeMade = True
            listControl = self.getControl( 211 )
            
            listitem = xbmcgui.ListItem( __language__(32013) )
            listitem.setProperty( "Path", 'noop' )
            
            listControl.addItem( listitem )
            
            # Set focus
            listControl.selectItem( listControl.size() -1 )
        
        if controlID == 302:
            # Delete an item
            log( "Delete item (302)" )
            self.changeMade = True
            
            listControl = self.getControl( 211 )
            num = self.getControl( 211 ).getSelectedPosition()
            
            if self.warnonremoval( listControl.getListItem( num ) ) == False:
                return
            
            LIBRARY._delete_playlist( self.getControl( 211 ).getListItem( num ).getProperty( "path" ) )
            
            self.changeMade = True
            itemIndex = listControl.getSelectedPosition()
            listControl.removeItem( itemIndex )
            listControl.selectItem( itemIndex )
            
            # If there are no other items in the list...
            if not listControl.size() == 0:
                # We're going to replace all the items, to ensure
                # overrides are up to date
                listitems = []
                DATA._clear_labelID()
                for x in range(0, self.getControl( 211 ).size()):
                    # Duplicate the item and add it to the listitems array
                    listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                    self._get_icon_overrides( listitemShortcutCopy )
                    listitems.append(listitemShortcutCopy)
                        
                self.getControl( 211 ).reset()
                self.getControl( 211 ).addItems(listitems)
                
                self.getControl( 211 ).selectItem( num )

            else:
                listitem = xbmcgui.ListItem( __language__(32013) )
                listitem.setProperty( "Path", 'noop' )
                
                listControl.addItem( listitem )
                
                # Set focus
                listControl.selectItem( listControl.size() -1 )
            
        if controlID == 303:
            # Move item up in list
            log( "Move up (303)" )
            listControl = self.getControl( 211 )
            
            itemIndex = listControl.getSelectedPosition()
            if itemIndex == 0:
                return
                
            self.changeMade = True
            
            listitem = self._duplicate_listitem( listControl.getListItem( itemIndex ) )
            swapitem = self._duplicate_listitem( listControl.getListItem( itemIndex - 1) )
            
            listitems = []
            DATA._clear_labelID()
            for x in range( 0 , listControl.size() ):
                if x == itemIndex:
                    # Where the original item was
                    self._get_icon_overrides( swapitem )
                    listitems.append( swapitem )
                elif x == itemIndex - 1:
                    # Where we want the item
                    self._get_icon_overrides( listitem )
                    listitems.append( listitem )
                else:
                    listitemCopy = self._duplicate_listitem( listControl.getListItem(x) )
                    self._get_icon_overrides( listitemCopy )
                    listitems.append( listitemCopy )
                    
            listControl.reset()
            listControl.addItems( listitems )
            listControl.selectItem( itemIndex - 1 )
            
        if controlID == 304:
            # Move item down in list
            log( "Move down (304)" )
            listControl = self.getControl( 211 )
            
            itemIndex = listControl.getSelectedPosition()
            if itemIndex > listControl.size():
                return
                
            self.changeMade = True
            
            listitem = self._duplicate_listitem( listControl.getListItem( itemIndex ) )
            swapitem = self._duplicate_listitem( listControl.getListItem( itemIndex + 1 ) )
            
            listitems = []
            DATA._clear_labelID()
            for x in range( 0, listControl.size() ):
                if x == itemIndex:
                    # Where the original item was
                    self._get_icon_overrides( swapitem )
                    listitems.append( swapitem )
                elif x == itemIndex + 1:
                    # Where we want the item
                    self._get_icon_overrides( listitem )
                    listitems.append( listitem )
                else:
                    listitemCopy = self._duplicate_listitem( listControl.getListItem(x) )
                    self._get_icon_overrides( listitemCopy )
                    listitems.append( listitemCopy )
                    
            listControl.reset()
            listControl.addItems( listitems )
            listControl.selectItem( itemIndex + 1 )

        if controlID == 305:
            # Change label
            log( "Change label (305)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            # Retreive current label and labelID
            label = listitem.getLabel()
            oldlabelID = listitem.getProperty( "labelID" )
            
            # If the item is blank, set the current label to empty
            if label == __language__(32013):
                label = ""
                
            # Get new label from keyboard dialog
            keyboard = xbmc.Keyboard( label, xbmc.getLocalizedString(528), False )
            keyboard.doModal()
            if ( keyboard.isConfirmed() ):
                label = keyboard.getText()
                if label == "":
                    label = __language__(32013)
            else:
                return
                
            self.changeMade = True
            
            # Update the label, local string and labelID
            listitem.setLabel( label )
            listitem.setProperty( "localizedString", "" )
            
            LIBRARY._rename_playlist( listitem.getProperty( "path" ), label )
            
            # If there's no label2, set it to custom shortcut
            if not listitem.getLabel2():
                listitem.setLabel2( __language__(32024) )
                listitem.setProperty( "shortcutType", "::SCRIPT::32024" )

        if controlID == 306:
            # Change thumbnail
            log( "Change thumbnail (306)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            # Get new thumbnail from browse dialog
            dialog = xbmcgui.Dialog()
            custom_thumbnail = dialog.browse( 2 , xbmc.getLocalizedString(1030), 'files')
            
            if custom_thumbnail:
                # Update the thumbnail
                self.changeMade = True
                listitem.setThumbnailImage( custom_thumbnail )
                listitem.setProperty( "thumbnail", custom_thumbnail )
            
        if controlID == 307:
            # Change Action
            log( "Change action (307)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            if self.warnonremoval( listitem ) == False:
                return
            
            # Retrieve current action
            action = urllib.unquote( listitem.getProperty( "path" ) )
            if action == "noop":
                action = ""
                
            # Get new action from keyboard dialog
            keyboard = xbmc.Keyboard( action, xbmc.getLocalizedString(528), False )
            keyboard.doModal()
            
            if ( keyboard.isConfirmed() ):
                action = keyboard.getText()
                if action == "":
                    action = "noop"
                    
                # Check that a change was really made
                if urllib.quote( action ) == listitem.getProperty( "path" ):
                    return
            else:
                return
                
            self.changeMade = True
            LIBRARY._delete_playlist( listitem.getProperty( "path" ) )
            
            # Update the action
            listitem.setProperty( "path", urllib.quote( action ) )
            listitem.setProperty( "displaypath", action )
            listitem.setLabel2( __language__(32024) )
            listitem.setProperty( "shortcutType", "::SCRIPT::32024" )
            
        if controlID == 308:
            # Reset shortcuts
            log( "Reset shortcuts (308)" )
            self.changeMade = True
            
            # Delete any auto-generated source playlists
            for x in range(0, self.getControl( 211 ).size()):
                LIBRARY._delete_playlist( self.getControl( 211 ).getListItem( x ).getProperty( "path" ) )

            self.getControl( 211 ).reset()
            
            # Call the load shortcuts function, but add that we don't want
            # previously saved user shortcuts
            self.load_shortcuts( False )
                
        if controlID == 309:
            # Choose widget
            log( "Choose widget (309)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            # Generate list of widgets for select dialog
            widget = [""]
            widgetLabel = [__language__(32053)]
            widgetName = [""]
            widgetType = [ None ]
            for key in self.widgets:
                widget.append( key[0] )
                widgetLabel.append( key[1] )
                widgetName.append( "" )
                widgetType.append( key[2] )
                
            # If playlists have been enabled for widgets, add them too
            if self.widgetPlaylists:
                for playlist in LIBRARY.widgetPlaylistsList:
                    widget.append( "::PLAYLIST::" + playlist[0] )
                    widgetLabel.append( playlist[1] )
                    widgetName.append( playlist[2] )
                    widgetType.append( self.widgetPlaylistsType )
                    
            # Show the dialog
            selectedWidget = xbmcgui.Dialog().select( __language__(32044), widgetLabel )
            
            if selectedWidget == -1:
                # User cancelled
                return
            elif selectedWidget == 0:
                # User selected no widget
                self._remove_additionalproperty( listitem, "widget" )
                self._remove_additionalproperty( listitem, "widgetName" )
                self._remove_additionalproperty( listitem, "widgetType" )
                self._remove_additionalproperty( listitem, "widgetPlaylist" )
                
            else:
                if widget[selectedWidget].startswith( "::PLAYLIST::" ):
                    self._add_additionalproperty( listitem, "widget", "Playlist" )
                    self._add_additionalproperty( listitem, "widgetName", widgetName[selectedWidget] )
                    self._add_additionalproperty( listitem, "widgetPlaylist", widget[selectedWidget].strip( "::PLAYLIST::" ) )
                else:
                    self._add_additionalproperty( listitem, "widgetName", widgetLabel[selectedWidget] )
                    self._add_additionalproperty( listitem, "widget", widget[selectedWidget] )
                    self._remove_additionalproperty( listitem, "widgetPlaylist" )
                
                if widgetType[ selectedWidget] is not None:
                    self._add_additionalproperty( listitem, "widgetType", widgetType[ selectedWidget] )
                else:
                    self._remove_additionalproperty( listitem, "widgetType" )
                
            self.changeMade = True
                
        if controlID == 310:
            # Choose background
            log( "Choose background (310)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            # Create lists for the select dialog, with image browse buttons if enabled
            if self.backgroundBrowse:
                background = ["", "", ""]         
                backgroundLabel = [__language__(32050), __language__(32051), __language__(32052)]
            else:
                background = [""]                         
                backgroundLabel = [__language__(32050)]

            # Generate list of backgrounds for the dialog
            for key in self.backgrounds:
                if "::PLAYLIST::" in key[1]:
                    for playlist in LIBRARY.widgetPlaylistsList:
                        background.append( [ key[0], playlist[0], playlist[1] ] )
                        backgroundLabel.append( key[1].replace( "::PLAYLIST::", playlist[1] ) )
                else:
                    background.append( key[0] )            
                    backgroundLabel.append( key[1] )
            
            # Show the dialog
            selectedBackground = xbmcgui.Dialog().select( __language__(32045), backgroundLabel )
            
            if selectedBackground == -1:
                # User cancelled
                return
            elif selectedBackground == 0:
                # User selected no background
                self._remove_additionalproperty( listitem, "background" )
                self._remove_additionalproperty( listitem, "backgroundName" )
                self._remove_additionalproperty( listitem, "backgroundPlaylist" )
                self._remove_additionalproperty( listitem, "backgroundPlaylistName" )

            elif self.backgroundBrowse == True and (selectedBackground == 1 or selectedBackground == 2):
                # User has chosen to browse for an image/folder
                imagedialog = xbmcgui.Dialog()
                if selectedBackground == 1: # Single image
                    custom_image = imagedialog.browse( 2 , xbmc.getLocalizedString(1030), 'files')
                else: # Multi-image
                    custom_image = imagedialog.browse( 0 , xbmc.getLocalizedString(1030), 'files')
                
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
                    self._add_additionalproperty( listitem, "backgroundName", backgroundLabel[selectedBackground] )
                    self._remove_additionalproperty( listitem, "backgroundPlaylist" )
                    self._remove_additionalproperty( listitem, "backgroundPlaylistName" )
            
            self.changeMade = True
        
        if controlID == 401:
            num = self.getControl( 211 ).getSelectedPosition()
            
            if self.warnonremoval( self.getControl( 211 ).getListItem( num ) ) == False:
                return
            
            selectedShortcut = LIBRARY.selectShortcut()
            if selectedShortcut is not None:
                listitemCopy = self._duplicate_listitem( selectedShortcut, self.getControl( 211 ).getListItem( num ) )
                if selectedShortcut.getProperty( "chosenPath" ):
                    listitemCopy.setProperty( "path", selectedShortcut.getProperty( "chosenPath" ) )
                    listitemCopy.setProperty( "displayPath", urllib.unquote( selectedShortcut.getProperty( "chosenPath" ) ) )
                LIBRARY._delete_playlist( self.getControl( 211 ).getListItem( num ).getProperty( "path" ) )
            
                self.changeMade = True
                
                # Loop through the original list, and replace the currently selected listitem with our new listitem
                listitems = []
                DATA._clear_labelID()
                for x in range(0, self.getControl( 211 ).size()):
                    if x == num:
                        self._get_icon_overrides( listitemCopy )
                        listitems.append(listitemCopy)
                    else:
                        # Duplicate the item and add it to the listitems array
                        listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                        self._get_icon_overrides( listitemShortcutCopy )
                        listitems.append(listitemShortcutCopy)
                        
                self.getControl( 211 ).reset()
                self.getControl( 211 ).addItems(listitems)
                
                self.getControl( 211 ).selectItem( num )
        
        #if controlID == 402:
        #    # NOTE: Even if edit controls are now fixed, this code is out of date
        #    # Change label (EDIT CONTROL)
        #    
        #    # Retrieve properties, copy item, etc (in case the user changes focus whilst we're running)
        #    custom_label = self.getControl( 211 ).getSelectedItem().getLabel()
        #    num = self.getControl( 211 ).getSelectedPosition()
        #    listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )
        #    
        #    custom_label = self.getControl( 402 ).getText()
        #    if custom_label == "":
        #        custom_label = __language__(32013)
        #        
        #    # Set properties of the listitemCopy
        #    listitemCopy.setLabel(custom_label)
        #    listitemCopy.setProperty( "localizedString", "" )
        #    listitemCopy.setProperty( "labelID", self._get_labelID(custom_label) )
        #    
        #    # If there's no label2, set it to custom shortcut
        #    if not listitemCopy.getLabel2():
        #        listitemCopy.setLabel2( __language__(32024) )
        #        listitemCopy.setProperty( "shortcutType", "::SCRIPT::32024" )
        #    
        #    # Loop through the original list, and replace the currently selected listitem with our new listitem with altered label
        #    listitems = []
        #    for x in range(0, self.getControl( 211 ).size()):
        #        if x == num:
        #            listitems.append(listitemCopy)
        #        else:
        #            # Duplicate the item and it to the listitems array
        #            listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
        #            
        #            listitems.append(listitemShortcutCopy)
        #            
        #    self.getControl( 211 ).reset()
        #    self.getControl( 211 ).addItems(listitems)
        #    
        #    self.getControl( 211 ).selectItem( num )
        
        
        #if controlID == 403:
        #    # NOTE: Even if edit controls are now fixed, this code is out of date
        #    # Change action (EDIT CONTROL)
        #     #Retrieve properties, copy item, etc (in case the user changes focus)
        #    custom_path = urllib.unquote( self.getControl( 211 ).getSelectedItem().getProperty( "path" ) )
        #    listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )
        #    num = self.getControl( 211 ).getSelectedPosition()
        #
        #    custom_path = self.getControl( 403 ).getText()
        #    if custom_path == "":
        #        custom_path = "noop"
        #            
        #    if not urllib.quote( custom_path ) == self.getControl( 211 ).getSelectedItem().getProperty( "path" ):
        #        listitemCopy.setProperty( "path", urllib.quote( custom_path ) )
        #        listitemCopy.setLabel2( __language__(32024) )
        #        listitemCopy.setProperty( "shortcutType", "::SCRIPT::32024" )
        #    
        #    # Loop through the original list, and replace the currently selected listitem with our new listitem with altered path
        #    listitems = []
        #    for x in range(0, self.getControl( 211 ).size()):
        #        if x == num:
        #            listitems.append(listitemCopy)
        #        else:
        #            # Duplicate the item and it to the listitems array
        #            listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
        #            
        #            listitems.append(listitemShortcutCopy)
        #            
        #    self.getControl( 211 ).reset()
        #    self.getControl( 211 ).addItems(listitems)
        #    
        #    self.getControl( 211 ).selectItem( num )
            
        if controlID == 404:
            # Set custom property
            log( "Setting custom property (404)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
            currentWindow = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
            propertyName = ""
            propertyValue = ""
            
            # Retrieve the custom property
            if currentWindow.getProperty( "customProperty" ):
                propertyName = currentWindow.getProperty( "customProperty" )
                currentWindow.clearProperty( "customProperty" )
            else:
                # The customProperty value needs to be set, so return
                currentWindow.clearProperty( "customValue" )
                return
            
            # Retrieve the custom value
            if currentWindow.getProperty( "customValue" ):
                propertyValue = currentWindow.getProperty( "customValue" )
                currentWindow.clearProperty( "customValue" )
                
            if propertyValue == "":
                # No value set, so remove it from additionalListItemProperties
                self._remove_additionalproperty( listitem, propertyName )
            else:
                # Set the property
                self._add_additionalproperty( listitem, propertyName, propertyValue )
            
        if controlID == 405:
            # Launch management dialog for submenu
            log( "Launching management dialog for submenu (405)" )

            currentWindow = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
            
            # Get the group we're about to edit
            launchGroup = self.getControl( 211 ).getSelectedItem().getProperty( "labelID" )
            groupName = self.getControl( 211 ).getSelectedItem().getLabel()
            
            # If the labelID property is empty, we need to generate one
            if launchGroup is None or launchGroup == "":
                DATA._clear_labelID()
                num = self.getControl( 211 ).getSelectedPosition()
                # Get the labelID's of all other menu items
                for x in range(0, self.getControl( 211 ).size()):
                    if not x == num:
                        DATA._get_labelID( self.getControl( 211 ).getListItem( x ).getProperty( "labelID" ) )
                        
                # Now generate labelID for this menu item
                labelID = self.getControl( 211 ).getListItem( num ).getProperty( "localizedString" )
                if labelID is None or labelID == "":
                    launchGroup = self._get_labelID( self.getControl( 211 ).getListItem( num ).getLabel() )
                else:
                    launchGroup = self._get_labelID( labelID )
                self.getControl( 211 ).getListItem( num ).setProperty( "labelID", launchGroup )                                        
            
            # Check if 'level' property has been set
            if currentWindow.getProperty("level"):
                launchGroup = launchGroup + "." + currentWindow.getProperty("level")
                currentWindow.clearProperty("level")
                
            # Check if 'groupname' property has been set
            if currentWindow.getProperty( "overrideName" ):
                groupName = currentWindow.getProperty( "overrideName" )
                currentWindow.clearProperty( "overrideName" )
                
            # Execute the script
            xbmc.executebuiltin( "RunScript(script.skinshortcuts,type=manage&group=" + launchGroup + "&groupname=" + groupName + "&nolabels=" + self.nolabels + ")" )
            

    def warnonremoval( self, item ):
        # This function will warn the user before they modify a settings link
        # (if the skin has enabled this function)
        tree = DATA._get_overrides_skin()
        if tree is None:
            return True
            
        for elem in tree.findall( "warn" ):
            if elem.text.lower() == item.getProperty( "displaypath" ).lower():
                # We want to show the message :)
                message = elem.attrib.get( "message" )
                if not message.find( "::SCRIPT::" ) == -1:
                    message = __language__(int( message[10:] ) )
                elif not message.find( "::LOCAL::" ) == -1:
                    message = xbmc.getLocalizedString(int( message[9:] ) )
                elif message.isdigit():
                    xbmc.getLocalizedString(int( message ) )
                    
                heading = elem.attrib.get( "heading" )
                if not message.find( "::SCRIPT::" ) == -1:
                    heading = __language__(int( heading[10:] ) )
                elif not heading.find( "::LOCAL::" ) == -1:
                    heading = xbmc.getLocalizedString(int( heading[9:] ) )
                elif heading.isdigit():
                    xbmc.getLocalizedString(int( heading ) )
                
                dialog = xbmcgui.Dialog()
                return dialog.yesno( heading, message )
                
        return True
    
    def load_shortcuts( self, includeUserShortcuts = True, addShortcutsToWindow = True ):
        log( "Loading shortcuts" )
        DATA._clear_labelID()
        
        # Set path based on existance of user defined shortcuts, then skin-provided, then script-provided
        loadGroup = DATA.slugify( self.group )
        usingUserShortcuts = False
        usingSkinShortcuts = False
        if xbmcvfs.exists( os.path.join( __datapath__ , loadGroup + ".shortcuts" ) ) and includeUserShortcuts:
            # User defined shortcuts
            path = os.path.join( __datapath__ , loadGroup + ".shortcuts" )
            usingUserShortcuts = True
        elif xbmcvfs.exists( os.path.join( __skinpath__ , loadGroup + ".shortcuts" ) ):
            # Skin-provided defaults
            path = os.path.join( __skinpath__ , loadGroup + ".shortcuts" )
            usingSkinShortcuts = True
        elif xbmcvfs.exists( os.path.join( __defaultpath__ , loadGroup + ".shortcuts" ) ):
            # Script-provided defaults
            path = os.path.join( __defaultpath__ , loadGroup + ".shortcuts" )
        else:
            # No custom shortcuts or defaults available
            path = ""
        tree = DATA._get_overrides_skin()
        matchedSkinRequredActions = []
            
        if not path == "":
            # Try to load shortcuts
            try:
                file = xbmcvfs.File( path )
                loaditems = eval( file.read() )
                file.close()
                
                DATA._clear_labelID()
                listitems = []
                
                for item in loaditems:
                    # Parse any localised labels
                    newItem = self._parse_listitem( item )
                    
                    if addShortcutsToWindow and tree is not None and self.group == "mainmenu":
                        # Check if the action for this newItem matches a skin-required action
                        for elem in tree.findall( "requiredshortcut" ):
                            if elem.text == newItem.getProperty( "displayPath" ):
                                # It does, so save the action and lock the item
                                newItem.setProperty( "LOCKED", "True" )
                                matchedSkinRequredActions.append( newItem.getProperty( "displayPath" ) )
                                # If we're using the skin-provided shortcuts, also change the label2 and add a property
                                if usingSkinShortcuts:
                                    newItem.setLabel2( xbmc.getSkinDir() )
                                    self._add_additionalproperty( newItem, "Skin-Required-Shortcut", xbmc.getSkinDir() )
                    
                    # Add to list
                    listitems.append( newItem )
                    
                if addShortcutsToWindow:
                    # Check for any skin-required actions not already in the list
                    if tree is not None and self.group == "mainmenu":
                        for elem in tree.findall( "requiredshortcut" ):
                            if elem.text not in matchedSkinRequredActions:
                                newItem = self._parse_listitem( [elem.attrib.get( "label" ), xbmc.getSkinDir(), elem.attrib.get( "icon"), elem.attrib.get( "thumb" ), elem.text] )
                                newItem.setProperty( "LOCKED", "True" )
                                self._add_additionalproperty( newItem, "Skin-Required-Shortcut", xbmc.getSkinDir() )
                                listitems.append( newItem )
                    # If we've loaded anything...
                    if len(listitems) != 0:
                        # Load widgets, backgrounds and any skin-specific properties
                        returnItems = self._check_properties( listitems, usingUserShortcuts )
                        
                        # Add them to the list of current shortcuts
                        self.getControl( 211 ).addItems(returnItems)
                    
                    # If there are no items in the list, add an empty one...
                    if self.getControl( 211 ).size() == 0:
                        listitem = xbmcgui.ListItem( __language__(32013) )
                        listitem.setProperty( "Path", 'noop' )
                        
                        self.getControl( 211 ).addItem( listitem )
                        
                        # Set focus
                        self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
                else:
                    return listitems
            except:
                # We couldn't load the file
                print_exc()
                log( "### ERROR could not load file %s" % path )
                return []
        else:
            if addShortcutsToWindow:
                # Add an empty item
                listitem = xbmcgui.ListItem( __language__(32013) )
                listitem.setProperty( "Path", 'noop' )
                
                self.getControl( 211 ).addItem( listitem )
                
                # Set focus
                self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
            else:
                return []
        
                
    def _add_additionalproperty( self, listitem, propertyName, propertyValue ):
        # Add an item to the additional properties of a user items
        properties = []
        if listitem.getProperty( "additionalListItemProperties" ):
            properties = eval( listitem.getProperty( "additionalListItemProperties" ) )
        
        foundProperty = False
        for property in properties:
            if property[0] == propertyName:
                foundProperty = True
                property[1] = propertyValue
                listitem.setProperty( propertyName, propertyValue )
                
        if foundProperty == False:
            properties.append( [propertyName, propertyValue] )
            listitem.setProperty( propertyName, propertyValue )
            
        listitem.setProperty( "additionalListItemProperties", repr( properties ) )
        
    def _remove_additionalproperty( self, listitem, propertyName ):
        # Remove an item from the additional properties of a user item
        properties = []
        hasProperties = False
        if listitem.getProperty( "additionalListItemProperties" ):
            properties = eval( listitem.getProperty( "additionalListItemProperties" ) )
            hasProperties = True
        
        for property in properties:
            if property[0] == propertyName:
                properties.remove( property )
        
        listitem.setProperty( "additionalListItemProperties", repr( properties ) )
            
        listitem.setProperty( propertyName, None )
        
                
    def _parse_listitem( self, item ):
        # Parse a loaded listitem, replacing ::SCRIPT:: or ::LOCAL:: with localized strings
        loadLabel = item[0]
        loadLabel2 = item[1]
        saveLabel2 = item[1]

        if not loadLabel2.find( "::SCRIPT::" ) == -1:
            saveLabel2 = __language__( int ( loadLabel2[10:] ) )
        elif not loadLabel2.find( "::LOCAL::" ) == -1:
            saveLabel2 = xbmc.getLocalizedString(int( loadLabel2[9:] ) )
        
        if not loadLabel.find( "::SCRIPT::" ) == -1:
            # An item with a script-localized string
            listitem = xbmcgui.ListItem(label=__language__(int( loadLabel[10:] ) ), label2=saveLabel2, iconImage=item[2], thumbnailImage=item[3])
            listitem.setProperty( "localizedString", loadLabel )
        elif not loadLabel.find( "::LOCAL::" ) == -1:
            # An item with an XBMC-localized string
            listitem = xbmcgui.ListItem(label= xbmc.getLocalizedString(int( loadLabel[9:] ) ), label2=saveLabel2, iconImage=item[2], thumbnailImage=item[3])
            listitem.setProperty( "localizedString", loadLabel )
        else:
            # An item without a localized string
            listitem = xbmcgui.ListItem(label=item[0], label2=saveLabel2, iconImage=item[2], thumbnailImage=item[3])
           
        # Load the action (the "path" property)
        action = item[4]
        displayAction = urllib.unquote( action )
        
        # If the displayAction uses the special://skin protocol, translate the path
        if "special://skin/" in displayAction:
            translate = xbmc.translatePath( "special://skin/" ).decode( "utf-8" )
            displayAction = displayAction.replace( "special://skin/", translate )
            action = urllib.quote( displayAction )
            
        # Set the action
        listitem.setProperty( "path", action )
        listitem.setProperty( "displaypath", displayAction )
        
        # Load the rest of the properties
        listitem.setProperty( "icon", item[2] )
        listitem.setProperty( "thumbnail", item[3] )
        
        listitem.setProperty( "shortcutType", loadLabel2 )
            
        listitem.setProperty( "labelID", self._get_labelID( loadLabel ) )
        return listitem
        
        
    def _get_labelID ( self, item ):
        # Translate certain localized strings into non-localized form for labelID
        item = item.replace("::SCRIPT::", "")
        item = item.replace("::LOCAL::", "")
        returnVal = None
        if item == "10006":
            returnVal = "videos"
        elif item == "342":
            returnVal = "movies"
        elif item == "20343":
            returnVal = "tvshows"
        elif item == "32022":
            returnVal = "livetv"
        elif item == "10005":
            returnVal = "music"
        elif item == "20389":
            returnVal = "musicvideos"
        elif item == "10002":
            returnVal = "pictures"
        elif item == "12600":
            returnVal = "weather"
        elif item == "10001":
            returnVal = "programs"
        elif item == "32032":
            returnVal = "dvd"
        elif item == "10004":
            returnVal = "settings"
        else:
            returnVal = item.replace(" ", "").lower()
        
        return DATA._get_labelID( returnVal )
        
        
    def _check_properties( self, listitems, usingUserShortcuts ):
        # Grab loaded properties (from skin.name.properties for menus user has already edited, else from skin defaults)
        if usingUserShortcuts:
            allProperties = self.currentProperties
        else:
            allProperties = self.defaultProperties
                    
        DATA._clear_labelID()
        # Check if we've loaded anything
        if len( allProperties ) == 0:
            for listitem in listitems:
                self._get_icon_overrides( listitem )
            return listitems
            
        # Process the files we've loaded, and match any properties to listitems
        for listitem in listitems:
            self._get_icon_overrides( listitem )
            backgroundName = None
            widgetName = None
            backgroundPlaylistName = None
            widgetPlaylistName = None
            
            # Loop through all the data we've loaded
            for singleProperty in allProperties:
                # singleProperty[0] = Group name
                # singleProperty[1] = labelID
                # singleProperty[2] = property name
                # singleProperty[3] = property value
                
                # If the group and labelID match, add the property
                if singleProperty[0] == self.group and singleProperty[1] == listitem.getProperty( "labelID" ):
                    self._add_additionalproperty( listitem, singleProperty[2], singleProperty[3] )
                    
                    # If we're not usingUserShortcuts and this is the background or widget property, load the name
                    # (We're not going to set the property quite yet in case we need and haven't loaded the playlist)
                    if not usingUserShortcuts:
                        if singleProperty[2] == "widget":
                            if singleProperty[3] == "Playlist":
                                widgetName = "Playlist"
                            else:
                                widgetName = self.widgetsPretty[ singleProperty[3] ]
                        elif singleProperty[2] == "widgetPlaylist":
                            widgetPlaylistName = singleProperty[3]
                            
                        elif singleProperty[2] == "background":
                            backgroundName = self.backgroundsPretty[ setValue ]
                        elif singleProperty[2] == "backgroundPlaylistName":
                            backgroundPlaylistName = singleProperty[3]
                            
            # Set the widgetName property
            if widgetName == "Playlist" and widgetPlaylistName is not None:
                for widgetPlaylistList in LIBRARY.widgetPlaylistsList:
                    if widgetPlaylistList[0] == widgetPlaylistName:
                        self._add_additionalproperty( listitem, "widgetName", widgetPlaylistList[1] )
                        break
            elif widgetName is not None:
                self._add_additionalproperty( listitem, "widgetName", widgetName )
                
            # Set the backgroundName property
            if backgroundName is not None and "::PLAYLIST::" in backgroundName and backgroundPlaylistName is not None:
                self._add_additionalproperty( listitem, "backgroundName", backgroundName.replace( "::PLAYLIST::", backgroundPlaylistName ) )
            elif backgroundName is not None:
                self._add_additionalproperty( listitem, "backgroundName", backgroundName )
                            
        return listitems
        
    
    def _load_properties( self ):
        # Load all saved properties (widgets, backgrounds, custom properties)
        path = os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".properties" )
        if xbmcvfs.exists( path ):
            # The properties file exists, load from it
            listProperties = eval( xbmcvfs.File( path ).read() )
            for listProperty in listProperties:
                # listProperty[0] = groupname
                # listProperty[1] = labelID
                # listProperty[2] = property name
                # listProperty[3] = property value
                self.currentProperties.append( [listProperty[0], listProperty[1], listProperty[2], listProperty[3]] )
            
        # Load skin defaults (in case we need them...)
        overridepath = os.path.join( __skinpath__ , "overrides.xml" )
        if xbmcvfs.exists(overridepath):
            try:
                overrides = xmltree.fromstring( xbmcvfs.File( overridepath ).read() )
                for elemSearch in [["widget", overrides.findall( "widgetdefault" )], ["background", overrides.findall( "backgrounddefault" )], ["custom", overrides.findall( "propertydefault" )] ]:
                    for elem in elemSearch[1]:
                        if elemSearch[0] == "custom":
                            # Custom property
                            if "group" not in elem.attrib:
                                self.defaultProperties.append( ["mainmenu", elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text ] )
                            else:
                                self.defaultProperties.append( [elem.attrib.get( "group" ), elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text ] )
                        else:
                            # Widget or background
                            if "group" not in elem.attrib:
                                self.defaultProperties.append( [ "mainmenu", elem.attrib.get( 'labelID' ), elemSearch[0], elem.text ] )
                                if elemSearch[0] == "widget":
                                    # Get and set widget type and name
                                    widgetDetails = DATA._getWidgetNameAndType( elem.text )
                                    log( repr( widgetDetails ) )
                                    if widgetDetails is not None:
                                        self.defaultProperties.append( [ "mainmenu", elem.attrib.get( "labelID" ), "widgetName", widgetDetails[0] ] )
                                        if widgetDetails[1] is not None:
                                            self.defaultProperties.append( [ "mainmenu", elem.attrib.get( "labelID" ), "widgetType", widgetDetails[1] ] )
                            else:
                                self.defaultProperties.append( [ elem.attrib.get( "group" ), elem.attrib.get( 'labelID' ), elemSearch[0], elem.text ] )
                                if elemSearch[0] == "widget":
                                    # Get and set widget type and name
                                    widgetDetails = DATA._getWidgetNameAndType( elem.text )
                                    if widgetDetails is not None:
                                        self.defaultProperties.append( [ elem.attrib.get( "group" ), elem.attrib.get( "labelID" ), "widgetName", widgetDetails[0] ] )
                                        if widgetDetails[1] is not None:
                                            self.defaultProperties.append( [ elem.attrib.get( "group" ), elem.attrib.get( "labelID" ), "widgetType", widgetDetails[1] ] )                

                # Should we allow the user to browse for background images...
                elem = overrides.find('backgroundBrowse')
                if elem is not None and elem.text == "True":
                    self.backgroundBrowse = True
                
                # Should we allow the user to select a playlist as a widget...
                elem = overrides.find('widgetPlaylists')
                if elem is not None and elem.text == "True":
                    self.widgetPlaylists = True
                    if "type" in elem.attrib:
                        self.widgetPlaylistsType = elem.attrib.get( "type" )
                
            except:
                pass
                        
        
    def _duplicate_listitem( self, listitem, originallistitem = None ):
        # Create a copy of an existing listitem
        listitemCopy = xbmcgui.ListItem(label=listitem.getLabel(), label2=listitem.getLabel2(), iconImage=listitem.getProperty("icon"), thumbnailImage=listitem.getProperty("thumbnail"))
        listitemCopy.setProperty( "path", listitem.getProperty("path") )
        listitemCopy.setProperty( "displaypath", urllib.unquote( listitem.getProperty("path") ) )
        listitemCopy.setProperty( "icon", listitem.getProperty("icon") )
        listitemCopy.setProperty( "thumbnail", listitem.getProperty("thumbnail") )
        listitemCopy.setProperty( "localizedString", listitem.getProperty("localizedString") )
        listitemCopy.setProperty( "shortcutType", listitem.getProperty("shortcutType") )       
        
        if listitem.getProperty( "LOCKED" ):
            listitemCopy.setProperty( "LOCKED", "True" )
        
        if listitem.getProperty( "customThumbnail" ):
            listitemCopy.setProperty( "customThumbnail", listitem.getProperty( "customThumbnail" ) )
            
        # Revert to original icon/thumbnail (because we'll override it again in a minute!)
        if listitem.getProperty( "original-icon" ):
            icon = listitem.getProperty( "original-icon" )
            if icon == "":
                icon = None
            listitemCopy.setIconImage( icon )
            listitemCopy.setProperty( "icon", icon )
        if listitem.getProperty( "original-thumbnail" ):
            thumb = listitem.getProperty( "original-thumbnail" )
            if thumb == "":
                thumb = None
            listitemCopy.setThumbnailImage( thumb )
            listitemCopy.setProperty( "thumbnail", thumb )
        
        # If we've haven't been passed an originallistitem, set the following from the listitem we were passed
        if originallistitem is None:
            listitemCopy.setProperty( "labelID", listitem.getProperty("labelID") )
            if listitem.getProperty( "additionalListItemProperties" ):
                listitemCopy.setProperty( "additionalListItemProperties", listitem.getProperty( "additionalListItemProperties" ) )
                listitemProperties = eval( listitem.getProperty( "additionalListItemProperties" ) )
                
                for listitemProperty in listitemProperties:
                    listitemCopy.setProperty( listitemProperty[0], listitemProperty[1] )
        else:
            # Set these from the original item we were passed (this will keep original labelID and additional properties
            # in tact)
            listitemCopy.setProperty( "labelID", originallistitem.getProperty( "labelID" ) )
            if originallistitem.getProperty( "additionalListItemProperties" ):
                listitemCopy.setProperty( "additionalListItemProperties", originallistitem.getProperty( "additionalListItemProperties" ) )
                listitemProperties = eval( originallistitem.getProperty( "additionalListItemProperties" ) )
                
                for listitemProperty in listitemProperties:
                    listitemCopy.setProperty( listitemProperty[0], listitemProperty[1] )        
                
        return listitemCopy
        
    def _get_icon_overrides( self, listitem, setToDefault = True ):
        # Start by getting the labelID
        labelID = listitem.getProperty( "localizedString" )
        if labelID == None or labelID == "":
            labelID = listitem.getLabel()
        labelID = self._get_labelID( labelID )
        
        # Retrieve icon
        icon = listitem.getProperty( "icon" )
        oldicon = None
        
        # Check for overrides
        tree = DATA._get_overrides_skin()
        if tree is not None:
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
        if not xbmc.skinHasImage( icon ) and setToDefault == True:
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
            self._get_icon_overrides( listitem, False )
        
        
    def _save_shortcuts( self ):
        # Save shortcuts
        if self.changeMade == True:
            log( "Saving changes" )
            listitems = []
            properties = []
            
            labelIDChanges = []
            labelIDChangesDict = {}
            
            DATA._clear_labelID()
            
            for x in range(0, self.getControl( 211 ).size()):
                listitem = self.getControl( 211 ).getListItem(x)
                
                # If the item has a label...
                if listitem.getLabel().decode("utf-8") != __language__(32013):
                    saveLabel = listitem.getLabel()
                    saveLabel2 = listitem.getLabel2()
                    
                    # Generate labelID, and mark if it has changes
                    labelID = listitem.getProperty( "labelID" )
                    newlabelID = labelID
                    localizedString = listitem.getProperty( "localizedString" )
                    if localizedString is None or localizedString == "":
                        newlabelID = self._get_labelID( listitem.getLabel() )
                    else:
                        newlabelID = self._get_labelID( localizedString )                        
                    
                    if self.group == "mainmenu":
                        labelIDChanges.append( [labelID, newlabelID] )
                        labelIDChangesDict[ labelID ] = newlabelID
                        
                    labelID = newlabelID
                    
                    # Save specific properties
                    if listitem.getProperty( "localizedString" ):
                        saveLabel = listitem.getProperty( "localizedString" ).decode('utf-8')
                        
                    # If we're seeing an overriden icon, switch to the original
                    if listitem.getProperty( "original-icon" ):
                        icon = listitem.getProperty( "original-icon" )
                    else:
                        icon = listitem.getProperty( "icon" )
                        
                    thumbnail = listitem.getProperty( "thumbnail" )
                    
                    savedata=[saveLabel, listitem.getProperty("shortcutType"), icon, thumbnail, listitem.getProperty("path")]
                        
                    if listitem.getProperty( "additionalListItemProperties" ):
                        properties.append( [ labelID, eval( listitem.getProperty( "additionalListItemProperties" ) ) ] )
                        
                    listitems.append(savedata)
                            
            path = os.path.join( __datapath__ , DATA.slugify( self.group ) + ".shortcuts" ).encode('utf-8')
            
            # If there are any shortcuts, save them
            try:
                log( "Saving " + path )
                f = xbmcvfs.File( path, 'w' )
                f.write( repr( listitems ).replace( "],", "],\n" ) )
                f.close()
            except:
                print_exc()
                log( "### ERROR could not save file %s" % __datapath__ )
            
                        
            # Now make any labelID changes
            while not len( labelIDChanges ) == 0:
                # Get the first labelID change, and check that we're not changing anything from that
                labelIDFrom = labelIDChanges[0][0]
                labelIDTo = labelIDChanges[0][1]
                
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
                            labelIDChanges.append( [tempLocation, labelIDTo] )
                            labelIDTo = tempLocation
                            break
                            
                # Make the change (0 - the main sub-menu, 1-5 - additional submenus )
                for i in range( 0, 6 ):
                    if i == 0:
                        paths = [[os.path.join( __datapath__, DATA.slugify( labelIDFrom ) + ".shortcuts" ).encode( "utf-8" ), "Move"], [os.path.join( __skinpath__, DATA.slugify( labelIDFrom ) + ".shortcuts" ).encode( "utf-8" ), "Copy"], [os.path.join( __defaultpath__, DATA.slugify( labelIDFrom ) + ".shortcuts" ).encode( "utf-8" ), "Copy"], [None, "New"]]
                        target = os.path.join( __datapath__, DATA.slugify( labelIDTo ) + ".shortcuts" ).encode( "utf-8" )
                    else:
                        paths = [[os.path.join( __datapath__, DATA.slugify( labelIDFrom ) + "." + str( i ) + ".shortcuts" ).encode( "utf-8" ), "Move"], [os.path.join( __skinpath__, DATA.slugify( labelIDFrom ) + "." + str( i ) + ".shortcuts" ).encode( "utf-8" ), "Copy"], [os.path.join( __defaultpath__, DATA.slugify( labelIDFrom ) + "." + str( i ) + ".shortcuts" ).encode( "utf-8" ), "Copy"]]
                        target = os.path.join( __datapath__, DATA.slugify( labelIDTo ) + "." + str( i ) + ".shortcuts" ).encode( "utf-8" )
                    
                    for path in paths:
                        if path[1] == "New":
                            # Create a new (empty) file at the target path
                            f = xbmcvfs.File( target, 'w' )
                            f.write( repr( [] ) )
                            f.close()
                            break
                        elif xbmcvfs.exists( path[0] ):
                            if path[1] == "Move":
                                # Move the original to the target path
                                xbmcvfs.rename( path[0], target )
                            else:
                                # Copy a default shortcuts file to the target path
                                xbmcvfs.copy( path[0], target )
                            break
                        
                labelIDChanges.pop( 0 )
                    
            # Save widgets, backgrounds and custom properties
            log( repr( properties ) )
            self._save_properties( properties, labelIDChangesDict )
            
            # Note that we've saved stuff
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-reloadmainmenu", "True" )
                    
    def _save_properties( self, properties, labelIDChanges ):
        # Save all additional properties (widgets, backgrounds, custom)
        log( "Saving properties" )
        
        # Get previously loaded properties
        currentProperties = self.currentProperties
        
        # Copy any items not in the current group to the array we'll save, and
        # make any labelID changes whilst we're at it
        saveData = []
        for property in currentProperties:
            #[ groupname, itemLabelID, property, value ]
            if not property[0] == self.group:
                if property[0] in labelIDChanges.keys():
                    property[0] = self.labelIDChanges[property[0]]
                saveData.append( property )
        
        # Add all the properties we've been passed
        for property in properties:
            # property[0] = labelID
            for toSave in property[1]:
                # toSave[0] = property name
                # toSave[1] = property value
                
                saveData.append( [ self.group, property[0], toSave[0], toSave[1] ] )
        
        # Try to save the file
        try:
            f = xbmcvfs.File( os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".properties" ), 'w' )
            f.write( repr( saveData ).replace( "],", "],\n" ) )
            f.close()
        except:
            print_exc()
            log( "### ERROR could not save file %s" % __datapath__ )                
            
    
    def _display_shortcuts( self ):
        # Load the currently selected shortcut group
        newGroup = LIBRARY.retrieveGroup( self.shortcutgroup )
        
        label = newGroup[0]
        if not newGroup[0].find( "::SCRIPT::" ) == -1:
            label = __language__(int( newGroup[0][10:] ) )
        elif not newGroup[0].find( "::LOCAL::" ) == -1:
            label = xbmc.getLocalizedString(int( newGroup[0][9:] ) )
        
        self.getControl( 111 ).reset()
        for item in newGroup[1]:
            newItem = self._duplicate_listitem( item )
            if item.getProperty( "action-show" ):
                newItem.setProperty( "action-show", item.getProperty( "action-show" ) )
                newItem.setProperty( "action-play", item.getProperty( "action-play" ) )
            self.getControl( 111 ).addItem( newItem )
        self.getControl( 101 ).setLabel( label + " (%s)" %self.getControl( 111 ).size() )
        
    def onAction( self, action ):
        if action.getId() in ACTION_CANCEL_DIALOG:
            #if self.getFocusId() == 402 and action.getId() == 61448: # Check we aren't backspacing on an edit dialog
            #    return
            #if self.getFocusId() == 403 and action.getId() == 61448: # Check we aren't backspacing on an edit dialog
            #    return
            self._save_shortcuts()
            xbmcgui.Window(self.window_id).clearProperty('groupname')
            self._close()

    def _close( self ):
            self.close()

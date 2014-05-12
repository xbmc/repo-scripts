# coding=utf-8
import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
from xml.dom.minidom import parse
from xml.sax.saxutils import escape as escapeXML
import thread
from traceback import print_exc
from unidecode import unidecode

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
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        self.group = kwargs[ "group" ]
        self.shortcutgroup = 1
        
        # Empty arrays for different shortcut types
        self.backgroundBrowse = False
        self.widgetPlaylists = False
        
        self.currentProperties = []
        self.defaultProperties = []
        
        self.changeMade = False
        #self.labelIDChanges = []
        self.labelIDChanges = {}
        
        log( 'Management module loaded' )

    def onInit( self ):
        if self.group == '':
            self._close()
        else:
            self.window_id = xbmcgui.getCurrentWindowDialogId()
            xbmcgui.Window(self.window_id).setProperty('groupname', self.group)
            
            # Load library shortcuts in thread
            thread.start_new_thread( LIBRARY.loadLibrary, () )
            
            # Load widget and background names
            self._load_widgetsbackgrounds()
            
            # Load saved and default properties
            self._load_properties()
            
            # Load current shortcuts
            self.load_shortcuts()
            
            # Set button labels
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
                log( "Not adit action button on GUI (id 307)" )
                
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
                if elem.attrib.get( 'label' ).isdigit():
                    self.widgets.append( [elem.text, xbmc.getLocalizedString( int( elem.attrib.get( 'label' ) ) ) ] )
                    self.widgetsPretty[elem.text] = xbmc.getLocalizedString( int( elem.attrib.get( 'label' ) ) )
                else:
                    self.widgets.append( [elem.text, elem.attrib.get( 'label' ) ] )
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
                self.shortcutgroup = 7
                
            self._display_shortcuts()

        if controlID == 103:
            # Move to next type of shortcuts
            self.shortcutgroup = self.shortcutgroup + 1
            if self.shortcutgroup == 8:
                self.shortcutgroup = 1
                
            self._display_shortcuts()
            
        if controlID == 111:
            # User has selected an available shortcut they want in their menu
            log( "Select shortcut (111)" )
            listControl = self.getControl( 211 )
            itemIndex = listControl.getSelectedPosition()
            altAction = None
            
            path = urllib.unquote( self.getControl( 111 ).getSelectedItem().getProperty( "Path" ) )
            if path.startswith( "||BROWSE||" ):
                # If this is a plugin, call our plugin browser
                self._browseLibrary( ["plugin://" + path.replace( "||BROWSE||", "" )], "plugin://" + path.replace( "||BROWSE||", "" ), [self.getControl( 111 ).getSelectedItem().getLabel()], [self.getControl( 111 ).getSelectedItem().getProperty("thumbnail")], self.getControl( 211 ).getSelectedPosition(), self.getControl( 111 ).getSelectedItem().getProperty("shortcutType")  )
                return
            elif path == "||PLAYLIST||":
                # Give the user the choice of playing or displaying the playlist
                dialog = xbmcgui.Dialog()
                userchoice = dialog.yesno( __language__( 32040 ), __language__( 32060 ), "", "", __language__( 32061 ), __language__( 32062 ) )
                # False: Display
                # True: Play
                if userchoice == False:
                    altAction = self.getControl( 111 ).getSelectedItem().getProperty( "action-show" )
                else:
                    altAction = self.getControl( 111 ).getSelectedItem().getProperty( "action-play" )
                
            self.changeMade = True
            
            # Copy the new shortcut
            listitem = self._duplicate_listitem( self.getControl( 111 ).getSelectedItem() )
            labelID = listitem.getProperty( "labelID" )
            
            # If altAction is set, change the path property
            if altAction is not None:
                listitem.setProperty( "Path", altAction )
            
            # Update the list
            listitems = []
            for x in range( 0, listControl.size() ):
                if x == itemIndex:
                    # Where the new shortcut should go
                    listitems.append( listitem )
                else:
                    listitems.append( self._duplicate_listitem( listControl.getListItem( x ) ) )
            
            listControl.reset()
            listControl.addItems( listitems )
            listControl.selectItem( itemIndex )
            
            if self.group == "mainmenu":
                self._remove_labelid_changes( labelID )
        
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
            
            itemIndex = listControl.getSelectedPosition()
            if self.group == "mainmenu":
                self._remove_labelid_changes( listControl.getListItem(itemIndex).getProperty( "labelID" ) )
            listControl.removeItem( itemIndex )
            listControl.selectItem( itemIndex )
            
            # If there are no other items in the list...
            if listControl.size() == 0:
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
            for x in range( 0 , listControl.size() ):
                if x == itemIndex:
                    # Where the original item was
                    listitems.append( swapitem )
                elif x == itemIndex - 1:
                    # Where we want the item
                    listitems.append( listitem )
                else:
                    listitems.append( self._duplicate_listitem( listControl.getListItem(x) ) )
                    
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
            for x in range( 0, listControl.size() ):
                if x == itemIndex:
                    # Where the original item was
                    listitems.append( swapitem )
                elif x == itemIndex + 1:
                    # Where we want the item
                    listitems.append( listitem )
                else:
                    listitems.append( self._duplicate_listitem( listControl.getListItem(x) ) )
                    
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
            listitem.setProperty( "labelID", self._get_labelID( label ) )
            
            # If there's no label2, set it to custom shortcut
            if not listitem.getLabel2():
                listitem.setLabel2( __language__(32024) )
                listitem.setProperty( "shortcutType", "::SCRIPT::32024" )
                
            # If this is the mainmenu group, update the labelIDChanges list
            if self.group == "mainmenu":
                self._update_labelid_changes( oldlabelID, listitem.getProperty( "labelID" ) )

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
                listitem.setProperty( "Thumbnail", custom_thumbnail )
                listitem.setProperty( "customThumbnail", "False" )
            
        if controlID == 307:
            # Change Action
            log( "Change action (307)" )
            listControl = self.getControl( 211 )
            listitem = listControl.getSelectedItem()
            
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
            
            # Update the action
            listitem.setProperty( "path", urllib.quote( action ) )
            listitem.setLabel2( __language__(32024) )
            listitem.setProperty( "shortcutType", "::SCRIPT::32024" )
            
        if controlID == 308:
            # Reset shortcuts
            log( "Reset shortcuts (308)" )
            self.changeMade = True
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
            for key in self.widgets:
                widget.append( key[0] )
                widgetLabel.append( key[1] )
                
            # If playlists have been enabled for widgets, add them too
            if self.widgetPlaylists:
                for playlist in LIBRARY.widgetPlaylistsList:
                    widget.append( "::PLAYLIST::" + playlist[0] )
                    widgetLabel.append( playlist[1] )
                    
            # Show the dialog
            selectedWidget = xbmcgui.Dialog().select( __language__(32044), widgetLabel )
            
            if selectedWidget == -1:
                # User cancelled
                return
            elif selectedWidget == 0:
                # User selected no widget
                self._remove_additionalproperty( listitem, "widget" )
                self._remove_additionalproperty( listitem, "widgetName" )
                self._remove_additionalproperty( listitem, "widgetPlaylist" )
                
            else:
                if widget[selectedWidget].startswith( "::PLAYLIST::" ):
                    self._add_additionalproperty( listitem, "widget", "Playlist" )
                    self._add_additionalproperty( listitem, "widgetPlaylist", widget[selectedWidget].strip( "::PLAYLIST::" ) )

                else:
                    self._add_additionalproperty( listitem, "widget", widget[selectedWidget] )
                    self._remove_additionalproperty( listitem, "widgetPlaylist" )
                
                self._add_additionalproperty( listitem, "widgetName", widgetLabel[selectedWidget] )
                
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
                    custom_image = dialog.browse( 2 , xbmc.getLocalizedString(1030), 'files')
                else: # Multi-image
                    custom_image = dialog.browse( 0 , xbmc.getLocalizedString(1030), 'files')
                
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
            # Choose shortcut (SELECT DIALOG)
            log( "Choose shortcut (401)" )
            labelID = None
            
            # Check for a window property designating category
            currentWindow = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
            shortcutCategory = -1
            if currentWindow.getProperty("category"):
                skinCategory = currentWindow.getProperty("category")
                if skinCategory == "common":
                    shortcutCategory = 0
                elif skinCategory == "video":
                    shortcutCategory = 1
                elif skinCategory == "music":
                    shortcutCategory = 2
                elif skinCategory == "playlists":
                    shortcutCategory = 3
                elif skinCategory == "favourites":
                    shortcutCategory = 4
                elif skinCategory == "addons":
                    shortcutCategory = 5
                elif skinCategory == "commands":
                    shortcutCategory = 6
            else:
                # No window property passed, ask the user what category they want
                shortcutCategories = [__language__(32029), __language__(32030), __language__(32031), __language__(32040), __language__(32006), __language__(32007), __language__(32057)]
                shortcutCategory = xbmcgui.Dialog().select( __language__(32043), shortcutCategories )
                
            # Clear the window property
            currentWindow.clearProperty("category")
            
            # Get the shortcuts for the group the user has selected
            displayLabel2 = False
                        
            if shortcutCategory == 0: # Common
                availableShortcuts = LIBRARY.common()
            elif shortcutCategory == 1: # Video Library
                availableShortcuts = LIBRARY.videolibrary()
                displayLabel2 = True
            elif shortcutCategory == 2: # Music Library
                availableShortcuts = LIBRARY.musiclibrary()
                displayLabel2 = True
            elif shortcutCategory == 3: # Playlists
                #    xbmc.sleep( 100 )
                availableShortcuts = LIBRARY.playlists()
                displayLabel2 = True
            elif shortcutCategory == 4: # Favourites
                availableShortcuts = LIBRARY.favourites()
            elif shortcutCategory == 5: # Add-ons
                availableShortcuts = LIBRARY.addons()
                displayLabel2 = True
            elif shortcutCategory == 6: # XBMC Commands
                availableShortcuts = LIBRARY.more()
                
            else: # No category selected
                log( "No shortcut category selected" )
                return
                            
            # Now build an array of items to show to the user
            displayShortcuts = []
            for shortcut in availableShortcuts:
                if displayLabel2:
                    displayShortcuts.append( "(" + shortcut.getLabel2() + ") " + shortcut.getLabel() )
                else:
                    displayShortcuts.append( shortcut.getLabel() )
            
            selectedShortcut = xbmcgui.Dialog().select( shortcutCategories[shortcutCategory], displayShortcuts )
            
            if selectedShortcut != -1:
                # Create a copy of the listitem
                listitemCopy = self._duplicate_listitem( availableShortcuts[selectedShortcut] )
                
                path = urllib.unquote( listitemCopy.getProperty( "Path" ) )
                if path.startswith( "||BROWSE||" ):
                    self._browseLibrary( ["plugin://" + path.replace( "||BROWSE||", "" )], "plugin://" + path.replace( "||BROWSE||", "" ), [listitemCopy.getLabel()], [listitemCopy.getProperty("thumbnail")], self.getControl( 211 ).getSelectedPosition(), listitemCopy.getProperty("shortcutType")  )
                    return
                elif path == "||PLAYLIST||" :
                    # Give the user the choice of playing or displaying the playlist
                    dialog = xbmcgui.Dialog()
                    userchoice = dialog.yesno( __language__( 32040 ), __language__( 32060 ), "", "", __language__( 32061 ), __language__( 32062 ) )
                    # False: Display
                    # True: Play
                    if userchoice == False:
                        listitemCopy.setProperty( "Path", availableShortcuts[selectedShortcut].getProperty( "action-show" ) )
                    else:
                        listitemCopy.setProperty( "Path", availableShortcuts[selectedShortcut].getProperty( "action-play" ) )
                    
                self.changeMade = True
                
                # Loop through the original list, and replace the currently selected listitem with our new listitem
                listitems = []
                num = self.getControl( 211 ).getSelectedPosition()
                for x in range(0, self.getControl( 211 ).size()):
                    if x == num:
                        labelID = self.getControl( 211 ).getListItem(x).getProperty( "labelID" )
                        listitems.append(listitemCopy)
                    else:
                        # Duplicate the item and add it to the listitems array
                        listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                        listitems.append(listitemShortcutCopy)
                        
                self.getControl( 211 ).reset()
                self.getControl( 211 ).addItems(listitems)
                
                self.getControl( 211 ).selectItem( num )
                
            if self.group == "mainmenu":
                self._remove_labelid_changes( labelID )
        
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
            
            # Check if this labelID has been updated - if so, we want to edit the original
            # labelID
            if self.group == "mainmenu" and len( self.labelIDChanges) != 0:
                for labelIDChange in self.labelIDChanges:
                    if launchGroup == labelIDChange[1]:
                        launchGroup = labelIDChange[0]
                
            
            # Check if 'level' property has been set
            if currentWindow.getProperty("level"):
                launchGroup = launchGroup + "." + currentWindow.getProperty("level")
                currentWindow.clearProperty("level")
                
            # Execute the script
            xbmc.executebuiltin( "RunScript(script.skinshortcuts,type=manage&group=" + launchGroup + ")" )

            
    def _browseLibrary( self, history, location, label, thumbnail, itemToReplace, itemType ):
        dialogLabel = label[0]

        # Default action - create shortcut
        displayList = [ " > " + __language__(32058) ]
        displayListActions = [ "||CREATE||" ]
        displayListThumbs = [ "NONE" ]
        
        # If this isn't the root, create a link to go up the heirachy
        if len( label ) is not 1:
            displayList.append( " > .." )
            displayListActions.append( "||BACK||" )
            displayListThumbs.append( "NONE" )
            
            dialogLabel = label[0] + " - " + label[ len( label ) - 1 ]
            
        dialog = xbmcgui.DialogProgress()
        dialog.create( dialogLabel, __language__( 32063) )
    
        # JSON query
        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Files.GetDirectory", "params": { "properties": ["title", "file", "thumbnail"], "directory": "' + location + '", "media": "files" } }')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        
        dialog.close()
            
        # Add all directories returned by the json query
        if json_response.has_key('result') and json_response['result'].has_key('files') and json_response['result']['files'] is not None:
            for item in json_response['result']['files']:
                if item["filetype"] == "directory":
                    displayList.append( item['label'] )
                    displayListActions.append( item['file'] )
                    displayListThumbs.append( item['thumbnail'] )
            
        # Show dialog
        dialog = xbmcgui.Dialog()
        selectedItem = dialog.select( dialogLabel, displayList )
        
        if selectedItem != -1:
            if displayListActions[ selectedItem ] == "||CREATE||":
                # User has chosen the shortcut they want
                self.changeMade = True
                
                # Build the action
                if itemType == "::SCRIPT::32010":
                    action = "ActivateWindow(10025," + location + ",Return)"
                elif itemType == "::SCRIPT::32011":
                    action = 'ActivateWindow(10501,&quot;' + location + '&quot;,Return)'
                elif itemType == "::SCRIPT::32012":
                    action = 'ActivateWindow(10002,&quot;' + location + '&quot;,Return)'
                else:
                    action = "RunAddon(" + location + ")"
                
                # Loop through existing list items, and replace the selected with our new item
                listitems = []
                for x in range(0, self.getControl( 211 ).size()):
                    if x == itemToReplace:
                        listitems.append( LIBRARY._create([action, label[ len( label ) - 1 ], itemType, thumbnail[ len( thumbnail ) - 1 ]]) )
                    else:
                        # Duplicate the item and add it to the listitems array
                        listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                        listitems.append(listitemShortcutCopy)
                
                self.getControl( 211 ).reset()
                self.getControl( 211 ).addItems(listitems)
                
                self.getControl( 211 ).selectItem( itemToReplace )
                
            elif displayListActions[ selectedItem ] == "||BACK||":
                # User is going up the heirarchy, remove current level and re-call this function
                history.pop()
                label.pop()
                thumbnail.pop()
                self._browseLibrary( history, history[ len( history ) -1 ], label, thumbnail, itemToReplace, itemType )
                
            else:
                # User has chosen a sub-level to display, add details and re-call this function
                history.append( displayListActions[ selectedItem ] )
                label.append( displayList[ selectedItem ] )
                thumbnail.append( displayListThumbs[ selectedItem ] )
                self._browseLibrary( history, displayListActions[ selectedItem ], label, thumbnail, itemToReplace, itemType )
                

    def load_shortcuts( self, includeUserShortcuts = True ):
        log( "Loading shortcuts" )
        
        # Set path based on existance of user defined shortcuts, then skin-provided, then script-provided
        loadGroup = DATA.slugify( self.group )
        usingUserShortcuts = False
        if xbmcvfs.exists( os.path.join( __datapath__ , loadGroup + ".shortcuts" ) ) and includeUserShortcuts:
            # User defined shortcuts
            path = os.path.join( __datapath__ , loadGroup + ".shortcuts" )
            usingUserShortcuts = True
        elif xbmcvfs.exists( os.path.join( __skinpath__ , loadGroup + ".shortcuts" ) ):
            # Skin-provided defaults
            path = os.path.join( __skinpath__ , loadGroup + ".shortcuts" )
        elif xbmcvfs.exists( os.path.join( __defaultpath__ , loadGroup + ".shortcuts" ) ):
            # Script-provided defaults
            path = os.path.join( __defaultpath__ , loadGroup + ".shortcuts" )
        else:
            # No custom shortcuts or defaults available
            path = ""
            
        if not path == "":
            # Try to load shortcuts
            try:
                file = xbmcvfs.File( path )
                loaditems = eval( file.read() )
                file.close()
                
                listitems = []
                
                for item in loaditems:
                    # Parse any localised labels
                    newItem = self._parse_listitem( item )
                    
                    # Add to list
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
            except:
                # We couldn't load the file
                print_exc()
                log( "### ERROR could not load file %s" % path )
                return []
        else:
            # Add an empty item
            listitem = xbmcgui.ListItem( __language__(32013) )
            listitem.setProperty( "Path", 'noop' )
            
            self.getControl( 211 ).addItem( listitem )
            
            # Set focus
            self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
        
                
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
        displayAction = urllib.unquote( item[4] )
        
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
        
            
        if len(item) == 6:
            listitem.setProperty( "customThumbnail", item[5] )
            
        listitem.setProperty( "labelID", self._get_labelID( loadLabel ) )
        return listitem
        
        
    def _get_labelID ( self, item ):
        # Translate certain localized strings into non-localized form for labelID
        item = item.replace("::SCRIPT::", "")
        item = item.replace("::LOCAL::", "")
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
            return item.replace(" ", "").lower()
            
            
    def _update_labelid_changes( self, oldlabelID, newlabelID ):
        if oldlabelID == "":
            return
        self.labelIDChanges[oldlabelID] = newlabelID
        
    def _remove_labelid_changes( self, labelID ):
        if labelID in self.labelIDChanges.keys():
            del self.labelIDChanges[labelID]
        
        
    def _check_properties( self, listitems, usingUserShortcuts ):
        # Grab loaded properties (from skin.name.properties for menus user has already edited, else from skin defaults)
        if usingUserShortcuts:
            allProperties = self.currentProperties
        else:
            allProperties = self.defaultProperties
                    
        # Check if we've loaded anything
        if len( allProperties ) == 0:
            return listitems
            
        # Process the files we've loaded, and match any properties to listitems
        for listitem in listitems:
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
                            else:
                                self.defaultProperties.append( [ elem.attrib.get( "group" ), elem.attrib.get( 'labelID' ), elemSearch[0], elem.text ] )

                # Should we allow the user to browse for background images...
                elem = overrides.find('backgroundBrowse')
                if elem is not None and elem.text == "True":
                    self.backgroundBrowse = True
                
                # Should we allow the user to select a playlist as a widget...
                elem = overrides.find('widgetPlaylists')
                if elem is not None and elem.text == "True":
                    self.widgetPlaylists = True
                
            except:
                pass
                        
        
    def _duplicate_listitem( self, listitem ):
        # Create a copy of an existing listitem
        listitemCopy = xbmcgui.ListItem(label=listitem.getLabel(), label2=listitem.getLabel2(), iconImage=listitem.getProperty("icon"), thumbnailImage=listitem.getProperty("thumbnail"))
        listitemCopy.setProperty( "path", listitem.getProperty("path") )
        listitemCopy.setProperty( "displaypath", urllib.unquote( listitem.getProperty("path") ) )
        listitemCopy.setProperty( "icon", listitem.getProperty("icon") )
        listitemCopy.setProperty( "thumbnail", listitem.getProperty("thumbnail") )
        listitemCopy.setProperty( "localizedString", listitem.getProperty("localizedString") )
        listitemCopy.setProperty( "shortcutType", listitem.getProperty("shortcutType") )
        listitemCopy.setProperty( "labelID", listitem.getProperty("labelID") )
        if listitem.getProperty( "customThumbnail" ):
            listitemCopy.setProperty( "customThumbnail", listitem.getProperty( "customThumbnail" ) )
        if listitem.getProperty( "additionalListItemProperties" ):
            listitemCopy.setProperty( "additionalListItemProperties", listitem.getProperty( "additionalListItemProperties" ) )
            listitemProperties = eval( listitem.getProperty( "additionalListItemProperties" ) )
            
            for listitemProperty in listitemProperties:
                listitemCopy.setProperty( listitemProperty[0], listitemProperty[1] )
                
        return listitemCopy
        
        
    def _save_shortcuts( self ):
        # Save shortcuts
        if self.changeMade == True:
            log( "Saving changes" )
            listitems = []
            properties = []
            
            for x in range(0, self.getControl( 211 ).size()):
                # If the item has a label, push it to an array
                listitem = self.getControl( 211 ).getListItem(x)
                
                if listitem.getLabel().decode("utf-8") != __language__(32013):
                    saveLabel = listitem.getLabel().decode('utf-8')
                    saveLabel2 = listitem.getLabel2().decode('utf-8')
                    
                    if listitem.getProperty( "localizedString" ):
                        saveLabel = listitem.getProperty( "localizedString" ).decode('utf-8')
                        
                    if listitem.getProperty( "customThumbnail" ):
                        savedata=[saveLabel, listitem.getProperty("shortcutType").decode('utf-8'), listitem.getProperty("icon").decode('utf-8'), listitem.getProperty("thumbnail").decode('utf-8'), listitem.getProperty("path").decode('utf-8'), listitem.getProperty("customThumbnail").decode('utf-8')]
                    else:
                        savedata=[saveLabel, listitem.getProperty("shortcutType").decode('utf-8'), listitem.getProperty("icon").decode('utf-8'), listitem.getProperty("thumbnail").decode('utf-8'), listitem.getProperty("path").decode('utf-8')]
                        
                    if listitem.getProperty( "additionalListItemProperties" ):
                        properties.append( [ listitem.getProperty( "labelID" ), eval( listitem.getProperty( "additionalListItemProperties" ) ) ] )
                        
                    listitems.append(savedata)
                            
            path = os.path.join( __datapath__ , DATA.slugify( self.group.decode( 'utf-8' ) ) + ".shortcuts" ).encode('utf-8')
            
            # If there are any shortcuts, save them
            try:
                log( "Saving " + path )
                f = xbmcvfs.File( path, 'w' )
                f.write( repr( listitems ) )
                f.close()
            except:
                print_exc()
                log( "### ERROR could not save file %s" % __datapath__ )
                
            # Save widgets, backgrounds and custom properties
            self._save_properties( properties )
            
            # If this the the mainmenu and there are any labelID changes, make the changes to the submenus
            if self.group == "mainmenu" and len( self.labelIDChanges ) != 0:
                for i in range( 0, 6 ):
                    for labelIDChange in self.labelIDChanges:
                        if i == 0:
                            paths = [os.path.join( __datapath__ , DATA.slugify( labelIDChange[0] ) + ".shortcuts" ).encode('utf-8'), os.path.join( __skinpath__ , DATA.slugify( labelIDChange[0] ) + ".shortcuts").encode('utf-8'), os.path.join( __defaultpath__ , DATA.slugify( labelIDChange[0] ) + ".shortcuts" ).encode('utf-8') ]
                            target = os.path.join( __datapath__ , DATA.slugify( labelIDChange[1] ) + ".shortcuts" ).encode('utf-8')
                        else:
                            paths = [os.path.join( __datapath__ , DATA.slugify( labelIDChange[0] ) + "." + str(i) + ".shortcuts" ).encode('utf-8'), os.path.join( __skinpath__ , DATA.slugify( labelIDChange[0] ) + "." + str(i) + ".shortcuts").encode('utf-8'), os.path.join( __defaultpath__ , DATA.slugify( labelIDChange[0] ) + "." + str(i) + ".shortcuts" ).encode('utf-8') ]
                            target = os.path.join( __datapath__ , DATA.slugify( labelIDChange[1] ) + "." + str(i) + ".shortcuts" ).encode('utf-8')
                        count = 0
                        for path in paths:
                            count += 1
                            if xbmcvfs.exists( path ):
                                if count == 1:
                                    # We're going to move the file
                                    xbmcvfs.rename( path, target )
                                else:
                                    # We're going to copy the file
                                    xbmcvfs.copy( path, target )
                                break
                    
            
            # Note that we've saved stuff
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-reloadmainmenu", "True" )
            
        
    def _save_properties( self, properties ):
        # Save all additional properties (widgets, backgrounds, custom)
        log( "Saving properties" )
        
        # Get previously loaded properties
        currentProperties = self.currentProperties
        
        # Copy any items not in the current group to the array we'll save, and
        # make any labelID changes whilst we're at it
        saveData = []
        for property in currentProperties:
            log( "Comparing " + self.group + " to " + property[0] )
            if not property[0] == self.group:
                if property[0] in self.labelIDChanges.keys():
                    property[0] = self.labelIDChanges[property[0]]
                saveData.append( property )

        log( "(" + str( len( saveData ) ) + " remaining)" )
        
        # Add all the properties we've been passed
        for property in properties:
            # property[0] = labelID
            for toSave in property[1]:
                # toSave[0] = property name
                # toSave[1] = property value
                
                saveData.append( [ self.group, property[0], toSave[0], toSave[1] ] )
        
        log( repr( saveData ) )
        
        # Try to save the file
        try:
            f = xbmcvfs.File( os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".properties" ), 'w' )
            f.write( repr( saveData ) )
            f.close()
        except:
            print_exc()
            log( "### ERROR could not save file %s" % __datapath__ )                
            
    
    def _display_shortcuts( self ):
        # Load the currently selected shortcut group
        if self.shortcutgroup == 1:
            # XBMC Common
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(LIBRARY.common())
            self.getControl( 101 ).setLabel( __language__(32029) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 2:
            # Video library
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(LIBRARY.videolibrary())
            self.getControl( 101 ).setLabel( __language__(32030) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 3:
            # Music library
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(LIBRARY.musiclibrary())
            self.getControl( 101 ).setLabel( __language__(32031) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 4:
            # Playlists
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(LIBRARY.playlists())
            self.getControl( 101 ).setLabel( __language__(32040) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 5:
            # Favourites
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(LIBRARY.favourites())
            self.getControl( 101 ).setLabel( __language__(32006) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 6:
            # Add-ons
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(LIBRARY.addons())
            self.getControl( 101 ).setLabel( __language__(32007) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 7:
            # More XBMC commands
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(LIBRARY.more())
            self.getControl( 101 ).setLabel( __language__(32057) + " (%s)" %self.getControl( 111 ).size() )
                
    def onAction( self, action ):
        if action.getId() in ACTION_CANCEL_DIALOG:
            log( "### CLOSING WINDOW" )
            #if self.getFocusId() == 402 and action.getId() == 61448: # Check we aren't backspacing on an edit dialog
            #    return
            #if self.getFocusId() == 403 and action.getId() == 61448: # Check we aren't backspacing on an edit dialog
            #    return
            self._save_shortcuts()
            xbmcgui.Window(self.window_id).clearProperty('groupname')
            self._close()

    def _close( self ):
            self.close()

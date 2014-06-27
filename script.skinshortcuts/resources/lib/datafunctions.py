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
    try:
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)
    except:
        pass
    
class DataFunctions():
    def __init__(self):
        pass
        
    
    def _get_labelID( self, labelID ):
        # This gets the unique labelID for the item we've been passed. We'll also store it, to make sure
        # we don't give it to any other item.
        
        # Check if the labelID exists in the list
        if labelID in self.labelIDList:
            # We're going to add an -x to the end of this
            count = 0
            while labelID + "-" + str( count ) in self.labelIDList:
                count += 1
                log( labelID + "-" + str( count ) )
                log( repr( self.labelIDList ) )
            
            # We can now use this one
            self.labelIDList.append( labelID + "-" + str( count ) )
            return labelID + "-" + str( count )
        else:
            # We can use this one
            self.labelIDList.append( labelID )
            return labelID
        
    
    def _clear_labelID( self ):
        # This clears our stored list of labelID's
        self.labelIDList = []
        
                
    def _get_shortcuts( self, group, isXML = False, profileDir = None ):
        # This will load the shortcut file, and save it as a window property
        # Additionally, if the override files haven't been loaded, we'll load them too
        log( "Loading shortcuts for group " + group )
        
        if isXML == False:
            try:
                returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-" + group )
                return pickle.loads( returnVal )
            except:
                pass
                
        if profileDir is None:
            profileDir = xbmc.translatePath( "special://profile/" ).decode( "utf-8" )
        
        userShortcuts = os.path.join( profileDir, "addon_data", __addonid__, self.slugify( group ) + ".shortcuts" ).encode('utf-8')
        skinShortcuts = os.path.join( __skinpath__ , self.slugify( group ) + ".shortcuts").encode('utf-8')
        defaultShortcuts = os.path.join( __defaultpath__ , self.slugify( group ) + ".shortcuts" ).encode('utf-8')

        paths = [userShortcuts, skinShortcuts, defaultShortcuts ]
        
        for path in paths:
            if xbmcvfs.exists( path ):
                try:
                    # Try loading shortcuts
                    list = xbmcvfs.File( path ).read()
                    unprocessedList = eval( list )
                    self._save_hash( path, list )
                    
                    # If this is a user-selected list of shortcuts...
                    if path == userShortcuts:
                        # Process shortcuts, marked as user-selected
                        processedList = self._process_shortcuts( unprocessedList, group, profileDir, True )
                        
                        # Update any localised strings
                        self._process_localised( path, unprocessedList )
                        
                    else:
                        # Otherwise, just process them normally
                        processedList = self._process_shortcuts( unprocessedList, group, profileDir )
                        
                        
                    if isXML == False:
                        xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-" + group, pickle.dumps( processedList ) )
                    
                    log( " - Loaded file " + path ) 
                    
                    if group == "mainmenu":
                        processedList = self._get_skin_required( processedList, group, profileDir, True )
                    
                    return processedList
                except:
                    print_exc()
                    return False
                    self._save_hash( path, None )
                
        # No file loaded
        log( " - No shortcuts" )
        if isXML == False:
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-" + group, pickle.dumps( [] ) )
        return [] 
                
            
    def _process_shortcuts( self, listitems, group, profileDir = "special:\\profile", isUserShortcuts = False, allowAdditionalRequired = True ):
        # This function will process any overrides, and return a set of listitems ready to be stored
        #  - We will process graphics overrides, action overrides and any visibility conditions set
        tree = self._get_overrides_skin()
        usertree = self._get_overrides_user( profileDir )
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
                # Check for a localised label from a non-current skin
                try:
                    skinName = item[6]
                    if skinName != xbmc.getSkinDir():
                        label = item[7]
                except:
                    hasChanged = False
            
            # Check for a skin-override on the icon
            item[2] = self._get_icon_overrides( tree, item[2], group, labelID )
            
            # Get any additional properties, including widget and background
            additionalProperties = self.checkAdditionalProperties( group, labelID, isUserShortcuts )
            
            # Loop through additional properties, looking for "Skin-Required-Shortcut"
            shouldContinue = True
            for additionalProperty in additionalProperties:
                if additionalProperty[0] == "Skin-Required-Shortcut":
                    if additionalProperty[1] != xbmc.getSkinDir():
                        shouldContinue = False
            if shouldContinue == False:
                continue
                                
            # Get action
            action = urllib.unquote( item[4] )
            
            # If the action uses the special://skin protocol, translate it
            if "special://skin/" in action:
                translate = xbmc.translatePath( "special://skin/" ).decode( 'utf-8' )
                action = action.replace( "special://skin/", translate )
            
            # Check visibility
            visibilityCondition = self.checkVisibility( action )
                    
            # Check action and visibility overrides
            newAction = ""
            showInverse = False
            trees = [usertree, tree]
            hasOverriden = False
            
            for overridetree in trees:
                
                if overridetree is not None:
                    elems = overridetree.findall( 'override' )
                    overridecount = 0
                    for elem in elems:
                        if "group" in elem.attrib:
                            checkGroup = elem.attrib.get( "group" )
                        else:
                            checkGroup = None
                        
                        if elem.attrib.get( 'action' ) == action and (checkGroup == None or checkGroup == group):
                            version = __xbmcversion__
                            if "version" in elem.attrib:
                                version = elem.attrib.get( "version" )
                                
                            if version == __xbmcversion__:
                                overridecount = overridecount + 1
                                hasOverriden = True
                                overrideVisibility = visibilityCondition
                                
                                # Check for visibility conditions
                                condition = elem.find( "condition" )
                                if condition is not None:
                                    if overrideVisibility == "":
                                        # New visibility condition
                                        overrideVisibility = condition.text
                                    else:
                                        # Add this to existing visibility condition
                                        overrideVisibility = overrideVisibility + " + [" + condition.text + "]"                        
                                        
                                # Check for overriden action
                                newAction = action
                                multiAction = "::MULTIPLE::"
                                actions = elem.findall( "action" )
                                count = 0
                                for singleAction in actions:
                                    count = count + 1
                                    if count == 1:
                                        newAction = urllib.quote( singleAction.text )
                                    multiAction = multiAction + "|" + singleAction.text
                                    
                                if count != 1 and count != 0:
                                    newAction = urllib.quote( multiAction )
                                    
                                overrideProperties = list( additionalProperties )
                                overrideProperties.append( [ "node.visible", overrideVisibility ] )
                
                                # Add item
                                returnitems.append( [label, item[1], item[2], item[3], newAction, labelID, overrideProperties] )
                            
                    if hasOverriden == False:
                        # Now check for a visibility condition in a skin-provided shortcut
                        elems = overridetree.findall( "shortcut" )
                        for elem in elems:
                            if elem.text == action and "condition" in elem.attrib:
                                newCondition = visibilityCondition
                                if visibilityCondition == "":
                                    visibilityCondition = elem.attrib.get( "condition" )
                                else:
                                    visibilityCondition = "[" + visibilityCondition + "] + [" + elem.attrib.get( "Condition" ) + "]"
                            break
                            
            # If we haven't added any overrides, add the item
            if hasOverriden == False:
                if visibilityCondition != "":
                    additionalProperties.append( [ "node.visible", visibilityCondition ] )
                returnitems.append( [label, item[1], item[2], item[3], item[4], labelID, additionalProperties] )
                
        return returnitems
        
    def _get_skin_required( self, listitems, group, profileDir, isUserShortcuts ):
        log( "### Checking skin-required shortcuts" )
        # This function checks for and adds any skin-required shortcuts
        tree = self._get_overrides_skin()
        if tree is None:
            return listitems
            
        # Get a list of all skin-required shortcuts
        requiredShortcuts = []
        for elem in tree.findall( "requiredshortcut" ):
            requiredShortcuts.append( [ False, elem.attrib.get( "label" ), xbmc.getSkinDir(), elem.attrib.get( "icon" ), elem.attrib.get( "thumbnail" ), elem.text ] )
            if len( requiredShortcuts ) == 0:
                return listitems
        
        # Now, we'll remove them if there's a shortcut already with the action
        for item in listitems:
            for requiredShortcut in requiredShortcuts:
                if requiredShortcut[0] == False:
                    if urllib.unquote( item[4] ) == requiredShortcut[5]:
                        requiredShortcut[0] == True
                        
        # Finally, we'll pass these to _process_shortcuts, which will apply any overrides
        # and then append what that returns to the listitems
        additionalItems = []
        for requiredShortcut in requiredShortcuts:
            if requiredShortcut[0] == False:
                icon = requiredShortcut[3]
                thumb = requiredShortcut[4]
                if icon is None:
                    icon = ""
                if thumb is None:
                    thumb = ""
                    
                additionalItems.append( [ requiredShortcut[1], requiredShortcut[2], icon, thumb, requiredShortcut[5] ] )
            
        if len( additionalItems ) == 0:
            return listitems
        
        additionalItems = self._process_shortcuts( additionalItems, group, profileDir, isUserShortcuts, False )        
        for additionalItem in additionalItems:
            listitems.append( additionalItem )
            
        return listitems
        
    def _get_icon_overrides( self, tree, icon, group, labelID, setToDefault = True ):
        # This function will get any icon overrides based on labelID or group
        oldicon = None
        newicon = icon
        
        # Check for overrides
        if tree is not None:
            for elem in tree.findall( "icon" ):
                if oldicon is None:
                    if ("labelID" in elem.attrib and elem.attrib.get( "labelID" ) == labelID) or ("image" in elem.attrib and elem.attrib.get( "image" ) == icon):
                        # LabelID matched
                        if "group" in elem.attrib:
                            if elem.attrib.get( "group" ) == group:
                                # Group also matches - change icon
                                oldicon = icon
                                newicon = elem.text
                                
                        elif "grouping" not in elem.attrib:
                            # No group - change icon
                            oldicon = icon
                            newicon = elem.text
        
        if not xbmc.skinHasImage( newicon ) and setToDefault == True:
            newicon = self._get_icon_overrides( tree, "DefaultShortcut.png", group, labelID, False )
        return newicon
        
    def _process_localised( self, path, items ):
        # We will check a file to see if it uses strings localised by the skin and, if so, save their non-localised version in case the user
        # switches skins in the future
        updatedString = False
        for item in items:
            if not item[0].find( "::LOCAL::" ) == -1:
                stringInt = int( item[0][9:] )
                if stringInt > 30000:
                    # This is a string localized by the skin
                    localID = xbmc.getLocalizedString( stringInt )
                    updateString = False
                    
                    # Check whether the skin providing the string is the current skin
                    try:
                        if item[6] == xbmc.getSkinDir():
                            # The string has already been localised, check it hasn't changed
                            if localID != item[7]:
                                item[7] = localID
                                updatedString = True
                    except:
                        # The string hasn't been localised at all
                        if len(item) == 5:
                            item.append( "False" )
                            
                        item.append( xbmc.getSkinDir() )
                        item.append( localID )
                        updatedString = True
            
        if updatedString == True:
            # We updated a string, so we want to save this file
            try:
                f = xbmcvfs.File( path, 'w' )
                f.write( repr( items ) )
                f.close()
            except:
                print_exc()
                log( "### ERROR could not save file %s" % path )                          
                    

    def _get_overrides_script( self ):
        # If we haven't already loaded skin overrides, or if the skin has changed, load the overrides file
        if not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-script-data" ) or not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-script" ) == __defaultpath__:
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-script", __defaultpath__ )
            overridepath = os.path.join( __defaultpath__ , "overrides.xml" )
            try:
                tree = xmltree.parse( overridepath )
                self._save_hash( overridepath, xbmcvfs.File( overridepath ).read() )
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-script-data", pickle.dumps( tree ) )
                return tree
            except:
                self._save_hash( overridepath, None )
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-script-data", "No overrides" )
                return None
   
        # Return the overrides
        returnData = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-script-data" )
        if returnData == "No overrides":
            return None
        else:
            return pickle.loads( returnData )


    def _get_overrides_skin( self ):
        # If we haven't already loaded skin overrides, or if the skin has changed, load the overrides file
        if not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-skin-data" ) or not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-skin" ) == __skinpath__:
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-skin", __skinpath__ )
            overridepath = os.path.join( __skinpath__ , "overrides.xml" )
            try:
                tree = xmltree.parse( overridepath )
                self._save_hash( overridepath, xbmcvfs.File( overridepath ).read() )
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-skin-data", pickle.dumps( tree ) )
                return tree
            except:
                self._save_hash( overridepath, None )
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-skin-data", "No overrides" )
                return None
   
        # Return the overrides
        returnData = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-skin-data" )
        if returnData == "No overrides":
            return None
        else:
            return pickle.loads( returnData )


    def _get_overrides_user( self, profileDir = "special://profile" ):
        # If we haven't already loaded user overrides
        profileDir = profileDir.encode( "utf-8" )
        if not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user-data" + profileDir ) or not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user" + profileDir ) == __profilepath__:
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user" + profileDir, profileDir )
            overridepath = os.path.join( profileDir , "overrides.xml" )
            try:
                tree = xmltree.parse( overridepath )
                self._save_hash( overridepath, xbmcvfs.File( overridepath ).read() )
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user-data" + profileDir, pickle.dumps( tree ) )
                return tree
            except:
                self._save_hash( overridepath, None )
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user-data" + profileDir, "No overrides" )
                return None
                
        # Return the overrides
        returnData = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user-data" + profileDir )
        if returnData == "No overrides":
            return None
        else:
            return pickle.loads( returnData )


    def _get_additionalproperties( self ):
        # Load all saved properties (widgets, backgrounds, custom properties)
        
        # Try loading from window property
        try:
            returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcutsAdditionalProperties" )
            return pickle.loads( returnVal )
        except:
            pass
            
        # Couldn't load from window property, load manually
        currentProperties = []
        defaultProperties = []
        
        path = os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".properties" )
        if xbmcvfs.exists( path ):
            # The properties file exists, load from it
            try:
                file = xbmcvfs.File( path ).read()
                listProperties = eval( file )
                self._save_hash( path, file )
                
                for listProperty in listProperties:
                    # listProperty[0] = groupname
                    # listProperty[1] = labelID
                    # listProperty[2] = property name
                    # listProperty[3] = property value
                    currentProperties.append( [listProperty[0], listProperty[1], listProperty[2], listProperty[3]] )
            except:
                pass
            
        # Load skin defaults (in case we need them...)
        tree = self._get_overrides_skin()
        if tree is not None:
            for elemSearch in [["widget", tree.findall( "widgetdefault" )], ["background", tree.findall( "backgrounddefault" )], ["custom", tree.findall( "propertydefault" )] ]:
                for elem in elemSearch[1]:
                    
                    if elemSearch[0] == "custom":
                        # Custom property
                        if "group" not in elem.attrib:
                            defaultProperties.append( ["mainmenu", elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text ] )
                        else:
                            defaultProperties.append( [elem.attrib.get( "group" ), elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text ] )
                    else:
                        # Widget or background
                        if "group" not in elem.attrib:
                            defaultProperties.append( [ "mainmenu", elem.attrib.get( 'labelID' ), elemSearch[0], elem.text ] )
                            if elemSearch[0] == "widget":
                                # Get and set widget type and name
                                widgetDetails = self._getWidgetNameAndType( elem.text )
                                if widgetDetails is not None:
                                    defaultProperties.append( [ "mainmenu", elem.attrib.get( "labelID" ), "widgetName", widgetDetails[0] ] )
                                    if widgetDetails[1] is not None:
                                        defaultProperties.append( [ "mainmenu", elem.attrib.get( "labelID" ), "widgetType", widgetDetails[1] ] )
                        else:
                            defaultProperties.append( [ elem.attrib.get( "group" ), elem.attrib.get( 'labelID' ), elemSearch[0], elem.text ] )
                            if elemSearch[0] == "widget":
                                # Get and set widget type and name
                                widgetDetails = self._getWidgetNameAndType( elem.text )
                                if widgetDetails is not None:
                                    defaultProperties.append( [ elem.attrib.get( "group" ), elem.attrib.get( "labelID" ), "widgetName", widgetDetails[0] ] )
                                    if widgetDetails[1] is not None:
                                        defaultProperties.append( [ elem.attrib.get( "group" ), elem.attrib.get( "labelID" ), "widgetType", widgetDetails[1] ] )                
                                        
        returnVal = [currentProperties, defaultProperties]
        xbmcgui.Window( 10000 ).setProperty( "skinshortcutsAdditionalProperties", pickle.dumps( returnVal ) )
        return returnVal
        
    def _getWidgetNameAndType( self, widgetID ):
        tree = self._get_overrides_skin()
        if tree is not None:
            for elem in tree.findall( "widget" ):
                if elem.text == widgetID:
                    if "type" in elem.attrib:
                        return [elem.attrib.get( "label" ), elem.attrib.get( "type" )]
                    else:
                        return [ elem.attrib.get( "label" ), None ]
                        
        return None
    
    
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
            return item.lower( ).replace( " ", "" )
            
    def checkVisibility ( self, action ):
        # Return whether mainmenu items should be displayed
        if action == "ActivateWindow(Weather)":
            return "!IsEmpty(Weather.Plugin)"
        if action.startswith( "ActivateWindowAndFocus(MyPVR" ) or action.startswith( "PlayPvr" ):
            return "System.GetBool(pvrmanager.enabled)"
        if action.startswith( "ActivateWindow(Video,Movie" ):
            return "Library.HasContent(Movies)"
        if action.startswith( "ActivateWindow(Videos,RecentlyAddedMovies" ):
            return "Library.HasContent(Movies)"
        if action.startswith( "ActivateWindow(Video,TVShow" ):
            return "Library.HasContent(TVShows)"
        if action.startswith( "ActivateWindow(Video,MusicVideo" ):
            return "Library.HasContent(MusicVideos)"
        if action.startswith( "ActivateWindow(MusicLibrary,MusicVideos" ):
            return "Library.HasContent(MusicVideos)"
        if action.startswith( "ActivateWindow(MusicLibrary," ):
            return "Library.HasContent(Music)"
        if action == "XBMC.PlayDVD()":
            return "System.HasMediaDVD"
            
        return ""
        
        
    def checkAdditionalProperties( self, group, labelID, isUserShortcuts ):
        # Return any additional properties, including widgets and backgrounds
        allProperties = self._get_additionalproperties()
        #log( "Getting additional properties for " + labelID + " in group " + group )
        currentProperties = allProperties[1]
        
        returnProperties = []
        
        # This returns two lists...
        #  allProperties[0] = Saved properties
        #  allProperties[1] = Default properties
        
        if isUserShortcuts:
            currentProperties = allProperties[0]
            
        # Loop through the current properties, looking for the current item
        for currentProperty in currentProperties:
            # currentProperty[0] = Group name
            # currentProperty[1] = labelID
            # currentProperty[2] = Property name
            # currentProperty[3] = Property value
            if currentProperty[0] == group and currentProperty[1] == labelID:
                returnProperties.append( [ currentProperty[2], currentProperty[3] ] )
                
        return returnProperties
            
        
    def checkShortcutLabelOverride( self, action ):
        tree = self._get_overrides_skin()
        if tree is not None:
            elemSearch = tree.findall( "availableshortcutlabel" )
            for elem in elemSearch:
                if elem.attrib.get( "action" ).lower() == action.lower():
                    # This matches :) Check if we're also overriding the type
                    if "type" in elem.attrib:
                        return [ elem.text, elem.attrib.get( "type" ) ]
                    else:
                        return [ elem.text ]

        return None
        
        
    def _save_hash( self, filename, file ):
        
        if file is not None:
            hasher = hashlib.md5()
            hasher.update( file )
            hashlist.list.append( [filename, hasher.hexdigest()] )
        else:
            hashlist.list.append( [filename, None] )
            
            
    # in-place prettyprint formatter
    def indent( self, elem, level=0 ):
        i = "\n" + level*"\t"
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "\t"
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
            

    def smart_truncate(string, max_length=0, word_boundaries=False, separator=' '):
        string = string.strip(separator)

        if not max_length:
            return string

        if len(string) < max_length:
            return string

        if not word_boundaries:
            return string[:max_length].strip(separator)

        if separator not in string:
            return string[:max_length]

        truncated = ''
        for word in string.split(separator):
            if word:
                next_len = len(truncated) + len(word) + len(separator)
                if next_len <= max_length:
                    truncated += '{0}{1}'.format(word, separator)
        if not truncated:
            truncated = string[:max_length]
        return truncated.strip(separator)

    def slugify(self, text, entities=True, decimal=True, hexadecimal=True, max_length=0, word_boundary=False, separator='-'):
        # text to unicode
        if type(text) != types.UnicodeType:
            text = unicode(text, 'utf-8', 'ignore')

        # decode unicode ( 影師嗎 = Ying Shi Ma)
        text = unidecode(text)

        # text back to unicode
        if type(text) != types.UnicodeType:
            text = unicode(text, 'utf-8', 'ignore')

        # character entity reference
        if entities:
            text = CHAR_ENTITY_REXP.sub(lambda m: unichr(name2codepoint[m.group(1)]), text)

        # decimal character reference
        if decimal:
            try:
                text = DECIMAL_REXP.sub(lambda m: unichr(int(m.group(1))), text)
            except:
                pass

        # hexadecimal character reference
        if hexadecimal:
            try:
                text = HEX_REXP.sub(lambda m: unichr(int(m.group(1), 16)), text)
            except:
                pass

        # translate
        text = unicodedata.normalize('NFKD', text)
        if sys.version_info < (3,):
            text = text.encode('ascii', 'ignore')

        # replace unwanted characters
        text = REPLACE1_REXP.sub('', text.lower()) # replace ' with nothing instead with -
        text = REPLACE2_REXP.sub('-', text.lower())

        # remove redundant -
        text = REMOVE_REXP.sub('-', text).strip('-')

        # smart truncate if requested
        if max_length > 0:
            text = smart_truncate(text, max_length, word_boundary, '-')

        if separator != '-':
            text = text.replace('-', separator)

        return text
        
# coding=utf-8
import os, sys, datetime, unicodedata, re, types
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
import hashlib, hashlist
import ast
from xml.dom.minidom import parse
from traceback import print_exc
from htmlentitydefs import name2codepoint
from unidecode import unidecode
from unicodeutils import try_decode

import nodefunctions
NODE = nodefunctions.NodeFunctions()

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id').decode( 'utf-8' )
KODIVERSION  = xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0]
LANGUAGE     = ADDON.getLocalizedString
CWD          = ADDON.getAddonInfo('path').decode("utf-8")
DATAPATH     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), ADDONID )
SKINPATH     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')
DEFAULTPATH  = xbmc.translatePath( os.path.join( CWD, 'resources', 'shortcuts').encode("utf-8") ).decode("utf-8")

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
    if ADDON.getSetting( "enable_logging" ) == "true":
        try:
            if isinstance (txt,str):
                txt = txt.decode('utf-8')
            message = u'%s: %s' % (ADDONID, txt)
            xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)
        except:
            pass
    
class DataFunctions():
    def __init__(self):
        self.overrides = {}

        self.widgetNameAndType = {}
        self.backgroundName = {}
        self.fallbackProperties = {}
        self.fallbackRequires = {}
        self.propertyRequires = None
        self.templateOnlyProperties = None

        self.currentProperties = None
        self.defaultProperties = None

        self.propertyInformation = { "fallbackProperties": {}, "fallbacks": {},
                "otherProperties": [], "requires": None, "templateOnly": None }
        
    
    def _get_labelID( self, labelID, action, getDefaultID = False, includeAddOnID = True, noNonLocalized = False ):
        # This gets the unique labelID for the item we've been passed. We'll also store it, to make sure
        # we don't give it to any other item.
        
        labelID = self.createNiceName( self.slugify( labelID.replace( " ", "" ).lower() ), noNonLocalized )
        
        if includeAddOnID:
            addon_labelID = self._get_addon_labelID( action )
            if addon_labelID is not None:
                labelID = addon_labelID
        
        # If we're getting the defaultID, just return this
        if getDefaultID == True:
            return labelID
        
        # Check if the labelID exists in the list
        if labelID in self.labelIDList:
            # We're going to add an --[int] to the end of this
            count = 0
            while labelID + "--" + str( count ) in self.labelIDList:
                count += 1
            
            # We can now use this one
            self.labelIDList.append( labelID + "--" + str( count ) )
            return labelID + "--" + str( count )
        else:
            # We can use this one
            self.labelIDList.append( labelID )
            return labelID
            
    def _get_addon_labelID( self, action ):
        # This will check the action to see if this is a program or the root of a plugin and, if so, return that as the labelID
        
        if action is None:
            return None
        
        try:
            if action.startswith( "RunAddOn(" ) and "," not in action:
                return action[9:-1]
                
            if action.startswith( "RunScript(" ) and "," not in action:
                return action[10:-1]
                
            if "plugin://" in action and "?" not in action:
                # Return the action
                # - less ActivateWindow(
                # - The second group after being split by comma
                # - Less plugin://
                return action[15:-1].split( "," )[1].replace( '"', '' )[9:]
        except:
            return None
            
        return None
    
    def _clear_labelID( self ):
        # This clears our stored list of labelID's
        self.labelIDList = []
        
    
    def _pop_labelID( self ):
        self.labelIDList.pop()
    
                
    def _get_shortcuts( self, group, defaultGroup = None, isXML = False, profileDir = None, defaultsOnly = False, processShortcuts = True, isSubLevel = False ):
        # This will load the shortcut file
        # Additionally, if the override files haven't been loaded, we'll load them too
        log( "Loading shortcuts for group " + group )
                
        if profileDir is None:
            profileDir = xbmc.translatePath( "special://profile/" ).decode( "utf-8" )
        
        userShortcuts = os.path.join( profileDir, "addon_data", ADDONID, self.slugify( group, True, isSubLevel = isSubLevel ) + ".DATA.xml" )
        skinShortcuts = os.path.join( SKINPATH , self.slugify( group ) + ".DATA.xml")
        defaultShortcuts = os.path.join( DEFAULTPATH , self.slugify( group ) + ".DATA.xml" )
        if defaultGroup is not None:
            skinShortcuts = os.path.join( SKINPATH , self.slugify( defaultGroup ) + ".DATA.xml")
            defaultShortcuts = os.path.join( DEFAULTPATH , self.slugify( defaultGroup ) + ".DATA.xml" )

        if defaultsOnly:
            paths = [skinShortcuts, defaultShortcuts ]
        else:
            paths = [userShortcuts, skinShortcuts, defaultShortcuts ]
        
        for path in paths:
            log( " - Attempting to load file %s" %( path ) )
            path = try_decode( path )
            tree = None
            if xbmcvfs.exists( path ):
                file = xbmcvfs.File( path ).read()
                self._save_hash( path, file )
                tree = xmltree.parse( path )
            
            if tree is not None and processShortcuts:
                # If this is a user-selected list of shortcuts...
                if path == userShortcuts:
                    if group == "mainmenu":
                        self._get_skin_required( tree, group, profileDir )
                    # Process shortcuts, marked as user-selected                    
                    self._process_shortcuts( tree, group, profileDir, True )
                    
                else:
                    if group == "mainmenu":
                        self._get_skin_required( tree, group, profileDir )
                    self._process_shortcuts( tree, group, profileDir )

                log( " - Loaded file" )
                return tree
            elif tree is not None:
                log( " - Loaded file " + path )
                log( " - Returning unprocessed shortcuts" )
                return tree
            else:
                self._save_hash( path, None )
                
        # No file loaded
        log( " - No shortcuts" )
        return xmltree.ElementTree( xmltree.Element( "shortcuts" ) )
                            
    def _process_shortcuts( self, tree, group, profileDir = "special:\\profile", isUserShortcuts = False, allowAdditionalRequired = True ):
        # This function will process any overrides and add them to the tree ready to be displayed
        #  - We will process graphics overrides, action overrides, visibility conditions
        skinoverrides = self._get_overrides_skin()
        useroverrides = self._get_overrides_user( profileDir )
        
        self._clear_labelID()
        
        # Iterate through all <shortcut/> nodes
        for node in tree.getroot().findall( "shortcut" ):
            # If not user shortcuts, remove locked nodes (in case of naughty skinners!)
            if isUserShortcuts == False:
                searchNode = node.find( "locked" )
                if searchNode is not None:
                    node.remove( searchNode )
                    
            # Remove any labelID node (because it confuses us!)
            searchNode = node.find( "labelID" )
            if searchNode is not None:
                node.remove( searchNode )
                    
            # Get the action
            action = node.find( "action" )
            if not action.text:
                action.text = "noop"
            
            # group overrides: add an additional onclick action for a particular menu
            # this will allow you to close a modal dialog before calling any other window
            # http://forum.kodi.tv/showthread.php?tid=224683
            allGroupOverrides = skinoverrides.findall( "groupoverride" )
            for override in allGroupOverrides:
                if override.attrib.get( "group" ) == group:
                    newaction = xmltree.SubElement( node, "additional-action" )
                    newaction.text = override.text
                    newaction.set( "condition", override.attrib.get( "condition" ) )
            
            # Generate the labelID
            labelID = self._get_labelID( self.local( node.find( "label" ).text )[3].replace( " ", "" ).lower(), action.text )
            xmltree.SubElement( node, "labelID" ).text = labelID
            
            # If there's no defaultID, set it to the labelID
            defaultID = labelID
            if node.find( "defaultID" ) is not None:
                defaultID = node.find( "defaultID" ).text
            xmltree.SubElement( node, "defaultID" ).text = defaultID
            
            # Check that any version node matches current XBMC version
            version = node.find( "version" )
            if version is not None:
                if KODIVERSION != version.text and self.checkVersionEquivalency( version.text, node.find( "action" ) ) == False:
                    tree.getroot().remove( node )
                    self._pop_labelID()
                    continue

            # Get any disabled element
            if node.find( "disabled" ) is not None:
                xmltree.SubElement( node, "disabled" ).text = "True"
                    
            # Load additional properties
            additionalProperties = self.checkAdditionalProperties( group, labelID, defaultID, isUserShortcuts, profileDir )

            # If icon and thumbnail are in the additional properties, overwrite anything in the .DATA.xml file
            # and remove them from the additional properties
            for additionalProperty in additionalProperties:
                if additionalProperty[ 0 ] == "icon":
                    node.find( "icon" ).text = additionalProperty[ 1 ]
                    additionalProperties.remove( additionalProperty )
                    break

            if node.find( "thumb" ) is None:
                xmltree.SubElement( node, "thumb" ).text = ""
            for additionalProperty in additionalProperties:
                if additionalProperty[ 0 ] == "thumb":
                    node.find( "thumb" ).text = additionalProperty[ 1 ]
                    additionalProperties.remove( additionalProperty )
                    break

            xmltree.SubElement( node, "additional-properties" ).text = repr( additionalProperties )

            iconNode = node.find( "icon" )
            if iconNode.text is None or iconNode.text == "":
                iconNode.text = "DefaultShortcut.png"
                        
            # Get a skin-overriden icon
            overridenIcon = self._get_icon_overrides( skinoverrides, node.find( "icon" ).text, group, labelID )
            if overridenIcon is not None:
                # Add a new node with the overriden icon
                xmltree.SubElement( node, "override-icon" ).text = overridenIcon
            
            # If the action uses the special://skin protocol, translate it
            if "special://skin/" in action.text:
                action.text = xbmc.translatePath( action.text )
                
            # Get visibility condition
            visibilityCondition = self.checkVisibility( action.text )
            visibilityNode = None

            if visibilityCondition != "":
                # Check whether visibility condition is overriden
                overriddenVisibility = False
                for override in skinoverrides.findall( "visibleoverride" ):
                    if override.attrib.get( "condition" ).lower() != visibilityCondition.lower():
                        # Not overriding this visibility condition
                        continue

                    if "group" in override.attrib and not override.attrib.get( "group" ) == group:
                        # Not overriding this group
                        continue

                    overriddenVisibility = True

                    # It's overriden - add the original action with the visibility condition
                    originalAction = xmltree.SubElement( node, "override-visibility" )
                    originalAction.text = action.text
                    originalAction.set( "condition", visibilityCondition )

                    # And add the new action with the inverse visibility condition
                    newaction = xmltree.SubElement( node, "override-visibility" )
                    newaction.text = override.text
                    newaction.set( "condition", "![%s]" %( visibilityCondition ) )

                    break

                if overriddenVisibility == False:
                    # The skin hasn't overriden the visibility
                    visibilityNode = xmltree.SubElement( node, "visibility" )
                    visibilityNode.text = visibilityCondition
            
            # Get action and visibility overrides
            overrideTrees = [useroverrides, skinoverrides]
            hasOverriden = False
            for overrideTree in overrideTrees:
                if hasOverriden == True:
                    continue
                if overrideTree is not None:
                    for elem in overrideTree.findall( "override" ):
                        # Pull out the current action, and any already-overriden actions
                        itemsToOverride = []
                        for itemToOverride in node.findall( "override-visibility" ):
                            itemsToOverride.append( itemToOverride )

                        if len( itemsToOverride ) == 0:
                            itemsToOverride = [ action ]

                        # Retrieve group property
                        checkGroup = None
                        if "group" in elem.attrib:
                            checkGroup = elem.attrib.get( "group" )

                        # Iterate through items
                        for itemToOverride in itemsToOverride:
                            # If the action and (if provided) the group match...
                            # OR if we have a global override specified
                            if ( elem.attrib.get( "action" ) == itemToOverride.text and ( checkGroup is None or checkGroup == group ) ) or ( elem.attrib.get( "action" ) == "globaloverride" and ( checkGroup is None or checkGroup == group ) ):
                                # Check the XBMC version matches
                                if "version" in elem.attrib:
                                    if elem.attrib.get( "version" ) != KODIVERSION:
                                        continue
                                    
                                hasOverriden = True
                                itemToOverride.set( "overriden", "True" )

                                # Get the visibility condition
                                condition = elem.find( "condition" )
                                overrideVisibility = None
                                if condition is not None:
                                    overrideVisibility = condition.text
                                
                                # Get the new action
                                for actions in elem.findall( "action" ):
                                    newaction = xmltree.SubElement( node, "override-action" )
                                    if "::ACTION::" in actions.text:
                                        newaction.text = actions.text.replace("::ACTION::",itemToOverride.text)
                                    else:
                                        newaction.text = actions.text
                                    if overrideVisibility is not None:
                                        newaction.set( "condition", overrideVisibility )

                                # Add visibility if no action specified
                                if len( elem.findall( "action" ) ) == 0:
                                    newaction = xmltree.SubElement( node, "override-action" )
                                    newaction.text = itemToOverride.text
                                    if overrideVisibility is not None:
                                        newaction.set( "condition", overrideVisibility )

                                # If there's already a condition, add it
                                if newaction is not None and itemToOverride.get( "condition" ):
                                    newaction.set( "condition", "[%s] + [%s]" %( itemToOverride.get( "condition" ), newaction.get( "condition" ) ) )

                                newaction = None

            # Sort any visibility overrides
            for elem in node.findall( "override-visibility" ):
                if elem.get( "overriden" ) == "True":
                    # The item has been overriden, delete it
                    node.remove( elem )
                else:
                    # The item hasn't been overriden, so change it to an override-action element
                    elem.tag = "override-action"
                       
            # Get visibility condition of any skin-provided shortcuts
            for elem in skinoverrides.findall( "shortcut" ):
                if elem.text == action.text and "condition" in elem.attrib:
                    if not visibilityNode:
                        xmltree.SubElement( node, "visibility" ).text = elem.attrib.get( "condition" )
                    else:
                        visibilityNode.text = "[" + visibilityNode.text + "] + [" + elem.attrib.get( "condition" ) + "]"
                            
            # Get any visibility conditions in the .DATA.xml file
            additionalVisibility = node.find( "visible" )
            if additionalVisibility is not None:
                if visibilityNode == None:
                    xmltree.SubElement( node, "visibility" ).text = additionalVisibility.text
                else:
                    visibilityNode.text = "[" + visibilityNode.text + "] + [" + additionalVisibility.text + "]"
        
        return tree
        
    def _get_skin_required( self, listitems, group, profileDir ):
        # This function builds a tree of any skin-required shortcuts not currently in the menu
        # Once the tree is built, it sends them to _process_shortcuts for any overrides, etc, then adds them to the menu tree
        
        tree = self._get_overrides_skin()
            
        # Get an array of all actions currently in the menu
        actions = []
        for node in listitems.getroot().findall( "shortcut" ):
            for action in node.findall( "action" ):
                actions.append( action.text )
                
        # Get a list of all skin-required shortcuts
        requiredShortcuts = []
        for elem in tree.findall( "requiredshortcut" ):
            if not elem.text in actions:
                # We need to add this shortcut - add it to the listitems
                requiredShortcut = xmltree.SubElement( listitems.getroot(), "shortcut" )
                
                # Label and label2
                xmltree.SubElement( requiredShortcut, "label" ).text = elem.attrib.get( "label" )
                xmltree.SubElement( requiredShortcut, "label2" ).text = xbmc.getSkinDir()
                
                # Icon and thumbnail
                if "icon" in elem.attrib:
                    xmltree.SubElement( requiredShortcut, "icon" ).text = elem.attrib.get( "icon" )
                else:
                    xmltree.SubElement( requiredShortcut, "icon" ).text = "DefaultShortcut.png"
                if "thumb" in elem.attrib:
                    xmltree.SubElement( requiredShortcut, "thumb" ).text = elem.attrib.get( "thumbnail" )
                    
                # Action
                xmltree.SubElement( requiredShortcut, "action" ).text = elem.text
                
                # Locked
                # - This is set to the skin directory, so it will only be locked in the management directory when using this skin
                xmltree.SubElement( requiredShortcut, "lock" ).text = xbmc.getSkinDir()
                
                
    def _get_icon_overrides( self, tree, icon, group, labelID, setToDefault = True ):        
        # This function will get any icon overrides based on labelID or group
        if icon is None:
            return

        icon = try_decode( icon )
            
        # If the icon is a VAR or an INFO, we aren't going to override
        if icon.startswith( "$" ):
            return icon
            
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
        
        if not (xbmc.skinHasImage(newicon.encode("utf-8")) or xbmcvfs.exists(newicon.encode("utf-8"))) and setToDefault == True:
            newicon = self._get_icon_overrides( tree, "DefaultShortcut.png", group, labelID, False )

        return newicon

        
    def _get_overrides_script( self ):
        # Get overrides.xml provided by script
        if "script" in self.overrides:
            return self.overrides[ "script" ]

        overridePath = os.path.join( DEFAULTPATH, "overrides.xml" )
        try:
            tree = xmltree.parse( overridePath )
            self._save_hash( overridePath, xbmcvfs.File( overridePath ).read() )
            self.overrides[ "script" ] = tree
            return tree
        except:
            if xbmcvfs.exists( overridePath ):
                log( "Unable to parse script overrides.xml. Invalid xml?" )
                self._save_hash( overridePath, xbmcvfs.File( overridePath ).read() )
            else:
                self._save_hash( overridePath, None )
            tree = xmltree.ElementTree( xmltree.Element( "overrides" ) )
            self.overrides[ "script" ] = tree
            return tree

    def _get_overrides_skin( self ):
        # Get overrides.xml provided by skin 
        if "skin" in self.overrides:
            return self.overrides[ "skin" ]

        overridePath = os.path.join( SKINPATH, "overrides.xml" )
        try:
            tree = xmltree.parse( overridePath )
            self._save_hash( overridePath, xbmcvfs.File( overridePath ).read() )
            self.overrides[ "skin" ] = tree
            return tree
        except:
            if xbmcvfs.exists( overridePath ):
                log( "Unable to parse skin overrides.xml. Invalid xml?" )
                self._save_hash( overridePath, xbmcvfs.File( overridePath ).read() )
            else:
                self._save_hash( overridePath, None )
            tree = xmltree.ElementTree( xmltree.Element( "overrides" ) )
            self.overrides[ "skin" ] = tree
            return tree

    def _get_overrides_user( self, profileDir = "special://profile" ):
        # Get overrides.xml provided by user
        if "user" in self.overrides:
            return self.overrides[ "user" ]

        overridePath = os.path.join( profileDir, "overrides.xml" )
        try:
            tree = xmltree.parse( xbmc.translatePath( overridePath ) )
            self._save_hash( overridePath, xbmcvfs.File( overridePath ).read() )
            self.overrides[ "user" ] = tree
            return tree
        except:
            if xbmcvfs.exists( overridePath ):
                log( "Unable to parse user overrides.xml. Invalid xml?" )
                self._save_hash( overridePath, xbmcvfs.File( overridePath ).read() )
            else:
                self._save_hash( overridePath, None )
            tree = xmltree.ElementTree( xmltree.Element( "overrides" ) )
            self.overrides[ "user" ] = tree
            return tree


    def _get_additionalproperties( self, profileDir ):
        # Load all saved properties (widgets, backgrounds, custom properties)

        if self.currentProperties is not None:
            return[ self.currentProperties, self.defaultProperties ]
            
        self.currentProperties = []
        self.defaultProperties = []
        
        path = os.path.join( profileDir, "addon_data", ADDONID, xbmc.getSkinDir().decode('utf-8') + ".properties" ).encode( "utf-8" )
        #path = os.path.join( DATAPATH , xbmc.getSkinDir().decode('utf-8') + ".properties" )
        if xbmcvfs.exists( path ):
            # The properties file exists, load from it
            try:
                file = xbmcvfs.File( path ).read()
                listProperties = ast.literal_eval( file )
                self._save_hash( path, file )
                
                for listProperty in listProperties:
                    # listProperty[0] = groupname
                    # listProperty[1] = labelID
                    # listProperty[2] = property name
                    # listProperty[3] = property value

                    # If listProperty[3] starts with $SKIN, it's from an older version of the script
                    # so quickly run it through the local function to remove the unecessary localisation
                    if listProperty[3].startswith( "$SKIN["):
                        listProperty[3] = self.local( listProperty[3] )[3]
                    self.currentProperties.append( [listProperty[0], listProperty[1], listProperty[2], listProperty[3]] )
            except:
                log( "Failed to load current properties" )
                print_exc()
                self.currentProperties = [ None ]
        else:
            self.currentProperties = [ None ]
            
        # Load skin defaults (in case we need them...)
        tree = self._get_overrides_skin()
        for elemSearch in [["widget", tree.findall( "widgetdefault" )], ["widget:node", tree.findall( "widgetdefaultnode" )], ["background", tree.findall( "backgrounddefault" )], ["custom", tree.findall( "propertydefault" )] ]:
            for elem in elemSearch[1]:
                # Get labelID and defaultID
                labelID = elem.attrib.get( "labelID" )
                defaultID = labelID
                if "defaultID" in elem.attrib:
                    defaultID = elem.attrib.get( "defaultID" )

                if elemSearch[0] == "custom":
                    # Custom property
                    if "group" not in elem.attrib:
                        self.defaultProperties.append( ["mainmenu", labelID, elem.attrib.get( 'property' ), elem.text, defaultID ] )
                    else:
                        self.defaultProperties.append( [elem.attrib.get( "group" ), labelID, elem.attrib.get( 'property' ), elem.text, defaultID ] )
                else:
                    # Widget or background
                    if "group" not in elem.attrib:
                        self.defaultProperties.append( [ "mainmenu", labelID, elemSearch[ 0 ].split( ":" )[ 0 ], elem.text, defaultID ] )
                        
                        if elemSearch[ 0 ] == "background":
                            # Get and set the background name
                            backgroundName = self._getBackgroundName( elem.text )
                            if backgroundName is not None:
                                self.defaultProperties.append( [ "mainmenu", labelID, "backgroundName", backgroundName, defaultID ] )
                            
                        if elemSearch[0] == "widget":
                            # Get and set widget type and name
                            widgetDetails = self._getWidgetNameAndType( elem.text )
                            if widgetDetails is not None:
                                self.defaultProperties.append( [ "mainmenu", labelID, "widgetName", widgetDetails[ "name" ], defaultID ] )
                                if "type" in widgetDetails:
                                    self.defaultProperties.append( [ "mainmenu", labelID, "widgetType", widgetDetails[ "type" ], defaultID ] )
                                if "path" in widgetDetails:
                                    self.defaultProperties.append( [ "mainmenu", labelID, "widgetPath", widgetDetails[ "path" ], defaultID ] )
                                if "target" in widgetDetails:
                                    self.defaultProperties.append( [ "mainmenu", labelID, "widgetTarget", widgetDetails[ "target" ], defaultID ] )

                        if elemSearch[0] == "widget:node":
                            # Set all widget properties from the default
                            if elem.text:
                                self.defaultProperties.append( [ "mainmenu", labelID, "widget", elem.attrib.get( "label" ), defaultID ] )
                            if "label" in elem.attrib:
                                self.defaultProperties.append( [ "mainmenu", labelID, "widgetName", elem.attrib.get( "label" ), defaultID ] )
                            if "type" in elem.attrib:
                                self.defaultProperties.append( [ "mainmenu", labelID, "widgetType", elem.attrib.get( "type" ), defaultID ] )
                            if "path" in elem.attrib:
                                self.defaultProperties.append( [ "mainmenu", labelID, "widgetPath", elem.attrib.get( "path" ), defaultID ] )
                            if "target" in elem.attrib:
                                self.defaultProperties.append( [ "mainmenu", labelID, "widgetTarget", elem.attrib.get( "target" ), defaultID ] )
                    else:
                        self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, elemSearch[ 0 ].split( ":" )[ 0 ], elem.text, defaultID ] )
                        
                        if elemSearch[ 0 ] == "background":
                            # Get and set the background name
                            backgroundName = self._getBackgroundName( elem.text )
                            if backgroundName is not None:
                                self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "backgroundName", backgroundName, defaultID ] )
                        
                        if elemSearch[0] == "widget":
                            # Get and set widget type and name
                            widgetDetails = self._getWidgetNameAndType( elem.text )
                            if widgetDetails is not None:
                                self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "widgetName", widgetDetails[ "name" ], defaultID ] )
                                if "type" in widgetDetails:
                                    self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "widgetType", widgetDetails[ "type" ], defaultID ] )
                                if "path" in widgetDetails:
                                    self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "widgetPath", widgetDetails[ "path" ], defaultID ] )
                                if "target" in widgetDetails:
                                    self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "widgetTarget", widgetDetails[ "target" ], defaultID ] )

                        if elemSearch[ 0 ] == "widget:node":
                            # Set all widget properties from the default
                            if "label" in elem.attrib:
                                self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "widgetName", elem.attrib.get( "label" ), defaultID ] )
                            if "type" in elem.attrib:
                                self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "widgetType", elem.attrib.get( "type" ), defaultID ] )
                            if "path" in elem.attrib:
                                self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "widgetPath", elem.attrib.get( "path" ), defaultID ] )
                            if "target" in elem.attrib:
                                self.defaultProperties.append( [ elem.attrib.get( "group" ), labelID, "widgetTarget", elem.attrib.get( "target" ), defaultID ] )

        # Load icons out of mainmenu.DATA.xml
        path = os.path.join( SKINPATH , "mainmenu.DATA.xml")
        if xbmcvfs.exists( path ):
            file = xbmcvfs.File( path ).read()
            self._save_hash( path, file )
            tree = xmltree.parse( path )
            for node in tree.getroot().findall( "shortcut" ):
                label = self.local( node.find( "label" ).text )[3].replace( " ", "" ).lower()
                action = node.find( "action.text" )
                labelID = self._get_labelID( label, action, getDefaultID = True )
                self.defaultProperties.append( [ "mainmenu", labelID, "icon", node.find( "icon" ).text ] )
                                        
        returnVal = [ self.currentProperties, self.defaultProperties ]
        return returnVal

    def _getCustomPropertyFallbacks( self, group ):
        if group in self.propertyInformation[ "fallbacks" ]:
            # We've already loaded everything, return it all
            return( self.propertyInformation[ "fallbackProperties" ][ group ], self.propertyInformation[ "fallbacks" ][ group ] )

        # Get skin overrides
        tree = self._get_overrides_skin()

        # Find all fallbacks
        fallbackProperties = []
        fallbacks = {}
        for elem in tree.findall( "propertyfallback" ):
            if ("group" not in elem.attrib and group == "mainmenu") or elem.attrib.get("group") == group:
                # This is a fallback for the group we've been asked for
                propertyName = elem.attrib.get( "property" )
                if propertyName not in fallbackProperties:
                    # Save the property name in the order in which we processed it
                    fallbackProperties.append( propertyName )
                if propertyName not in fallbacks.keys():
                    # Create an empty list to hold fallbacks for this property
                    fallbacks[ propertyName ] = []
                # Check whether any attribute/value pair has to match for this fallback
                attribName = None
                attribValue = None
                if "attribute" in elem.attrib and "value" in elem.attrib:
                    # This particular property is a matched property
                    attribName = elem.attrib.get( "attribute" )
                    attribValue = elem.attrib.get( "value" )
                # Upgrade widgetTarget where value is video to videos
                value = elem.text
                if propertyName.startswith( "widgetTarget" ) and value == "video":
                    value = "videos"
                # Save details
                fallbacks[ propertyName ].append( ( value, attribName, attribValue ) )
        # Save all the results for this group
        self.propertyInformation[ "fallbackProperties" ][ group ] = fallbackProperties
        self.propertyInformation[ "fallbacks" ][ group ] = fallbacks
        
        return( self.propertyInformation[ "fallbackProperties" ][ group ], self.propertyInformation[ "fallbacks" ][ group ] )

    def _getPropertyRequires( self ):
        if self.propertyInformation[ "requires" ] is not None:
            # We've already loaded requires and templateOnly properties, return eveything
            return( self.propertyInformation[ "otherProperties" ], self.propertyInformation[ "requires" ], self.propertyInformation[ "templateOnly" ] )

        # Get skin overrides
        tree = self._get_overrides_skin()

        # Find all property requirements
        requires = {}
        templateOnly = []
        for elem in tree.findall( "propertySettings" ):
            propertyName = elem.attrib.get( "property" )
            if propertyName not in self.propertyInformation[ "otherProperties" ]:
                # Save the property name in the order in which we processed it
                self.propertyInformation[ "otherProperties" ].append( propertyName )
            if "requires" in elem.attrib:
                # This property requires another to be present
                requires[ propertyName ] = elem.attrib.get( "requires" )
            if "templateonly" in elem.attrib and elem.attrib.get( "templateonly" ).lower() == "true":
                # This property is only used by the template, and should not be written to the main menu
                templateOnly.append( propertyName )
        # Save all the results
        self.propertyInformation[ "requires" ] = requires
        self.propertyInformation[ "templateOnly" ] = templateOnly
        
        return( self.propertyInformation[ "otherProperties" ], self.propertyInformation[ "requires" ], self.propertyInformation[ "templateOnly" ] )
        
    def _getWidgetNameAndType( self, widgetID ):
        if widgetID in self.widgetNameAndType:
            return self.widgetNameAndType[ widgetID ]

        tree = self._get_overrides_skin()
        for elem in tree.findall( "widget" ):
            if elem.text == widgetID:
                widgetInfo = { "name": elem.attrib.get( "label" ) }
                if "type" in elem.attrib:
                    widgetInfo[ "type" ] = elem.attrib.get( "type" )
                if "path" in elem.attrib:
                    widgetInfo[ "path" ] = elem.attrib.get( "path" )
                if "target" in elem.attrib:
                    widgetInfo[ "target" ] = elem.attrib.get( "target" )
                self.widgetNameAndType[ widgetID ] = widgetInfo
                return widgetInfo
                        
        self.widgetNameAndType[ widgetID ] = None
        return None
        
    def _getBackgroundName( self, backgroundID ):
        if backgroundID in self.backgroundName:
            return self.backgroundName[ backgroundID ]

        tree = self._get_overrides_skin()
        for elem in tree.findall( "background" ):
            if elem.text == backgroundID:
                returnString = elem.attrib.get( "label" )
                self.backgroundName[ backgroundID ] = returnString
                return returnString
                        
        self.backgroundName[ backgroundID ] = None
        return None
                
    def _reset_backgroundandwidgets( self ):
        # This function resets all skin properties used to identify if specific backgrounds or widgets are active
        tree = self._get_overrides_skin()
        for elem in tree.findall( "widget" ):
            xbmc.executebuiltin( "Skin.Reset(skinshortcuts-widget-" + elem.text + ")" )
        for elem in tree.findall( "background" ):
            xbmc.executebuiltin( "Skin.Reset(skinshortcuts-background-" + elem.text + ")" )
                
    
    def createNiceName ( self, item, noNonLocalized = False ):
        # Translate certain localized strings into non-localized form for labelID
        if noNonLocalized == False:
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
            if item == "32087":
                return "radio"
        
        return item.lower( ).replace( " ", "" )
            
    def checkVisibility ( self, action ):
        # Return whether mainmenu items should be displayed
        action = action.lower().replace( " ", "" ).replace( "\"", "" )

        # Catch-all for shortcuts to plugins
        if "plugin://" in action:
            return ""

        # Video node visibility
        if action.startswith( ( "activatewindow(videos,videodb://", "activatewindow(videolibrary,videodb://",
                 "activatewindow(10025,videodb://", "activatewindow(videos,library://video/", 
                 "activatewindow(videolibrary,library://video", "activatewindow(10025,library://video/" ) ):
            path = action.split( "," )
            if path[ 1 ].endswith( ")" ):
                path[ 1 ] = path[ 1 ][:-1]
            return NODE.get_visibility( path[ 1 ] )

        # Audio node visibility - Isengard and earlier
        elif action.startswith( "activatewindow(musiclibrary,musicdb://" ) or action.startswith( "activatewindow(10502,musicdb://" ) or action.startswith( "activatewindow(musiclibrary,library://music/" ) or action.startswith( "activatewindow(10502,library://music/" ):
            path = action.split( "," )
            if path[ 1 ].endswith( ")" ):
                path[ 1 ] = path[ 1 ][:-1]
            return NODE.get_visibility( path[ 1 ] )

        # Audio node visibility - Additional checks for Jarvis and later
        # (Note when cleaning up in the future, some of the Isengard checks - those with window 10502 - are still valid...)
        elif action.startswith( "activatewindow(music,musicdb://" ) or action.startswith( "activatewindow(music,library://music/" ):
            path = action.split( "," )
            if path[ 1 ].endswith( ")" ):
                path[ 1 ] = path[ 1 ][:-1]
            return NODE.get_visibility( path[ 1 ] )

        # Power menu visibilities
        elif action == "quit()" or action == "quit":
            return "System.ShowExitButton"
        elif action == "powerdown()" or action == "powerdown":
            return "System.CanPowerDown"
        elif action == "alarmclock(shutdowntimer,shutdown())":
            return "!System.HasAlarm(shutdowntimer) + [System.CanPowerDown | System.CanSuspend | System.CanHibernate]"
        elif action == "cancelalarm(shutdowntimer)":
            return "System.HasAlarm(shutdowntimer)"
        elif action == "suspend()" or action == "suspend":
            return "System.CanSuspend"
        elif action == "hibernate()" or action == "hibernate":
            return "System.CanHibernate"
        elif action == "reset()" or action == "reset":
            return "System.CanReboot"
        elif action == "system.logoff":
            return "[System.HasLoginScreen | IntegerGreaterThan(System.ProfileCount,1)] + System.Loggedon"
        elif action == "mastermode":
            return "System.HasLocks"
        elif action == "inhibitidleshutdown(true)":
            return "System.HasShutdown +!System.IsInhibit"
        elif action == "inhibitidleshutdown(false)":
            return "System.HasShutdown + System.IsInhibit"
        elif action == "restartapp":
            return "[System.Platform.Windows | System.Platform.Linux] +! System.Platform.Linux.RaspberryPi"

        # General visibilities
        elif action == "activatewindow(weather)" and int( KODIVERSION ) >= 17:
            return "!String.IsEmpty(Weather.Plugin)"
        elif action == "activatewindow(weather)":
            return "!IsEmpty(Weather.Plugin)"
        elif action.startswith( "activatewindowandfocus(mypvr" ) or action.startswith( "playpvr" ) and ADDON.getSetting( "donthidepvr" ) == "false":
            return "PVR.HasTVChannels"
        elif action.startswith( "activatewindow(tv" ) and ADDON.getSetting( "donthidepvr" ) == "false":
            if int( KODIVERSION ) >= 17:
                return "System.HasPVRAddon"
            else:
                return "PVR.HasTVChannels"
        elif action.startswith( "activatewindow(radio" ) and ADDON.getSetting( "donthidepvr" ) == "false":
            if int( KODIVERSION ) >= 17:
                return "System.HasPVRAddon"
            else:
                return "PVR.HasRadioChannels"
        elif action.startswith( "activatewindow(videos,movie" ):
            return "Library.HasContent(Movies)"
        elif action.startswith( "activatewindow(videos,recentlyaddedmovies" ):
            return "Library.HasContent(Movies)"
        elif action.startswith( "activatewindow(videos,tvshow" ) or action.startswith( "activatewindow(videos,tvshow" ):
            return "Library.HasContent(TVShows)"
        elif action.startswith( "activatewindow(videos,recentlyaddedepisodes" ):
            return "Library.HasContent(TVShows)"
        elif action.startswith( "activatewindow(videos,musicvideo" ):
            return "Library.HasContent(MusicVideos)"
        elif action.startswith( "activatewindow(videos,recentlyaddedmusicvideos" ):
            return "Library.HasContent(MusicVideos)"
        elif action == "xbmc.playdvd()" or action == "playdvd":
            return "System.HasMediaDVD"
        elif action.startswith( "activatewindow(eventlog" ):
            return "system.getbool(eventlog.enabled)"
            
        return ""


    def checkVersionEquivalency( self, version, action, type = "shortcuts" ):
        # Check whether the version specified for a shortcut has an equivalency
        # to the version of Kodi we're running
        trees = [ self._get_overrides_skin(), self._get_overrides_script() ]

        # Set up so we can handle both groupings and shortcuts in one
        if type == "shortcuts":
            if action is None:
                action = ""
            else:
                action = action.text
            findElem = "shortcutEquivalent"
            findAttrib = "action"
        if type == "groupings":
            if action is None:
                action = ""
            findElem = "groupEquivalent"
            findAttrib = "condition"

        for tree in trees:
            if tree.find( "versionEquivalency" ) is None:
                continue
            for elem in tree.find( "versionEquivalency" ).findall( findElem ):
                if elem.attrib.get( findAttrib ) is not None and elem.attrib.get( findAttrib ).lower() != action.lower():
                    # Action's don't match
                    continue
                if int( elem.attrib.get( "version" ) ) > int( KODIVERSION ):
                    # This version of Kodi is older than the shortcut is intended for
                    continue

                # The actions match, and the version isn't too old, so
                # now check it's not too new
                if elem.text == "All":
                    # This shortcut matches all newer versions
                    return True
                elif int( elem.text ) >= int( KODIVERSION ):
                    return True

                # The version didn't match
                break

        return False
        
    def checkAdditionalProperties( self, group, labelID, defaultID, isUserShortcuts, profileDir ):
        # Return any additional properties, including widgets, backgrounds, icons and thumbnails
        allProperties = self._get_additionalproperties( profileDir )
        currentProperties = allProperties[1]
        
        returnProperties = []
        
        # This returns two lists...
        #  allProperties[0] = Saved properties
        #  allProperties[1] = Default properties
        
        if isUserShortcuts and ( len( allProperties[ 0 ] ) == 0 or allProperties[ 0 ][ 0 ] is not None ):
            currentProperties = allProperties[0]
            
        # Loop through the current properties, looking for the current item
        for currentProperty in currentProperties:
            # currentProperty[0] = Group name
            # currentProperty[1] = labelID
            # currentProperty[2] = Property name
            # currentProperty[3] = Property value
            # currentProperty[4] = defaultID
            if labelID is not None and currentProperty[0] == group and currentProperty[1] == labelID:
                returnProperties.append( self.upgradeAdditionalProperties( currentProperty[2], currentProperty[3] ) )
            elif len( currentProperty ) is not 4:
                if defaultID is not None and currentProperty[0] == group and currentProperty[4] == defaultID:
                    returnProperties.append( self.upgradeAdditionalProperties( currentProperty[2], currentProperty[3] ) )
                
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


    def checkIfMenusShared( self, isSubLevel = False ):
        # Check if the skin required the menu not to be shared
        tree = self._get_overrides_skin()
        if tree is not None:
            # If this is a sublevel, and the skin has asked for sub levels to not be shared...
            if isSubLevel and tree.find( "doNotShareLevels" ) is not None:
                return False
            # If the skin has asked for all menu's not to be shared...
            if tree.find( "doNotShareMenu" ) is not None:
                return False

        # Check if the user has asked for their menus not to be shared
        if ADDON.getSetting( "shared_menu" ).lower() == "false":
            return False
        return True

    def getSharedSkinList( self ):
        # This will return a list of skins the user can import the menu from
        skinNames = []
        skinFiles = []
        for files in xbmcvfs.listdir( DATAPATH ):
            # Try deleting all shortcuts
            if files:
                for file in files:
                    if file.endswith( ".hash" ) and not file.startswith( "%s-" %( xbmc.getSkinDir() ) ):
                        canImport, skinName = self.parseHashFile( os.path.join( DATAPATH, file.decode( 'utf-8' ) ).encode( 'utf-8' ) )
                        if canImport == True:
                            skinNames.append( skinName )
                    elif file.endswith( ".DATA.xml" ) and not file.startswith( "%s-" %( xbmc.getSkinDir() ) ):
                        skinFiles.append( file )

        # Remove any files which start with one of the skin names
        removeSkins = []
        removeFiles = []
        for skinName in skinNames:
            matched = False
            for skinFile in skinFiles:
                if skinFile.startswith( "%s-" %( skinName ) ):
                    if matched == False:
                        matched = True
                    removeFiles.append( skinFile )
            if matched == False:
                # This skin doesn't have a custom menu
                removeSkins.append( skinName )

        skinNames = [x for x in skinNames if x not in removeSkins]
        skinFiles = [x for x in skinFiles if x not in removeFiles]

        # If there are any files left in skinFiles, we have a shared menu
        if len( skinFiles ) != 0:
            skinNames.insert( 0, LANGUAGE(32111) )

        return (skinNames, skinFiles)

    def getFilesForSkin( self, skinName ):
        # This will return a list of all menu files for a particular skin
        skinFiles = []
        for files in xbmcvfs.listdir( DATAPATH ):
            # Try deleting all shortcuts
            if files:
                for file in files:
                    if file.endswith( ".DATA.xml" ) and file.startswith( "%s-" % ( skinName ) ):
                        skinFiles.append( file )

        return skinFiles


    def parseHashFile( self, file ):
        try:
            hashes = ast.literal_eval( xbmcvfs.File( file ).read() )
        except:
            # There is no hash list, return False
            return( False, "" )

        canImport = False
        skinName = None
        for hash in hashes:
            if hash[0] == "::FULLMENU::":
                canImport = True
                if skinName:
                    return( True, skinName )
            if hash[0] == "::SKINDIR::":
                skinName = hash[1]
                if canImport == True:
                    return( True, skinName )
        
        return( canImport, skinName )

    def importSkinMenu( self, files, skinName = None ):
        # This function copies one skins menus to another
        for oldFile in files:
            if skinName:
                newFile = oldFile.replace( skinName, xbmc.getSkinDir() )
            else:
                newFile = "%s-%s" %( xbmc.getSkinDir(), oldFile )
            oldPath = os.path.join( DATAPATH, oldFile.decode( 'utf-8' ) ).encode( 'utf-8' )
            newPath = os.path.join( DATAPATH, newFile.decode( 'utf-8' ) ).encode( 'utf-8' )

            # Copy file
            xbmcvfs.copy( oldPath, newPath )

        # Delete any .properties file
        propFile = os.path.join( DATAPATH, "%s.properties" %( xbmc.getSkinDir() ) ).encode( 'utf-8' )
        if xbmcvfs.exists( propFile ):
            xbmcvfs.delete( propFile )


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
                
                
    def local( self, data ):
        # This is our function to manage localisation
        # It accepts strings in one of the following formats:
        #   #####, ::LOCAL::#####, ::SCRIPT::#####
        #   $LOCALISE[#####], $SKIN[####|skin.id|last translation]
        #   $ADDON[script.skinshortcuts #####]
        # If returns a list containing:
        #   [Number/$SKIN, $LOCALIZE/$ADDON/Local string, Local string]
        #   [Used for saving, used for building xml, used for displaying in dialog]
        
        if data is None:
            return ["","","",""]
        
        data = try_decode( data )

        skinid = None
        lasttranslation = None
        
        # Get just the integer of the string, for the input forms where this is valid
        if not data.find( "::SCRIPT::" ) == -1:
            data = data[10:]
        elif not data.find( "::LOCAL::" ) == -1:            
            data = data[9:]
        elif not data.find( "$LOCALIZE[" ) == -1:
            data = data.replace( "$LOCALIZE[", "" ).replace( "]", "" ).replace( " ", "" )
        elif not data.find( "$ADDON[script.skinshortcuts" ) == -1:
            data = data.replace( "$ADDON[script.skinshortcuts", "" ).replace( "]", "" ).replace( " ", "" )
        
        # Get the integer and skin id, from $SKIN input forms
        elif not data.find( "$SKIN[" ) == -1:
            splitdata = data[6:-1].split( "|" )
            data = splitdata[0]
            skinid = splitdata[1]
            lasttranslation = splitdata[2]
            
        if data.isdigit():
            if int( data ) >= 31000 and int( data ) < 32000:
                # A number from a skin - we're going to return a $SKIN[#####|skin.id|last translation] unit
                if skinid is None:
                    # Set the skinid to the current skin id
                    skinid = xbmc.getSkinDir()
                    
                # If we're on the same skin as the skinid, get the latest translation
                if skinid == xbmc.getSkinDir():
                    lasttranslation = xbmc.getLocalizedString( int( data ) )
                    returnString = "$SKIN[" + data + "|" + skinid + "|" + lasttranslation + "]"
                    return [ returnString, "$LOCALIZE[" + data + "]", lasttranslation, data ]
                    
                returnString = "$SKIN[" + data + "|" + skinid + "|" + lasttranslation + "]"
                return [ returnString, lasttranslation, lasttranslation, data ]
                
            elif int( data ) >= 32000 and int( data ) < 33000:
                # A number from the script
                return [ data, "$ADDON[script.skinshortcuts " + data + "]", LANGUAGE( int( data ) ), data ]
                
            else:
                # A number from XBMC itself (probably)
                return [ data, "$LOCALIZE[" + data + "]", xbmc.getLocalizedString( int( data ) ), data ]
                
        # This isn't anything we can localize, just return it (in triplicate ;))
        return[ data, data, data, data ]

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

    def slugify(self, text, userShortcuts=False, entities=True, decimal=True, hexadecimal=True, max_length=0, word_boundary=False, separator='-', convertInteger=False, isSubLevel=False):
        # Handle integers
        if convertInteger and text.isdigit():
            text = "NUM-" + text
    
        # text to unicode
        if type(text) != types.UnicodeType:
            text = unicode(text, 'utf-8', 'ignore')

        # decode unicode ( ??? = Ying Shi Ma)
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

        # If this is a shortcut file (.DATA.xml) and user shortcuts aren't shared, add the skin dir
        if userShortcuts == True and self.checkIfMenusShared( isSubLevel ) == False:
            text = "%s-%s" %( xbmc.getSkinDir(), text )

        return text

    # ----------------------------------------------------------------
    # --- Functions that should get their own module in the future ---
    # --- (when xml building functions are revamped/simplified) ------
    # ----------------------------------------------------------------

    def getListProperty( self, onclick ):
        # For ActivateWindow elements, extract the path property
        if onclick.startswith( "ActivateWindow" ):
            # An ActivateWindow - Let's start by removing the 'ActivateWindow(' and the ')'
            listProperty = onclick
            # Handle (the not uncommon) situation where the trailing ')' has been forgotten
            if onclick.endswith( ")" ):
                listProperty = onclick[ :-1 ]
            listProperty = listProperty.split( "(", 1 )[ 1 ]

            # Split what we've got left on commas
            listProperty = listProperty.split( "," )

            # Get the part of the onclick that we're actually interested in
            if len( listProperty ) == 1:
                # 'elementWeWant'
                return listProperty[ 0 ]
            elif len( listProperty ) == 2 and listProperty[ 1 ].lower().replace( " ", "" ) == "return":
                # 'elementWeWant' 'return'
                return listProperty[ 0 ]
            elif len( listProperty ) == 2:
                # 'windowToActivate' 'elementWeWant'
                return listProperty[ 1 ]
            elif len( listProperty ) == 3:
                # 'windowToActivate' 'elementWeWant' 'return'
                return listProperty[ 1 ]
            else:
                # Situation we haven't anticipated - log the issue and return original onclick
                log( "Unable to get 'list' property for shortcut %s" %( onclick ) )
                return onclick
        else:
            # Not an 'ActivateWindow' - return the onclick
            return onclick

    def upgradeAction( self, action ):
        # This function looks for actions used in a previous version of Kodi, and upgrades them to the current action

        if not action.lower().startswith( "activatewindow(" ): return action

        # Isengard + earlier music addons
        if int( KODIVERSION ) <= 15:
            # Shortcut to addon section
            if action.lower().startswith( "activatewindow(musiclibrary,addons" ) and xbmc.getCondVisibility( "!Library.HasContent(Music)" ):
                return( "ActivateWindow(MusicFiles,Addons,return)" )
            elif action.lower().startswith( "activatewindow(10502,addons" ) and xbmc.getCondVisibility( "!Library.HasContent(Music)" ):
                return( "ActivateWindow(10501,Addons,return)" )
            elif action.lower().startswith( "activatewindow(musicfiles,addons" ) and xbmc.getCondVisibility( "Library.HasContent(Music)" ):
                return( "ActivateWindow(MusicLibrary,Addons,return)" )
            elif action.lower().startswith( "activatewindow(10501,addons" ) and xbmc.getCondVisibility( "Library.HasContent(Music)" ):
                return( "ActivateWindow(10502,Addons,return)" )

            # Shortcut to a specific addon
            if "plugin://" in action.lower():
                if action.lower().startswith( "activatewindow(musiclibrary" ) and xbmc.getCondVisibility( "!Library.HasContent(Music)" ):
                    return self.buildReplacementMusicAddonAction( action, "MusicFiles" )
                elif action.lower().startswith( "activatewindow(10502" ) and xbmc.getCondVisibility( "!Library.HasContent(Music)" ):
                    return self.buildReplacementMusicAddonAction( action, "10501" )
                elif action.lower().startswith( "activatewindow(musicfiles" ) and xbmc.getCondVisibility( "Library.HasContent(Music)" ):
                    return self.buildReplacementMusicAddonAction( action, "MusicLibrary" )
                elif action.lower().startswith( "activatewindow(10501" ) and xbmc.getCondVisibility( "Library.HasContent(Music)" ):
                    return self.buildReplacementMusicAddonAction( action, "10502" )


        # Jarvis + later music windows
        if action.lower() == "activatewindow(musicfiles)" and int( KODIVERSION ) >= 16:
            return "ActivateWindow(Music,Files,Return)"

        if action.lower().startswith("activatewindow(musiclibrary") and int( KODIVERSION ) >= 16:
            if "," in action:
                return "ActivateWindow(Music," + action.split( ",", 1 )[ 1 ]
            else:
                return "ActivateWindow(Music)"

        # Isengard + later (all supported versions) video windows
        if action.lower().startswith( "activatewindow(videolibrary"):
            if "," in action:
                return "ActivateWindow(Videos," + action.split( ",", 1 )[ 1 ]
            else:
                return "ActivateWindow(Videos)"

        # No matching upgrade
        return action

    def upgradeAdditionalProperties( self, propertyName, propertyValue ):
        # This function fixes any changes to additional properties between Kodi versions
        if propertyName.startswith( "widgetTarget" ) and propertyValue == "video":
            propertyValue = "videos"
        
        return [ propertyName, propertyValue ]

    def buildReplacementMusicAddonAction( self, action, window ):
        # Builds a replacement action for an Isengard or earlier shortcut to a specific music addon
        splitAction = action.split( "," )
        # [0] = ActivateWindow([window]
        # [1] = "plugin://plugin.name/path?params"
        # [2] = return)
        
        if len(splitAction) == 2:
            return "ActivateWindow(%s,%s)" %( window, splitAction[ 1 ] )
        else:
            return "ActivateWindow(%s,%s,return)" %( window, splitAction[ 1 ] )

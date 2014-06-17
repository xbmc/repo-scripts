# coding=utf-8
import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, xbmcaddon, urllib
import xml.etree.ElementTree as xmltree
#from xml.dom.minidom import parse
from xml.sax.saxutils import escape as escapeXML
from traceback import print_exc

__addon__        = xbmcaddon.Addon()
__addonid__      = sys.modules[ "__main__" ].__addonid__
__addonversion__ = __addon__.getAddonInfo('version')
__xbmcversion__  = xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0]
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ ).encode('utf-8')
__masterpath__     = os.path.join( xbmc.translatePath( "special://masterprofile/addon_data/" ).decode('utf-8'), __addonid__ ).encode('utf-8')
__language__     = __addon__.getLocalizedString

import datafunctions
DATA = datafunctions.DataFunctions()
import hashlib, hashlist

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)
    
class XMLFunctions():
    def __init__(self):
        pass
        
    def buildMenu( self, mainmenuID, groups, numLevels, buildMode ):
        # Entry point for building includes.xml files
        if xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-isrunning" ) == "True":
            return
        
        xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-isrunning", "True" )
 
        # Get a list of profiles
        fav_file = xbmc.translatePath( 'special://userdata/profiles.xml' ).decode("utf-8")
        tree = None
        if xbmcvfs.exists( fav_file ):
            tree = xmltree.parse( fav_file )
        
        profilelist = []
        if tree is not None:
            profiles = tree.findall( "profile" )
            for profile in profiles:
                name = profile.find( "name" ).text.encode( "utf-8" )
                dir = profile.find( "directory" ).text.encode( "utf-8" )
                log( "Profile found: " + name + " (" + dir + ")" )
                # Localise the directory
                if "://" in dir:
                    dir = xbmc.translatePath( dir ).decode( "utf-8" )
                else:
                    # Base if off of the master profile
                    dir = xbmc.translatePath( os.path.join( "special://masterprofile", dir ) ).decode( "utf-8" )
                profilelist.append( [dir, "StringCompare(System.ProfileName," + name.decode( "utf-8" ) + ")"] )
                
        else:
            profilelist = [["special://masterprofile", None]]
 
        if self.shouldwerun( profilelist ) == False:
            log( "Menu is up to date" )
            xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-isrunning" )
            return

        progress = None
        # Create a progress dialog
        progress = xbmcgui.DialogProgressBG()
        progress.create(__addon__.getAddonInfo( "name" ), __language__( 32049 ) )
        progress.update( 0 )
        
        # Write the menus
        try:
            self.writexml( profilelist, mainmenuID, groups, numLevels, buildMode, progress )
            complete = True
        except:
            log( "Failed to write menu" )
            print_exc()
            complete = False
            
        
        # Clear window properties for overrides, widgets, backgrounds, properties
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-script" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-script-data" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-skin" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-skin-data" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-user" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-user-data" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsAdditionalProperties" )
        
        # Mark that we're no longer running, clear the progress dialog
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-isrunning" )
        progress.close()
        
        # Reload the skin
        if complete == True:
            xbmc.executebuiltin( "XBMC.ReloadSkin()" )
        else:
            xbmcgui.Dialog().ok( __addon__.getAddonInfo( "name" ), "Unable to build menu" )
        
    def shouldwerun( self, profilelist ):
        log( "Checking if user has updated menu" )
        try:
            property = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-reloadmainmenu" )
            xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-reloadmainmenu" )
            if property == "True":
                log( " - Yes")
                return True
        except:
            log( " - No" )
            
        log( "Checking include files exist" )
        # Get the skins addon.xml file
        addonpath = xbmc.translatePath( os.path.join( "special://skin/", 'addon.xml').encode("utf-8") ).decode("utf-8")
        addon = xmltree.parse( addonpath )
        extensionpoints = addon.findall( "extension" )
        paths = []
        skinpaths = []
        
        # Get the skin version
        skinVersion = addon.getroot().attrib.get( "version" )
        
        # Get the directories for resolutions this skin supports
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get( "point" ) == "xbmc.gui.skin":
                resolutions = extensionpoint.findall( "res" )
                for resolution in resolutions:
                    path = xbmc.translatePath( os.path.join( "special://skin/", resolution.attrib.get( "folder" ), "script-skinshortcuts-includes.xml").encode("utf-8") ).decode("utf-8")
                    paths.append( path )
                    skinpaths.append( path )
        
        # Check for the includes file
        for path in paths:
            if not xbmcvfs.exists( path ):
                log( " - No" )
                return True
            else:
                log( " - Yes" )
                


        try:
            hashes = eval( xbmcvfs.File( os.path.join( __masterpath__ , xbmc.getSkinDir() + ".hash" ) ).read() )
        except:
            # There is no hash list, return True
            log( "No hash list" )
            print_exc()
            return True
        
        log( "Checking hashes..." )
        checkedXBMCVer = False
        checkedSkinVer = False
        checkedScriptVer = False
        checkedProfileList = False
        checkedLanguage = False
            
        for hash in hashes:
            if hash[1] is not None:
                if hash[0] == "::XBMCVER::":
                    # Check the skin version is still the same as hash[1]
                    checkedXBMCVer = True
                    if __xbmcversion__ != hash[1]:
                        log( "  - XBMC version does not match" )
                        return True
                elif hash[0] == "::SKINVER::":
                    # Check the skin version is still the same as hash[1]
                    checkedSkinVer = True
                    if skinVersion != hash[1]:
                        log( "  - Skin version does not match" )
                        return True
                elif hash[0] == "::SCRIPTVER::":
                    # Check the script version is still the same as hash[1]
                    checkedScriptVer = True
                    if __addonversion__ != hash[1]:
                        log( "  - Script version does not match" )
                        return True
                elif hash[0] == "::PROFILELIST::":
                    # Check the profilelist is still the same as hash[1]
                    checkedProfileList = True
                    if profilelist != hash[1]:
                        log( "  - Profile list does not match" )
                        return True
                elif hash[0] == "::LANGUAGE::":
                    # Check that the XBMC language is still the same as hash[1]
                    checkedLanguage = True
                    if xbmc.getLanguage() != hash[1]:
                        log( "  - Language does not match" )
                        return True
                else:
                    hasher = hashlib.md5()
                    hasher.update( xbmcvfs.File( hash[0] ).read() )
                    if hasher.hexdigest() != hash[1]:
                        log( "  - Hash does not match on file " + hash[0] )
                        return True
            else:
                if xbmcvfs.exists( hash[0] ):
                    log( "  - File now exists " + hash[0] )
                    return True
                
        # If the skin or script version, or profile list, haven't been checked, we need to rebuild the menu 
        # (most likely we're running an old version of the script)
        if checkedXBMCVer == False or checkedSkinVer == False or checkedScriptVer == False or checkedProfileList == False or checkedLanguage == False:
            return True
        
            
        # If we get here, the menu does not need to be rebuilt.
        return False


    def writexml( self, profilelist, mainmenuID, groups, numLevels, buildMode, progress ):        
        # Reset the hashlist, add the profile list and script version
        hashlist.list = []
        hashlist.list.append( ["::PROFILELIST::", profilelist] )
        hashlist.list.append( ["::SCRIPTVER::", __addonversion__] )
        hashlist.list.append( ["::XBMCVER::", __xbmcversion__] )
        hashlist.list.append( ["::LANGUAGE::", xbmc.getLanguage()] )
        
        # Create a new tree and includes for the various groups
        tree = xmltree.ElementTree( xmltree.Element( "includes" ) )
        root = tree.getroot()
        
        mainmenuTree = xmltree.SubElement( root, "include" )
        mainmenuTree.set( "name", "skinshortcuts-mainmenu" )
        
        submenuTrees = []
        for level in range( 0,  int( numLevels) + 1 ):
            subelement = xmltree.SubElement(root, "include")
            subtree = xmltree.SubElement( root, "include" )
            if level == 0:
                subtree.set( "name", "skinshortcuts-submenu" )
            else:
                subtree.set( "name", "skinshortcuts-submenu-" + str( level ) )
            submenuTrees.append( subtree )
        
        if buildMode == "single":
            allmenuTree = xmltree.SubElement( root, "include" )
            allmenuTree.set( "name", "skinshortcuts-allmenus" )
        
        profilePercent = 100 / len( profilelist )
        profileCount = -1
        
        
        for profile in profilelist:
            # Load profile details
            profileDir = profile[0]
            profileVis = profile[1]
            profileCount += 1
            
            # Clear any previous labelID's
            DATA._clear_labelID()
            
            # Get groups OR main menu shortcuts
            if not groups == "":
                menuitems = groups.split( "|" )
            else:
                menuitems = DATA._get_shortcuts( "mainmenu", True, profile[0] )
                
            if len( menuitems ) == 0:
                break
            
        
            # Work out percentages for dialog
            percent = profilePercent / len( menuitems )
                
            i = 0
            for item in menuitems:
                i += 1
                progress.update( ( profilePercent * profileCount) + percent * i )
                
                # Build the main menu item
                if groups == "":
                    submenu = DATA._get_labelID( item[5] )
                    mainmenuItemA = self.buildElement( item, mainmenuTree, "mainmenu", None, profile[1], submenu )
                    if buildMode == "single":
                        mainmenuItemB = self.buildElement( item, allmenuTree, "mainmenu", None, profile[1], submenu )
                else:
                    submenu = DATA._get_labelID( item )
                
                # Build the sub-menu items
                count = 0
                
                for submenuTree in submenuTrees:
                    # Create trees for individual submenu's
                    justmenuTreeA = xmltree.SubElement( root, "include" )
                    justmenuTreeB = xmltree.SubElement( root, "include" )
                    
                    # Get the submenu items
                    if count == 0:
                        justmenuTreeA.set( "name", "skinshortcuts-group-" + DATA.slugify( submenu ) )
                        justmenuTreeB.set( "name", "skinshortcuts-group-alt-" + DATA.slugify( submenu ) )
                        submenuitems = DATA._get_shortcuts( submenu, True, profile[0] )
                        
                        # Set whether there are any submenu items for the main menu
                        if groups == "":
                            if not len( submenuitems ) == 0:
                                hasSubMenu = xmltree.SubElement( mainmenuItemA, "property" )
                                hasSubMenu.set( "name", "hasSubmenu" )
                                hasSubMenu.text = "True"
                                if buildMode == "single":
                                    hasSubMenu = xmltree.SubElement( mainmenuItemB, "property" )
                                    hasSubMenu.set( "name", "hasSubmenu" )
                                    hasSubMenu.text = "True"
                                
                    else:
                        # This is an additional sub-menu, not the primary one
                        justmenuTreeA.set( "name", "skinshortcuts-group-" + DATA.slugify( submenu ) + "-" + str( count ) )
                        justmenuTreeB.set( "name", "skinshortcuts-group-alt-" + DATA.slugify( submenu ) + "-" + str( count ) )
                        submenuitems = DATA._get_shortcuts( submenu + "." + str( count ), True, profile[0] )
                    
                    # If there is a submenu, and we're building a single menu list, replace the onclick of mainmenuItemB AND recreate it as the first
                    # submenu item
                    if buildMode == "single" and not len( submenuitems ) == 0:
                        onClickElement = mainmenuItemB.find( "onclick" )
                        altOnClick = xmltree.SubElement( mainmenuItemB, "onclick" )
                        altOnClick.text = onClickElement.text
                        altOnClick.set( "condition", "StringCompare(Window(10000).Property(submenuVisibility)," + DATA.slugify( submenu ) + ")" )
                        onClickElement.text = "SetProperty(submenuVisibility," + DATA.slugify( submenu ) + ",10000)"
                        onClickElement.set( "condition", "!StringCompare(Window(10000).Property(submenuVisibility)," + DATA.slugify( submenu ) + ")" )
                        
                    for subitem in submenuitems:
                        self.buildElement( subitem, submenuTree, submenu, "StringCompare(Container(" + mainmenuID + ").ListItem.Property(submenuVisibility)," + escapeXML( DATA.slugify( submenu ) ) + ")", profile[1] )
                        self.buildElement( subitem, justmenuTreeA, submenu, None, profile[1] )
                        self.buildElement( subitem, justmenuTreeB, submenu, "StringCompare(Window(10000).Property(submenuVisibility)," + DATA.slugify( submenu ) + ")", profile[1] )
                        if buildMode == "single":
                            self.buildElement( subitem, allmenuTree, submenu, "StringCompare(Window(10000).Property(submenuVisibility)," + DATA.slugify( submenu ) + ")", profile[1] )
                
                    # Increase the counter
                    count += 1
            
        progress.update( 100 )
            
        # Get the skins addon.xml file
        addonpath = xbmc.translatePath( os.path.join( "special://skin/", 'addon.xml').encode("utf-8") ).decode("utf-8")
        addon = xmltree.parse( addonpath )
        extensionpoints = addon.findall( "extension" )
        paths = []
        for extensionpoint in extensionpoints:
            if extensionpoint.attrib.get( "point" ) == "xbmc.gui.skin":
                resolutions = extensionpoint.findall( "res" )
                for resolution in resolutions:
                    path = xbmc.translatePath( os.path.join( "special://skin/", resolution.attrib.get( "folder" ), "script-skinshortcuts-includes.xml").encode("utf-8") ).decode("utf-8")
                    paths.append( path )
        skinVersion = addon.getroot().attrib.get( "version" )
                    
        # Append the skin version to the hashlist
        hashlist.list.append( ["::SKINVER::", skinVersion] )
        
        # Save the tree
        for path in paths:
            tree.write( path, encoding="utf-8" )
        
        # Save the hashes
        file = xbmcvfs.File( os.path.join( __masterpath__ , xbmc.getSkinDir() + ".hash" ), "w" )
        file.write( repr( hashlist.list ) )
        file.close
        
    def buildElement( self, item, Tree, groupName, visibilityCondition, profileVisibility, submenuVisibility = None ):
        # This function will build an element for the passed Item in
        # the passed Tree
        newelement = xmltree.SubElement( Tree, "item" )
        
        # Onclick
        action = urllib.unquote( item[4] ).decode( "utf-8" )
        if action.find("::MULTIPLE::") == -1:
            onclick = xmltree.SubElement( newelement, "onclick" )
            if action.startswith( "pvr-channel://" ):
                # PVR action
                onclick.text = "RunScript(script.skinshortcuts,type=launchpvr&channel=" + action.replace( "pvr-channel://", "" ) + ")"
                log( "PVR: " + "RunScript(script.skinshortcuts,type=launchpvr&channel=" + action.replace( "pvr-channel://", "" )  + ")" )
            else:
                # Single action, place in as-is
                onclick.text = action
        else:
            # Multiple actions, separated by |
            actions = action.split( "|" )
            for singleAction in actions:
                if singleAction != "::MULTIPLE::":
                    onclick = xmltree.SubElement( newelement, "onclick" )
                    onclick.text = singleAction
        
        # Label
        label = xmltree.SubElement( newelement, "label" )
        if item[0].isdigit():
            label.text="$NUMBER[" + item[0].decode( "utf-8" ) + "]"
        else:
            try:
                label.text = item[0].decode( "utf-8" )
            except:
                label.text = item[0]
        
        # Label 2
        label2 = xmltree.SubElement( newelement, "label2" )
        if not item[1].find( "::SCRIPT::" ) == -1:
            label2.text = __language__( int( item[1][10:] ) )
        else:
            try:
                label2.text = item[1].decode( "utf-8" )
            except:
                label2.text = item[1]


        # Icon
        icon = xmltree.SubElement( newelement, "icon" )
        try:
            icon.text = item[2].decode( "utf-8" )
        except:
            icon.text = item[2]
        
        # Thumb
        thumb = xmltree.SubElement( newelement, "thumb" )
        try:
            thumb.text = item[3].decode( "utf-8" )
        except:
            thumb.text = item[3]
        
        # LabelID
        labelID = xmltree.SubElement( newelement, "property" )
        labelID.set( "name", "labelID" )
        try:
            labelID.text = item[5].decode( "utf-8" )
        except:
            labelID.text = item[5]
        
        # Group name
        group = xmltree.SubElement( newelement, "property" )
        group.set( "name", "group" )
        try:
            group.text = groupName.decode( "utf-8" )
        except:
            group.text = groupName
        
        # Submenu visibility
        if submenuVisibility is not None:
            submenuVisibilityElement = xmltree.SubElement( newelement, "property" )
            submenuVisibilityElement.set( "name", "submenuVisibility" )
            submenuVisibilityElement.text = DATA.slugify( submenuVisibility )
            
        # Visibility
        if visibilityCondition is not None:
            visibilityElement = xmltree.SubElement( newelement, "visible" )
            if profileVisibility is not None:
                visibilityElement.text = profileVisibility + " + [" + visibilityCondition + "]"
            else:
                visibilityElement.text = visibilityCondition
            issubmenuElement = xmltree.SubElement( newelement, "property" )
            issubmenuElement.set( "name", "isSubmenu" )
            issubmenuElement.text = "True"
        elif profileVisibility is not None:
            visibilityElement = xmltree.SubElement( newelement, "visible" )
            visibilityElement.text = profileVisibility
        
        # Additional properties
        if len( item[6] ) != 0:
            repr( item[6] )
            for property in item[6]:
                if property[0] == "node.visible":
                    visibleProperty = xmltree.SubElement( newelement, "visible" )
                    try:
                        visibleProperty.text = property[1].decode( "utf-8" )
                    except:
                        visibleProperty.text = property[1]
                else:
                    additionalproperty = xmltree.SubElement( newelement, "property" )
                    additionalproperty.set( "name", property[0].decode( "utf-8" ) )
                    try:
                        additionalproperty.text = property[1].decode( "utf-8" )
                    except:
                        additionalproperty.text = property[1]
                    
        return newelement
        
    def findIncludePosition( self, list, item ):
        try:
            return list.index( item )
        except:
            return None
            
            

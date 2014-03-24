# coding=utf-8
import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, xbmcaddon, urllib
import xml.etree.ElementTree as xmltree
from xml.dom.minidom import parse
from xml.sax.saxutils import escape as escapeXML
from traceback import print_exc

__addon__        = xbmcaddon.Addon()
__addonid__      = sys.modules[ "__main__" ].__addonid__
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ ).encode('utf-8')
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
        log( "Loaded xml functions" )
        
    def buildMenu( self, mainmenuID, groups, numLevels ):
        # Entry point for building includes.xml files
        if xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-isrunning" ) == "True":
            return
        
        xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-isrunning", "True" )
        
        if self.shouldwerun() == False:
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
            self.writexml( mainmenuID, groups, numLevels, progress )
            complete = True
        except:
            log( "Failed to write menu" )
            print_exc()
            complete = False
            
        
        # Clear window properties for overrides, widgets, backgrounds, properties
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-skin" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-skin-data" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-user" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-overrides-user-data" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsWidgets" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsCustomProperties" )
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcutsBackgrounds" )
        
        # Mark that we're no longer running, clear the progress dialog
        xbmcgui.Window( 10000 ).clearProperty( "skinshortcuts-isrunning" )
        progress.close()
        
        # Reload the skin
        if complete == True:
            xbmc.executebuiltin( "XBMC.ReloadSkin()" )
        else:
            xbmcgui.Dialog().ok( __addon__.getAddonInfo( "name" ), "Unable to build menu" )
        
    def shouldwerun( self ):
        log( "Checking is user has updated menu" )
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

        
        log( "Checking hashes..." )

        try:
            hashes = eval( xbmcvfs.File( os.path.join( __datapath__ , xbmc.getSkinDir() + ".hash" ) ).read() )
        except:
            # There is no hash list, return True
            print_exc()
            return True
            
        for hash in hashes:
            if hash[1] is not None:
                hasher = hashlib.md5()
                hasher.update( xbmcvfs.File( hash[0] ).read() )
                if hasher.hexdigest() != hash[1]:
                    log( "  - Hash does not match on file " + hash[0] )
                    return True
            else:
                if xbmcvfs.exists( hash[0] ):
                    log( "  - File now exists " + hash[0] )
                    return True
                
        return False
        
    def writexml( self, mainmenuID, groups, numLevels, progress ):        
        # Clear the hashlist
        hashlist.list = []

        # Create a new tree
        tree = xmltree.ElementTree( xmltree.Element( "includes" ) )
        root = tree.getroot()
        
        submenus = []
        
        if groups == "":
            # We're building the mainmenu and submenu's
            menuitems = DATA._get_shortcuts( "mainmenu", True )
            subelement = xmltree.SubElement(root, "include")
            subelement.set( "name", "skinshortcuts-mainmenu" )
            
            i = 0
            for item in menuitems:
                i += 1
                newelement = xmltree.SubElement( subelement, "item" )
                
                # Onclick
                action = urllib.unquote( item[4] )
                if action.find("::MULTIPLE::") == -1:
                    # Single action, run it
                    onclick = xmltree.SubElement( newelement, "onclick" )
                    onclick.text = escapeXML( action )
                else:
                    # Multiple actions, separated by |
                    actions = action.split( "|" )
                    for singleAction in actions:
                        if singleAction != "::MULTIPLE::":
                            onclick = xmltree.SubElement( newelement, "onclick" )
                            onclick.text = escapeXML( singleAction )
                
                # Label
                label = xmltree.SubElement( newelement, "label" )
                label.text = escapeXML( item[0] )
                
                # Label 2
                label2 = xmltree.SubElement( newelement, "label2" )
                if not item[1].find( "::SCRIPT::" ) == -1:
                    label2.text = escapeXML( __language__( int( item[1][10:] ) ) )
                else:
                    label2.text = escapeXML( item[1] )

                # Icon
                icon = xmltree.SubElement( newelement, "icon" )
                icon.text = escapeXML( item[2] )
                
                # Thumb
                thumb = xmltree.SubElement( newelement, "thumb" )
                thumb.text = escapeXML( item[3] )
                
                # LabelID
                labelID = xmltree.SubElement( newelement, "property" )
                labelID.set( "name", "labelID" )
                labelID.text = escapeXML( item[5] )
                submenus.append( item[5] )
                
                # Submenu visibility
                submenuVisibility = xmltree.SubElement( newelement, "property" )
                submenuVisibility.set( "name", "submenuVisibility" )
                submenuVisibility.text = escapeXML( DATA.slugify( item[5] ) )
                
                # Additional properties
                if len( item[6] ) != 0:
                    repr( item[6] )
                    for property in item[6]:
                        if property[0] == "node.visible":
                            visibleProperty = xmltree.SubElement( newelement, "visible" )
                            visibleProperty.text = escapeXML( property[1] )
                        else:
                            additionalproperty = xmltree.SubElement( newelement, "property" )
                            additionalproperty.set( "name", property[0] )
                            additionalproperty.text = escapeXML( property[1] )
        
        else:
            # We're building just for specific submenus, so pop these into the
            # submenu list
            groups = groups.split( "|" )
            for group in groups:
                submenus.append( group )
                
        log( repr( submenus) )
                
        # Now build the submenus
        if len(submenus) == 0:
            log( "No submenus found. Last error:" )
            try:
                print_exc()
            except:
                pass
                
        else:
            percent = 100 / ( len(submenus) * ( int( numLevels) + 1 ) )
            for level in range( 0,  int( numLevels) + 1 ):
                subelement = xmltree.SubElement(root, "include")
                if level == 0:
                    subelement.set( "name", "skinshortcuts-submenu" )
                else:
                    subelement.set( "name", "skinshortcuts-submenu-" + str( level ) )

                i = 0
                for submenu in submenus:
                    i += 1
                    progress.update( percent * i )
                    individualelement = xmltree.SubElement( root, "include" )
                    if level == 0:
                        individualelement.set( "name", "skinshortcuts-group-" + escapeXML( DATA.slugify( submenu ) ) )
                        menuitems = DATA._get_shortcuts( submenu, True )
                    else:
                        individualelement.set( "name", "skinshortcuts-group-" + escapeXML( DATA.slugify( submenu ) ) + "-" + str( level ) )
                        menuitems = DATA._get_shortcuts( submenu + "." + str( level ), True )
                    
                    
                    
                    for item in menuitems:
                        newelementA = xmltree.SubElement( subelement, "item" )
                        newelementB = xmltree.SubElement( individualelement, "item" )
                        
                        # Onclick
                        action = urllib.unquote( item[4] )
                        if action.find("::MULTIPLE::") == -1:
                            # Single action, run it
                            onclickA = xmltree.SubElement( newelementA, "onclick" )
                            onclickA.text = action
                            onclickB = xmltree.SubElement( newelementB, "onclick" )
                            onclickB.text = action
                        else:
                            # Multiple actions, separated by |
                            actions = action.split( "|" )
                            for singleAction in actions:
                                if singleAction != "::MULTIPLE::":
                                    onclickA = xmltree.SubElement( newelementA, "onclick" )
                                    onclickA.text = singleAction
                                    onclickB = xmltree.SubElement( newelementB, "onclick" )
                                    onclickB.text = singleAction
                        
                        # Label
                        labelA = xmltree.SubElement( newelementA, "label" )
                        labelA.text = item[0]
                        labelB = xmltree.SubElement( newelementB, "label" )
                        labelB.text = item[0]
                        
                        # Label 2
                        label2A = xmltree.SubElement( newelementA, "label2" )
                        label2B = xmltree.SubElement( newelementB, "label2" )
                        if not item[1].find( "::SCRIPT::" ) == -1:
                            label2A.text = __language__( int( item[1][10:] ) )
                            label2B.text = __language__( int( item[1][10:] ) )
                        else:
                            label2A.text = item[1]
                            label2B.text = item[1]

                        # Icon
                        iconA = xmltree.SubElement( newelementA, "icon" )
                        iconA.text = item[2]
                        iconB = xmltree.SubElement( newelementB, "icon" )
                        iconB.text = item[2]
                        
                        # Thumb
                        thumbA = xmltree.SubElement( newelementA, "thumb" )
                        thumbA.text = item[3]
                        thumbB = xmltree.SubElement( newelementB, "thumb" )
                        thumbB.text = item[3]
                        
                        # LabelID
                        labelIDA = xmltree.SubElement( newelementA, "property" )
                        labelIDA.set( "name", "labelID" )
                        labelIDA.text = item[5]
                        labelIDB = xmltree.SubElement( newelementB, "property" )
                        labelIDB.set( "name", "labelID" )
                        labelIDB.text = item[5]
                        
                        # Submenu visibility
                        submenuVisibility = xmltree.SubElement( newelementA, "visible" )
                        submenuVisibility.text = "StringCompare(Container(" + mainmenuID + ").ListItem.Property(submenuVisibility)," + escapeXML( DATA.slugify( submenu ) ) + ")"
                        
                        # Additional properties
                        if len( item[6] ) != 0:
                            repr( item[6] )
                            for property in item[6]:
                                if property[0] == "node.visible":
                                    visiblePropertyA = xmltree.SubElement( newelementA, "visible" )
                                    visiblePropertyA.text = property[1]
                                    visiblePropertyB = xmltree.SubElement( newelementB, "visible" )
                                    visiblePropertyB.text = property[1]
                                else:
                                    additionalpropertyA = xmltree.SubElement( newelementA, "property" )
                                    additionalpropertyA.set( "name", property[0] )
                                    additionalpropertyA.text = property[1]
                                    additionalpropertyB = xmltree.SubElement( newelementB, "property" )
                                    additionalpropertyB.set( "name", property[0] )
                                    additionalpropertyB.text = property[1]

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
        
        # Save the tree
        for path in paths:
            tree.write( path, encoding="UTF-8" )
            #tree.write( "C://temp//temp.xml", encoding="UTF-8" )
        
        # Save the hashes
        file = xbmcvfs.File( os.path.join( __datapath__ , xbmc.getSkinDir() + ".hash" ), "w" )
        file.write( repr( hashlist.list ) )
        file.close
        

        
    def findIncludePosition( self, list, item ):
        try:
            return list.index( item )
        except:
            return None
            
            

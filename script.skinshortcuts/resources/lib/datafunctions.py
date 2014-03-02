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
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)
    
class DataFunctions():
    def __init__(self):
        log( "Loaded data functions" )

    def _get_shortcuts( self, group, isXML = False ):
        # This will load the shortcut file, and save it as a window property
        # Additionally, if the override files haven't been loaded, we'll load them too
        log( "### Loading shortcuts for group " + group )
        
        if isXML == False:
            try:
                returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-" + group )
                return pickle.loads( returnVal )
            except:
                i = 1
                
        userShortcuts = os.path.join( __datapath__ , self.slugify( group ) + ".shortcuts" ).encode('utf-8')
        skinShortcuts = os.path.join( __skinpath__ , self.slugify( group ) + ".shortcuts").encode('utf-8')
        defaultShortcuts = os.path.join( __defaultpath__ , self.slugify( group ) + ".shortcuts" ).encode('utf-8')

        paths = [userShortcuts, skinShortcuts, defaultShortcuts ]
        
        for path in paths:
            try:
                # Try loading shortcuts
                #unprocessedList = eval( xbmcvfs.File( path ).read() ) 
                list = xbmcvfs.File( path ).read()
                unprocessedList = eval( list )
                self._save_hash( path, list )
                
                processedList = self._process_shortcuts( unprocessedList, group )
                
                if path == userShortcuts:
                    self._process_localised( path, unprocessedList )
                    
                if isXML == False:
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-" + group, pickle.dumps( processedList ) )
                
                log( " - Loaded file " + path ) 
                
                return processedList
            except:
                self._save_hash( path, None )
                
        # No file loaded
        log( " - No shortcuts" )
        if isXML == False:
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-" + group, pickle.dumps( [] ) )
        return [] 
                
            
    def _process_shortcuts( self, listitems, group, isXML = False ):
        # This function will process any overrides, and return a set of listitems ready to be stored
        #  - We will process graphics overrides, action overrides and any visibility conditions set
        
        tree = self._get_overrides_skin( isXML )
        usertree = self._get_overrides_user( isXML )
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
                        log( "Using localised label from " + skinName )
                except:
                    hasChanged = False
            
            # If the user hasn't overridden the thumbnail, check for skin override
            if not len(item) == 6 or (len(item) == 6 and item[5] == "True"):
                if tree is not None:
                    elems = tree.findall('thumbnail')
                    for elem in elems:
                        if elem is not None:
                            if "group" in elem.attrib:
                                if elem.attrib.get( "group" ) == group:
                                    if elem.attrib.get( 'labelID' ) == labelID:
                                        item[3] = elem.text
                                    if elem.attrib.get( 'image' ) == item[3]:
                                        item[3] = elem.text
                                    if elem.attrib.get( 'image' ) == item[2]:
                                        item[2] = elem.text
                            else:
                                if elem.attrib.get( 'labelID' ) == labelID:
                                    item[3] = elem.text
                                if elem.attrib.get( 'image' ) == item[3]:
                                    item[3] = elem.text
                                if elem.attrib.get( 'image' ) == item[2]:
                                    item[2] = elem.text
                            
            # Get additional mainmenu properties
            additionalProperties = []
                   
            widgetCheck = self.checkWidget( labelID, group )
            if widgetCheck != "":
                additionalProperties.append( ["widget", widgetCheck] )
                
            backgroundCheck = self.checkBackground( labelID, group )
            if backgroundCheck != "":
                additionalProperties.append( ["background", backgroundCheck] )
                    
            customProperties = self.checkCustomProperties( labelID, group )
            if len( customProperties ) != 0:
                for customProperty in customProperties:
                    additionalProperties.append( [customProperty[0], customProperty[1]] )
                    
            # Get action
            action = urllib.unquote( item[4] )
            
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
                        else:
                            i = 1
                            
            # If we haven't added any overrides, add the item
            if hasOverriden == False:
                if visibilityCondition != "":
                    additionalProperties.append( [ "node.visible", visibilityCondition ] )
                returnitems.append( [label, item[1], item[2], item[3], item[4], labelID, additionalProperties] )
                
        return returnitems            
        
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
                    

    def _get_overrides_skin( self, isXML = False ):
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


    def _get_overrides_user( self, isXML = False ):
        # If we haven't already loaded user overrides
        if not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user-data" ) or not xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user" ) == __profilepath__:
            xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user", __profilepath__ )
            overridepath = os.path.join( __profilepath__ , "overrides.xml" )
            try:
                tree = xmltree.parse( overridepath )
                self._save_hash( overridepath, xbmcvfs.File( overridepath ).read() )
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user-data", pickle.dumps( tree ) )
                return tree
            except:
                self._save_hash( overridepath, None )
                xbmcgui.Window( 10000 ).setProperty( "skinshortcuts-overrides-user-data", "No overrides" )
                return None
                
        # Return the overrides
        returnData = xbmcgui.Window( 10000 ).getProperty( "skinshortcuts-overrides-user-data" )
        if returnData == "No overrides":
            return None
        else:
            return pickle.loads( returnData )

    def _get_widgets( self, isXML = False ):
        # This will load the shortcut file, and save it as a window property
        # Additionally, if the override files haven't been loaded, we'll load them too
        
        try:
            returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcutsWidgets" )
            return pickle.loads( returnVal )
        except:
            # Try to load user-defined widgets
            if xbmcvfs.exists( os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".widgets" ) ):
                path = os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".widgets" )
                try:
                    # Try loading widgets
                    file = xbmcvfs.File( path ).read()
                    contents = eval( file )
                    self._save_hash( path, file )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsWidgets", pickle.dumps( contents ) )
                    return contents
                except:
                    self._save_hash( path, None )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsWidgets", pickle.dumps( [] ) )
                    return []

            else:
                # User hasn't set any widgets, so we'll load them from the
                # skins overrides.xml instead
                tree = self._get_overrides_skin( isXML )
                widgets = []
                
                if tree is not None:
                    elems = tree.findall('widgetdefault')
                    for elem in elems:
                        if "group" not in elem.attrib:
                            widgets.append( [ elem.attrib.get( 'labelID' ), elem.text, "mainmenu" ] )
                        else:
                            widgets.append( [ elem.attrib.get( 'labelID' ), elem.text, elem.attrib.get( "group" ) ] )
                
                # Save the widgets to a window property               
                xbmcgui.Window( 10000 ).setProperty( "skinshortcutsWidgets", pickle.dumps( widgets ) )
                return widgets


    def _get_customproperties( self, isXML = False ):
        # This will load the shortcut file, and save it as a window property
        # Additionally, if the override files haven't been loaded, we'll load them too
        
        try:
            returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcutsCustomProperties" )
            return pickle.loads( returnVal )
        except:
            # Try to load user-defined custom properties
            if xbmcvfs.exists( os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".customproperties" ) ):
                path = os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".customproperties" )
                try:
                    # Try loading custom properties
                    file = xbmcvfs.File( path ).read()
                    contents = eval( file )
                    self._save_hash( path, file )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsCustomProperties", pickle.dumps( contents ) )
                    return contents
                except:
                    self._save_hash( path, None )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsCustomProperties", pickle.dumps( [] ) )
                    return []

            else:
                # User hasn't set any custom properties, so we'll load them from the
                # skins overrides.xml instead
                tree = self._get_overrides_skin( isXML )
                properties = []
                
                if tree is not None:
                    elems = tree.findall('propertydefault')
                    for elem in elems:
                        if "group" not in elem.attrib:
                            properties.append( [ elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text, "mainmenu" ] )
                        else:
                            properties.append( [ elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text, elem.attrib.get( "group" ) ] )
                
                # Save the custom properties to a window property               
                xbmcgui.Window( 10000 ).setProperty( "skinshortcutsCustomProperties", pickle.dumps( properties ) )
                return properties

    def _get_backgrounds( self, isXML = False ):
        # This function will load users backgrounds settings
        try:
            returnVal = xbmcgui.Window( 10000 ).getProperty( "skinshortcutsBackgrounds" )
            return pickle.loads( returnVal )
        except:
            # Try to load user-defined widgets
            if xbmcvfs.exists( os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".backgrounds" ) ):
                path = os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".backgrounds" )
                try:
                    # Try loading widgets
                    file = xbmcvfs.File( path ).read()
                    contents = eval( file )
                    self._save_hash( path, file )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsBackgrounds", pickle.dumps( contents ) )
                    return contents
                except:
                    self._save_hash( path, None )
                    xbmcgui.Window( 10000 ).setProperty( "skinshortcutsBackgrounds", pickle.dumps( [] ) )
                    return []

            else:
                # User hasn't set any backgrounds, so we'll load them from the
                # skins overrides.xml instead
                tree = self._get_overrides_skin( isXML )
                backgrounds = []
                
                if tree is not None:
                    elems = tree.findall('backgrounddefault')
                    for elem in elems:
                        if "group" not in elem.attrib:
                            backgrounds.append( [ elem.attrib.get( 'labelID' ), elem.text, "mainmenu" ] )
                        else:
                            backgrounds.append( [ elem.attrib.get( 'labelID' ), elem.text, elem.attrib.get( "group" ) ] )
                
                # Save the widgets to a window property               
                xbmcgui.Window( 10000 ).setProperty( "skinshortcutsBackgrounds", pickle.dumps( backgrounds ) )
                return backgrounds
                
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
            
    def checkVisibility ( self, action ):
        # Return whether mainmenu items should be displayed
        if action == "ActivateWindow(Weather)":
            return "!IsEmpty(Weather.Plugin)"
        if action.startswith( "ActivateWindowAndFocus(MyPVR" ):
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
        if action == "XBMC.PlayDVD()" or action == "EjectTray()":
            return "System.HasMediaDVD"
            
        return ""
        
            
    def checkWidget( self, item, group, isXML = False ):
        # Return any widget for mainmenu items
        currentWidgets = ( self._get_widgets( isXML ) )
        
        # Loop through current widgets, looking for the current item
        for currentWidget in currentWidgets:
            if currentWidget[0].encode('utf-8') == item:
                try:
                    if currentWidget[2] == group:
                        return currentWidget[1]
                except:
                    if group == "mainmenu":
                        return currentWidget[1]
                
        return ""
        
    
    def checkBackground( self, item, group, isXML = False ):
        # Return any widget for mainmenu items
        currentBackgrounds = ( self._get_backgrounds( isXML ) )
        
        # Loop through current widgets, looking for the current item
        for currentBackground in currentBackgrounds:
            if currentBackground[0].encode('utf-8') == item:
                try:
                    if currentBackground[2] == group:
                        return currentBackground[1]
                except:
                    if group == "mainmenu":
                        return currentBackground[1]
                
        return ""
        
    
    def checkCustomProperties( self, item, group, isXML = False ):
        # Return any custom properties for mainmenu items
        currentProperties = ( self._get_customproperties( isXML ) )
        
        # Loop through current properties, looking for the current item
        returnVals = []
        for currentProperty in currentProperties:
            if currentProperty[0].encode('utf-8') == item:
                try:
                    if currentProperty[3] == group:
                        returnVals.append( [currentProperty[1], currentProperty[2]] )
                except:
                    if group == "mainmenu":
                        returnVals.append( [currentProperty[1], currentProperty[2]] )
                
        return returnVals
        
        
    def _save_hash( self, filename, file ):
        
        if file is not None:
            hasher = hashlib.md5()
            hasher.update( file )
            hashlist.list.append( [filename, hasher.hexdigest()] )
        else:
            hashlist.list.append( [filename, None] )

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

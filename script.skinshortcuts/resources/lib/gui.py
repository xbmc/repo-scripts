# coding=utf-8
import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
from xml.dom.minidom import parse
from xml.sax.saxutils import escape as escapeXML
from traceback import print_exc
from unidecode import unidecode

import datafunctions
DATA = datafunctions.DataFunctions()

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
        self.arrayXBMCCommon = []
        self.arrayVideoLibrary = []
        self.arrayMusicLibrary = []
        self.arrayPlaylists = []
        self.arrayFavourites = []
        self.arrayAddOns = []
        self.arrayMoreCommands = []
        
        self.has311 = True
        self.has312 = True
        
        self.backgroundBrowse = False
        self.widgetPlaylists = False
        self.widgetPlaylistsList = []
        
        self.changeMade = False
        self.labelIDChanges = []
        
        log('script version %s started - management module' % __addonversion__)

    def onInit( self ):
        if self.group == '':
            self._close()
        else:
            self.window_id = xbmcgui.getCurrentWindowDialogId()
            xbmcgui.Window(self.window_id).setProperty('groupname', self.group)
            
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
            
            #try:
            #    self.has402 = True
            #    if self.getControl( 402 ).getLabel() == "":
            #        self.getControl( 402 ).setLabel( __language__(32025) )
            #except:
            #    self.has402 = False
            #    log( "No label edit control on GUI" )
            #try:
            #    self.has403 = True
            #    if self.getControl( 403 ).getLabel() == "":
            #        self.getControl( 403 ).setLabel( __language__(32041) )
            #except:
            #    self.has403 = False
            #    log( "No action edit control on GUI" )
            
            # List XBMC common shortcuts (likely to be used on a main menu)
            try:
                self._load_xbmccommon()
            except:
                log( "Failed to load common XBMC shortcuts" )
                print_exc()
            
            # List video and music library shortcuts
            try:
                if self._load_videolibrary( "custom" ) == False:
                    self._load_videolibrary( "default" )
            except:
                log( "Failed to load custom video nodes" )
                print_exc()
                try:
                    self._load_videolibrary( "default" )
                except:
                    log( "Failed to load default video nodes" )
                    print_exc()
                
                
            try:
                self._load_musiclibrary()
            except:
                log( "Failed to load music library" )
                print_exc()
            
            # Load favourites, playlists, add-ons
            try:
                self._fetch_playlists()
            except:
                log( "Failed to load playlists" )
                print_exc()
            
            try:
                self._fetch_favourites()
            except:
                log( "Failed to load favourites" )
                print_exc()
                
            try:
                self._fetch_addons()
            except:
                log( "Failed to load add-ons" )
                print_exc()
                
            try:
                self._load_moreCommands()
            except:
                log( "Failed to load more XBMC commands" )
                print_exc()
            
            try:
                self._display_shortcuts()
            except:
                log( "No list of shortcuts to choose from on GUI" )
            
            # Load widget and background names
            self._load_widgetsbackgrounds()
            
            self.updateEditControls()
        
    def _load_xbmccommon( self ):
        listitems = []
        log('Listing xbmc common items...')
        
        # Videos, Movies, TV Shows, Live TV, Music, Music Videos, Pictures, Weather, Programs,
        # Play dvd, eject tray
        # Settings, File Manager, Profiles, System Info
        listitems.append( self._create(["ActivateWindow(Videos)", "::LOCAL::10006", "::SCRIPT::32034", "DefaultVideo.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieTitles,return)", "::LOCAL::342", "::SCRIPT::32034", "DefaultMovies.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,TVShowTitles,return)", "::LOCAL::20343", "::SCRIPT::32034", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,34,0 ,13,0)", "::SCRIPT::32022", "::SCRIPT::32034", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindow(Music)", "::LOCAL::10005", "::SCRIPT::32034", "DefaultMusicAlbums.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,MusicVideos,return)", "::LOCAL::20389", "::SCRIPT::32034", "DefaultMusicVideos.png"]) )
        listitems.append( self._create(["ActivateWindow(Pictures)", "::LOCAL::10002", "::SCRIPT::32034", "DefaultPicture.png"]) )
        listitems.append( self._create(["ActivateWindow(Weather)", "::LOCAL::12600", "::SCRIPT::32034", ""]) )
        listitems.append( self._create(["ActivateWindow(Programs,Addons,return)", "::LOCAL::10001", "::SCRIPT::32034", "DefaultProgram.png"]) )

        listitems.append( self._create(["XBMC.PlayDVD()", "::SCRIPT::32032", "::SCRIPT::32034", "DefaultDVDFull.png"]) )
        listitems.append( self._create(["EjectTray()", "::SCRIPT::32033", "::SCRIPT::32034", "DefaultDVDFull.png"]) )
                
        listitems.append( self._create(["ActivateWindow(Settings)", "::LOCAL::10004", "::SCRIPT::32034", ""]) )
        listitems.append( self._create(["ActivateWindow(FileManager)", "::LOCAL::7", "::SCRIPT::32034", "DefaultFolder.png"]) )
        listitems.append( self._create(["ActivateWindow(Profiles)", "::LOCAL::13200", "::SCRIPT::32034", "UnknownUser.png"]) )
        listitems.append( self._create(["ActivateWindow(SystemInfo)", "::LOCAL::10007", "::SCRIPT::32034", ""]) )
        
        listitems.append( self._create(["ActivateWindow(Favourites)", "::LOCAL::1036", "::SCRIPT::32034", ""]) )
        
        self.arrayXBMCCommon = listitems
        
    def _load_videolibrary( self, type ):
        listitems = []
        rootdir = os.path.join( xbmc.translatePath( "special://userdata".decode('utf-8') ), "library", "video" )
        if type == "custom":
            log('Listing custom video nodes...')
        else:
            rootdir = os.path.join( xbmc.translatePath( "special://xbmc".decode('utf-8') ), "system", "library", "video" )
            log( "Listing default video nodes..." )
        
        # Check the path exists
        if not os.path.exists( rootdir ):
            log( "No nodes found" )
            return False
            
        # Walk the path
        for root, subdirs, files in os.walk(rootdir):
            videonodes = {}
            unnumberedNode = 100
            label2 = "::SCRIPT::32014"
            if "index.xml" in files:
                # Parse the XML file to get the type of these nodes
                tree = xmltree.parse( os.path.join( root, "index.xml") )
                label = tree.find( 'label' )
                if label.text.isdigit():
                    label2 = "::LOCAL::" + label.text
                else:
                    label2 = label.text
            for file in files:
                if not file == "index.xml":
                    # Load the file
                    tree = xmltree.parse( os.path.join( root, file) )
                    
                    # Check for a pretty library link
                    prettyLink = self._pretty_videonode( tree, file )
                    
                    # Create the action for this file
                    if prettyLink == False:
                        path = "ActivateWindow(Videos,library://video/" + os.path.relpath( os.path.join( root, file), rootdir ) + ",return)"
                        path.replace("\\", "/")
                    else:
                        path = "ActivateWindow(Videos," + prettyLink + ",return)"
                        
                    listitem = [path]
                    
                    # Get the label
                    label = tree.find( 'label' )
                    if label is not None:
                        if label.text.isdigit():
                            listitem.append( "::LOCAL::" + label.text )
                        else:
                            listitem.append( label.text )
                    else:
                        listitem.append( "::SCRIPT::32042" )
                        
                    # Add the label2
                    listitem.append( label2 )
                    
                    # Get the icon
                    icon = tree.find( 'icon' )
                    if icon is not None:
                        listitem.append( icon.text )
                    else:
                        listitem.append( "defaultshortcut.png" )
                        
                    # Get the node 'order' value
                    order = tree.getroot()
                    try:
                        videonodes[ order.attrib.get( 'order' ) ] = listitem
                    except:
                        videonodes[ str( unnumberedNode ) ] = listitem
                        unnumberedNode = unnumberedNode + 1
                        
            for key in sorted(videonodes.iterkeys()):
                listitems.append( self._create( videonodes[ key ] ) )

        # PVR
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,32,0 ,11,0)", "::LOCAL::19023", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,33,0 ,12,0)", "::LOCAL::19024", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,31,0 ,10,0)", "::LOCAL::19069", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,34,0 ,13,0)", "::LOCAL::19163", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,35,0 ,14,0)", "::SCRIPT::32023", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        
        self.arrayVideoLibrary = listitems
        
    def _pretty_videonode( self, tree, filename ):
        # We're going to do lots of matching, to try to figure out the pretty library link
        
        # Root
        if filename == "addons.xml":
            if self._check_videonode( tree, False ):
                return "Addons"
        elif filename == "files.xml":
            if self._check_videonode( tree, False ):
                return "Files"
        # elif filename == "inprogressshows.xml": - Don't know a pretty library link for this...
        elif filename == "playlists.xml":
            if self._check_videonode( tree, False ):
                return "Playlists"
        elif filename == "recentlyaddedepisodes.xml":
            if self._check_videonode( tree, False ):
                return "RecentlyAddedEpisodes"
        elif filename == "recentlyaddedmovies.xml":
            if self._check_videonode( tree, False ):
                return "RecentlyAddedMovies"
        elif filename == "recentlyaddedmusicvideos.xml":
            if self._check_videonode( tree, False ):
                return "RecentlyAddedMusicVideos"
              
        # For the rest, they should all specify a type, so get that first
        shortcutType = self._check_videonode_type( tree )
        if shortcutType != "Custom Node":
            if filename == "actors.xml":    # Movies, TV Shows
                if self._check_videonode( tree, True ):
                    return shortcutType + "Actors"
            elif filename == "country.xml":   # Movies
                if self._check_videonode( tree, True ):
                    return shortcutType + "Countries"
            elif filename == "directors.xml": # Movies
                if self._check_videonode( tree, True ):
                    return shortcutType + "Directors"
            elif filename == "genres.xml":    # Movies, Music Videos, TV Shows
                if self._check_videonode( tree, True ):
                    return shortcutType + "Genres"
            elif filename == "sets.xml":      # Movies
                if self._check_videonode( tree, True ):
                    return shortcutType + "Sets"
            elif filename == "studios.xml":   # Movies, Music Videos, TV Shows
                if self._check_videonode( tree, True ):
                    return shortcutType + "Studios"
            elif filename == "tags.xml":      # Movies, Music Videos, TV Shows
                if self._check_videonode( tree, True ):
                    return shortcutType + "Tags"
            elif filename == "titles.xml":    # Movies, Music Videos, TV Shows
                if self._check_videonode( tree, True ):
                    return shortcutType + "Titles"
            elif filename == "years.xml":     # Movies, Music Videos, TV Shows
                if self._check_videonode( tree, True ):
                    return shortcutType + "Years"
            elif filename == "albums.xml":    # Music Videos
                if self._check_videonode( tree, True ):
                    return shortcutType + "Albums"
            elif filename == "artists.xml":   # Music Videos
                if self._check_videonode( tree, True ):
                    return shortcutType + "Artists"
            elif filename == "directors.xml": # Music Videos
                if self._check_videonode( tree, True ):
                    return shortcutType + "Directors"

        # If we get here, we couldn't find a pretty link
        return False
            
    def _check_videonode( self, tree, checkPath ):
        # Check a video node for custom entries
        if checkPath == False:
            if tree.find( 'match' ) is not None or tree.find( 'rule' ) is not None or tree.find( 'limit' ) is not None:
                return False
            else:
                return True
        else:
            if tree.find( 'match' ) is not None or tree.find( 'rule' ) is not None or tree.find( 'limit' ) is not None or tree.find( 'path' ) is not None:
                return False
            else:
                return True
                
    def _check_videonode_type( self, tree ):
        try:
            type = tree.find( 'content' ).text
            if type == "movies":
                return "Movie"
            elif type == "tvshows":
                return "TvShow"
            elif type == "musicvideos":
                return "MusicVideo"
            else:
                return "Custom Node"
        except:
            return "Custom Node"
                
    def _load_musiclibrary( self ):
        listitems = []
        log('Listing music library...')
        
        # Music
        listitems.append( self._create(["ActivateWindow(MusicFiles)", "::LOCAL::744", "::SCRIPT::32019", "DefaultFolder.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,MusicLibrary,return)", "::LOCAL::15100", "::SCRIPT::32019", "DefaultFolder.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,MusicVideos,return)", "::LOCAL::20389", "::SCRIPT::32019", "DefaultMusicVideos.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Genres,return)", "::LOCAL::135", "::SCRIPT::32019", "DefaultMusicGenres.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Artists,return)", "::LOCAL::133", "::SCRIPT::32019", "DefaultMusicArtists.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Albums,return)", "::LOCAL::132", "::SCRIPT::32019", "DefaultMusicAlbums.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Songs,return)", "::LOCAL::134", "::SCRIPT::32019", "DefaultMusicSongs.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Years,return)", "::LOCAL::652", "::SCRIPT::32019", "DefaultMusicYears.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Top100,return)", "::LOCAL::271", "::SCRIPT::32019", "DefaultMusicTop100.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Top100Songs,return)", "::LOCAL::10504", "::SCRIPT::32019", "DefaultMusicTop100Songs.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Top100Albums,return)", "::LOCAL::10505", "::SCRIPT::32019", "DefaultMusicTop100Albums.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,RecentlyAddedAlbums,return)", "::LOCAL::359", "::SCRIPT::32019", "DefaultMusicRecentlyAdded.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,RecentlyPlayedAlbums,return)", "::LOCAL::517", "::SCRIPT::32019", "DefaultMusicRecentlyPlayed.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Playlists,return)", "::LOCAL::136", "::SCRIPT::32019", "DefaultMusicPlaylists.png"]) )
        
        self.arrayMusicLibrary = listitems
        
    def _create ( self, item ):
        # Create localised label
        displayLabel = item[1]
        try:
            if not item[1].find( "::SCRIPT::" ) == -1:
                displayLabel = __language__(int( item[1][10:] ) )
            elif not item[1].find( "::LOCAL::" ) == -1:
                displayLabel = xbmc.getLocalizedString(int( item[1][9:] ) )
        except:
            print_exc()
        
        # Create localised label2
        displayLabel2 = item[2]
        try:
            if not item[2].find( "::SCRIPT::" ) == -1:
                displayLabel2 = __language__(int( item[2][10:] ) )
            elif not item[2].find( "::LOCAL::" ) == -1:
                displayLabel2 = xbmc.getLocalizedString(int( item[2][9:] ) )
        except:
            print_exc()
            
        # Build listitem
        listitem = xbmcgui.ListItem(label=displayLabel, label2=displayLabel2, iconImage="DefaultShortcut.png", thumbnailImage=item[3])
        #if not item[1].find( "::SCRIPT::" ) == -1:
        #    listitem = xbmcgui.ListItem(label=__language__(int( item[1][10:] ) ), label2=__language__( int ( item[2][10:]) ), iconImage="DefaultShortcut.png", thumbnailImage=item[3])
        #elif not item[1].find( "::LOCAL::" ) == -1:
        #    log( __language__( int ( item[2][10:]) ) )
        #    listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(int( item[1][9:] ) ), label2=__language__( int ( item[2][10:]) ), iconImage="DefaultShortcut.png", thumbnailImage=item[3])
        #else:
        #    listitem = xbmcgui.ListItem(label=xbmc.item[1], label2=__language__( int ( item[2][10:]) ), iconImage="DefaultShortcut.png", thumbnailImage=item[3])
        listitem.setProperty( "path", urllib.quote( item[0] ) )
        listitem.setProperty( "localizedString", item[1] )
        listitem.setProperty( "shortcutType", item[2] )
        listitem.setProperty( "icon", "DefaultShortcut.png" )
        listitem.setProperty( "thumbnail", item[3] )
        
        return( listitem )
        
    def _fetch_playlists( self ):
        listitems = []
        # Music Playlists
        log('Loading music playlists...')
        paths = [['special://profile/playlists/video/','32004','VideoLibrary'], ['special://profile/playlists/music/','32005','MusicLibrary'], ['special://profile/playlists/mixed/','32008','MusicLibrary']]
        for path in paths:
            try:
                dirlist = os.listdir( xbmc.translatePath( path[0] ).decode('utf-8') )
            except:
                dirlist = []
            for item in dirlist:
                playlist = os.path.join( path[0].decode( 'utf-8' ), item).encode( 'utf-8' )
                playlistfile = xbmc.translatePath( playlist ).decode( 'utf-8' )
                if item.endswith('.xsp'):
                    contents = xbmcvfs.File(playlistfile, 'r')
                    contents_data = contents.read().decode('utf-8')
                    xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                    for line in xmldata.getiterator():
                        if line.tag == "name":
                            name = line.text
                            if not name:
                                name = item[:-4]
                            log('Playlist found %s' % name)
                            # Create a list item
                            listitem = xbmcgui.ListItem(label=name, label2= __language__(int(path[1])), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                            listitem.setProperty( "path", urllib.quote( "ActivateWindow(" + path[2] + "," + playlist + ", return)" ).encode( 'utf-8' ) )
                            listitem.setProperty( "icon", "DefaultShortcut.png" )
                            listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                            listitem.setProperty( "shortcutType", "::SCRIPT::" + path[1] )
                            listitems.append(listitem)
                            
                            # Save it for the widgets list
                            self.widgetPlaylistsList.append( [playlist.decode( 'utf-8' ), "(" + __language__( int( path[1] ) ) + ") " + name] )
                            break
                elif item.endswith('.m3u'):
                    name = item[:-4]
                    log('Music playlist found %s' % name)
                    listitem = xbmcgui.ListItem(label=name, label2= __language__(32005), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                    listitem.setProperty( "path", urllib.quote( "ActivateWindow(MusicLibrary," + playlist + ", return)" ) )
                    listitem.setProperty( "icon", "DefaultShortcut.png" )
                    listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                    listitem.setProperty( "shortcutType", "::SCRIPT::" +  "32005" )
                    listitems.append(listitem)
                        
        self.arrayPlaylists = listitems
                
    def _fetch_favourites( self ):
        log('Loading favourites...')
        
        listitems = []
        listing = None
        
        fav_file = xbmc.translatePath( 'special://profile/favourites.xml' ).decode("utf-8")
        if xbmcvfs.exists( fav_file ):
            doc = parse( fav_file )
            listing = doc.documentElement.getElementsByTagName( 'favourite' )
        else:
            self.arrayFavourites = listitems
            return
            
        for count, favourite in enumerate(listing):
            name = favourite.attributes[ 'name' ].nodeValue
            path = favourite.childNodes [ 0 ].nodeValue
            if ('RunScript' not in path) and ('StartAndroidActivity' not in path):
                path = path.rstrip(')')
                path = path + ',return)'
            if 'playlists/music' in path or 'playlists/video' in path:
                thumb = "DefaultPlaylist.png"
                if self.PLAY:
                    if 'playlists/music' in path:
                        path = path.replace( 'ActivateWindow(10502,', 'PlayMedia(' )
                    else:
                        path = path.replace( 'ActivateWindow(10025,', 'PlayMedia(' )
            else:
                try:
                    thumb = favourite.attributes[ 'thumb' ].nodeValue
                except:
                    thumb = "DefaultFolder.png"
                    
            log( "Favourite found " + name + " - " + path )
            listitem = xbmcgui.ListItem(label=name, label2=__language__(32006), iconImage="DefaultShortcut.png", thumbnailImage=thumb)
            listitem.setProperty( "path", urllib.quote( path.encode( 'utf-8' ) ) )
            listitem.setProperty( "thumbnail", thumb )
            listitem.setProperty( "shortcutType", "::SCRIPT::32006" )
            listitems.append(listitem)
        
        #json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Favourites.GetFavourites", "params": { "properties": ["window", "windowparameter", "thumbnail", "path"] } }')
        #json_query = unicode(json_query, 'utf-8', errors='ignore')
        #json_response = simplejson.loads(json_query)
        #
        #listitems = []
        #
        #if json_response.has_key('result') and json_response['result'].has_key('favourites') and json_response['result']['favourites'] is not None:
        #    for item in json_response['result']['favourites']:
        #        listitem = xbmcgui.ListItem(label=item['title'], label2=__language__(32006), iconImage="DefaultShortcut.png", thumbnailImage=item['thumbnail'])
        #        
        #        # Build a path depending on the type of favourite returns
        #        if item['type'] == "window":
        #            action = 'ActivateWindow(' + item['window'] + ', ' + item['windowparameter'] + ', return)'
        #        elif item['type'] == "media":
        #            action = 'PlayMedia("' + item['path'] + '")'
        #        elif item['type'] == "script":
        #            action = 'RunScript("' + item['path'] + '")'
        #        else:
        #            if not 'path' in item.keys():
        #                break
        #            action = item['path']
        #        
        #        log( action )
        #        listitem.setProperty( "path", urllib.quote( action.encode( 'utf-8' ) ) )
        #        
        #        if not item['thumbnail'] == "":
        #            listitem.setProperty( "thumbnail", item['thumbnail'] )
        #        else:
        #            listitem.setThumbnailImage( "DefaultShortcut.png" )
        #            listitem.setProperty( "thumbnail", "DefaultShortcut.png" )
        #        
        #        listitem.setProperty( "icon", "DefaultShortcut.png" )
        #        listitem.setProperty( "shortcutType", "::SCRIPT::32006" )
        #        listitems.append(listitem)
        #
        self.arrayFavourites = listitems
        
    def _fetch_addons( self ):
        listitems = []
        log( 'Loading add-ons' )
        
        # Add links to each add-on type in library
        listitems.append( self._create(["ActivateWindow(Videos,Addons,return)", "::LOCAL::1037", "::SCRIPT::32014", "DefaultAddonVideo.png"]) )
        listitems.append( self._create(["ActivateWindow(MusicLibrary,Addons,return)", "::LOCAL::1038", "::SCRIPT::32019", "DefaultAddonMusic.png"]) )
        listitems.append( self._create(["ActivateWindow(Pictures,Addons,return)", "::LOCAL::1039", "::SCRIPT::32020", "DefaultAddonPicture.png"]) )
        listitems.append( self._create(["ActivateWindow(Programs,Addons,return)", "::LOCAL::10001", "::SCRIPT::32021", "DefaultAddonProgram.png"]) )
        
        contenttypes = ["executable", "video", "audio", "image"]
        for contenttype in contenttypes:
            if contenttype == "executable":
                contentlabel = __language__(32009)
                shortcutType = "32009"
            elif contenttype == "video":
                contentlabel = __language__(32010)
                shortcutType = "32010"
            elif contenttype == "audio":
                contentlabel = __language__(32011)
                shortcutType = "32011"
            elif contenttype == "image":
                contentlabel = __language__(32012)
                shortcutType = "32012"
                
            json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Addons.Getaddons", "params": { "content": "%s", "properties": ["name", "path", "thumbnail", "enabled"] } }' % contenttype)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            
            if json_response.has_key('result') and json_response['result'].has_key('addons') and json_response['result']['addons'] is not None:
                for item in json_response['result']['addons']:
                    if item['enabled'] == True:
                        listitem = xbmcgui.ListItem(label=item['name'], label2=contentlabel, iconImage="DefaultAddon.png", thumbnailImage=item['thumbnail'])
                        listitem.setProperty( "path", urllib.quote( "RunAddOn(" + item['addonid'].encode('utf-8') + ")" ) )
                        if item['thumbnail'] != "":
                            listitem.setProperty( "thumbnail", item['thumbnail'] )
                        else:
                            listitem.setProperty( "thumbnail", "DefaultAddon.png" )
                        
                        listitem.setProperty( "icon", "DefaultAddon.png" )
                        listitem.setProperty( "shortcutType", "::SCRIPT::" + shortcutType )
                        listitems.append(listitem)
        
        self.arrayAddOns = listitems
        
    def _load_moreCommands( self ):
        listitems = []
        log( 'Listing more XBMC commands...' )
        
        listitems.append( self._create(["Reboot", "::LOCAL::13013", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["ShutDown", "::LOCAL::13005", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["PowerDown", "::LOCAL::13016", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["Quit", "::LOCAL::13009", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["Hibernate", "::LOCAL::13010", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["Suspend", "::LOCAL::13011", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["ActivateScreensaver", "::LOCAL::360", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["Minimize", "::LOCAL::13014", "::SCRIPT::32054", ""]) )

        listitems.append( self._create(["Mastermode", "::LOCAL::20045", "::SCRIPT::32054", ""]) )
        
        listitems.append( self._create(["RipCD", "::LOCAL::600", "::SCRIPT::32054", ""]) )
        
        listitems.append( self._create(["UpdateLibrary(video)", "::SCRIPT::32046", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["UpdateLibrary(audio)", "::SCRIPT::32047", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["CleanLibrary(video)", "::SCRIPT::32055", "::SCRIPT::32054", ""]) )
        listitems.append( self._create(["CleanLibrary(audio)", "::SCRIPT::32056", "::SCRIPT::32054", ""]) )
        
        self.arrayMoreCommands = listitems
    
    def _load_widgetsbackgrounds( self ):
        self.widgets = {}
        self.backgrounds = {}
        
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
                    self.widgets[elem.text] = xbmc.getLocalizedString( int( elem.attrib.get( 'label' ) ) )
                else:
                    self.widgets[elem.text] = elem.attrib.get( 'label' )
        # Get backgrounds
        if tree is not None:
            elems = tree.findall('background')
            for elem in elems:
                if elem.attrib.get( 'label' ).isdigit():
                    self.backgrounds[elem.text] = xbmc.getLocalizedString( int( elem.attrib.get( 'label' ) ) )
                else:
                    self.backgrounds[elem.text] = elem.attrib.get( 'label' )
                    
        
        
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
            self.changeMade = True
            
            # Create a copy of the listitem
            listitemCopy = self._duplicate_listitem( self.getControl( 111 ).getSelectedItem() )
            labelID = listitemCopy.getProperty( "labelID" )
            
            # Loop through the original list, and replace the currently selected listitem with our new listitem
            listitems = []
            num = self.getControl( 211 ).getSelectedPosition()
            for x in range(0, self.getControl( 211 ).size()):
                if x == num:
                    log ( "### Found the item" )
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
            
            self.updateEditControls()
        
        if controlID == 301:
            # Add a new item
            self.changeMade = True
            
            listitem = xbmcgui.ListItem( __language__(32013) )
            listitem.setProperty( "Path", 'noop' )
            
            self.getControl( 211 ).addItem( listitem )
            
            # Set focus
            self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
            self.updateEditControls()
        
        if controlID == 302:
            # Delete an item
            self.changeMade = True
            listitems = []
            num = self.getControl( 211 ).getSelectedPosition()
            labelID = None
            
            for x in range(0, self.getControl( 211 ).size()):
                if x != num:
                    # Duplicate the item and it to the listitems array
                    listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                    listitems.append(listitemShortcutCopy)
                else:
                    labelID = self.getControl( 211 ).getListItem( num ).getProperty( "labelID" )
            
            self.getControl( 211 ).reset()
            self.getControl( 211 ).addItems(listitems)
            
            # If there are no items in the list, add an empty one...
            if self.getControl( 211 ).size() == 0:
                listitem = xbmcgui.ListItem( __language__(32013) )
                listitem.setProperty( "Path", 'noop' )
                
                self.getControl( 211 ).addItem( listitem )
                
                # Set focus
                self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
               
            if self.group == "mainmenu":
                self._remove_labelid_changes( labelID )
                
            self.updateEditControls()
            
        if controlID == 303:
            # Move item up in list
            self.changeMade = True
            
            listitems = []
            num = self.getControl( 211 ).getSelectedPosition()
            if num != 0:
                # Copy the selected item and the one above it
                listitemSelected = self._duplicate_listitem( self.getControl( 211 ).getListItem(num) )
                listitemSwap = self._duplicate_listitem( self.getControl( 211 ).getListItem(num - 1) )
                
                for x in range(0, self.getControl( 211 ).size()):
                    if x == num:
                        listitems.append(listitemSwap)
                    elif x == num - 1:
                        listitems.append(listitemSelected)
                    else:
                        listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                        listitems.append(listitemCopy)
                
                self.getControl( 211 ).reset()
                self.getControl( 211 ).addItems(listitems)
                
                self.getControl( 211 ).selectItem( num - 1 )
                
            self.updateEditControls()

        if controlID == 304:
            # Move item down in list
            self.changeMade = True
            
            listitems = []
            num = self.getControl( 211 ).getSelectedPosition()
            if num != self.getControl( 211 ).size() -1:
                # Copy the selected item and the one below it
                listitemSelected = self._duplicate_listitem( self.getControl( 211 ).getListItem(num) )
                listitemSwap = self._duplicate_listitem( self.getControl( 211 ).getListItem(num + 1) )
                
                for x in range(0, self.getControl( 211 ).size()):
                    if x == num:
                        listitems.append(listitemSwap)
                    elif x == num + 1:
                        listitems.append(listitemSelected)
                    else:
                        listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )

                        listitems.append(listitemCopy)
                
                self.getControl( 211 ).reset()
                self.getControl( 211 ).addItems(listitems)
                
                self.getControl( 211 ).selectItem( num + 1 )
                
            self.updateEditControls()

        if controlID == 305:
            # Change label
            self.changeMade = True
            
            # Retrieve properties, copy item, etc (in case the user changes focus whilst we're running)
            custom_label = self.getControl( 211 ).getSelectedItem().getLabel()
            num = self.getControl( 211 ).getSelectedPosition()
            listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )
            oldlabelID = listitemCopy.getProperty( "labelID" )
            
            if custom_label == __language__(32013):
                custom_label = ""
            keyboard = xbmc.Keyboard( custom_label, xbmc.getLocalizedString(528), False )
            keyboard.doModal()
            if ( keyboard.isConfirmed() ):
                custom_label = keyboard.getText()
                if custom_label == "":
                    custom_label = __language__(32013)
                
            # Set properties of the listitemCopy
            listitemCopy.setLabel(custom_label)
            listitemCopy.setProperty( "localizedString", "" )
            listitemCopy.setProperty( "labelID", self._get_labelID(custom_label) )
            
            # If there's no label2, set it to custom shortcut
            if not listitemCopy.getLabel2():
                listitemCopy.setLabel2( __language__(32024) )
                listitemCopy.setProperty( "shortcutType", "::SCRIPT::32024" )
            
            # Loop through the original list, and replace the currently selected listitem with our new listitem with altered label
            listitems = []
            for x in range(0, self.getControl( 211 ).size()):
                if x == num:
                    listitems.append(listitemCopy)
                else:
                    # Duplicate the item and it to the listitems array
                    listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                    
                    listitems.append(listitemShortcutCopy)
                    
            # If this is the mainmenu group, update the labelIDChanges list
            if self.group == "mainmenu":
                self._update_labelid_changes( oldlabelID, listitemCopy.getProperty( "labelID" ) )
                    
            self.getControl( 211 ).reset()
            self.getControl( 211 ).addItems(listitems)
            
            self.getControl( 211 ).selectItem( num )
            self.updateEditControls()

        if controlID == 306:
            # Change thumbnail
            self.changeMade = True
            
            # Retrieve properties, copy item, etc (in case the user changes focus)
            custom_thumbnail = self.getControl( 211 ).getSelectedItem().getProperty( "thumbnail" )
            num = self.getControl( 211 ).getSelectedPosition()
            listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )

            dialog = xbmcgui.Dialog()
            custom_thumbnail = dialog.browse( 2 , xbmc.getLocalizedString(1030), 'files')
            
            # Create a copy of the listitem
            if custom_thumbnail:
                listitemCopy.setThumbnailImage( custom_thumbnail )
                listitemCopy.setProperty( "Thumbnail", custom_thumbnail )
                listitemCopy.setProperty( "customThumbnail", "False" )
                
            # Loop through the original list, and replace the currently selected listitem with our new listitem with altered thumbnail
            listitems = []
            for x in range(0, self.getControl( 211 ).size()):
                if x == num:
                    listitems.append(listitemCopy)
                else:
                    # Duplicate the item and it to the listitems array
                    listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                    
                    listitems.append(listitemShortcutCopy)
                    
            self.getControl( 211 ).reset()
            self.getControl( 211 ).addItems(listitems)
            
            self.getControl( 211 ).selectItem( num )
            self.updateEditControls()

            
        if controlID == 307:
            # Change Action
            self.changeMade = True
            
            #Retrieve properties, copy item, etc (in case the user changes focus)
            custom_path = urllib.unquote( self.getControl( 211 ).getSelectedItem().getProperty( "path" ) )
            listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )
            num = self.getControl( 211 ).getSelectedPosition()

            if custom_path == "noop":
                custom_path = ""
            keyboard = xbmc.Keyboard( custom_path, xbmc.getLocalizedString(528), False )
            keyboard.doModal()
            if ( keyboard.isConfirmed() ):
                custom_path = keyboard.getText()
                if custom_path == "":
                    custom_path = "noop"
                    
            if not urllib.quote( custom_path ) == self.getControl( 211 ).getSelectedItem().getProperty( "path" ):
                listitemCopy.setProperty( "path", urllib.quote( custom_path ) )
                listitemCopy.setLabel2( __language__(32024) )
                listitemCopy.setProperty( "shortcutType", "::SCRIPT::32024" )
            
            # Loop through the original list, and replace the currently selected listitem with our new listitem with altered path
            listitems = []
            for x in range(0, self.getControl( 211 ).size()):
                if x == num:
                    listitems.append(listitemCopy)
                else:
                    # Duplicate the item and it to the listitems array
                    listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                    
                    listitems.append(listitemShortcutCopy)
                    
            self.getControl( 211 ).reset()
            self.getControl( 211 ).addItems(listitems)
            
            self.getControl( 211 ).selectItem( num )
            self.updateEditControls()
            
        if controlID == 308:
            # Reset shortcuts
            self.changeMade = True
            self.getControl( 211 ).reset()
            
            self.labelIDChanges = []
            
            # Set path based on existance of user defined shortcuts, then skin-provided, then script-provided
            if xbmcvfs.exists( os.path.join( __skinpath__ , urllib.quote( self.group ) + ".shortcuts" ) ):
                # Skin-provided defaults
                path = os.path.join( __skinpath__ , urllib.quote( self.group ) + ".shortcuts" )
            elif xbmcvfs.exists( os.path.join( __defaultpath__ , urllib.quote( self.group ) + ".shortcuts" ) ):
                # Script-provided defaults
                path = os.path.join( __defaultpath__ , urllib.quote( self.group ) + ".shortcuts" )
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
                        listitems.append( self._parse_listitem( item ) )
                        
                    # If we've loaded anything, save them to the list
                    if len(listitems) != 0:
                        returnItems = self._check_properties( listitems )
                        self.getControl( 211 ).addItems(returnItems)   
                        
                    # If there are no items in the list, add an empty one...
                    if self.getControl( 211 ).size() == 0:
                        listitem = xbmcgui.ListItem( __language__(32013) )
                        listitem.setProperty( "Path", 'noop' )
                        
                        self.getControl( 211 ).addItem( listitem )
                        
                        # Set focus
                        self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
                        
                    self.updateEditControls()
                except:
                    # We couldn't load the file
                    log( "### ERROR could not load file %s" % path )
                    return []
            else:
                # Add an empty item
                listitem = xbmcgui.ListItem( __language__(32013) )
                listitem.setProperty( "Path", 'noop' )
                
                self.getControl( 211 ).addItem( listitem )
                
                # Set focus
                self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
                self.updateEditControls()
                
        if controlID == 309:
            # Choose widget
            self.changeMade = True
            
            listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )
            num = self.getControl( 211 ).getSelectedPosition()
            
            # Get widgets
            widgetLabel = [__language__(32053)]
            widget = [""]         
            for key in self.widgets:
                widgetLabel.append( self.widgets[key] )
                widget.append( key )
                
            if self.widgetPlaylists == True:
                for playlist in self.widgetPlaylistsList:
                    widgetLabel.append( playlist[1] )
                    widget.append( "::PLAYLIST::" + playlist[0] )
            
            dialog = xbmcgui.Dialog()
            selectedWidget = dialog.select( __language__(32044), widgetLabel )
            
            if selectedWidget != -1:
                # Update the widget
                if selectedWidget == 0:
                    # No widget
                    self._remove_additionalproperty( listitemCopy, "widget" )
                    self._remove_additionalproperty( listitemCopy, "widgetPlaylist" )
                            
                    # Copy the item again - this will clear the widget property
                    listitemCopy = self._duplicate_listitem( listitemCopy )
                else:
                    if widget[selectedWidget].startswith( "::PLAYLIST::" ):
                        self._add_additionalproperty( listitemCopy, "widget", "Playlist" )
                        self._add_additionalproperty( listitemCopy, "widgetPlaylist", widget[selectedWidget].strip( "::PLAYLIST::" ) )

                    else:
                        self._add_additionalproperty( listitemCopy, "widget", widget[selectedWidget] )
                        self._remove_additionalproperty( listitemCopy, "widgetPlaylist" )
                    
                # Loop through the original list, and replace the currently selected listitem with our new listitem with altered label
                listitems = []
                for x in range(0, self.getControl( 211 ).size()):
                    if x == num:
                        listitems.append(listitemCopy)
                    else:
                        # Duplicate the item and it to the listitems array
                        listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                        
                        listitems.append(listitemShortcutCopy)
                        
                self.getControl( 211 ).reset()
                self.getControl( 211 ).addItems(listitems)
                
                self.getControl( 211 ).selectItem( num )
                
                self.updateEditControls()
                
        if controlID == 310:
            # Choose background
            log( "Changing background" )
            self.changeMade = True
            
            listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )
            num = self.getControl( 211 ).getSelectedPosition()
            
            # Get backgrounds
            if self.backgroundBrowse == True:
                backgroundLabel = [__language__(32050), __language__(32051), __language__(32052)]
                background = ["", "", ""]         
            else:
                backgroundLabel = [__language__(32050)]
                background = [""]                         
                
            for key in self.backgrounds:
                log( key )
                if "::PLAYLIST::" in self.backgrounds[key]:
                    for playlist in self.widgetPlaylistsList:
                        backgroundLabel.append( self.backgrounds[key].replace( "::PLAYLIST::", playlist[1] ) )
                        background.append( [ key, playlist[0], playlist[1] ] )
                else:
                    backgroundLabel.append( self.backgrounds[key] )
                    background.append( key )
            
            dialog = xbmcgui.Dialog()
            selectedBackground = dialog.select( __language__(32045), backgroundLabel )
            
            if selectedBackground != -1:
                # Update the Background
                if selectedBackground == 0:
                    # No background
                    if listitemCopy.getProperty( "additionalListItemProperties" ):
                        self._remove_additionalproperty( listitemCopy, "background" )
                        self._remove_additionalproperty( listitemCopy, "backgroundPlaylist" )
                        self._remove_additionalproperty( listitemCopy, "backgroundPlaylistName" )
                            
                    # Copy the item again - this will clear the background property
                    listitemCopy = self._duplicate_listitem( listitemCopy )
                    
                elif self.backgroundBrowse == True and (selectedBackground == 1 or selectedBackground == 2):
                    # Single image or multi-image
                    imagedialog = xbmcgui.Dialog()
                    if selectedBackground == 1:
                        custom_image = dialog.browse( 2 , xbmc.getLocalizedString(1030), 'files')
                    else:
                        custom_image = dialog.browse( 0 , xbmc.getLocalizedString(1030), 'files')
                    
                    if custom_image:
                        self._add_additionalproperty( listitemCopy, "background", custom_image )
                        self._remove_additionalproperty( listitemCopy, "backgroundPlaylist" )
                        self._remove_additionalproperty( listitemCopy, "backgroundPlaylistName" )

                else:
                    if isinstance( background[selectedBackground], list ):
                        # User has selected a playlist backgrounds
                        self._add_additionalproperty( listitemCopy, "background", background[selectedBackground][0] )
                        self._add_additionalproperty( listitemCopy, "backgroundPlaylist", background[selectedBackground][1] )
                        self._add_additionalproperty( listitemCopy, "backgroundPlaylistName", background[selectedBackground][2] )
                        
                    else:
                        # User has selected a normal background
                        self._add_additionalproperty( listitemCopy, "background", background[selectedBackground] )
                        self._remove_additionalproperty( listitemCopy, "backgroundPlaylist" )
                        self._remove_additionalproperty( listitemCopy, "backgroundPlaylistName" )
                    
                # Loop through the original list, and replace the currently selected listitem with our new listitem with altered label
                listitems = []
                for x in range(0, self.getControl( 211 ).size()):
                    if x == num:
                        listitems.append(listitemCopy)
                    else:
                        # Duplicate the item and it to the listitems array
                        listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                        
                        listitems.append(listitemShortcutCopy)
                        
                self.getControl( 211 ).reset()
                self.getControl( 211 ).addItems(listitems)
                
                self.getControl( 211 ).selectItem( num )
                
            self.updateEditControls()
        
        if controlID == 401:
            # Choose shortcut (SELECT DIALOG)
            self.changeMade = True
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
                availableShortcuts = self.arrayXBMCCommon
            elif shortcutCategory == 1: # Video Library
                availableShortcuts = self.arrayVideoLibrary
                displayLabel2 = True
            elif shortcutCategory == 2: # Music Library
                availableShortcuts = self.arrayMusicLibrary
                displayLabel2 = True
            elif shortcutCategory == 3: # Playlists
                availableShortcuts = self.arrayPlaylists
                displayLabel2 = True
            elif shortcutCategory == 4: # Favourites
                availableShortcuts = self.arrayFavourites
            elif shortcutCategory == 5: # Add-ons
                availableShortcuts = self.arrayAddOns
                displayLabel2 = True
            elif shortcutCategory == 6: # XBMC Commands
                availableShortcuts = self.arrayMoreCommands
                
                
            elif shortcutCategory != -1: # No category selected
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
                
                # Loop through the original list, and replace the currently selected listitem with our new listitem
                listitems = []
                num = self.getControl( 211 ).getSelectedPosition()
                for x in range(0, self.getControl( 211 ).size()):
                    if x == num:
                        log ( "### Found the item" )
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
                
            self.updateEditControls()
        
        #if controlID == 402:
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
            self.changeMade = True
            log( "### Setting custom property" )
            
            listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )
            num = self.getControl( 211 ).getSelectedPosition()
            
            # Retrieve window properties
            currentWindow = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
            propertyName = ""
            propertyValue = ""
            if currentWindow.getProperty( "customProperty" ):
                propertyName = currentWindow.getProperty( "customProperty" )
                currentWindow.clearProperty( "customProperty" )
            else:
                # The customProperty value needs to be set, so return
                currentWindow.clearProperty( "customValue" )
                return
                
            if currentWindow.getProperty( "customValue" ):
                propertyValue = currentWindow.getProperty( "customValue" )
                currentWindow.clearProperty( "customValue" )
                
            if propertyValue == "":
                # No value set, so remove it from additionalListItemProperties
                self._remove_additionalproperty( listitemCopy, propertyName )
            else:
                # Set the property
                self._add_additionalproperty( listitemCopy, propertyName, propertyValue )

            # Loop through the original list, and replace the currently selected listitem with our new listitem with altered label
            listitems = []
            for x in range(0, self.getControl( 211 ).size()):
                if x == num:
                    listitems.append(listitemCopy)
                else:
                    # Duplicate the item and it to the listitems array
                    listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                    
                    listitems.append(listitemShortcutCopy)
                    
            self.getControl( 211 ).reset()
            self.getControl( 211 ).addItems(listitems)
            
            self.getControl( 211 ).selectItem( num )

            
        if controlID == 405:
            # Launch management dialog for submenu
            log( "### Launching management dialog for submenu" )

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

            
    def load_shortcuts( self ):
        log( "Loading shortcuts" )
        
        # Set path based on existance of user defined shortcuts, then skin-provided, then script-provided
        loadGroup = DATA.slugify( self.group )
        if xbmcvfs.exists( os.path.join( __datapath__ , loadGroup + ".shortcuts" ) ):
            # User defined shortcuts
            path = os.path.join( __datapath__ , loadGroup + ".shortcuts" )
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
                    returnItems = self._check_properties( listitems )
                    
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
            
        log( "Added property: " + propertyName + " = " + propertyValue ) 
            
        listitem.setProperty( "additionalListItemProperties", repr( properties ) )
        
        return
        
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
        
        if len( properties ) == 0:
            if hasProperties == True:
                listitem.clearProperty( "additionalListItemProperties" )
        else:
            listitem.setProperty( "additionalListItemProperties", repr( properties ) )
            
        log( "Removed property: " + propertyName )
            
        listitem.setProperty( propertyName, None )
        
        return                
                
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
            listitem.setProperty( "path", item[4] )
            listitem.setProperty( "icon", item[2] )
            listitem.setProperty( "thumbnail", item[3] )
            listitem.setProperty( "localizedString", loadLabel )
            listitem.setProperty( "shortcutType", loadLabel2 )

        elif not loadLabel.find( "::LOCAL::" ) == -1:
            # An item with an XBMC-localized string
            listitem = xbmcgui.ListItem(label= xbmc.getLocalizedString(int( loadLabel[9:] ) ), label2=saveLabel2, iconImage=item[2], thumbnailImage=item[3])
            listitem.setProperty( "path", item[4] )
            listitem.setProperty( "icon", item[2] )
            listitem.setProperty( "thumbnail", item[3] )
            listitem.setProperty( "localizedString", loadLabel )
            listitem.setProperty( "shortcutType", loadLabel2 )
            
        else:
            # An item without a localized string
            listitem = xbmcgui.ListItem(label=item[0], label2=saveLabel2, iconImage=item[2], thumbnailImage=item[3])
            listitem.setProperty( "path", item[4] )
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
        # If the labelIDChanges list is empty, add this change
        if len(self.labelIDChanges) == 0:
            self.labelIDChanges.append( [oldlabelID, newlabelID] )
            
        else:
            # Check whether this labelID has already been changed...
            updated = False
            for labelIDChange in self.labelIDChanges:
                if labelIDChange[1] == oldlabelID:
                    updated = True
                    if labelIDChange[0] == newlabelID:
                        self.labelIDChanges.remove( labelIDChange )
                        break
                    labelIDChange[1] = newlabelID
                    break
                    
            if updated == False:
                self.labelIDChanges.append( [oldlabelID, newlabelID] )
        
    def _remove_labelid_changes( self, labelID ):
        if len(self.labelIDChanges) == 0:
            # There are no labelID changes
            return
            
        else:
            for labelIDChange in self.labelIDChanges:
                if labelIDChange[1] == labelID:
                    # This is the item, remove it
                    self.labelIDChanges.remove( labelIDChange )
                    break
        
    def _check_properties( self, listitems ):
        # Load widget, background and custom properties and add them as properties of the listitems
        dataFiles = self._load_properties()
                    
        # Check if we've loaded anything
        if len( dataFiles ) == 0:
            return listitems
            
        # Process the files we've loaded, and match any properties to listitems
        returnitems = []
        for listitem in listitems:
            # Copy this listitem
            listitemCopy = self._duplicate_listitem( listitem )
            
            # Loop through all the data we've loaded
            for dataFile in dataFiles:
                for listProperty in dataFile[0]:
                    try:
                        if listProperty[0] == listitemCopy.getProperty( "labelID" ):
                            setProperty = dataFile[1]
                            setValue = listProperty[1]
                            groupValue = listProperty[2]
                            if dataFile[1] == "custom":
                                # If we're loading custom values, the properties we'll set are slightly different...
                                setProperty = listProperty[1]
                                setValue = listProperty[2]
                                groupValue = listProperty[3]
                                
                            # Check the group matches...
                            if groupValue == self.group:
                                # Add a custom property
                                #listitemCopy.setProperty( setProperty, setValue )
                                # If there is already an additionalListItemProperties array, add this to it
                                self._add_additionalproperty( listitemCopy, setProperty, setValue )
                                #if listitemCopy.getProperty( "additionalListItemProperties" ):
                                #    listitemProperties = eval( listitemCopy.getProperty( "additionalListItemProperties" ) )
                                #    listitemProperties.append( [setProperty, setValue] )
                                #    listitemCopy.setProperty( "additionalListItemProperties", repr( listitemProperties ) )
                                #else:
                                #    # Create a new additionalListItemProperties array
                                #    listitemProperties = [[ setProperty, setValue ]]
                                #    listitemCopy.setProperty( "additionalListItemProperties", repr( listitemProperties ) )
                    except:
                        log( "Couldn't load data" )
            
            returnitems.append( listitemCopy )
            
        return returnitems
        
    
    def _load_properties( self ):
        # Load all widgets, backgrounds and custom properties
        # Load the files
        paths = [[os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".widgets" ),"widget"], [os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".backgrounds" ),"background"], [os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".customproperties" ),"custom"]]
        overrides = False
        loadedProperties = False
        dataFiles = []
        for path in paths:
            if xbmcvfs.exists( path[0] ):
                try:
                    # Try loading file
                    listProperties = eval( xbmcvfs.File( path[0] ).read() )
                    
                    loadedProperties = True
                    
                    # Check that properties have a groupname set:
                    for listProperty in listProperties:
                        if path[1] == "widget" or path[1] == "background":
                            try:
                                groupName = listProperty[2]
                            except:
                                listProperty.append( "mainmenu" )
                        else:
                            try:
                                groupName = listProperty[3]
                            except:
                                listProperty.append( "mainmenu" )

                    dataFiles.append( [listProperties, path[1]] )
                except:
                    log( "### ERROR could not load file %s" % path )   
            else:
                # Try to get defaults from skins overrides.xml
                if overrides == False:
                    # Load the overrides file
                    overridepath = os.path.join( __skinpath__ , "overrides.xml" )
                    if xbmcvfs.exists(overridepath):
                        try:
                            overrides = xmltree.fromstring( xbmcvfs.File( overridepath ).read() )
                        except:
                            overrides = "::NONE::"
                    else:
                        overrides = "::NONE::"
                        
                # If we have loaded an overrides file, get all defaults
                if overrides != "::NONE::":
                    elems = ""
                    if path[1] == "widget":
                        elems = overrides.findall('widgetdefault')
                    elif path[1] == "background":
                        elems = overrides.findall('backgrounddefault')
                    elif path[1] == "custom":
                        elems = overrides.findall('propertydefault')
                    
                    # Add each default to data array
                    data = []
                    for elem in elems:
                        if path[1] == "custom":
                            if "group" not in elem.attrib:
                                data.append( [elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text, "mainmenu" ] )
                            else:
                                data.append( [elem.attrib.get( 'labelID' ), elem.attrib.get( 'property' ), elem.text, elem.attrib.get( "group" ) ] )
                        else:
                            if "group" not in elem.attrib:
                                data.append( [ elem.attrib.get( 'labelID' ), elem.text, "mainmenu" ] )
                            else:
                                data.append( [ elem.attrib.get( 'labelID' ), elem.text, elem.attrib.get( "group" ) ] )
                                
                    if len( data ) != 0:
                        dataFiles.append( [data, path[1]] )
                        
        # Check whether we should be allowing users to browse for backgrounds, select playlists as widgets
        if overrides == False:
            # Load the overrides file
            overridepath = os.path.join( __skinpath__ , "overrides.xml" )
            if xbmcvfs.exists(overridepath):
                try:
                    overrides = xmltree.fromstring( xbmcvfs.File( overridepath ).read() )
                except:
                    overrides = "::NONE::"
            else:
                overrides = "::NONE::"
        
        if overrides != "::NONE::":
            elem = overrides.find('backgroundBrowse')
            if elem is not None and elem.text == "True":
                self.backgroundBrowse = True
            
            elem = overrides.find('widgetPlaylists')
            if elem is not None and elem.text == "True":
                self.widgetPlaylists = True
                
        return dataFiles
        
    def _duplicate_listitem( self, listitem ):
        # Create a copy of an existing listitem
        listitemCopy = xbmcgui.ListItem(label=listitem.getLabel(), label2=listitem.getLabel2(), iconImage=listitem.getProperty("icon"), thumbnailImage=listitem.getProperty("thumbnail"))
        listitemCopy.setProperty( "path", listitem.getProperty("path") )
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
        # Save widget, background and custom properties
        log( "Saving properties" )
        
        rawData = self._load_properties()
        dataFiles = {"widget":[], "background":[], "custom":[]}
        
        # Convert to dictionary
        for propertyGroup in rawData:
            dataFiles[propertyGroup[1]] = propertyGroup[0]
            
        # If there are any labelID changes, make them
        if self.group == "mainmenu":
            if len( self.labelIDChanges ) != 0:
                for dataFile in dataFiles:
                    if len( dataFiles[dataFile] ) != 0:
                        for labelIDChange in self.labelIDChanges:
                            for data in dataFiles[dataFile]:
                                if dataFile == "custom":
                                    if data[3] == DATA.slugify( labelIDChange[0] ):
                                        data[3] = DATA.slugify( labelIDChange[1] )
                                else:
                                    if data[2] == DATA.slugify( labelIDChange[0] ):
                                        data[2] = DATA.slugify( labelIDChange[1] )
        
        # Get a list of all labelID's
        labelIDList = []
        for group in properties:
            if not group[0] in labelIDList:
                labelIDList.append( group[0] )
                
        # Remove all properties from the datafiles with the current group and a matching labelID
        dataFileTypes = "custom", "background", "widget"
        for dataFileType in dataFileTypes:
            dataFile = dataFiles[dataFileType]
            if len( dataFile ) != 0:
                for currentProperty in dataFile:
                    if currentProperty[0] in labelIDList:
                        if dataFileType == "custom" and currentProperty[3] == self.group:
                            dataFile.remove( currentProperty )
                        elif currentProperty[2] == self.group:
                            dataFile.remove( currentProperty )
                            
        # Now add all properties to the datafiles
        ## [ [labelID, [property name, property value, groupName]] , [labelID, [property name, property value, groupName]] ]
        for group in properties:
            # group[0] - labelID
            # group[1] - [ [property name, property value], [] ]
            for property in group[1]:
                type = "custom"
                if property[0] == "widget":
                    type = "widget"
                elif property[0] == "background":
                    type = "background"
                    
                datafile = dataFiles[type]
                    
                if type == "custom":
                    datafile.append( [ group[0], property[0], property[1], self.group ] )
                else:
                    datafile.append( [ group[0], property[1], self.group ] )
                        
                # Update the dataFiles
                dataFiles[type] = datafile

                
        # Save the files
        paths = [[os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".widgets" ),"widget"], [os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".backgrounds" ),"background"], [os.path.join( __datapath__ , xbmc.getSkinDir().decode('utf-8') + ".customproperties" ),"custom"]]
        for path in paths:
            # Try to save the file
            try:
                f = xbmcvfs.File( path[0], 'w' )
                f.write( repr( dataFiles[path[1]] ) )
                f.close()
            except:
                print_exc()
                log( "### ERROR could not save file %s" % __datapath__ )                
    
    def _display_shortcuts( self ):
        # Load the currently selected shortcut group
        if self.shortcutgroup == 1:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayXBMCCommon)
            self.getControl( 101 ).setLabel( __language__(32029) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 2:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayVideoLibrary)
            self.getControl( 101 ).setLabel( __language__(32030) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 3:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayMusicLibrary)
            self.getControl( 101 ).setLabel( __language__(32031) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 4:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayPlaylists)
            self.getControl( 101 ).setLabel( __language__(32040) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 5:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayFavourites)
            self.getControl( 101 ).setLabel( __language__(32006) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 6:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayAddOns)
            self.getControl( 101 ).setLabel( __language__(32007) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 7:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayMoreCommands)
            self.getControl( 101 ).setLabel( __language__(32057) + " (%s)" %self.getControl( 111 ).size() )
            
    def updateEditControls( self ):
        xbmc.sleep(50)
        
        # Label edit control
        #if self.has402 == True:
        #    label = self.getControl( 211 ).getSelectedItem().getLabel()
        #    log( label )
        #    if label == __language__(32013):
        #        self.getControl( 402 ).setText( "" )
        #    else:
        #        self.getControl( 402 ).setText( label )
                
        # Action edit control
        #if self.has403 == True:
        #    label = urllib.unquote( self.getControl( 211 ).getSelectedItem().getProperty('path') )
        #    log( label )
        #    if label == "noop":
        #        self.getControl( 403 ).setText( "" )
        #    else:
        #        self.getControl( 403 ).setText( label )
                
        # Widget name
        if self.has311 == True:
            try:
                self.getControl( 311 ).setLabel( self.widgets[self.getControl( 211 ).getSelectedItem().getProperty('widget')] )
            except KeyError:
                try:
                    widgetLabel = self.getControl( 211 ).getSelectedItem().getProperty('widget')
                    if widgetLabel == "Playlist":
                        self.getControl( 311 ).setLabel( self.getControl( 211 ).getSelectedItem().getProperty('widgetPlaylist') )
                    else:
                        self.getControl( 311 ).setLabel( widgetLabel )
                except:
                    try:
                        self.getControl( 311 ).setLabel( "" )
                    except:
                        self.has311 = False
            except:
                self.has311 = False
        
        # Background name
        if self.has312 == True:
            try:
                backgroundLabel = self.getControl( 211 ).getSelectedItem().getProperty( 'background' )
                backgroundLabel = self.backgrounds[backgroundLabel]
                if "::PLAYLIST::" in backgroundLabel:
                    self.getControl( 312 ).setLabel( backgroundLabel.replace( "::PLAYLIST::", self.getControl( 211 ).getSelectedItem().getProperty( "backgroundPlaylistName" ) ) )
                else:
                    self.getControl( 312 ).setLabel( backgroundLabel )
            except KeyError:
                try:
                    self.getControl( 312 ).setLabel( "" )
                except:
                    self.has312 = False
            except:
                self.has312 = False
                
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
            
        if self.getFocusId() == 211: # User focused on currently selected shortcut
            self.updateEditControls()

    def _close( self ):
            self.close()

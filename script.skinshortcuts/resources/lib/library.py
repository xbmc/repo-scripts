# coding=utf-8
import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
from xml.dom.minidom import parse
from xml.sax.saxutils import escape as escapeXML
from traceback import print_exc
from unidecode import unidecode

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

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class LibraryFunctions():
    def __init__( self, *args, **kwargs ):
        
        # Empty arrays for different shortcut types
        self.arrayXBMCCommon = None
        self.arrayVideoLibrary = None
        self.arrayMusicLibrary = None
        self.arrayPlaylists = None
        self.widgetPlaylistsList = []
        self.arrayFavourites = None
        self.arrayAddOns = None
        self.arrayMoreCommands = None
        
    def loadLibrary( self ):
        # Load all library data, for use with threading
        self.common()
        self.more()
        self.videolibrary()
        self.musiclibrary()
        self.playlists()
        self.favourites()
        self.addons()                
        
    def common( self ):
        if isinstance( self.arrayXBMCCommon, list):
            # The List has already been populated, return it
            return self.arrayXBMCCommon
        elif self.arrayXBMCCommon == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while False:
                xbmc.sleep( 100 )
                count += 1
                if count > 10:
                    # We've waited long enough, return an empty list
                    return []
                if isinstance( self.arrayXBMCCommon, list):
                    return self.arrayXBMCCommon
        else:
            # We're going to populate the list
            self.arrayXBMCCommon = "Loading"
        
        listitems = []
        log('Listing xbmc common items...')
        
        # Videos, Movies, TV Shows, Live TV, Music, Music Videos, Pictures, Weather, Programs,
        # Play dvd, eject tray
        # Settings, File Manager, Profiles, System Info
        try:
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
        except:
            log( "Failed to load common XBMC shortcuts" )
            print_exc()
            listitems = []
            
        log( "Listing skin-provided shortcuts" )
        self._load_skinProvidedShortcuts( listitems )
        
        self.arrayXBMCCommon = listitems
        
        return self.arrayXBMCCommon

    def _load_skinProvidedShortcuts( self, listitems ):
        path = os.path.join( __skinpath__ , "overrides.xml" )
        tree = None
        if xbmcvfs.exists( path ):
            try:
                tree = xmltree.fromstring( xbmcvfs.File( path ).read().encode( 'utf-8' ) )
            except:
                log( "No skin overrides.xml file" )
        
        if tree is not None:
            elems = tree.findall('shortcut')
            for elem in elems:
                label = elem.attrib.get( "label" )
                type = elem.attrib.get( "type" )
                action = elem.text
                
                if label.isdigit():
                    label = "::LOCAL::" + label
                    
                if type.isdigit():
                    type = "::LOCAL::" + type
                
                listitems.append( self._create([action, label, type, ""]) )
                    
        return listitems
        
    def more( self ):
        if isinstance( self.arrayMoreCommands, list):
            # The List has already been populated, return it
            return self.arrayMoreCommands
        elif self.arrayMoreCommands == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while False:
                xbmc.sleep( 100 )
                count += 1
                if count > 10:
                    # We've waited long enough, return an empty list
                    return []
                if isinstance( self.arrayMoreCommands, list):
                    return self.arrayMoreCommands
        else:
            # We're going to populate the list
            self.arrayMoreCommands = "Loading"

        try:
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
        except:
            log( "Failed to load more XBMC commands" )
            print_exc()
            self.arrayMoreCommands = []
            
        return self.arrayMoreCommands
        
    def videolibrary( self ):
        if isinstance( self.arrayVideoLibrary, list):
            # The List has already been populated, return it
            return self.arrayVideoLibrary
        elif self.arrayVideoLibrary == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while False:
                xbmc.sleep( 100 )
                count += 1
                if count > 10:
                    # We've waited long enough, return an empty list
                    return []
                if isinstance( self.arrayVideoLibrary, list):
                    return self.arrayVideoLibrary
        else:
            # We're going to populate the list
            self.arrayVideoLibrary = "Loading"
            
        # Try loading custom nodes first
        try:
            if self._parse_videolibrary( "custom" ) == False:
                self._parse_videolibrary( "default" )
        except:
            log( "Failed to load custom video nodes" )
            print_exc()
            try:
                # Try loading default nodes
                self._parse_videolibrary( "default" )
            except:
                # Return empty library
                log( "Failed to load default video nodes" )
                print_exc()
                self.arrayVideoLibrary = []

                listitems = []
                
        return self.arrayVideoLibrary
        
    def _parse_videolibrary( self, type ):
        listitems = []
        rootdir = os.path.join( xbmc.translatePath( "special://profile".decode('utf-8') ), "library", "video" )
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
                
    def musiclibrary( self ):
        if isinstance( self.arrayMusicLibrary, list):
            # The List has already been populated, return it
            return self.arrayMusicLibrary
        elif self.arrayMusicLibrary == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while False:
                xbmc.sleep( 100 )
                count += 1
                if count > 10:
                    # We've waited long enough, return an empty list
                    return []
                if isinstance( self.arrayMusicLibrary, list):
                    return self.arrayMusicLibrary
        else:
            # We're going to populate the list
            self.arrayMusicLibrary = "Loading"

        try:
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
        except:
            log( "Failed to load music library" )
            print_exc()
            self.arrayMusicLibrary = []
            
        return self.arrayMusicLibrary
        
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
        listitem.setProperty( "path", urllib.quote( item[0] ) )
        listitem.setProperty( "localizedString", item[1] )
        listitem.setProperty( "shortcutType", item[2] )
        listitem.setProperty( "icon", "DefaultShortcut.png" )
        listitem.setProperty( "thumbnail", item[3] )
        
        return( listitem )
        
    def playlists( self ):
        if isinstance( self.arrayPlaylists, list):
            # The List has already been populated, return it
            return self.arrayPlaylists
        elif self.arrayPlaylists == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while False:
                xbmc.sleep( 100 )
                count += 1
                if count > 10:
                    # We've waited long enough, return an empty list
                    return []
                if isinstance( self.arrayPlaylists, list):
                    return self.arrayPlaylists
        else:
            # We're going to populate the list
            self.arrayPlaylists = "Loading"
            
        try:
            listitems = []
            # Music Playlists
            log('Loading playlists...')
            paths = [['special://profile/playlists/video/','32004','VideoLibrary'], ['special://profile/playlists/music/','32005','MusicLibrary'], ['special://profile/playlists/mixed/','32008','MusicLibrary'], [xbmc.translatePath( "special://skin/playlists/" ).decode('utf-8'),'32059',None], [xbmc.translatePath( "special://skin/extras/" ).decode('utf-8'),'32059',None]]
            for path in paths:
                count = 0
                rootpath = xbmc.translatePath( path[0] ).decode('utf-8')
                for root, subdirs, files in os.walk( rootpath ):
                    for file in files:
                        playlist = root.replace( rootpath, path[0] )
                        if not playlist.endswith( '/' ):
                            playlist = playlist + "/"
                        playlist = playlist + file
                        playlistfile = os.path.join( root, file ).decode( 'utf-8' )
                        mediaLibrary = path[2]
                        
                        if file.endswith( '.xsp' ):
                            contents = xbmcvfs.File(playlistfile, 'r')
                            contents_data = contents.read().decode('utf-8')
                            xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                            for line in xmldata.getiterator():
                                if line.tag == "smartplaylist":
                                    mediaType = line.attrib['type']
                                    if mediaType == "movies" or mediaType == "tvshows" or mediaType == "seasons" or mediaType == "episodes" or mediaType == "musicvideos" or mediaType == "sets":
                                        mediaLibrary = "VideoLibrary"
                                    elif mediaType == "albums" or mediaType == "artists" or mediaType == "songs":
                                        mediaLibrary = "MusicLibrary"                                
                                    
                                if line.tag == "name" and mediaLibrary is not None:
                                    name = line.text
                                    if not name:
                                        name = file[:-4]
                                    # Create a list item
                                    listitem = xbmcgui.ListItem(label=name, label2= __language__(int(path[1])), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                                    #listitem.setProperty( "path", urllib.quote( "ActivateWindow(" + mediaLibrary + "," + playlist + ", return)" ).encode( 'utf-8' ) )
                                    listitem.setProperty( "path", urllib.quote( "||PLAYLIST||" ) )
                                    listitem.setProperty( "action-play", urllib.quote( "PlayMedia(" + playlist + ")" ) )
                                    listitem.setProperty( "action-show", urllib.quote( "ActivateWindow(" + mediaLibrary + "," + playlist + ", return)" ).encode( 'utf-8' ) )
                                    listitem.setProperty( "icon", "DefaultShortcut.png" )
                                    listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                                    listitem.setProperty( "shortcutType", "::SCRIPT::" + path[1] )
                                    listitems.append(listitem)
                                    
                                    # Save it for the widgets list
                                    self.widgetPlaylistsList.append( [playlist.decode( 'utf-8' ), "(" + __language__( int( path[1] ) ) + ") " + name] )
                                    
                                    count += 1
                                    break
                        elif file.endswith( '.m3u' ):
                            name = file[:-4]
                            listitem = xbmcgui.ListItem(label=name, label2= __language__(32005), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                            #listitem.setProperty( "path", urllib.quote( "ActivateWindow(MusicLibrary," + playlist + ", return)" ) )
                            listitem.setProperty( "path", urllib.quote( "||PLAYLIST||" ) )
                            listitem.setProperty( "action-play", urllib.quote( "PlayMedia(" + playlist + ")" ) )
                            listitem.setProperty( "action-show", urllib.quote( "ActivateWindow(MusicLibrary," + playlist + ", return)" ).encode( 'utf-8' ) )
                            listitem.setProperty( "icon", "DefaultShortcut.png" )
                            listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                            listitem.setProperty( "shortcutType", "::SCRIPT::" +  "32005" )
                            listitems.append(listitem)
                            
                            count += 1
                            
                log( " - [" + path[0] + "] " + str( count ) + " playlists found" )
            
            self.arrayPlaylists = listitems
            
        except:
            log( "Failed to load playlists" )
            print_exc()
            self.arrayPlaylists = []
            
        return self.arrayPlaylists
                
    def favourites( self ):
        if isinstance( self.arrayFavourites, list):
            # The List has already been populated, return it
            return self.arrayFavourites
        elif self.arrayFavourites == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while False:
                xbmc.sleep( 100 )
                count += 1
                if count > 10:
                    # We've waited long enough, return an empty list
                    return []
                if isinstance( self.arrayFavourites, list):
                    return self.arrayFavourites
        else:
            # We're going to populate the list
            self.arrayFavourites = "Loading"
            
        try:
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
                if ('RunScript' not in path) and ('StartAndroidActivity' not in path) and not (path.endswith(',return)') ):
                    path = path.rstrip(')')
                    path = path + ',return)'
                else:
                    try:
                        thumb = favourite.attributes[ 'thumb' ].nodeValue
                    except:
                        thumb = "DefaultFolder.png"
                        
                listitem = xbmcgui.ListItem(label=name, label2=__language__(32006), iconImage="DefaultShortcut.png", thumbnailImage=thumb)
                listitem.setProperty( "path", urllib.quote( path.encode( 'utf-8' ) ) )
                listitem.setProperty( "thumbnail", thumb )
                listitem.setProperty( "shortcutType", "::SCRIPT::32006" )
                listitems.append(listitem)
            
            log( " - " + str( len( listitems ) ) + " favourites found" )
            
            self.arrayFavourites = listitems
            
        except:
            log( "Failed to load favourites" )
            print_exc()
            self.arrayFavourites = []
            
        return self.arrayFavourites
        
    def addons( self ):
        if isinstance( self.arrayAddOns, list):
            # The List has already been populated, return it
            return self.arrayAddOns
        elif self.arrayAddOns == "Loading":
            # The list is currently being populated, wait and then return it
            count = 0
            while False:
                xbmc.sleep( 100 )
                count += 1
                if count > 10:
                    # We've waited long enough, return an empty list
                    return []
                if isinstance( self.arrayAddOns, list):
                    return self.arrayAddOns
        else:
            # We're going to populate the list
            self.arrayAddOns = "Loading"
            
        try:
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
                            
                            # If this is a plugin, mark that we can browse it
                            if item['addonid'].startswith( "plugin." ):
                                listitem.setProperty( "path", urllib.quote( "||BROWSE||" + item['addonid'].encode('utf-8') ) )
                                listitem.setProperty( "action", urllib.quote( "RunAddOn(" + item['addonid'].encode('utf-8') + ")" ) )
                            else:
                                listitem.setProperty( "path", urllib.quote( "RunAddOn(" + item['addonid'].encode('utf-8') + ")" ) )

                            if item['thumbnail'] != "":
                                listitem.setProperty( "thumbnail", item['thumbnail'] )
                            else:
                                listitem.setProperty( "thumbnail", "DefaultAddon.png" )
                            
                            listitem.setProperty( "icon", "DefaultAddon.png" )
                            listitem.setProperty( "shortcutType", "::SCRIPT::" + shortcutType )
                            listitems.append(listitem)
            
            log( " - " + str( len( listitems ) ) + " add-ons found" )
            
            self.arrayAddOns = listitems
            
        except:
            log( "Failed to load addons" )
            print_exc()
            self.arrayAddOns = []
        
        return self.arrayAddOns
        
    def _displayShortcuts( self, skinLabel, skinAction, skinType, skinThumbnail, category, custom ):
        # This function allows the user to select a shortcut, then passes it off to the skin to do with as it will
        
        if category is not None:
            if category == "common":
                category = 0
            elif category == "video":
                category = 1
            elif category == "music":
                category = 2
            elif category == "playlists":
                category = 3
            elif category == "favourites":
                category = 4
            elif category == "addons":
                category = 5
            elif category == "commands":
                category = 6
            elif category == "custom":
                category = 7
        else:
            # No window property passed, ask the user what category they want
            shortcutCategories = [__language__(32029), __language__(32030), __language__(32031), __language__(32040), __language__(32006), __language__(32007), __language__(32057)]
            if custom == "True" or custom == "true":
                shortcutCategories.append( __language__(32027) )
            category = xbmcgui.Dialog().select( __language__(32043), shortcutCategories )
        
        # Get the shortcuts for the group the user has selected
        displayLabel2 = False
                    
        if category == 0: # Common
            availableShortcuts = self.common()
        elif category == 1: # Video Library
            availableShortcuts = self.videolibrary()
            displayLabel2 = True
        elif category == 2: # Music Library
            availableShortcuts = self.musiclibrary()
            displayLabel2 = True
        elif category == 3: # Playlists
            #    xbmc.sleep( 100 )
            availableShortcuts = self.playlists()
            displayLabel2 = True
        elif category == 4: # Favourites
            availableShortcuts = self.favourites()
        elif category == 5: # Add-ons
            availableShortcuts = self.addons()
            displayLabel2 = True
        elif category == 6: # XBMC Commands
            availableShortcuts = self.more()
            
        elif category == 7: # Custom action
            keyboard = xbmc.Keyboard( "", xbmc.getLocalizedString(528), False )
            keyboard.doModal()
            
            if ( keyboard.isConfirmed() ):
                action = keyboard.getText()
                if action != "":
                    # We're only going to update the action and type properties for this...
                    if skinAction is not None:
                        xbmc.executebuiltin( "Skin.SetString(" + skinAction + "," + action + " )" )
                    if skinType is not None:
                        xbmc.executebuiltin( "Skin.SetString(" + skinType + "," + __language__(32024) + ")" )
            
            return
            
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
        
        selectedShortcut = xbmcgui.Dialog().select( shortcutCategories[category], displayShortcuts )
        
        if selectedShortcut != -1:
            # Create a copy of the listitem
            path = urllib.unquote( availableShortcuts[selectedShortcut].getProperty( "Path" ) )
            if path.startswith( "||BROWSE||" ):
                self._browseLibrary( ["plugin://" + path.replace( "||BROWSE||", "" )], "plugin://" + path.replace( "||BROWSE||", "" ), [availableShortcuts[selectedShortcut].getLabel()], [availableShortcuts[selectedShortcut].getProperty("thumbnail")], [skinLabel, skinAction, skinType, skinThumbnail], availableShortcuts[selectedShortcut].getProperty("shortcutType")  )
                return
            elif path == "||PLAYLIST||" :
                # Give the user the choice of playing or displaying the playlist
                dialog = xbmcgui.Dialog()
                userchoice = dialog.yesno( __language__( 32040 ), __language__( 32060 ), "", "", __language__( 32061 ), __language__( 32062 ) )
                # False: Display
                # True: Play
                if userchoice == False:
                    path = urllib.unquote( availableShortcuts[selectedShortcut].getProperty( "action-show" ) )
                else:
                    path = urllib.unquote( availableShortcuts[selectedShortcut].getProperty( "action-play" ) )
                
            # Set the skin.string properties we've been passed
            if skinLabel is not None:
                log( "Setting label (" + skinLabel + ") : " + availableShortcuts[selectedShortcut].getLabel() )
                xbmc.executebuiltin( "Skin.SetString(" + skinLabel + "," + availableShortcuts[selectedShortcut].getLabel() + ")" )
            if skinAction is not None:
                log( "Setting action (" + skinAction + ") : " + path )
                xbmc.executebuiltin( "Skin.SetString(" + skinAction + "," + path + " )" )
            if skinType is not None:
                xbmc.executebuiltin( "Skin.SetString(" + skinType + "," + availableShortcuts[selectedShortcut].getLabel2() + ")" )
            if skinThumbnail is not None:
                xbmc.executebuiltin( "Skin.SetString(" + skinThumbnail + "," + availableShortcuts[selectedShortcut].getProperty( "thumbnail" ) + ")" )

                
    def _browseLibrary( self, history, location, label, thumbnail, skinStrings, itemType ):
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
                skinLabel = skinStrings[0]
                skinAction = skinStrings[1]
                skinType = skinStrings[2]
                skinThumbnail = skinStrings[3]
                
                if skinLabel is not None:
                    log( "Setting label (" + skinLabel + ") : " + label[ len( label ) - 1 ] )
                    xbmc.executebuiltin( "Skin.SetString(" + skinLabel + "," + label[ len( label ) - 1 ] + ")" )
                if skinAction is not None:
                    log( "Setting action (" + skinAction + ") : " + action )
                    xbmc.executebuiltin( "Skin.SetString(" + skinAction + "," + action + " )" )
                if skinType is not None:
                    xbmc.executebuiltin( "Skin.SetString(" + skinType + "," + itemType + ")" )
                if skinThumbnail is not None:
                    xbmc.executebuiltin( "Skin.SetString(" + skinThumbnail + "," + thumbnail[ len( thumbnail ) - 1 ] + ")" )
                    
                #listitems = []
                #for x in range(0, self.getControl( 211 ).size()):
                #    if x == itemToReplace:
                #        listitems.append( LIBRARY._create([action, label[ len( label ) - 1 ], itemType, thumbnail[ len( thumbnail ) - 1 ]]) )
                #    else:
                #        # Duplicate the item and add it to the listitems array
                #        listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                #        listitems.append(listitemShortcutCopy)
                #
                #self.getControl( 211 ).reset()
                #self.getControl( 211 ).addItems(listitems)
                #
                #self.getControl( 211 ).selectItem( itemToReplace )
                
            elif displayListActions[ selectedItem ] == "||BACK||":
                # User is going up the heirarchy, remove current level and re-call this function
                history.pop()
                label.pop()
                thumbnail.pop()
                self._browseLibrary( history, history[ len( history ) -1 ], label, thumbnail, skinStrings, itemType )
                
            else:
                # User has chosen a sub-level to display, add details and re-call this function
                history.append( displayListActions[ selectedItem ] )
                label.append( displayList[ selectedItem ] )
                thumbnail.append( displayListThumbs[ selectedItem ] )
                self._browseLibrary( history, displayListActions[ selectedItem ], label, thumbnail, skinStrings, itemType )
                

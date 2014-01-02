import os, sys, datetime, unicodedata
import xbmc, xbmcgui, xbmcvfs, urllib
import xml.etree.ElementTree as xmltree
from xml.dom.minidom import parse
from traceback import print_exc

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
        self.arrayVideoPlaylists = []
        self.arrayAudioPlaylists = []
        self.arrayFavourites = []
        self.arrayAddOns = []
        
        log('script version %s started - management module' % __addonversion__)

    def onInit( self ):
        if self.group == '':
            self._close()
        else:
            self.window_id = xbmcgui.getCurrentWindowDialogId()
            xbmcgui.Window(self.window_id).setProperty('SkinShortcuts.CurrentGroup', self.group)
            
            # Set button labels
            self.getControl( 301 ).setLabel( __language__(32000) )
            self.getControl( 302 ).setLabel( __language__(32001) )
            self.getControl( 303 ).setLabel( __language__(32002) )
            self.getControl( 304 ).setLabel( __language__(32003) )
            self.getControl( 305 ).setLabel( __language__(32025) )
            self.getControl( 306 ).setLabel( __language__(32026) )
            self.getControl( 307 ).setLabel( __language__(32027) )
            self.getControl( 308 ).setLabel( __language__(32028) )
            
            # List XBMC common shortcuts (likely to be used on a main menu
            self._load_xbmccommon()
            
            # List video and music library shortcuts
            self._load_videolibrary()
            self._load_musiclibrary()
            
            # Load favourites, playlists, add-ons
            self._fetch_videoplaylists()
            self._fetch_musicplaylists()
            self._fetch_favourites()
            self._fetch_addons()
            
            self._display_shortcuts()
            
            # Load current shortcuts
            self.load_shortcuts()
        
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
        
        self.arrayXBMCCommon = listitems
        
    def _load_videolibrary( self ):
        listitems = []
        log('Listing video library...')
        
        # Videos
        listitems.append( self._create(["ActivateWindow(Videos,Movies,return)", "::LOCAL::342", "::SCRIPT::32014", "DefaultMovies.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,TVShows,return)", "::LOCAL::20343", "::SCRIPT::32014", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,34,0 ,13,0)", "::SCRIPT::32022", "::SCRIPT::32014", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideos,return)", "::LOCAL::20389", "::SCRIPT::32014", "DefaultMusicVideos.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,Files,return)", "::LOCAL::744", "::SCRIPT::32014", "DefaultFolder.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,Playlists,return)", "::LOCAL::136", "::SCRIPT::32014", "DefaultVideoPlaylists.png"]) )
        
        # Movies
        listitems.append( self._create(["ActivateWindow(Videos,RecentlyAddedMovies,return)", "::LOCAL::20386", "::SCRIPT::32015", "DefaultRecentlyAddedMovies.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieActors,return)", "::LOCAL::344", "::SCRIPT::32015", "DefaultActor.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieCountries,return)", "::LOCAL::20451", "::SCRIPT::32015", "DefaultCountry.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieDirectors,return)", "::LOCAL::20348", "::SCRIPT::32015", "DefaultDirector.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieGenres,return)", "::LOCAL::135", "::SCRIPT::32015", "DefaultGenre.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieSets,return)", "::LOCAL::20434", "::SCRIPT::32015", "DefaultSets.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieStudios,return)", "::LOCAL::20388", "::SCRIPT::32015", "DefaultStudios.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieTags,return)", "::LOCAL::20459", "::SCRIPT::32015", "DefaultTags.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieTitles,return)", "::LOCAL::369", "::SCRIPT::32015", "DefaultMovieTitle.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MovieYears,return)", "::LOCAL::562", "::SCRIPT::32015", "DefaultYear.png"]) )

        # TV Shows
        listitems.append( self._create(["ActivateWindow(Videos,RecentlyAddedEpisodes,return)", "::LOCAL::20387", "::SCRIPT::32016", "DefaultRecentlyAddedEpisodes.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,TVShowActors,return)", "::LOCAL::344", "::SCRIPT::32016", "DefaultActor.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,TVShowGenres,return)", "::LOCAL::135", "::SCRIPT::32016", "DefaultGenre.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,TVShowStudios,return)", "::LOCAL::20388", "::SCRIPT::32016", "DefaultStudios.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,TVShowTags,return)", "::LOCAL::20459", "::SCRIPT::32016", "DefaultTags.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,TVShowTitles,return)", "::LOCAL::369", "::SCRIPT::32016", "DefaultTVShowTitle.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,TVShowYears,return)", "::LOCAL::562", "::SCRIPT::32016", "DefaultYear.png"]) )

        # PVR
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,32,0 ,11,0)", "::LOCAL::19023", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,33,0 ,12,0)", "::LOCAL::19024", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,31,0 ,10,0)", "::LOCAL::19069", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,34,0 ,13,0)", "::LOCAL::19163", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        listitems.append( self._create(["ActivateWindowAndFocus(MyPVR,35,0 ,14,0)", "::SCRIPT::32023", "::SCRIPT::32017", "DefaultTVShows.png"]) )
        
        # Music Videos
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideoAlbums,return)", "::LOCAL::20389", "::SCRIPT::32018", "DefaultMusicVideos.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideoArtists,return)", "::LOCAL::133", "::SCRIPT::32018", "DefaultMusicArtists.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideoDirectors,return)", "::LOCAL::20348", "::SCRIPT::32018", "DefaultDirector.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideoGenres,return)", "::LOCAL::135", "::SCRIPT::32018", "DefaultMusicGenres.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideoStudios,return)", "::LOCAL::20388", "::SCRIPT::32018", "DefaultStudios.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideoTags,return)", "::LOCAL::20459", "::SCRIPT::32018", "DefaultTags.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideoTitles,return)", "::LOCAL::369", "::SCRIPT::32018", "DefaultMusicVideoTitle.png"]) )
        listitems.append( self._create(["ActivateWindow(Videos,MusicVideoYears,return)", "::LOCAL::562", "::SCRIPT::32018", "DefaultMusicYears.png"]) )
        
        self.arrayVideoLibrary = listitems
                
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
        if not item[1].find( "::SCRIPT::" ) == -1:
            listitem = xbmcgui.ListItem(label=__language__(int( item[1][10:] ) ), label2=__language__( int ( item[2][10:]) ), iconImage="DefaultShortcut.png", thumbnailImage=item[3])
        elif not item[1].find( "::LOCAL::" ) == -1:
            listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(int( item[1][9:] ) ), label2=__language__( int ( item[2][10:]) ), iconImage="DefaultShortcut.png", thumbnailImage=item[3])
        else:
            listitem = xbmcgui.ListItem(label=xbmc.item[1], label2=__language__( int ( item[2][10:]) ), iconImage="DefaultShortcut.png", thumbnailImage=item[3])
        listitem.setProperty( "path", urllib.quote( item[0] ) )
        listitem.setProperty( "localizedString", item[1] )
        listitem.setProperty( "shortcutType", item[2] )
        listitem.setProperty( "icon", "DefaultShortcut.png" )
        listitem.setProperty( "thumbnail", item[3] )
        
        return( listitem )
        
    def _fetch_videoplaylists( self ):
        listitems = []
        log('Loading playlists...')
        path = 'special://profile/playlists/video/'
        try:
            dirlist = os.listdir( xbmc.translatePath( path ).decode('utf-8') )
        except:
            dirlist = []
        for item in dirlist:
            playlist = os.path.join( path, item)
            playlistfile = xbmc.translatePath( playlist )
            if item.endswith('.xsp'):
                contents = xbmcvfs.File(playlistfile, 'r')
                contents_data = contents.read().decode('utf-8')
                xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                for line in xmldata.getiterator():
                    if line.tag == "name":
                        name = line.text
                        if not name:
                            name = item[:-4]
                        log('Video playlist found %s' % name)
                        listitem = xbmcgui.ListItem(label=name, label2=__language__(32004), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                        listitem.setProperty( "path", urllib.quote( "ActivateWindow(VideoLibrary," + playlist + ", return)" ) )
                        listitem.setProperty( "icon", "DefaultShortcut.png" )
                        listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                        listitem.setProperty( "shortcutType", "::SCRIPT::" +  "32004" )
                        listitems.append(listitem)
                        break
            elif item.endswith('.m3u'):
                name = item[:-4]
                log('Video playlist found %s' % name)
                listitem = xbmcgui.ListItem(label=name, label2= __language__(32004), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                listitem.setProperty( "path", urllib.quote( "ActivateWindow(MusicLibrary," + playlist + ", return)" ) )
                listitem.setProperty( "icon", "DefaultShortcut.png" )
                listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                listitem.setProperty( "shortcutType", "::SCRIPT::" +  "32004" )
                listitems.append(listitem)
                
        self.arrayVideoPlaylists = listitems

    def _fetch_musicplaylists( self ):
        listitems = []
        # Music Playlists
        log('Loading music playlists...')
        path = 'special://profile/playlists/music/'
        try:
            dirlist = os.listdir( xbmc.translatePath( path ).decode('utf-8') )
        except:
            dirlist = []
        for item in dirlist:
            playlist = os.path.join( path, item)
            playlistfile = xbmc.translatePath( playlist )
            if item.endswith('.xsp'):
                contents = xbmcvfs.File(playlistfile, 'r')
                contents_data = contents.read().decode('utf-8')
                xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                for line in xmldata.getiterator():
                    if line.tag == "name":
                        name = line.text
                        if not name:
                            name = item[:-4]
                        log('Music playlist found %s' % name)
                        listitem = xbmcgui.ListItem(label=name, label2= __language__(32005), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                        listitem.setProperty( "path", urllib.quote( "ActivateWindow(MusicLibrary," + playlist + ", return)" ) )
                        listitem.setProperty( "icon", "DefaultShortcut.png" )
                        listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                        listitem.setProperty( "shortcutType", "::SCRIPT::" +  "32005" )
                        listitems.append(listitem)
                        break
            elif item.endswith('.m3u'):
                name = item[:-4]
                log('Music playlist found %s' % name)
                listitem = xbmcgui.ListItem(label=name, label2= __language__(32005), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                listitem.setProperty( urllib.quote( "path", "ActivateWindow(MusicLibrary," + playlist + ", return)" ) )
                listitem.setProperty( "icon", "DefaultShortcut.png" )
                listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                listitem.setProperty( "shortcutType", "::SCRIPT::" +  "32005" )
                listitems.append(listitem)
                
        # Mixed Playlists
        log('Loading mixed playlists...')
        path = 'special://profile/playlists/mixed/'
        try:
            dirlist = os.listdir( xbmc.translatePath( path ).decode('utf-8') )
        except:
            dirlist = []
        for item in dirlist:
            playlist = os.path.join( path, item)
            playlistfile = xbmc.translatePath( playlist )
            if item.endswith('.xsp'):
                contents = xbmcvfs.File(playlistfile, 'r')
                contents_data = contents.read().decode('utf-8')
                xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                for line in xmldata.getiterator():
                    if line.tag == "name":
                        name = line.text
                        if not name:
                            name = item[:-4]
                        log('Music playlist found %s' % name)
                        listitem = xbmcgui.ListItem(label=name, label2= __language__(32008), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                        listitem.setProperty( "path", urllib.quote( "ActivateWindow(MusicLibrary," + playlist + ", return)" ) )
                        listitem.setProperty( "icon", "DefaultShortcut.png" )
                        listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                        listitem.setProperty( "shortcutType", "::SCRIPT::" +  "32008" )
                        listitems.append(listitem)
                        break
            elif item.endswith('.m3u'):
                name = item[:-4]
                log('Music playlist found %s' % name)
                listitem = xbmcgui.ListItem(label=name, label2= __language__(32008), iconImage='DefaultShortcut.png', thumbnailImage='DefaultPlaylist.png')
                listitem.setProperty( "path", urllib.quote( "ActivateWindow(MusicLibrary," + playlist + ", return)" ) )
                listitem.setProperty( "icon", "DefaultShortcut.png" )
                listitem.setProperty( "thumbnail", "DefaultPlaylist.png" )
                listitem.setProperty( "shortcutType", "::SCRIPT::" +  "32008" )
                listitems.append(listitem)
        
        self.arrayAudioPlaylists = listitems
                
    def _fetch_favourites( self ):
        log('Loading favourites...')
        
        json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Favourites.GetFavourites", "params": { "properties": ["path", "thumbnail", "window", "windowparameter"] } }')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        
        listitems = []
        
        if json_response.has_key('result') and json_response['result'].has_key('favourites') and json_response['result']['favourites'] is not None:
            for item in json_response['result']['favourites']:
                listitem = xbmcgui.ListItem(label=item['title'], label2=__language__(32006), iconImage="DefaultShortcut.png", thumbnailImage=item['thumbnail'])
                
                # Build a path depending on the type of favourite returns
                if item['type'] == "window":
                    action = 'ActivateWindow(' + item['window'] + ', ' + item['windowparameter'] + ', return)'
                elif item['type'] == "media":
                    log( " - This is media" )
                    action = 'PlayMedia("' + item['path'] + '")'
                elif item['type'] == "script":
                    action = 'RunScript("' + item['path'] + '")'
                else:
                    action = item['path']
                
                log( action )
                listitem.setProperty( "path", urllib.quote( action ) )
                
                if not item['thumbnail'] == "":
                    listitem.setProperty( "thumbnail", item['thumbnail'] )
                else:
                    listitem.setThumbnailImage( "DefaultShortcut.png" )
                    listitem.setProperty( "thumbnail", "DefaultShortcut.png" )
                
                listitem.setProperty( "icon", "DefaultShortcut.png" )
                listitem.setProperty( "shortcutType", "::SCRIPT::32006" )
                listitems.append(listitem)
        
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
                        listitem.setProperty( "path", urllib.quote( "RunAddOn(" + item['addonid'] + ")" ) )
                        if item['thumbnail'] != "":
                            listitem.setProperty( "thumbnail", item['thumbnail'] )
                        else:
                            listitem.setProperty( "thumbnail", "DefaultAddon.png" )
                        
                        listitem.setProperty( "icon", "DefaultAddon.png" )
                        listitem.setProperty( "shortcutType", "::SCRIPT::" + shortcutType )
                        listitems.append(listitem)
        
        self.arrayAddOns = listitems
        
    def onAction(self, action):
        if action.getId() in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.close()
        
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
            # Create a copy of the listitem
            listitemCopy = self._duplicate_listitem( self.getControl( 111 ).getSelectedItem() )
            
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
        
        if controlID == 301:
            # Add a new item
            listitem = xbmcgui.ListItem( __language__(32013) )
            listitem.setProperty( "Path", 'noop' )
            
            self.getControl( 211 ).addItem( listitem )
            
            # Set focus
            self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
        
        if controlID == 302:
            # Delete an item
            listitems = []
            num = self.getControl( 211 ).getSelectedPosition()
            
            for x in range(0, self.getControl( 211 ).size()):
                if x != num:
                    # Duplicate the item and it to the listitems array
                    listitemShortcutCopy = self._duplicate_listitem( self.getControl( 211 ).getListItem(x) )
                    listitems.append(listitemShortcutCopy)
            
            self.getControl( 211 ).reset()
            self.getControl( 211 ).addItems(listitems)
            
            # If there are no items in the list, add an empty one...
            if self.getControl( 211 ).size() == 0:
                listitem = xbmcgui.ListItem( __language__(32013) )
                listitem.setProperty( "Path", 'noop' )
                
                self.getControl( 211 ).addItem( listitem )
                
                # Set focus
                self.getControl( 211 ).selectItem( self.getControl( 211 ).size() -1 )
            
        if controlID == 303:
            # Move item up in list
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

        if controlID == 304:
            # Move item down in list
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

        if controlID == 305:
            # Change label
            
            # Retrieve properties, copy item, etc (in case the user changes focus whilst we're running)
            custom_label = self.getControl( 211 ).getSelectedItem().getLabel()
            num = self.getControl( 211 ).getSelectedPosition()
            listitemCopy = self._duplicate_listitem( self.getControl( 211 ).getSelectedItem() )
            
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
                    
            self.getControl( 211 ).reset()
            self.getControl( 211 ).addItems(listitems)
            
            self.getControl( 211 ).selectItem( num )

        if controlID == 306:
            # Change thumbnail
            
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

            
        if controlID == 307:
            # Change path
            
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
            
        if controlID == 308:
            # Reset shortcuts
            self.getControl( 211 ).reset()
            
            # Set path based on existance of user defined shortcuts, then skin-provided, then script-provided
            if xbmcvfs.exists( os.path.join( __skinpath__ , self.group + ".shortcuts" ) ):
                # Skin-provided defaults
                path = os.path.join( __skinpath__ , self.group + ".shortcuts" )
            elif xbmcvfs.exists( os.path.join( __defaultpath__ , self.group + ".shortcuts" ) ):
                # Script-provided defaults
                path = os.path.join( __defaultpath__ , self.group + ".shortcuts" )
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
                        self.getControl( 211 ).addItems(listitems)
                    
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
            
    def load_shortcuts( self ):
        log( "Loading shortcuts" )
        
        # Set path based on existance of user defined shortcuts, then skin-provided, then script-provided
        if xbmcvfs.exists( os.path.join( __datapath__ , self.group + ".shortcuts" ) ):
            # User defined shortcuts
            path = os.path.join( __datapath__ , self.group + ".shortcuts" )
        elif xbmcvfs.exists( os.path.join( __skinpath__ , self.group + ".shortcuts" ) ):
            # Skin-provided defaults
            path = os.path.join( __skinpath__ , self.group + ".shortcuts" )
        elif xbmcvfs.exists( os.path.join( __defaultpath__ , self.group + ".shortcuts" ) ):
            # Script-provided defaults
            path = os.path.join( __defaultpath__ , self.group + ".shortcuts" )
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
                    self.getControl( 211 ).addItems(listitems)
                
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
        
                
    def _parse_listitem( self, item ):
        # Parse a loaded listitem, replacing ::SCRIPT:: or ::LOCAL:: with localized strings
        loadLabel = item[0]
        loadLabel2 = item[1]
        saveLabel2 = item[1]

        if not loadLabel2.find( "::SCRIPT::" ) == -1:
            saveLabel2 = __language__( int ( loadLabel2[10:] ) )
        
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
            
        return listitem
            
    def _duplicate_listitem( self, listitem ):
        # Create a copy of an existing listitem
        listitemCopy = xbmcgui.ListItem(label=listitem.getLabel(), label2=listitem.getLabel2(), iconImage=listitem.getProperty("icon"), thumbnailImage=listitem.getProperty("thumbnail"))
        listitemCopy.setProperty( "path", listitem.getProperty("path") )
        listitemCopy.setProperty( "icon", listitem.getProperty("icon") )
        listitemCopy.setProperty( "thumbnail", listitem.getProperty("thumbnail") )
        listitemCopy.setProperty( "localizedString", listitem.getProperty("localizedString") )
        listitemCopy.setProperty( "shortcutType", listitem.getProperty("shortcutType") )
        if listitem.getProperty( "customThumbnail" ):
            listitemCopy.setProperty( "customThumbnail", listitem.getProperty( "customThumbnail" ) )
        return listitemCopy
        
    def _save_shortcuts( self ):
        # Save shortcuts
        log( "Saving shortcuts" )
        listitems = []
        
        for x in range(0, self.getControl( 211 ).size()):
            # If the item has a path, push it to an array
            listitem = self.getControl( 211 ).getListItem(x)
            
            if listitem.getLabel() != __language__(32013):
                saveLabel = listitem.getLabel()
                saveLabel2 = listitem.getLabel2()
                
                if listitem.getProperty( "localizedString" ):
                    saveLabel = listitem.getProperty( "localizedString" )
                    
                if listitem.getProperty( "customThumbnail" ):
                    savedata=[saveLabel, listitem.getProperty("shortcutType"), listitem.getProperty("icon"), listitem.getProperty("thumbnail"), listitem.getProperty("path"), listitem.getProperty("customThumbnail")]
                else:
                    savedata=[saveLabel, listitem.getProperty("shortcutType"), listitem.getProperty("icon"), listitem.getProperty("thumbnail"), listitem.getProperty("path")]
                    
                listitems.append(savedata)
        
        path = os.path.join( __datapath__ , self.group + ".shortcuts" )
        
        if listitems:
            # If there are any shortcuts, save them
            try:
                f = xbmcvfs.File( path, 'w' )
                f.write( repr( listitems ) )
                f.close()
            except:
                print_exc()
                log( "### ERROR could not save file %s" % __datapath__ )
        else:
            # There are no shortcuts, delete the existing file if it exists
            try:
                xbmcvfs.delete( path )
            except:
                print_exc()
                log( "### No shortcuts, no existing file %s" % __datapath__ )            
    
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
            self.getControl( 111 ).addItems(self.arrayVideoPlaylists)
            self.getControl( 101 ).setLabel( __language__(32004) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 5:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayAudioPlaylists)
            self.getControl( 101 ).setLabel( __language__(32005) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 6:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayFavourites)
            self.getControl( 101 ).setLabel( __language__(32006) + " (%s)" %self.getControl( 111 ).size() )
        if self.shortcutgroup == 7:
            self.getControl( 111 ).reset()
            self.getControl( 111 ).addItems(self.arrayAddOns)
            self.getControl( 101 ).setLabel( __language__(32007) + " (%s)" %self.getControl( 111 ).size() )
            
                
    def onAction( self, action ):
        if action.getId() in ACTION_CANCEL_DIALOG:
            self._save_shortcuts()
            self._close()

    def _close( self ):
            log('Gui closed')
            self.close()

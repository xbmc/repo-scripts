# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# *  For more information on it's use please check -
# *  http://forum.xbmc.org/showthread.php?t=79378
# *
# *  Thanks to:
# *
# *  Nuka for the original RecentlyAdded.py on which this is based
# *
# *  ppic, Hitcher & ronie for the updates

import xbmc, xbmcgui, xbmcaddon
import re, sys, os, random
import xml.dom.minidom
from urllib import quote_plus, unquote_plus

__cwd__ = xbmcaddon.Addon().getAddonInfo('path')


class Main:
    # grab the home window
    WINDOW = xbmcgui.Window( 10000 )

    def _clear_properties( self ):
        # reset totals property for visible condition
        self.WINDOW.clearProperty( "Addons.Count" )
        # we enumerate thru and clear individual properties in case other scripts set window properties
        for count in range( self.LIMIT ):
            # we clear title for visible condition
            self.WINDOW.clearProperty( "RandomMovie.%d.Title" % ( count + 1, ) )
            self.WINDOW.clearProperty( "RandomEpisode.%d.ShowTitle" % ( count + 1, ) )
            self.WINDOW.clearProperty( "RandomSong.%d.Title" % ( count + 1, ) )
            self.WINDOW.clearProperty( "RandomSong.%d.Album" % ( count + 1, ) )
            self.WINDOW.clearProperty( "RandomAddon.%d.Name" % ( count + 1, ) )

    def _get_media( self, path, file ):
        # set default values
        play_path = fanart_path = thumb_path = path + file
        # we handle stack:// media special
        if ( file.startswith( "stack://" ) ):
            play_path = fanart_path = file
            thumb_path = file[ 8 : ].split( " , " )[ 0 ]
        # we handle rar:// and zip:// media special
        if ( file.startswith( "rar://" ) or file.startswith( "zip://" ) ):
            play_path = fanart_path = thumb_path = file
        # return media info
        return xbmc.getCacheThumbName( thumb_path ), xbmc.getCacheThumbName( fanart_path ), play_path

    def _parse_argv( self ):
        try:
            # parse sys.argv for params
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            # no params passed
            params = {}
        # set our preferences
        self.LIMIT = int( params.get( "limit", "5" ) )
        self.ALBUMS = params.get( "albums", "" ) == "True"
        self.UNPLAYED = params.get( "unplayed", "" ) == "True"
        self.PLAY_TRAILER = params.get( "trailer", "" ) == "True"
        self.ALARM = int( params.get( "alarm", "0" ) )
        self.RANDOM_ORDER = "True"
        self.ALBUMID = params.get( "albumid", "" )

    def _set_alarm( self ):
        # only run if user/skinner preference
        if ( not self.ALARM ): return
        # set the alarms command
        command = "XBMC.RunScript(%s,limit=%d&albums=%s&unplayed=%s&trailer=%s&alarm=%d)" % ( os.path.join( xbmc.translatePath(__cwd__), __file__ ), self.LIMIT, str( self.ALBUMS ), str( self.UNPLAYED ), str( self.PLAY_TRAILER ), self.ALARM, )
        xbmc.executebuiltin( "AlarmClock(RandomItems,%s,%d,true)" % ( command, self.ALARM, ) )

    def __init__( self ):
        # parse argv for any preferences
        self._parse_argv()
        # format our records start and end
        xbmc.executehttpapi( "SetResponseFormat()" )
        xbmc.executehttpapi( "SetResponseFormat(OpenRecord,%s)" % ( "<record>", ) )
        xbmc.executehttpapi( "SetResponseFormat(CloseRecord,%s)" % ( "</record>", ) )
        # check if we were executed internally
        print self.ALBUMID
        if self.ALBUMID:
            self._Play_Album( self.ALBUMID )
        else:
            # clear properties
            self._clear_properties()
            # set any alarm
            self._set_alarm()
            # fetch media info
            self._fetch_movie_info()
            self._fetch_tvshow_info()
            self._fetch_music_info()
            self._fetch_addon_info()

    def _fetch_movie_info( self ):
        # set our unplayed query
        unplayed = ( "", "where playCount is null ", )[ self.UNPLAYED ]
        # sql statement
        if ( self.RANDOM_ORDER ):
            # random order
            sql_movies = "select * from movieview %sorder by RANDOM() limit %d" % ( unplayed, self.LIMIT, )
        else:
            # movies not finished
            sql_movies = "select movieview.*, bookmark.timeInSeconds from movieview join bookmark on (movieview.idFile = bookmark.idFile) %sorder by movieview.c00 limit %d" % ( unplayed, self.LIMIT, )
        # query the database
        movies_xml = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % quote_plus( sql_movies ), )
        # separate the records
        movies = re.findall( "<record>(.+?)</record>", movies_xml, re.DOTALL )
        # enumerate thru our records and set our properties
        for count, movie in enumerate( movies ):
            # separate individual fields
            fields = re.findall( "<field>(.*?)</field>", movie, re.DOTALL )
            # set properties

            self.WINDOW.setProperty( "RandomMovie.%d.Title" % ( count + 1, ), fields[ 2 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Rating" % ( count + 1, ), "%.1f" % float(fields[ 7 ]) )
            self.WINDOW.setProperty( "RandomMovie.%d.Year" % ( count + 1, ), fields[ 9 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Plot" % ( count + 1, ), fields[ 3 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.RunningTime" % ( count + 1, ), fields[ 13 ] )
            # get cache names of path to use for thumbnail/fanart and play path
            thumb_cache, fanart_cache, play_path = self._get_media( fields[ 27 ], fields[ 26 ] )
            if os.path.isfile("%s.dds" % (xbmc.translatePath( "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", os.path.splitext(fanart_cache)[0],) ) )):
                fanart_cache = "%s.dds" % (os.path.splitext(fanart_cache)[0],)
            self.WINDOW.setProperty( "RandomMovie.%d.Path" % ( count + 1, ), ( play_path, fields[ 21 ], )[ fields[ 21 ] != "" and self.PLAY_TRAILER ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Trailer" % ( count + 1, ), fields[ 21 ] )
            self.WINDOW.setProperty( "RandomMovie.%d.Fanart" % ( count + 1, ), "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", fanart_cache, ) )
            # initial thumb path
            thumb = "special://profile/Thumbnails/Video/%s/%s" % ( thumb_cache[ 0 ], thumb_cache, )
            # if thumb does not exist use an auto generated thumb path
            if ( not os.path.isfile( xbmc.translatePath( thumb ) ) ):
                thumb = "special://profile/Thumbnails/Video/%s/auto-%s" % ( thumb_cache[ 0 ], thumb_cache, )
            self.WINDOW.setProperty( "RandomMovie.%d.Thumb" % ( count + 1, ), thumb )

    def _fetch_tvshow_info( self ):
        # set our unplayed query
        unplayed = ( "", "where playCount is null ", )[ self.UNPLAYED ]
        # sql statement
        if ( self.RANDOM_ORDER ):
            # random order
            sql_episodes = "select * from episodeview %sorder by RANDOM() limit %d" % ( unplayed, self.LIMIT, )
        else:
            # tv shows not finished
            sql_episodes = "select episodeview.*, bookmark.timeInSeconds from episodeview join bookmark on (episodeview.idFile = bookmark.idFile) %sorder by episodeview.strTitle limit %d" % ( unplayed, self.LIMIT, )
        # query the database
        episodes_xml = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % quote_plus( sql_episodes ), )
        # separate the records
        episodes = re.findall( "<record>(.+?)</record>", episodes_xml, re.DOTALL )
        # enumerate thru our records and set our properties
        for count, episode in enumerate( episodes ):
            # separate individual fields
            fields = re.findall( "<field>(.*?)</field>", episode, re.DOTALL )
            # set properties        
            self.WINDOW.setProperty( "RandomEpisode.%d.ShowTitle" % ( count + 1, ), fields[ 30 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeTitle" % ( count + 1, ), fields[ 2 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeNo" % ( count + 1, ), "s%02de%02d" % ( int( fields[ 14 ] ), int( fields[ 15 ] ), ) )
            self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeSeason" % ( count + 1, ), fields[ 14 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeNumber" % ( count + 1, ), fields[ 15 ] )
            self.WINDOW.setProperty( "RandomEpisode.%d.Rating" % ( count + 1, ), "%.1f" % float(fields[ 5 ]) )
            self.WINDOW.setProperty( "RandomEpisode.%d.Plot" % ( count + 1, ), fields[ 3 ] )
            # get cache names of path to use for thumbnail/fanart and play path
            thumb_cache, fanart_cache, play_path = self._get_media( fields[ 27 ], fields[ 26 ] )
            if ( not os.path.isfile( xbmc.translatePath( "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", fanart_cache, ) ) ) ):
                fanart_cache = xbmc.getCacheThumbName(os.path.join(os.path.split(os.path.split(fields[ 27 ])[0])[0], ""))
            if os.path.isfile("%s.dds" % (xbmc.translatePath( "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", os.path.splitext(fanart_cache)[0],) ) )):
                fanart_cache = "%s.dds" % (os.path.splitext(fanart_cache)[0],)
            self.WINDOW.setProperty( "RandomEpisode.%d.Path" % ( count + 1, ), play_path )
            self.WINDOW.setProperty( "RandomEpisode.%d.Fanart" % ( count + 1, ), "special://profile/Thumbnails/Video/%s/%s" % ( "Fanart", fanart_cache, ) )
            # initial thumb path
            thumb = "special://profile/Thumbnails/Video/%s/%s" % ( thumb_cache[ 0 ], thumb_cache, )
            # if thumb does not exist use an auto generated thumb path
            if ( not os.path.isfile( xbmc.translatePath( thumb ) ) ):
                thumb = "special://profile/Thumbnails/Video/%s/auto-%s" % ( thumb_cache[ 0 ], thumb_cache, )
            self.WINDOW.setProperty( "RandomEpisode.%d.Thumb" % ( count + 1, ), thumb )

    def _fetch_music_info( self ):
            # Current Working Directory
            # sql statement
            if ( self.ALBUMS ):
                sql_music = "select * from albumview order by RANDOM() limit %d" % ( self.LIMIT, )
                # query the database for recently added albums
                music_xml = xbmc.executehttpapi( "QueryMusicDatabase(%s)" % quote_plus( sql_music ), )
                # separate the records
                items = re.findall( "<record>(.+?)</record>", music_xml, re.DOTALL )
                # enumerate thru our records and set our properties
                for count, item in enumerate( items ):
                    # separate individual fields
                    fields = re.findall( "<field>(.*?)</field>", item, re.DOTALL )
                    # set properties
                    self.WINDOW.setProperty( "RandomSong.%d.Title" % ( count + 1, ), fields[ 1 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Year" % ( count + 1, ), fields[ 8 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Artist" % ( count + 1, ), fields[ 6 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Rating" % ( count + 1, ), fields[ 18 ] )
                    # Album Path  (ID)
                    path = 'XBMC.RunScript(script.randomitems,albumid=' + fields[ 0 ] + ')'
                    self.WINDOW.setProperty( "RandomSong.%d.Path" % ( count + 1, ), path )
                    # get cache name of path to use for fanart
                    cache_name = xbmc.getCacheThumbName( fields[ 6 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Fanart" % ( count + 1, ), "special://profile/Thumbnails/Music/%s/%s" % ( "Fanart", cache_name, ) )
                    self.WINDOW.setProperty( "RandomSong.%d.Thumb" % ( count + 1, ), fields[ 9 ] )
            else:
                # set our unplayed query
                unplayed = ( "", "where lastplayed is null ", )[ self.UNPLAYED ]
                # sql statement
                sql_music = "select * from songview %sorder by RANDOM() limit %d" % ( unplayed, self.LIMIT, )
                # query the database
                music_xml = xbmc.executehttpapi( "QueryMusicDatabase(%s)" % quote_plus( sql_music ), )
                # separate the records
                items = re.findall( "<record>(.+?)</record>", music_xml, re.DOTALL )
                # enumerate thru our records and set our properties
                for count, item in enumerate( items ):
                    # separate individual fields
                    fields = re.findall( "<field>(.*?)</field>", item, re.DOTALL )
                    # set properties
                    self.WINDOW.setProperty( "RandomSong.%d.Title" % ( count + 1, ), fields[ 3 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Year" % ( count + 1, ), fields[ 6 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Artist" % ( count + 1, ), fields[ 24 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Album" % ( count + 1, ), fields[ 21 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Rating" % ( count + 1, ), fields[ 18 ] )
                    path = fields[ 22 ]
                    # don't add song for albums list TODO: figure out how toplay albums
                    ##if ( not self.ALBUMS ):
                    path += fields[ 8 ]
                    self.WINDOW.setProperty( "RandomSong.%d.Path" % ( count + 1, ), path )
                    # get cache name of path to use for fanart
                    cache_name = xbmc.getCacheThumbName( fields[ 24 ] )
                    self.WINDOW.setProperty( "RandomSong.%d.Fanart" % ( count + 1, ), "special://profile/Thumbnails/Music/%s/%s" % ( "Fanart", cache_name, ) )
                    self.WINDOW.setProperty( "RandomSong.%d.Thumb" % ( count + 1, ), fields[ 27 ] )

    def _fetch_addon_info( self ):
        # initialize our list
        addonlist = []
        # list the contents of the addons folder
        addonpath = xbmc.translatePath( 'special://home/addons/' )
        addons = os.listdir(addonpath)
        # find directories in the addons folder
        for item in addons:
            if os.path.isdir(os.path.join(addonpath, item)):
                # find addon.xml in the addon folder
                addonfile = os.path.join(addonpath, item, 'addon.xml')
                if os.path.exists(addonfile):
                    # find addon id
                    addonfilecontents = xml.dom.minidom.parse(addonfile)
                    for addonentry in addonfilecontents.getElementsByTagName("addon"): 
                        addonid = addonentry.getAttribute("id")
                    # find plugins and scripts
                    addontype = xbmcaddon.Addon(id=addonid).getAddonInfo('type')
                    if (addontype == 'xbmc.python.script') or (addontype == 'xbmc.python.pluginsource'):
                        addonlist.append(addonid)
                    addonfilecontents.unlink()
        # set total property
        self.WINDOW.setProperty( "Addons.Count", str( len(addonlist) ) )
        # count thru our addons
        for count in range( self.LIMIT ):
            # check if we don't run out of items before LIMIT is reached
            if len(addonlist) > 0:
                # select a random item
                addonid = random.choice(addonlist)
                # remove the item from our list
                addonlist.remove(addonid)
                # set properties
                self.WINDOW.setProperty( "RandomAddon.%d.Name" % ( count + 1, ), xbmcaddon.Addon(id=addonid).getAddonInfo('name') )
                self.WINDOW.setProperty( "RandomAddon.%d.Author" % ( count + 1, ), xbmcaddon.Addon(id=addonid).getAddonInfo('author') )
                self.WINDOW.setProperty( "RandomAddon.%d.Summary" % ( count + 1, ), xbmcaddon.Addon(id=addonid).getAddonInfo('summary') )
                self.WINDOW.setProperty( "RandomAddon.%d.Version" % ( count + 1, ), xbmcaddon.Addon(id=addonid).getAddonInfo('version') )
                self.WINDOW.setProperty( "RandomAddon.%d.Path" % ( count + 1, ), xbmcaddon.Addon(id=addonid).getAddonInfo('id') )
                self.WINDOW.setProperty( "RandomAddon.%d.Fanart" % ( count + 1, ), xbmcaddon.Addon(id=addonid).getAddonInfo('fanart') )
                self.WINDOW.setProperty( "RandomAddon.%d.Thumb" % ( count + 1, ), xbmcaddon.Addon(id=addonid).getAddonInfo('icon') )
            else:
                # set empty properties if we ran out of items before LIMIT was reached
                self.WINDOW.setProperty( "RandomAddon.%d.Name" % ( count + 1, ), '' )
                self.WINDOW.setProperty( "RandomAddon.%d.Author" % ( count + 1, ), '' )
                self.WINDOW.setProperty( "RandomAddon.%d.Summary" % ( count + 1, ), '' )
                self.WINDOW.setProperty( "RandomAddon.%d.Version" % ( count + 1, ), '' )
                self.WINDOW.setProperty( "RandomAddon.%d.Path" % ( count + 1, ), '' )
                self.WINDOW.setProperty( "RandomAddon.%d.Fanart" % ( count + 1, ), '' )
                self.WINDOW.setProperty( "RandomAddon.%d.Thumb" % ( count + 1, ), '' )

    def _Play_Album( self, ID ):
            print "play album"
            playlist=xbmc.PlayList(0)
            playlist.clear()
            # sql statements
            sql_song = "select * from songview where idAlbum='%s' order by iTrack " % ( ID )
            # query the databases
            songs_xml = xbmc.executehttpapi( "QueryMusicDatabase(%s)" % quote_plus( sql_song ), )
            # separate the records
            songs = re.findall( "<record>(.+?)</record>", songs_xml, re.DOTALL )
            # enumerate thru our records and set our properties
            for count, movie in enumerate( songs ):
                # separate individual fields
                fields = re.findall( "<field>(.*?)</field>", movie, re.DOTALL )
                # set album name
                path = fields[ 22 ] + fields[ 8 ]
                listitem = xbmcgui.ListItem( fields[ 7 ] )
                xbmc.PlayList(0).add (path, listitem )
            xbmc.Player().play(playlist)

if ( __name__ == "__main__" ):
    Main()

Parameters (separated by comma , ):

type = Movie/Episode/Music       | Script will request Movie database or Episode database
                                 | (/!\ Caution : upper and lower case are important)
limit = #                        | # to limit returned results (default=10)
method = Last/Random             | Last to get last added items and Random to get random items
playlist = PathAndNameOfPlaylist | Name of the smartplaylist like special://masterprofile/playlists/video/children.xsp
                                 | or empty to request global database
                                 | If you set this parameter, you don't need to set type= because type will be read from playlist file
menu =                           | Name of custom or standard menu which display the widget
unwatched = True/False           | unwatched=True to filter only unwatched items
resume = True/False              | resume=True to filter only partially watched items
propertie = NameOfTheProperty    | You can overwrite the default properties names Playlist<method><type><menu> by using this parameter
                                 | example : propertie=CustomMenu1Widget1

/!\ CAUTION /!\
resume=True can slow down script when working on playlist

For example:
 
XBMC.RunScript(script.RandomAndLastItems,type=Movie,limit=10,method=Random,playlist=special://masterprofile/playlists/video/children.xsp,menu=Menu1)

will return 10 random movies in Children Smartplaylist.

Properties return to Home window (id 10000) :

* type=Movie

Playlist<method>Movie<menu>.Type = Movie
Playlist<method>Movie<menu>.Count = Number of movies in library or playlist
Playlist<method>Movie<menu>.Unwatched = Number of unwatched movies in library or playlist
Playlist<method>Movie<menu>.Watched = Number of watched movies in library or playlist
Playlist<method>Movie<menu>.<# of movie>.Rating = Movie N°# rate
Playlist<method>Movie<menu>.<# of movie>.Plot = Movie N°# plot
Playlist<method>Movie<menu>.<# of movie>.RunningTime = Movie N°# running time
Playlist<method>Movie<menu>.<# of movie>.Path = Movie N°# path (eg : C:\Movies\Movie1\Movie1.mkv)
Playlist<method>Movie<menu>.<# of movie>.Rootpath = Movie N°# root path (eg : C:\Movies\Movie1\)
Playlist<method>Movie<menu>.<# of movie>.Fanart = Movie N°# fanart
Playlist<method>Movie<menu>.<# of movie>.Thumb = Movie N°# thumbnail
Playlist<method>Movie<menu>.<# of movie>.Title = Movie N°# title
Playlist<method>Movie<menu>.<# of movie>.Year = Movie N°# year
Playlist<method>Movie<menu>.<# of movie>.Trailer = Movie N°# trailer
Playlist<method>Movie<menu>.<# of movie>.Resolution = Movie N°# (values are blank, 480, 540, 576, 720, 1080)

* type=Episode

Playlist<method>Episode<menu>.Type = Episode
Playlist<method>Episode<menu>.Count = Number of episodes in library or playlist
Playlist<method>Episode<menu>.Unwatched = Number of unwatched episodes in library or playlist
Playlist<method>Episode<menu>.Watched = Number of watched episodes in library or playlist
Playlist<method>Episode<menu>.TvShows = Number of TV shows in library or playlist
Playlist<method>Episode<menu>.<# of episode>.Rating = Episode N°# rate
Playlist<method>Episode<menu>.<# of episode>.Plot = Episode N°# plot
Playlist<method>Episode<menu>.<# of episode>.RunningTime = Episode N°# running time
Playlist<method>Episode<menu>.<# of episode>.Path = Episode N°# path (ex : C:\TVShows\TVShow1\Season1\Episode1.avi)
Playlist<method>Episode<menu>.<# of episode>.Rootpath = Episode N°# root path (ex : C:\TVShows\TVShow1\)
Playlist<method>Episode<menu>.<# of episode>.Fanart = Episode N°# fanart
Playlist<method>Episode<menu>.<# of episode>.Thumb = Episode N°# thumbnail
Playlist<method>Episode<menu>.<# of episode>.ShowTitle = Episode N°# TV Show title
Playlist<method>Episode<menu>.<# of episode>.EpisodeTitle = Episode N°# title
Playlist<method>Episode<menu>.<# of episode>.EpisodeNo = Episode N°# (format sXXeXX)
Playlist<method>Episode<menu>.<# of episode>.EpisodeSeason = Episode N°# season number
Playlist<method>Episode<menu>.<# of episode>.EpisodeNumber = Episode N°# number

* type=Music

Playlist<method>Music<menu>.Type = Music
Playlist<method>Music<menu>.Artists = Number of artists in library or playlist
Playlist<method>Music<menu>.Albums = Number of albums in library or playlist
Playlist<method>Music<menu>.Songs = Nombre of songs in library or playlist
Playlist<method>Music<menu>.<# of album>.Album = Album N°# title
Playlist<method>Music<menu>.<# of album>.Artist = Album N°# artist name
Playlist<method>Music<menu>.<# of album>.Year = Album N°# year
Playlist<method>Music<menu>.<# of album>.Fanart = Album N°# fanart
Playlist<method>Music<menu>.<# of album>.Thumb = Album N°# thumbnail
Playlist<method>Music<menu>.<# of album>.ArtistPath = Album N°# artist path (eg : C:\Music\Artist1)
Playlist<method>Music<menu>.<# of album>.AlbumPath = Album N°# path (ex : C:\Music\Artist1\Album1)
Playlist<method>Music<menu>.<# of album>.AlbumDesc = Album N°# description
Playlist<method>Music<menu>.<# of album>.PlayPath = Album N°# for playing (musicdb://3/1/)

With :
XBMC.RunScript(script.RandomAndLastItems,type=Movie,limit=10,method=Random,playlist=special://masterprofile/playlists/video/children.xsp,menu=Menu1)
properties will be :

PlaylistRandomMovieMenu1.Count
PlaylistRandomMovieMenu1.1.Title
...
...
PlaylistRandomMovieMenu1.10.Title

For more information and help please check :

http://forum.xbmc.org/showthread.php?p=1014084
Parameters (separated by comma , ):

type = Movie/Episode/Music       | Script will request Movie database or Episode database
                                 | (/!\ Caution : upper and lower case are important)
limit = #                        | # to limit returned results (default=10)
method = Last/Random/Playlist    | Last to get last added items, Random to get random items and Playlist to use the order of the playlist
playlist = PathAndNameOfPlaylist | Name of the smartplaylist like special://masterprofile/playlists/video/children.xsp
                                 | or empty to request global database
                                 | If you set this parameter, you don't need to set type= because type will be read from playlist file
menu =                           | Name of custom or standard menu which display the widget
unwatched = True/False           | unwatched=True to filter only unwatched items
resume = True/False              | resume=True to filter only partially watched items
property = NameOfTheProperty     | You can overwrite the default properties names Playlist<method><type><menu> by using this parameter
                                 | example : property=CustomMenu1Widget1

/!\ CAUTION /!\
resume=True can slow down script when working on playlist

For example:
 
XBMC.RunScript(script.RandomAndLastItems,type=Movie,limit=10,method=Random,playlist=special://masterprofile/playlists/video/children.xsp,menu=Menu1)

will return 10 random movies in Children Smartplaylist.

Properties return to Home window (id 10000) :

%s.Loaded = Will be cleared upon starting the script and set to "true" if the script is done.

* type=Movie

Script will look at smart playlist type to make the difference between Movies and Music videos

1 - Properties for Movies

%s = Playlist<method>Movie<menu>
%d = Movie number

%s.Type = Movie
%s.Count = Number of movies in library or playlist
%s.Unwatched = Number of unwatched movies in library or playlist
%s.Watched = Number of watched movies in library or playlist
%s.Name = Name of the playlist
%s.%d.DBID
%s.%d.Title
%s.%d.OriginalTitle
%s.%d.Year
%s.%d.Genre
%s.%d.Studio
%s.%d.Country
%s.%d.Plot
%s.%d.PlotOutline
%s.%d.Tagline
%s.%d.Runtime
%s.%d.Rating
%s.%d.Trailer
%s.%d.MPAA
%s.%d.Director
%s.%d.Art(thumb) (same value as Art(poster) but make skinner life easier ;)
%s.%d.Art(poster)
%s.%d.Art(fanart)
%s.%d.Art(clearlogo)
%s.%d.Art(clearart)
%s.%d.Art(landscape)
%s.%d.Art(banner)
%s.%d.Art(discart)
%s.%d.Resume
%s.%d.PercentPlayed
%s.%d.Watched
%s.%d.File
%s.%d.Path
%s.%d.Play
%s.%d.VideoCodec
%s.%d.VideoResolution
%s.%d.VideoAspect
%s.%d.AudioCodec
%s.%d.AudioChannels

2 - Properties for Music videos

%s = Playlist<method>MusicVideos<menu>
%d = Movie number

%s.Type = MusicVideo
%s.Count = Number of movies in library or playlist
%s.Unwatched = Number of unwatched movies in library or playlist
%s.Watched = Number of watched movies in library or playlist
%s.Name = Name of the playlist
%s.%d.DBID
%s.%d.Title
%s.%d.Year
%s.%d.Genre
%s.%d.Studio
%s.%d.Artist
%s.%d.Album
%s.%d.Track
%s.%d.Plot
%s.%d.Tag
%s.%d.Runtime
%s.%d.Director
%s.%d.Art(thumb) (same value as Art(poster) but make skinner life easier ;)
%s.%d.Art(poster)
%s.%d.Art(fanart)
%s.%d.Art(clearlogo)
%s.%d.Art(clearart)
%s.%d.Art(landscape)
%s.%d.Art(banner)
%s.%d.Art(discart)
%s.%d.Resume
%s.%d.PercentPlayed
%s.%d.Watched
%s.%d.File
%s.%d.Path
%s.%d.Play
%s.%d.VideoCodec
%s.%d.VideoResolution
%s.%d.VideoAspect
%s.%d.AudioCodec
%s.%d.AudioChannels


* type=Episode

%s = Playlist<method>Episode<menu>
%d = Episode number

%s.Type = Episode
%s.Count = Number of episodes in library or playlist
%s.Unwatched = Number of unwatched episodes in library or playlist
%s.Watched = Number of watched episodes in library or playlist
%s.TvShows = Number of TV shows in library or playlist
%s.Name = Name of the playlist
%s.%d.DBID
%s.%d.Title
%s.%d.Episode
%s.%d.EpisodeNo
%s.%d.Season
%s.%d.Plot
%s.%d.TVshowTitle
%s.%d.Rating
%s.%d.Art(thumb)
%s.%d.Art(tvshow.fanart)
%s.%d.Art(tvshow.poster)
%s.%d.Art(tvshow.banner)
%s.%d.Art(tvshow.clearlogo)
%s.%d.Art(tvshow.clearart)
%s.%d.Art(tvshow.landscape)
%s.%d.Art(fanart)
%s.%d.Art(poster)
%s.%d.Art(banner)
%s.%d.Art(clearlogo)
%s.%d.Art(clearart)
%s.%d.Art(landscape)
%s.%d.Resume
%s.%d.Watched
%s.%d.Premiered
%s.%d.Runtime
%s.%d.PercentPlayed
%s.%d.File
%s.%d.MPAA
%s.%d.Studio
%s.%d.Path
%s.%d.Play
%s.%d.VideoCodec
%s.%d.VideoResolution
%s.%d.VideoAspect
%s.%d.AudioCodec
%s.%d.AudioChannels

* type=Music

%s = Playlist<method>Music<menu>
%d = Album number
%s.Type = Music
%s.Artists = Number of artists in library or playlist
%s.Albums = Number of albums in library or playlist
%s.Songs = Nombre of songs in library or playlist
%s.Name = Name of the playlist
%s.%d.Title
%s.%d.Artist
%s.%d.Genre
%s.%d.Year
%s.%d.Theme
%s.%d.Mood
%s.%d.Style
%s.%d.Type
%s.%d.RecordLabel
%s.%d.Description
%s.%d.Rating
%s.%d.Art(thumb)
%s.%d.Art(fanart)
%s.%d.Play
%s.%d.LibraryPath

With :
XBMC.RunScript(script.RandomAndLastItems,type=Movie,limit=10,method=Random,playlist=special://masterprofile/playlists/video/children.xsp,menu=Menu1)
properties will be :

PlaylistRandomMovieMenu1.Count
PlaylistRandomMovieMenu1.1.Title
...
...
PlaylistRandomMovieMenu1.10.Title

Code example to play album:

   <onclick>$INFO[Window(Home).Property(RandomAlbum.%d.Play)]</onclick>

Code example to open album:

   <onclick>$INFO[Window(Home).Property(RandomArtist.%d.LibraryPath)]</onclick>

   
For more information and help please check :

http://forum.xbmc.org/showthread.php?p=1014084

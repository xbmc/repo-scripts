
INFORMATION FOR SKINNERS
------------------------

CONTENTS:
0.   Running the addon 
I.   Infolabels available in script-globalsearch.xml
II.  Control id's used in script-globalsearch.xml
III. Available window properties



0. Running the addon
--------------------
The addon can be run in two ways:
- the user executes the addon
- the addon is executed by another addon/skin: RunScript(script.globalsearch,searchstring=foo)

You can specify which categories should be searched (this overrides the user preferences set in the addon settings):
RunScript(script.globalsearch,movies=true)
RunScript(script.globalsearch,tvshows=true&amp;musicvideos=true&amp;songs=true)

available options: movies, tvshows, episodes, musicvideos, artists, albums, songs, livetv, actors, directors



I. Infolabels available in script-globalsearch.xml
-------------------------------------------------------
Container.Content
- returns one of the following: movies, tvshows, episodes, musicvideos, artists, albums, songs, livetv, actors, directors

LIVETV:
ListItem.Label
ListItem.Icon
ListItem.Property(Genre)
ListItem.Property(Plot)
ListItem.Property(Duration)
ListItem.Property(Starttime)
ListItem.Property(Endtime)
ListItem.Property(ChannelName)
ListItem.Property(DBID)


MOVIES:
ListItem.Label
ListItem.Icon
ListItem.Art()
ListItem.OriginalTitle
ListItem.Genre
ListItem.Plot
ListItem.Plotoutline
ListItem.Duration
ListItem.Studio
ListItem.Tagline
ListItem.Year
ListItem.Trailer
ListItem.Playcount
ListItem.Rating
ListItem.UserRating
ListItem.Mpaa
ListItem.Director
ListItem.Writer
ListItem.VideoResolution
ListItem.VideoCodec
ListItem.VideoAspect
ListItem.AudioCodec
ListItem.AudioChannels
ListItem.Path
ListItem.DBID
ListItem.DBType


ACTOR:
ListItem.Label
ListItem.Label2
ListItem.Icon


DIRECTOR:
ListItem.Label
ListItem.Label2
ListItem.Icon


TV SHOWS:
ListItem.Label
ListItem.Icon
ListItem.Art()
ListItem.Episode
ListItem.Season
ListItem.Mpaa
ListItem.Year
ListItem.Genre
ListItem.Plot
ListItem.Premiered
ListItem.Studio
ListItem.Rating
ListItem.UserRating
ListItem.Playcount
ListItem.Path
ListItem.DBID
ListItem.DBType


SEASONS:
ListItem.Label
ListItem.Icon
ListItem.Art()
ListItem.Episode
ListItem.Season
ListItem.TvShowTitle
ListItem.Playcount
ListItem.UserRating
ListItem.Path
ListItem.DBID
ListItem.DBType


EPISODES:
ListItem.Label
ListItem.Icon
ListItem.Art()
ListItem.Episode
ListItem.Season
ListItem.Plot
ListItem.Rating
ListItem.UserRating
ListItem.Director
ListItem.Duration
ListItem.TvShowTitle
ListItem.Premiered
ListItem.Playcount
ListItem.VideoResolution
ListItem.VideoCodec
ListItem.VideoAspect
ListItem.AudioCodec
ListItem.AudioChannels
ListItem.Path
ListItem.DBID
ListItem.DBType


MUSIC VIDEOS:
ListItem.Label
ListItem.Icon
ListItem.Art()
ListItem.Album
ListItem.Artist
ListItem.Director
ListItem.Genre
ListItem.Plot
ListItem.Rating
ListItem.UserRating
ListItem.Duration
ListItem.Studio
ListItem.Year
ListItem.Playcount
ListItem.VideoResolution
ListItem.VideoCodec
ListItem.VideoAspect
ListItem.AudioCodec
ListItem.AudioChannels
ListItem.Path
ListItem.DBID
ListItem.DBType


ARTISTS:
ListItem.Label
ListItem.Icon
ListItem.Art()
ListItem.Path
ListItem.DBID
ListItem.DBType
ListItem.Property(Artist_Born)
ListItem.Property(Artist_Died)
ListItem.Property(Artist_Formed)
ListItem.Property(Artist_Disbanded)
ListItem.Property(Artist_YearsActive)
ListItem.Property(Artist_Mood)
ListItem.Property(Artist_Style)
ListItem.Property(Artist_Genre)
ListItem.Property(Artist_Description)


ALBUMS:
ListItem.Label
ListItem.Icon
ListItem.Art()
ListItem.Artist
ListItem.Album
ListItem.Genre
ListItem.UserRating
ListItem.Year
ListItem.Path
ListItem.DBID
ListItem.DBType
ListItem.Property(Album_Label)
ListItem.Property(Album_Description)
ListItem.Property(Album_Theme)
ListItem.Property(Album_Style)
ListItem.Property(Album_Rating)
ListItem.Property(Album_Type)
ListItem.Property(Album_Mood)


SONGS:
ListItem.Label
ListItem.Icon
ListItem.Art()
ListItem.Artist
ListItem.Album
ListItem.Genre
ListItem.Comment
ListItem.Track
ListItem.Rating
ListItem.UserRating
ListItem.Playcount
ListItem.Duration
ListItem.Year
ListItem.Path
ListItem.DBID
ListItem.DBType



II. Control id's used in script-globalsearch.xml
------------------------------------------------------
990  - 'New search' button, visible when the script finished searching
991  - Search category label, visible when the script is searching
999  - 'No results found' label, visible when no results are found
9000 - Menu list



III.  Available window properties
--------------------------------
Window.Property(GlobalSearch.SearchString) - the string the user is searching for


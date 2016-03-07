# script.skin.helper.service
a helper service for Kodi skins

________________________________________________________________________________________________________

### Settings for the script
The script is controlled by the skinner through skin settings to allow the skinner to fully integrate the settings of this script within the skin settings of the skin.
This means that the skinner enables functions of the script with enabling some skin settings.

Important settings:

| setting name 		| how to set 		| description                           |
|:-------------- | :--------------- | :---------------------------------------- |
|SkinHelper.EnableExtraFanart	| Skin.ToggleSetting(SkinHelper.EnableExtraFanart)	| enables the extrafanart background scanner |
|SkinHelper.CustomStudioImagesPath | Skin.SetString(SkinHelper.CustomStudioImagesPath,[PATH])| if you want the user (or yourself as skinner) be able to set the path to the studio logos. If empty it will try to locate the images (later to be replaced with the new image resource packs in Kodi 16)|
|SkinHelper.ShowInfoAtPlaybackStart	| Skin.SetNumeric(SkinHelper.ShowInfoAtPlaybackStart)	| Show OSD info panel at playback start for number of seconds (0 or empty disables this) |
|SkinHelper.AutoCloseVideoOSD	| Skin.SetNumeric(SkinHelper.AutoCloseVideoOSD)	| Auto close the Video OSD panel when activated by the user after number of seconds (0 or empty disables this) |
|SkinHelper.AutoCloseMusicOSD	| Skin.SetNumeric(SkinHelper.AutoCloseMusicOSD)	| Auto close the Music OSD panel when activated by the user after number of seconds (0 or empty disables this) |
|SkinHelper.RandomFanartDelay	| Skin.SetNumeric(SkinHelper.RandomFanartDelay)	| Sets the time in seconds for the interval of the rotating backgrounds provided by the script (0 or empty disable the backgrounds by this script completely) |
|SkinHelper.CustomPicturesBackgroundPath	| Skin.SetPath(SkinHelper.CustomPicturesBackgroundPath)	| Sets a custom path from which the global pictures background should be pulled from. (when empty uses all picture sources) |
|SmartShortcuts.playlists | Skin.SetBool(SmartShortcuts.playlists) | Enable smart shortcuts for Kodi playlists |
|SmartShortcuts.favorites | Skin.SetBool(SmartShortcuts.favorites) | Enable smart shortcuts for Kodi favorites |
|SmartShortcuts.plex | Skin.SetBool(SmartShortcuts.plex) | Enable smart shortcuts for plexbmc addon |
|SmartShortcuts.emby | Skin.SetBool(SmartShortcuts.emby) | Enable smart shortcuts for emby addon |
|SmartShortcuts.netflix | Skin.SetBool(SmartShortcuts.netflix) | Enable smart shortcuts for flix2kodi addon |
|SkinHelper.EnableAddonsLookups	| Skin.ToggleSetting(SkinHelper.EnableAddonsLookups)	| enables the background scanner for addons artwork and additional properties |
|SkinHelper.EnablePVRThumbs	| Skin.ToggleSetting(SkinHelper.EnablePVRThumbs)	| enables the background scanner for PVR artwork |

________________________________________________________________________________________________________
________________________________________________________________________________________________________

### Window Properties provided by the script
The script provides several window properties to provide additional info about your skin and media info.
The window properties can be called in your skin like this: $INFO[Window(Home).Property(propertyname)]

________________________________________________________________________________________________________



#### General window Properties
| property 			| description |
|:-----------------------------	| :----------- |
|Window(Home).Property(SkinHelper.skinTitle) | your skin name including the version |
|Window(Home).Property(SkinHelper.skinVersion) | only the version of your skin |
|Window(Home).Property(SkinHelper.TotalAddons) | total number of all installed addons |
|Window(Home).Property(SkinHelper.TotalAudioAddons) | total number of installed Audio addons |
|Window(Home).Property(SkinHelper.TotalVideoAddons) | total number of installed Video addons |
|Window(Home).Property(SkinHelper.TotalProgramAddons) | total number of installed Program addons |
|Window(Home).Property(SkinHelper.TotalPicturesAddons) | total number of installed Picture addons |
|Window(Home).Property(SkinHelper.TotalFavourites) | total number of favourites |
|Window(Home).Property(SkinHelper.TotalTVChannels) | total number of TV channels in the PVR |
|Window(Home).Property(SkinHelper.TotalRadioChannels) | total number of Radio channels in the PVR |
|Window(Home).Property(SkinHelper.TotalMovieSets) | total number of Movie sets in the library |
|Window(Home).Property(SkinHelper.TotalMoviesInSets) | total number of Movies belonging to moviesets |
|Window(Home).Property(SkinHelper.ContentHeader) | Shows the real amount of items (excluding any all* entries) and the content type, for example: "23 albums"|
________________________________________________________________________________________________________
#### Video library window properties
Some additional window properties that can be used in the video library. 

| property 			| description |
|:-----------------------------	| :----------- |
|Window(Home).Property(SkinHelper.ExtraFanArtPath) | will return the extrafanart path for the listitem (to be used with multiimage control), empty if none is found. This window property is only available when browsing the video library and when the following Skin Bool is true: SkinHelper.EnableExtraFanart|
|Window(Home).Property(SkinHelper.ExtraFanArt.X) | Get extrafanart image X, only available when extrafanart is enabled. Start counting from 0 |
|Window(Home).Property(SkinHelper.Player.AddonName) | If you want to display the name of the addon in the player |
|Window(Home).Property(SkinHelper.Player.AddonName) | If you want to display the name of the addon in the player |
|Window(Home).Property(SkinHelper.ListItemDuration) | Formatted duration hours:minutes of the current listitem total runtime |
|Window(Home).Property(SkinHelper.ListItemDuration.Hours) | Only the hours part of the current listitem duration |
|Window(Home).Property(SkinHelper.ListItemDuration.Minutes) | Only the minutes part of the current listitem duration |
|Window(Home).Property(SkinHelper.ListItemGenres) | Will return all genres of the current listitem seperated by [CR] |
|Window(Home).Property(SkinHelper.ListItemGenre.X) | Will return all genres of the current listitem. Start counting from 0|
|Window(Home).Property(SkinHelper.ListItemDirectors) | Will return all directors of the current listitem seperated by [CR] |
|Window(Home).Property(SkinHelper.ListItemSubtitles) | Will return all subtitles of the current listitem seperated by / |
|Window(Home).Property(SkinHelper.ListItemSubtitles.Count) | Will return the number of Subtitles |
|Window(Home).Property(SkinHelper.ListItemLanguages) | Will return all audio languages of the current listitem seperated by / |
|Window(Home).Property(SkinHelper.ListItemLanguages.Count) | Will return the number of Languages |
|Window(Home).Property(SkinHelper.ListItemSubtitles.X) | Will return subtitle X of the current listitem. Start counting from 0 |
|Window(Home).Property(SkinHelper.ListItemAudioStreams.Count) | Will return the number of Audio streams |
|Window(Home).Property(SkinHelper.ListItemAudioStreams.X) | Will return the language-codec-channels of audiostream X for the current listitem. Start counting from 0 |
|Window(Home).Property(SkinHelper.ListItemAudioStreams.X.Language) | Will return the language of audiostream X for the current listitem. Start counting from 0 |
|Window(Home).Property(SkinHelper.ListItemAudioStreams.X.AudioCodec) | Will return the AudioCodec of audiostream X for the current listitem. Start counting from 0 |
|Window(Home).Property(SkinHelper.ListItemAudioStreams.X.AudioChannels) | Will return the AudioChannels of audiostream X for the current listitem. Start counting from 0 |
|Window(Home).Property(SkinHelper.ListItemAllAudioStreams) | Will return a formatted list of all audiostreams for the current listitem separated by / |
|Window(Home).Property(SkinHelper.ListItemVideoHeight) | Will return the height of the video stream for the current listitem |
|Window(Home).Property(SkinHelper.ListItemVideoWidth) | Will return the width of the video stream for the current listitem |
|Window(Home).Property(SkinHelper.RottenTomatoesRating) | rotten tomatoes rating |
|Window(Home).Property(SkinHelper.RottenTomatoesMeter) | rotten tomatoes meter |
|Window(Home).Property(SkinHelper.RottenTomatoesFresh) | rotten tomatoes fresh count |
|Window(Home).Property(SkinHelper.RottenTomatoesRotten) | rotten tomatoes rotten count |
|Window(Home).Property(SkinHelper.RottenTomatoesImage) | rotten tomatoes image description (e.g. certified) |
|Window(Home).Property(SkinHelper.RottenTomatoesReviews) | number of official reviews on Rotten tomatoes |
|Window(Home).Property(SkinHelper.RottenTomatoesConsensus) | critic consensus from rotten tomatoes |
|Window(Home).Property(SkinHelper.RottenTomatoesAudienceMeter) | rotten tomatoes user meter |
|Window(Home).Property(SkinHelper.RottenTomatoesAudienceRating) | user rating from rotten tomatoes |
|Window(Home).Property(SkinHelper.RottenTomatoesAudienceReviews) | No. of user reviews on rotten tomatoes |
|Window(Home).Property(SkinHelper.RottenTomatoesAwards) | awards for the movie |
|Window(Home).Property(SkinHelper.RottenTomatoesBoxOffice) | amount the film made at box office |
|Window(Home).Property(SkinHelper.RottenTomatoesDVDRelease) | date of DVD release |
|Window(Home).Property(SkinHelper.MetaCritic.Rating) | rating from metacritic |
|Window(Home).Property(SkinHelper.IMDB.Rating) | rating on IMDB |
|Window(Home).Property(SkinHelper.IMDB.Votes) | No. of votes for rating on IMDB |
|Window(Home).Property(SkinHelper.IMDB.MPAA) | MPAA rating on IMDB |
|Window(Home).Property(SkinHelper.IMDB.Runtime) | Runtime on IMDB |
|Window(Home).Property(SkinHelper.TMDB.Budget) | budget spent to this movie in dollars (from tmdb)|
|Window(Home).Property(SkinHelper.TMDB.Budget.mln) | budget spent to this movie in millions of dollars|
|Window(Home).Property(SkinHelper.TMDB.Budget.formatted) | Same as Budget.mln but formatted as $ 123 mln.|
|Window(Home).Property(SkinHelper.TMDB.Revenue) | revenue for this movie in dollars (from tmdb) |
|Window(Home).Property(SkinHelper.TMDB.Revenue.mln) | Revenue for this movie in millions of dollars|
|Window(Home).Property(SkinHelper.TMDB.Revenue.formatted) | Same as Revenue.mln but formatted as $ 123 mln.|
|Window(Home).Property(SkinHelper.TMDB.Tagline) | tagline for this movie (from tmdb) |
|Window(Home).Property(SkinHelper.TMDB.Homepage) | homepage for this movie (from tmdb) |
|Window(Home).Property(SkinHelper.TMDB.Status) | status for this movie, e.g. released (from tmdb) |
|Window(Home).Property(SkinHelper.TMDB.Popularity) | popularity for this movie (from tmdb) |


________________________________________________________________________________________________________
#### Animated Posters
Provides animated poster in window property (cached locally)
For info, see: http://forum.kodi.tv/showthread.php?tid=215727

Only available when enabled as skin setting --> Skin.SetBool(SkinHelper.EnableAnimatedPosters)

| property 			| description |
|:-----------------------------	| :----------- |
|Window(Home).Property(SkinHelper.AnimatedPoster) | Animated (gif) Movie poster image -if available-  |
|Window(Home).Property(SkinHelper.AnimatedFanart) | Animated (gif) Movie fanart image -if available-  |

________________________________________________________________________________________________________
#### Studio Logos
The script can provide you the full path of the studio logo found for the selected listitem.
It will do that by looking up all found studio images and do a smart compare to match the correct one.
If the listitem has multiple studios it will return the logo from the first studio found in the list thas has a logo.
This will prevent you from having to sort out that logic yourself in your skin.

The script handles this logic to locate the fanart:

1. custom path set by you in the skin: Skin.String(SkinHelper.CustomStudioImagesPath)

2. try to locate the images in skin\extras\flags\studios  (and flags\studioscolor for coloured images)

3. try to locate the images in the new image resource addons provided by the Kodi team


| property 			| description |
|:-----------------------------	| :----------- |
|Window(Home).Property(SkinHelper.ListItemStudioLogo) | Will return the full image path of the (default/white) studio logo for the current selected item in a list. |
|Window(Home).Property(SkinHelper.ListItemStudioLogoColor) | Will return the full image path of the coloured studio logo for the current selected item in a list. |
|Window(Home).Property(SkinHelper.ListItemStudio) | Will just return the first studio of the listitem if you want to locate the images yourself. |
|Window(Home).Property(SkinHelper.ListItemStudios) | Will return all studios seperated by [CR] |


#### Movie sets window properties
If the selected listitem in the videolibrary is a movie set, some additional window properties are provided:

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(SkinHelper.MovieSet.Title) | All titles in the movie set, separated by [CR] |
| Window(Home).Property(SkinHelper.MovieSet.Runtime) | Total runtime (in minutes) of the movie set |
| Window(Home).Property(SkinHelper.MovieSet.Duration) | Formatted duration hours:minutes of the movieset total runtime |
| Window(Home).Property(SkinHelper.MovieSet.Duration.Hours) | Only the hours part of the formatted duration |
| Window(Home).Property(SkinHelper.MovieSet.Duration.Minutes) | Only the minutes part of the formatted duration |
| Window(Home).Property(SkinHelper.MovieSet.Writer) | All writers of the movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.Director) | All directors of the movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.Genre) | All genres of the movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.Country) | All countries of the movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.Studio) | All studios of the movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.Years) | All years of the movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.Year) | Year of first movie - Year of last movie |
| Window(Home).Property(SkinHelper.MovieSet.Plot) | All plots of the movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.ExtendedPlot) | Plots combined with movie title info |
| Window(Home).Property(SkinHelper.MovieSet.Count) | Total movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.WatchedCount) | Total watched movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.UnWatchedCount) | Total unwatched movies in the set |
| Window(Home).Property(SkinHelper.ExtraFanArtPath) | Rotating fanart images from movies in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.Title) | Title of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.Poster) | Poster image of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.FanArt) | FanArt image of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.Landscape) | Landscape image of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.Banner) | Banner image of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.DiscArt) | DiscArt image of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.ClearLogo) | Clearlogo image of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.ClearArt) | ClearArt image of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.AspectRatio) | AspectRatio of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.Resolution) | Resolution of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.Codec) | Codec of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.AudioCodec) | AudioCodec of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.AudioChannels) | AudioChannels of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.AudioLanguage) | AudioLanguage of Movie X in the set |
| Window(Home).Property(SkinHelper.MovieSet.X.SubTitle) | SubTitle of Movie X in the set |

For the individual items (MovieSet.X) replace X with the number of the movie in the set. Start counting at 0 and movies are ordered by year.
The ListItemStudioLogo and ListItemDuration properties will also be provided (if available) for the movie set.

________________________________________________________________________________________________________



#### Music library window properties
Some additional window properties that can be used in the music library.
The artwork is detected in the music paths automatically. Also in the addon settings for the skinhelper addon, you can enable a scraper for music artwork.

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(SkinHelper.Music.Banner) | Will return the Artist's banner image for the current selected item in the list. |
| Window(Home).Property(SkinHelper.Music.FanArt) | Will return the Artist's fanart image for the current selected item in the list. |
| Window(Home).Property(SkinHelper.Music.ClearLogo) | Will return the Artist's logo image for the current selected item in the list. |
| Window(Home).Property(SkinHelper.Music.DiscArt) | Will return the Album's cd art image for the current selected item in the list. |
| Window(Home).Property(SkinHelper.Music.ExtraFanArt) | Will return the ExtraFanArt path (if exists) for the current selected item in the list, to be used in a multiimage control. |
| Window(Home).Property(SkinHelper.Music.Info) | Returns the album's description or if empty the artist info. Can be used at both album- and songlevel.  |
| Window(Home).Property(SkinHelper.Music.TrackList) | Returns all tracks (in the library) for the selected album or artist, separated by [CR] in the format tracknumber - title  |
| Window(Home).Property(SkinHelper.Music.TrackList.Formatted) | Same as Tracklist, but prefixed with a • character|
| Window(Home).Property(SkinHelper.Music.Albums) | Returns all albums (in the library) for the selected artist, separated by [CR] |
| Window(Home).Property(SkinHelper.Music.Albums.Formatted) | Same as Albums, but prefixed with a • character|
| Window(Home).Property(SkinHelper.Music.SongCount) | Returns the number of songs for the selected artist or album |
| Window(Home).Property(SkinHelper.Music.AlbumCount) | Returns the number of albums for the selected artist |

Note: If you also want to have the Music Properties for your homescreen widgets, you need to set a Window Property "SkinHelper.WidgetContainer" with the ID of your widget container:
For example in home.xml: <onload>SetProperty(SkinHelper.WidgetContainer,301)</onload>

##### Music artwork/properties for music player
The music properties are also available for the player:

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(SkinHelper.Player.Music.Banner) | Will return the Artist's banner image (if found). |
| Window(Home).Property(SkinHelper.Player.Music.FanArt) | Will return the Artist's fanart image (if found). |
| Window(Home).Property(SkinHelper.Player.Music.ClearLogo) | Will return the Artist's logo image (if found). |
| Window(Home).Property(SkinHelper.Player.Music.DiscArt) | Will return the Album's cd art image (if found). |
| Window(Home).Property(SkinHelper.Player.Music.ExtraFanArt) | Will return the ExtraFanArt path for the artist (if found). |
| Window(Home).Property(SkinHelper.Player.Music.Info) | Returns the album's description or if empty the artist info. (if found).  |
| Window(Home).Property(SkinHelper.Player.Music.TrackList) | Returns all tracks (in the library) for the selected album or artist  |
| Window(Home).Property(SkinHelper.Player.Music.Albums) | Returns all albums (in the library) for the selected artist, separated by [CR] |
| Window(Home).Property(SkinHelper.Player.Music.SongCount) | Returns the number of songs for the selected artist or album |
| Window(Home).Property(SkinHelper.Player.Music.AlbumCount) | Returns the number of albums for the selected artist |

________________________________________________________________________________________________________


#### PVR window properties
Some additional window properties that can be used in the PVR windows. 
Enables a live scraper for images of the selected program in the PVR. Comes with smart caching so it will be faster once used more often.
You must set the following Skin Bool to true --> SkinHelper.EnablePVRThumbs for the scraper to activate.
The properties will also be available for your homescreen widgets if you set the kinHelper.WidgetContainer property.

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(SkinHelper.PVR.Poster) | Will return the IMDB poster image for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.FanArt) | Will return the IMDB fanart image for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.Thumb) | Will return the thumb for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.ActualThumb) | Will return the thumb returned by the PVR addon itself (if supported) |
| Window(Home).Property(SkinHelper.PVR.ClearLogo) | Will return the clearlogo for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.Landscape) | Will return the landscape art for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.ClearArt) | Will return the ClearArt for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.DiscArt) | Will return the DiscArt for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.CharacterArt) | Will return the CharacterArt for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.Banner) | Will return the Banner for the currently selected show/movie (only if found) |
| Window(Home).Property(SkinHelper.PVR.ChannelLogo) | Will return the channel logo for the currently selected channel (only if found) |
| Window(Home).Property(SkinHelper.PVR.ExtraFanArt) | Will return the ExtraFanArt path (if exists) for the current selected item in the list, to be used in a multiimage control. |

NOTE: The images will only be scraped if you have set the following Skin Bool to true --> SkinHelper.EnablePVRThumbs

Also note that the addon-settings for this addon will allow fine-tuning of the PVR thumbs feature

If you want to use the PVR thumbs inside a Kodi list/panel container you can do that by using the scripts webservice.
See below in this readme...

________________________________________________________________________________________________________

#### window properties for Home widgets or custom containers
All above described window props can also be used for a custom container, like widgets on the home screen.
The script will automatically figure out what content is in your widget and provide the appropriate window props (e.g. pvr properties, music or video).
What you need to do is set a window property with the ID of your widget container: SetProperty(SkinHelper.WidgetContainer,510,Home) (replace 510 with your container ID)
For example set that in the onload of your home window if you only have 1 focusable widget control or set it as onfocus action on the widgetcontainer itself with the correct ID.


________________________________________________________________________________________________________

#### window properties for addons
By default all additional window properties (TMDB info, rotten tomatoes etc.) will ONLY be returned for items in the library.
If you want to use these properties for addon provided content too, like plexbmc or trailers, you will have to enable a skin setting:
Skin.SetBool(SkinHelper.EnableAddonsLookups)

If that bool is set, the script will also lookup any items provided by an addon, including artwork.
For the artwork, the same mechanism is used as for the pvr artwork feature, so the artwork is returned in the pvr properties.

________________________________________________________________________________________________________


#### Backgrounds provided by the script
The script has a background scanner to provide some rotating fanart backgrounds which can be used in your skin as backgrounds. The backgrounds are available in window properties.

Note: You must set the skin string SkinHelper.RandomFanartDelay to enable the backgrounds. 
If you want to change this interval you can set a Skin String "SkinHelper.RandomFanartDelay" with the number of seconds as value.
Set it to 0 or clear the string to disable the backgrounds.

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(SkinHelper.AllMoviesBackground) | Random fanart of movies in video database|
| Window(Home).Property(SkinHelper.AllTvShowsBackground) | Random fanart of TV shows in video database|
| Window(Home).Property(SkinHelper.AllMusicVideosBackground) | Random fanart of music videos in video database|
| Window(Home).Property(SkinHelper.RecentMusicBackground) | Random fanart of recently added music|
| Window(Home).Property(SkinHelper.AllMusicBackground) | Random fanart of music artists in database|
| Window(Home).Property(SkinHelper.GlobalFanartBackground) | Random fanart of all media types|
| Window(Home).Property(SkinHelper.InProgressMoviesBackground) | Random fanart of in progress movies|
| Window(Home).Property(SkinHelper.RecentMoviesBackground) | Random fanart of in recently added movies|
| Window(Home).Property(SkinHelper.UnwatchedMoviesBackground) | Random fanart of unwatched movies|
| Window(Home).Property(SkinHelper.InProgressShowsBackground) | Random fanart of in progress tv shows|
| Window(Home).Property(SkinHelper.RecentEpisodesBackground) | Random fanart of recently added episodes|
| Window(Home).Property(SkinHelper.GlobalFanartBackground) | Random fanart of all media types|
| Window(Home).Property(SkinHelper.AllVideosBackground) | Random videos background (movie/show/musicvideo)|
| Window(Home).Property(SkinHelper.RecentVideosBackground) | Recent videos background (movie or tvshow)|
| Window(Home).Property(SkinHelper.InProgressVideosBackground) | In progress videos background (movie or tvshow)|
| Window(Home).Property(SkinHelper.PvrBackground) | Random fanart collected by the PVR thumbs feature|
| Window(Home).Property(SkinHelper.PicturesBackground) | Random pictures from all picture sources. By default this pulls images from all picture sources the user has configured. It is however possible to provide a custom source from which the images should be pulled from by setting Skin String: SkinHelper.CustomPicturesBackgroundPath|
| Window(Home).Property(SkinHelper.AllMoviesBackground.Wall) | Collection of Movie fanart images (from the library) as wall prebuilt by the script|
| Window(Home).Property(SkinHelper.AllMoviesBackground.Wall.BW) | Collection of Movie fanart images (from the library) as wall (black and white) prebuilt by the script|
| Window(Home).Property(SkinHelper.AllMoviesBackground.Poster.Wall) | Collection of Movie poster images (from the library) as wall prebuilt by the script|
| Window(Home).Property(SkinHelper.AllMoviesBackground.Poster.Wall.BW) | Collection of Movie poster images (from the library) as wall (black and white) prebuilt by the script|
| Window(Home).Property(SkinHelper.AllMusicBackground.Wall) | Collection of Artist fanart images (from the library) as wall prebuilt by the script|
| Window(Home).Property(SkinHelper.AllMusicBackground.Wall.BW) | Collection of Artist fanart images (from the library) as wall (black and white) prebuilt by the script|
| Window(Home).Property(SkinHelper.AllMusicSongsBackground.Wall) | Collection of Song/Album cover images (from the library) as wall prebuilt by the script|
| Window(Home).Property(SkinHelper.AllTvShowsBackground.Wall) | Collection of Tv show fanart images (from the library) as wall prebuilt by the script|
| Window(Home).Property(SkinHelper.AllTvShowsBackground.Wall.BW) | Collection of Tv show fanart images (from the library) as wall (black and white) prebuilt by the script|
| Window(Home).Property(SkinHelper.AllTvShowsBackground.Wall.Poster) | Collection of Tv show poster images (from the library) as wall prebuilt by the script|
| Window(Home).Property(SkinHelper.AllTvShowsBackground.Wall.Poster.BW) | Collection of Tv show poster images (from the library) as wall (black and white) prebuilt by the script|

Additional properties available for the backgrounds (e.g. SkinHelper.AllMoviesBackground.Poster)

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(SkinHelper.BACKGROUNDNAME.poster) | Poster image for the background (if available)|
| Window(Home).Property(SkinHelper.BACKGROUNDNAME.clearlogo) | Clearlogo image for the background (if available)|
| Window(Home).Property(SkinHelper.BACKGROUNDNAME.landscape) | Landscape image for the background (if available)|
| Window(Home).Property(SkinHelper.BACKGROUNDNAME.title) | Title for the background (if available)|

NOTE: the generation of wall images is experimental and might have impact on the cpu while creating them (at startup only). The feature can be disabled in the addon settings.


#### Individual random images for creating image walls yourself in your skin
If you want to create a wall with images yourself in your skin and you need randomly changing images, there is a way to let the script provide these images for you.

First of all you need to enable this by setting the delay in a skin string: Skin.SetString(SkinHelper.WallImagesDelay, 10)
0 disables the feature completely, any other number controls the amount of seconds that the wall will rotate a random image.

Secondly you will have to enable the generation of wall images for each SkinHelper provided background by setting a skin string:
Skin.SetString(BACKGROUNDNAME.EnableWallImages, 20)
This value controls the number of images that should be provided by the script, if empty or 0 there will be no images generated.
Once both the global delay and the item-specific limit skinstrings are set, the images will be available like this: 
Window(Home).Property(BACKGROUNDNAME.Wall.X) (where X is the number of the image, start counting from 0)

You should be able to enable the wall-images feature for any rotating skinhelper background, including those from the smart shortcuts.
Also note that the additional properties will also be available e.g. Window(Home).Property(SkinHelper.AllMoviesBackground.Wall.1.Poster)

Examples...

To get a collection of 10 images from the AllMoviesBackground provided by skinhelper:

Skin.SetString(SkinHelper.AllMoviesBackground.EnableWallImages, 10)

And to get e.g. fanart image 5 from the collection: Window(Home).Property(SkinHelper.AllMoviesBackground.Wall.5)

Or the poster: Window(Home).Property(SkinHelper.AllMoviesBackground.Wall.5.Poster)



Or to get the images for one of the plex smart shortcuts:
Skin.SetString(plexbmc.0.image.EnableWallImages, 10)  --> enable it for 10 images

And to get for example the first fanart image of the collection: Window(Home).Property(plexbmc.0.image.Wall.0)


Last example, get the images for playlists (smart shortcuts for playlists should be enabled!)

Skin.SetString(playlist.0.image.EnableWallImages, 10)  --> enable it for the first playlist and we want 10 images

And to get for example the second fanart image of the collection: Window(Home).Property(playlist.0.image.Wall.1)


The dynamic backgrounds for the smartshortcuts (e.g. playlist.X.image) should be set individually.

It should be pretty safe if you just enable them for all available options, the script checks if the smartshortcuts actually exists.

So ,you should be fine if you do this:

Skin.SetString(playlist.0.image.EnableWallImages, 10)

Skin.SetString(playlist.1.image.EnableWallImages, 10)

Skin.SetString(playlist.2.image.EnableWallImages, 10)

Skin.SetString(playlist.3.image.EnableWallImages, 10)

etc. etc.


CAUTION: The script uses the already cached in memory collections of images to provide you the individual images to build your wall, it does add a little overhead but it should not be noticeable.
What you do have to realize is that if you show for example a wall of 20 fanart images in your skin, all 20 fanart images will be cached by Kodi in memory, this WILL impact the performance.
You might run into problems when using this approach on a low powered platform such as the Raspberry Pi.

To have the least impact on performance as possible, you can use the prebuilt wall images that are provided by this script.
These are already resized into 1 image so that Kodi will only have to load 1 fanart image in memory.

________________________________________________________________________________________________________

### Tools and actions provided by the script
The script provides several tools and actions which you can use in your skin.

________________________________________________________________________________________________________

#### Music library search
```
RunScript(script.skin.helper.service,action=musicsearch)
```
This command will open the default search window for the music library. Might come in handy if you want to create a shortcut to music search from outside the music library window.

________________________________________________________________________________________________________



#### Video library search (extended)
```
RunScript(script.skin.helper.service,action=videosearch)
```
This command will open the special search window in the script. It has a onscreen keyboard to quickly search for movies, tvshows and episodes. You can customize the look and feel of this search dialog. To do that include the files script-skin_helper_service-CustomSearch.xml and script-skin_helper_service-CustomInfo.xml in your skin and skin it to your needs.

________________________________________________________________________________________________________


#### Special Info Dialog
```
RunScript(script.skin.helper.service,action=showinfo,movieid=&amp;INFO[ListItem.DBID])
RunScript(script.skin.helper.service,action=showinfo,tvshowid=&amp;INFO[ListItem.DBID])
RunScript(script.skin.helper.service,action=showinfo,episodeid=&amp;INFO[ListItem.DBID])
```
It is possible to show the infodialog provided by the script (see video library search command), for example if you want to call that info screen from your widgets.
In that case run the command above. In the info dialog will also all special properties be available from the script.
Note that ListItem.DBID and ListItem.DBTYPE can only be used for "real" library items, for widgets provided by this script, use ListItem.Property(DBID) and ListItem.Property(type) instead.

________________________________________________________________________________________________________

#### Yes/No Dialog (dialogYesNo)
```
RunScript(script.skin.helper.service,action=dialogyesno,header[yourheadertext],message=[your message body],action=[your action])
```
This command will open Kodi's YesNo dialog with the text you supplied.
If the user presses YES, the action will be executed you supplied. To provide multiple actions, seperate by | 
________________________________________________________________________________________________________


#### Message Dialog (dialogOK)
```
RunScript(script.skin.helper.service,action=dialogok,header[yourheadertext],message=[your message body])
```
This command will open Kodi's dialog OK window with the text you supplied
________________________________________________________________________________________________________


#### Message Dialog (textviewer)
```
RunScript(script.skin.helper.service,action=textviewer,header[yourheadertext],message=[your message body])
```
This command will open Kodi's TextViewer window with the text you supplied (NOTE: textviewer is available as of Kodi Jarvis 16)
________________________________________________________________________________________________________



#### Color Picker
```
RunScript(script.skin.helper.service,action=colorpicker,skinstring=XXX)
```
This command will open the color picker of the script. After the user selected a color, the color will be stored in the skin string. Required parameters:
- skinstring: Skin String inwhich the value of the color (ARGB) will be stored.

In your skin you can just use the skin string to color a control, example: <textcolor>$INFO[Skin.String(defaultLabelColor)]</textcolor>

Notes: 
1) If you want to display the name of the selected color, add a prefix .name to your skin string.
For example: <label>Default color for labels: $INFO[Skin.String(defaultLabelColor.name)]</label>

2) If you want to customize the look and feel of the color picker window, make sure to include script-skin_helper_service-ColorPicker.xml in your skin and skin it to your needs.

3) If you want to specify the header title of the color picker, make sure to include a label with ID 1 in the XML and add the header= parameter when you launch the script.
For example: RunScript(script.skin.helper.service,action=colorpicker,skinstring=MySkinString,header=Set the OSD Foreground Color)

4) By default the colorpicker will provide a list of available colors.
If you want to provide that list yourself, create a file "colors.xml" in skin\extras\colors\colors.xml
See the default colors file in the script's location, subfolder resources\colors

##### Set a skinshortcuts property with the color
If you want to set a Window(home) Property instead of a skin settings:
RunScript(script.skin.helper.service,action=colorpicker,winproperty=XXX)

If you want to use the color picker to store the color in a shortcut-property from the skinshortcuts script, 
include a button in your script-skinshortcuts.xml with this onclick-action:

RunScript(script.skin.helper.service,action=colorpicker,shortcutproperty=XXX)


##### Multiple color palettes
The color picker supports having multiple color palettes in your colors.xml.
The structure of your colors.xml file will then be layered, like this:
'''xml
<colors>
    <palette name="mypalette1">
        <color name="color1">ffffffff</color>
    </palette>
</colors>
'''
If you do not create the palette sublevel in your colors.xml, the script will just display all <color> tags.
If you have specified multiple palettes you can use a button with ID 3030 to switch between color palettes.
Also it is possible to launch the color picker with a specific palette, in that case supply the palette= parameter when you open the picker, for example:

RunScript(script.skin.helper.service,action=colorpicker,skinstring=MySkinString,palette=mypalette1)

________________________________________________________________________________________________________


#### Webservice --> $INFO images inside list/panel containers and image lookups
This script comes with a little web-helper service to retrieve images that are normally only available as window property and/or only available for the current focused listitem, such as the pvr artwork or music artwork.
NOTE: The scripts webservice runs on tcp port 52307. This is currently hardcoded because there is no way to pass the port as an variable to the skin inside a list (which was the whole purpose of the webservice in the first place)

The following use-cases are currently supported:

##### PVR images inside lists
All Windows properties for the PVR-thumbs feature only provided for the current selected listitem.
If you want to use them inside a panel (so you can list all channels with correct artwork), you can use the webservice:

```xml
<control type="image">
    <!--pvr thumb image-->
    <texture background="true">http://localhost:52307/getpvrthumb&amp;title=$INFO[Listitem.Title]&amp;channel=$INFO[ListItem.ChannelName]&amp;type=poster</texture>
    <visible>Skin.HasSetting(SkinHelper.EnablePVRThumbs) + SubString(ListItem.FolderPath,pvr://)</visible>
</control>
```
The above example will return the PVR artwork, you can specify the type that should be returned with type=[kodi artwork type]
You can also supply multiple arttypes by using , (comma) as a seperator. In that case the script will supply the image for the first arttype found.

Optional parameter: fallback --> Allows you to set a fallback image if no image was found.
For example &amp;fallback=$INFO[ListItem.Icon]

##### General thumb/image for searchphrase
You can use this to search for a general thumb using google images. For example to get a actor thumb.

```xml
<control type="image">
    <!--thumb image-->
    <texture background="true">http://localhost:52307/getthumb&amp;title=$INFO[Listitem.Label]</texture>
</control>
```
The argument to pass is title which will be the searchphrase. In the above example replace $INFO[Listitem.Label] with any other infolabel or text.
For example inside DialogVideoInfo.xml to supply a thumb of the director:

<texture background="true">http://localhost:52307/getthumb&amp;title=$INFO[Listitem.Director] IMDB</texture>

Optional parameter: fallback --> Allows you to set a fallback image if no image was found.
For example &amp;fallback=DefaultDirector.png

##### Music Artwork
You can use this to have the music artwork inside a list/panel container.

```xml
<control type="image">
    <!--music artwork-->
    <texture background="true">http://localhost:52307/getmusicart&amp;artist=$INFO[Listitem.Artist]&amp;track=$INFO[Listitem.Title]&amp;album=$INFO[Listitem.Album]&amp;type=banner,clearlogo,discart</texture>
</control>
```
The arguments to pass are album, track and artist. You can supply all of them or just a selection (e.g. artist+album)
Possibilities are banner, clearlogo and discart for music artwork. Fanart and album thumb should be provided by Kodi itself.

Optional parameter: fallback --> Allows you to set a fallback image if no image was found.
For example &amp;fallback=$INFO[ListItem.Thumb]


##### Image from skin string or window property inside a panel
Normally $INFO window properties or skin string can't be used inside a container.
With this little workaround you can also use them inside containers...

```xml
<control type="image">
    <!--music artwork-->
    <texture background="true">http://localhost:52307/getvarimage&amp;title=$INFO{Window(Home).Property(MyCustomWindowProp)}</texture>
</control>
```

You provide the window property (or any other $INFO label as the title param. Note that you must replace the normal [] brackets with {}
At the moment it is not possible to use this approach for the new resource images addons due to a bug in Kodi: http://trac.kodi.tv/ticket/16366

http://localhost:52307/getvarimage&amp;title=$INFO{Skin.String(MyCustomPath)}/logo.png



##### Genre images
You can use this to create a custom view for movie/tvshow genres with posters/fanart from the genre

```xml
<texture background="true">http://localhost:52307/getmoviegenreimages&amp;title=$INFO[Listitem.Label]&amp;type=poster.0&amp;fallback=DefaultGenre.png</texture>
<texture background="true">http://localhost:52307/gettvshowgenreimages&amp;title=$INFO[Listitem.Label]&amp;type=poster.0&amp;fallback=DefaultGenre.png</texture>
<texture background="true">http://localhost:52307/getmoviegenreimages&amp;title=$INFO[Listitem.Label]&amp;type=fanart.0&amp;fallback=DefaultGenre.png</texture>
<texture background="true">http://localhost:52307/gettvshowgenreimages&amp;title=$INFO[Listitem.Label]&amp;type=fanart.0&amp;fallback=DefaultGenre.png</texture>
```
Possible types are poster.X and fanart.X (replace X with count, only 0-4 are available)



##### Webservice optional params

Optional parameter: fallback --> Allows you to set a fallback image if no image was found.
For example &amp;fallback=$INFO[ListItem.Thumb]

Optional parameter: refresh --> By default the textures are cached by Kodi's texture cache which can be sticky when the underlying image was changed. Use an refresh param to force refresh.
For example &amp;refresh=$INFO[System.Time(hh)]

________________________________________________________________________________________________________



#### Youtube search
Shows a selectdialog with all searchresults found by the Youtube plugin, for example to search for trailers in DialogVideoInfo.xml.
The benefit of that is that user stays in the same window and is not moved away from the library to the youtube plugin.
You can supply a searchphrase to the script and optionally provide a label for the header in the DialogSelect.

RunScript(script.skin.helper.service,action=searchyoutube,title=[SEARCHPHRASE],header=[HEADER FOR THE DIALOGSELECT]

TIP: The results of the script displayed in DialogSelect.xml will have the label2 of the ListItem set to the description.

example 1: Search for trailers in DialogVideoInfo.xml
```xml
<control type="button">
	<label>YouTube $LOCALIZE[20410]</label>
	<onclick condition="System.HasAddon(plugin.video.youtube)">RunScript(script.skin.helper.service,action=searchyoutube,title=$INFO[ListItem.Title] Trailer,header=Search YouTube Trailers)</onclick>
	<onclick condition="!System.HasAddon(plugin.video.youtube)">ActivateWindow(Videos,plugin://plugin.video.youtube)</onclick>
	<visible>Container.Content(movies)</visible>
</control>
           
```
example 2: Search for artist videos in DialogAlbumInfo.xml
```
RunScript(script.skin.helper.service,action=searchyoutube,title=$INFO[ListItem.Artist], header=Videos for $INFO[ListItem.Artist])             
```

Optional parameters:
windowed=true --> plays the selected video windowed instead of fullscreen
autoplay=true --> just automatically play the first video that is found (no dialog is shown)

________________________________________________________________________________________________________



#### Busy spinner selector
Allows the user to select a busy spinner from some predefined ones in your skin. It supports both multiimage (folder with images) and single image (.gif) spinners. The user can provide his own texture(s) or select from predefined spinners in the skin.

```
RunScript(script.skin.helper.service,action=busytexture)             
```
The script fills this Skin Strings after selection: 
SkinHelper.SpinnerTexture --> the name of the selected busy texture
SkinHelper.SpinnerTexturePath --> The full path of the selected busy texture

#####To provide busy spinners with your skin:
- Make sure to create a directory "busy_spinners" in your skin's extras folder.
- Inside that directory you can put subdirectories for multimage spinners or just gif files in the root.

#####To use the busy texture
Make sure that you use a multiimage control in DialogBusy.xml. Example code:
```xml
<control type="multiimage">
	<width>150</width>
	<height>150</height>
	<aspectratio>keep</aspectratio>
	<imagepath>$INFO[Skin.String(SkinHelper.SpinnerTexturePath)]</imagepath>
	<timeperimage>100</timeperimage>
	<colordiffuse>$INFO[Skin.String(SpinnerTextureColor)]</colordiffuse>
	<fadetime>0</fadetime>
	<visible>!Skin.String(SkinHelper.SpinnerTexturePath,None)</visible>
</control>
```


________________________________________________________________________________________________________

#### Conditional Background overrides
Allows the user to globally override the skin's background on certain date conditions.
For example setup a christmas background at late december etc.
By launching this script entrypoint the user will be presented with a dialog to add, delete and edit conditional overrides.

```
RunScript(script.skin.helper.service,action=conditionalbackgrounds)             
```

#####To use the conditional background in your skin
If a background is active the window property "Window(home).Property(SkinHelper.ConditionalBackground)" will be filled by the service.


________________________________________________________________________________________________________

#### Toggle Kodi setting
Can be used to set/unset a specific Kodi system setting (boolean).

```
RunScript(script.skin.helper.service,action=togglekodisetting,setting=[NAME OF THE SETTING IN GUISETTINGS])             
```
You must supply the name of the setting as can be found in guisettings.xml or the Json API

#####Example: Toggle the RSS feed
```
<!--toggle rss feed-->
<control type="radiobutton" id="123456">
    <label>Show RSS Feed</label>
    <onclick>XBMC.RunScript(script.skin.helper.service,action=togglekodisetting,setting=lookandfeel.enablerssfeeds)</onclick>
    <selected>system.getbool(lookandfeel.enablerssfeeds)</selected>
</control>
```

________________________________________________________________________________________________________

#### Strip string
Can be used to strip/split a string, the results will be stored to a window property.

```
RunScript(script.skin.helper.service,action=stripstring,splitchar=[splitter text],string=[your string],output=[your window prop])             
```

Example:

<onload>RunScript(script.skin.helper.service,action=stripstrin,splitchar=.,string=$INFO[System.BuildVersion],output=kodiversion_main)</onload>

The above command will take the Kodi Buildversion Info string and split it on the "." character. The result is the main Kodi version, e.g. "15" or "16".
You can access the result in your skin as a window property, in the above example kodiversion_main:
$INFO[Window(Home).Property(kodiversion_main)]

Optional argument: index
Used to specify which part to return after splitting the string, start counting at 0|
For example:

<onload>RunScript(script.skin.helper.service,action=stripstrin,splitchar=#,string=this#is#a#test,output=kodiversion_main,index=1)</onload>
will return "is" in the result

________________________________________________________________________________________________________


#### Check if file exists
```
RunScript(script.skin.helper.service,action=fileexists,file=[filenamepath],skinstring=[skinstring to store the result],windowprop=[windowprop to store the result])
```
This command will check the filesystem if a particular file exists and will write the results to either a skin string or window property.
If the file exists, the result will be written as EXISTS in the property or skinstring, if it doesn't exist, the property/string will be empty.
________________________________________________________________________________________________________




#### Set skin setting
Can be used to present a select dialog to specify a certain skin setting.
Prevents you from creating all kinds of toggle options.


You need to create the file skinsettings.xml in your extras folder (special://skin/extras/skinsettings.xml).
Inside that xml file you define all options that a user can choose when setting a specific skin string.
For example:
```xml
<settings>
    <!-- home layout -->
    <setting id="HomeLayout" value="1" label="$LOCALIZE[31309] - 1 row" condition="" icon="" description=""/>
    <setting id="HomeLayout" value="2" label="$LOCALIZE[31309] - 2 rows" condition="" icon="" description="" default="true"/>
    <setting id="HomeLayout" value="3" label="$LOCALIZE[31309] - 3 rows" condition="" icon="" description=""/>
    
    <!-- background setting -->
    <setting id="CustomBackgroundSetting" value="default" label="$LOCALIZE[31023]" condition="" icon="special://skin/extras/backgrounds/global.jpg" description=""/>
    <setting id="CustomBackgroundSetting" value="weather" label="$LOCALIZE[31025]" condition="" icon="$VAR[WeatherFanArtPath]$INFO[Window(Weather).Property(current.fanartCode)]/weather.jpg" description=""/>
    <setting id="CustomBackgroundSetting" value="||BROWSEIMAGE||" label="Custom image" condition="" description=""/>
</settings>
```

If you want to set the Skin String "HomeLayout", you can call the script like this:

```
<control type="button" id="423003">
    <label>[B]$LOCALIZE[31121]:[/B] $INFO[Skin.String(HomeLayout.label)]</label>
    <onclick>RunScript(script.skin.helper.service,action=setskinsetting,setting=HomeLayout,header=$LOCALIZE[31124])</onclick>
</control>         
```
This will present DialogSelect with your options. Once the user makes a selection, the value will be written to the Skin String.
Also the prefix .label will store the label from the select dialog.

Attributes for the XML:

id: name of the setting, required attribute
value: the value that should be written when selecting this value, required attribute
label: label for the option (will also be written to setting.label), required attribute
condition: any kodi condition syntax to make the option show up or not, optional but attribute must be present in the xml
icon: icon to show in dialogselect, optional but attribute must be present in the xml
description: description to show in dialogselect (label2), optional but attribute must be present in the xml
default: if set to "true" this will be the default value for your skin (will be set at skin startup/change/update), you may use a visibility condition instead of true


#### Working with sublevels

It's possible to have a sublevel in the settings dialog, for example if you have many options for one setting.
This way you can have layered navigation.
Syntax:

```
<settings>
    <!-- home layout -->
    <setting id="HomeLayout" value="||SUBLEVEL||HomeLayout_horizontal" label="Horizontal home layouts" condition="" icon="" description="All horizontal homemenu layouts"/>
    <setting id="HomeLayout" value="tiles" label="Tile based layout" condition="" icon="" description=""/>
    
    <!-- sublevel: horizontal home layouts -->
    <setting id="HomeLayout_horizontal" value="layout1" label="Horizontal layout 1" condition="" icon="" description="" />
    <setting id="HomeLayout_horizontal" value="layout2" label="Horizontal layout 2" condition="" icon="" description="" />

</settings>
```

#### Special values to use as the value argument

Instead of a predefined value you can also have an option to let the user input the value himself.
In that case you have to use a special syntax as the value:

||PROMPTNUMERIC|| --> Asks the user for a numeric input

||PROMPTSTRING|| --> Asks the user for a string input

||PROMPTSTRINGASNUMERIC|| --> Asks the user for a string which must be numeric (allows having negative numbers)

||BROWSEIMAGE|| --> Asks the user to select a single image or imagepath

||BROWSESINGLEIMAGE|| --> Asks the user to select a single image

||SKIPSTRING|| --> Do not write the results to a skin string (can be used if you only use the script with the onselect actions)


#### Apply other actions when user selects a value

It is possible to apply other settings when the user selects a certain value.
Syntax:

```
<settings>
    <setting id="HomeLayout" value="mylayout" label="My great layout" condition="" icon="" description="">
        <onselect condition="True">Skin.Reset(OpenSubMenuOnClick)</onselect>
        <onselect condition="True">Skin.SetString(widgetstyle,landscape)</onselect>
    </setting>

</settings>
```

#### Multiselect

If you have some sort of multiple options the user can enable and you don't want to create a whole bunch of radiobuttons (and set default values)..
Syntax:

```
    <!-- options to show in videoinfo - multiselect -->
    <setting id="videoinfo_buttons" value="||MULTISELECT||" label="" condition="" icon="" description="">
        <option id="videoinfo_button_play" label="$LOCALIZE[208]" condition="" default="true"/>
        <option id="videoinfo_button_trailer" label="$LOCALIZE[20410]" condition="" default="true"/>
        <option id="videoinfo_button_cast" label="$LOCALIZE[206]" condition="" default="true"/>
    </setting>
```

The ID specified in the option will be set as Skin Bool.
E.g. if you call the script with RunScript(script.skin.helper.service,action=setskinsetting,setting=videoinfo_buttons,header=Enable buttons in videoinfo)
If the user enables the playbutton, the command Skin.SetBool(videoinfo_button_play) will be called, otherwise it will be reset.
With the default attribute you can specify what the default value should be for the setting (applied at skin startup, change or update)


#### Write constants to includes file
You can use the above described approach for skin settings to write constants to an includes file.
For this you can use the same settings file with the same xml elements etc.
Only, instead of calling "setskinsetting", you should call "setskinconstant".
Any value that is selected by the user will be written to an XML file in your skin directory called script-skin_helper_service-includes.xml

```
RunScript(script.skin.helper.service,action=setskinconstant,setting=PanelWidth,header=Width for Panel)
```

On your defined <skinsettings> you may use the additional attribute constantdefault="MyVisibilityCondition" to set your default value at skin install/update.
________________________________________________________________________________________________________


#### Splash screen / skin intro 
Can be used to easily provide a splash/intro option to your skin.
Supports all media files: music, video or photo.

First, set the setting somewhere in your skin settings, for example with this code:

```
control type="radiobutton">
    <label>Enable splash screen (photo, video or music)</label>
    <onclick condition="!Skin.String(SplashScreen)">Skin.SetFile(SplashScreen)</onclick>
    <onclick condition="Skin.String(SplashScreen)">Skin.Reset(SplashScreen)</onclick>
    <selected>Skin.String(SplashScreen)</selected>
</control>
```

Secondly you have to adjust your Startup.xml from your skin to support the splash intro:

```
<onload condition="Skin.String(SplashScreen)">RunScript(script.skin.helper.service,action=splashscreen,file=$INFO[Skin.String(SplashScreen)],duration=5)</onload>
<onload condition="!Skin.String(SplashScreen)">ReplaceWindow($INFO[System.StartupWindow])</onload>         
```

and you need to add both a videowindow and image control to your startup.xml:

```
<!-- video control for splash -->
<control type="videowindow">
    <width>100%</width>
    <height>100%</height>
</control>
<!-- image control for splash -->
<control type="image">
    <width>100%</width>
    <height>100%</height>
    <aspectratio>keep</aspectratio>
    <texture background="true">$INFO[Window(Home).Property(SkinHelper.SplashScreen)]</texture>
</control>
```

Offcourse make sure to remove any other references which replaces the window...
The duration parameter is optional, this will set the amount of seconds that an image will be shown as splash, defaults to 5 seconds if ommitted.
Music and video files always default to play to the end before closing the splash screen.


________________________________________________________________________________________________________

#### Views selector
```
RunScript(script.skin.helper.service,action=setview)               
```
This feature shows the user a select dialog with all the views that are available. This replaces the default "toggle" button in the MyXXNav.xml windows. Note that you must create a views.xml file in your skin's extras folder. The selection dialog is built from that views.xml file and auto checks the visibility conditions so a view will only be shown if it's suitable for the current media content.

*example content of the views.xml file (to be placed in extras folder of your skin):*
```xml
<views>
    <view id="List" value="50" languageid="31443" type="all"/>
	  <view id="Thumbs details" value="512" languageid="31439" type="movies,setmovies,tvshows,musicvideos,seasons,sets,episodes,artists,albums,songs,tvchannels,tvrecordings,programs,pictures" />
	  <view id="Poster Shift" value="514" languageid="31441" type="movies,setmovies,tvshows,musicvideos,seasons,sets" />
</views>
```
id = the unlocalized version of the views name.
value = the skin view ID.
languageid = localized label ID.
type = the type of content the view is suitable for, use "all" to support all types. 

Supported types are currently: movies,setmovies,tvshows,musicvideos,seasons,sets,episodes,artists,albums,songs,tvchannels,tvrecordings,programs,pictures

Note: If you want a thumbnail of the view displayed in the select dialog, you need to create some small screenshots of your views and place them in your skin's extras folder:
- in your skin\extras folder, create a subfolder "viewthumbs"
- inside that viewthumbs folder save a .JPG file (screenshot) for all your views. Save them as [VIEWID].jpg where [VIEWID] is the numeric ID of the view.

________________________________________________________________________________________________________



#### Enable views
```
RunScript(script.skin.helper.service,action=enableviews)             
```
This will present a selection dialog to the user to enable (or disable) views. It uses the views.xml file to display the available views (see above). When a view is disabled it will be hidden from the view selection dialog. Also, a Skin String will be set so you can check in your skin if the view has been disabled (and not include it or set a visiblity condition).
The name of the Skin String that will be set by the script is: SkinHelper.View.Disabled.[VIEWID] where [VIEWID] is the numerical ID of the view.

Example: 
```xml
<include condition="!Skin.HasSetting(SkinHelper.View.Disabled.55)">View_55_BannerList</include>
```
________________________________________________________________________________________________________



#### Set Forced views
```
RunScript(script.skin.helper.service,action=setforcedview,contenttype=[TYPE])             
```
The script can help you to set a forced view for a specific contenttype in your skin. For example if the user wants to set the list view for all tvshow content etc. For [TYPE] you must fill in one of the content types, see above at "Views selector". When a button is pressed with the above command, a select dialog appears and the user can choose on of the available views. Disabled views and views that aren't suitable for the specified type are hidden from the list.
When the user made a choice from the list a Skin String will be filled by the script: SkinHelper.ForcedViews.[TYPE]
The value of that skin string is the numeric ID of the selected view.

Note: It is recommended that you create a Skin toggle to enable/disable the forced views feature.

Note 2: When the user select another view in the normal viewselector, the forcedview setting will also be set to the newly chosen view.



##### How to use the forced views feature in your skin?

Example code to use in your skin settings:

```xml
<control type="radiobutton" id="6009">
	<label>Enable forced views</label>
	<onclick>Skin.ToggleSetting(SkinHelper.ForcedViews.Enabled)</onclick>
	<selected>Skin.HasSetting(SkinHelper.ForcedViews.Enabled)</selected>
</control>
<control type="button" id="6010">
	<onclick>RunScript(script.skin.helper.service,action=setforcedview,contenttype=movies)</onclick>
	<visible>Skin.HasSetting(SkinHelper.ForcedViews.Enabled)</visible>
	<label>Forced view for movies: $INFO[Skin.String(SkinHelper.ForcedViews.movies)]</label>
</control>
<control type="button" id="6011">
	<onclick>RunScript(script.skin.helper.service,action=setforcedview,contenttype=tvshows)</onclick>
	<visible>Skin.HasSetting(SkinHelper.ForcedViews.Enabled)</visible>
	<label>Forced view for tv shows:  $INFO[Skin.String(SkinHelper.ForcedViews.tvshows)]</label>
</control>
<control type="button" id="6012">
	<onclick>RunScript(script.skin.helper.service,action=setforcedview,contenttype=seasons)</onclick>
	<visible>Skin.HasSetting(SkinHelper.ForcedViews.Enabled)</visible>
	<label>Forced view for seasons:  $INFO[Skin.String(SkinHelper.ForcedViews.seasons)]</label>
</control>
<control type="button" id="6013">
	<onclick>RunScript(script.skin.helper.service,action=setforcedview,contenttype=episodes)</onclick>
	<visible>Skin.HasSetting(SkinHelper.ForcedViews.Enabled)</visible>
	<label>Forced view for episodes: $INFO[Skin.String(SkinHelper.ForcedViews.episodes)]</label>
	<font>Reg28</font>
</control>
<control type="button" id="6014">
	<onclick>RunScript(script.skin.helper.service,action=setforcedview,contenttype=sets)</onclick>
	<visible>Skin.HasSetting(SkinHelper.ForcedViews.Enabled)</visible>
	<label>Forced view for movie sets: $INFO[Skin.String(SkinHelper.ForcedViews.sets)]</label>
</control>
<control type="button" id="6015">
	<onclick>RunScript(script.skin.helper.service,action=setforcedview,contenttype=setmovies)</onclick>
	<visible>Skin.HasSetting(SkinHelper.ForcedViews.Enabled)</visible>
	<label>Forced view for movies inside set: $INFO[Skin.String(SkinHelper.ForcedViews.setmovies)]</label>
</control>
```

the above example can off course be extended with other view types, such as pvr channels etc.

Example code to use for your views visibility conditions:
```xml
<control type="panel" id="51">
	<visible>StringCompare(Window(Home).Property(SkinHelper.ForcedView),53) | IsEmpty(Window(Home).Property(SkinHelper.ForcedView))</visible>
</control>
```
Note: The forced view visibility condition has to be added to all view controls in order to work properly. The ForcedView window property will only be set if you have set this bool to true in your skin: SkinHelper.ForcedViews.Enabled


________________________________________________________________________________________________________
________________________________________________________________________________________________________

### Color themes feature
The script comes with a color theme feature. Basically it's just a simplified version of the skin backup/restore feature but it only backs up the colorsettings. Color Themes has the following features:

- Present a list of skin provided color themes including screenshots.
- Let's the user save his custom settings to a color theme.
- Let's the user export his custom color theme to file.
- Let's the user import a custom color theme from file.

#####To present the dialog with all available color themes:
```
<control type="button">
	<onclick>RunScript(script.skin.helper.service,action=colorthemes)</onclick>
	<label>$ADDON[script.skin.helper.service 32085]</label>
    <description>Manage Color Themes</description>
</control>
RunScript(script.skin.helper.service,action=colorthemes)             
```



#####Provide color themes with your skin
It is possible to deliver skin provided color themes. Those colorthemes should be stored in the skin's extras\skinthemes folder.
If you want to create one or more skinprovided color themes (for example the defaults):
- Create a folder "skinthemes" in your skin's "extras" folder. 
- Make all color modifications in your skin to represent the colortheme
- Hit the button to save your colortheme (createcolortheme command)
- Name it and select the correct screenshot
- On the filesystem navigate to Kodi userdata\addon_data\[YOURSKIN]\themes
- Copy both the themename.theme and the themename.jpg file to your above created skinthemes directory
- Do this action for every theme you want to include in your skin.
- It is possible to change the description of the theme, just open the .themes file in a texteditor. You can change both the THEMENAME and the DESCRIPTION values to your needs.

#####What settings are stored in the theme file ?
All Skin Settings settings that contain one of these words: color, opacity, texture.
Also the skin's theme will be saved (if any). So, to make sure the skin themes feature works properly you must be sure that all of your color-settings contain the word color. If any more words should be supported, please ask.


#####Automatically set a color theme at day/night
You can have the script set a specified theme during day or night.
This will allow the user to have some more relaxing colors at night time and more fluid/bright during day time.

To enable this feature you must set the skin Bool SkinHelper.EnableDayNightThemes to true.

To setup the theme (and time) to use at day time:  XBMC.RunScript(script.skin.helper.service,action=ColorThemes,daynight=day)
To setup the theme (and time) to use at night time:  XBMC.RunScript(script.skin.helper.service,action=ColorThemes,daynight=night)

The script will auto set the correct theme at the specified times and fill these Skin Settings:
Skin.String(SkinHelper.ColorTheme.[day/night] --> A formatted string of the selected theme and the time it will apply for day or night
Skin.String(SkinHelper.ColorTheme.[day/night].theme --> Only the name of the chosen theme
Skin.String(SkinHelper.ColorTheme.[day/night].time --> Only the time of the chosen theme
Skin.String(SkinHelper.ColorTheme.[day/night].file --> Only the filename of the chosen theme
SkinHelper.LastColorTheme --> This will always hold the name of the last chosen theme (also if this day/night mode is disabled)

Some example code to use:

```xml
<control type="radiobutton" id="15033">
    <label>Enable day/night color themes</label>
    <onclick>Skin.ToggleSetting(SkinHelper.EnableDayNightThemes)</onclick>
    <selected>Skin.HasSetting(SkinHelper.EnableDayNightThemes)</selected>
</control>

<control type="button" id="15034">
    <label>Theme to use at day time: $INFO[Skin.String(SkinHelper.ColorTheme.Day)]</label>
    <onclick>XBMC.RunScript(script.skin.helper.service,action=ColorThemes,daynight=day)</onclick>
    <visible>Skin.HasSetting(SkinHelper.EnableDayNightThemes)</visible>
</control>
<control type="button" id="15035">
    <label>Theme to use at night time: $INFO[Skin.String(SkinHelper.ColorTheme.Night)]</label>
    <onclick>XBMC.RunScript(script.skin.helper.service,action=ColorThemes,daynight=night)</onclick>
    <visible>Skin.HasSetting(SkinHelper.EnableDayNightThemes)</visible>
</control>
```

________________________________________________________________________________________________________
________________________________________________________________________________________________________

### Skin backup feature
The script comes with a backup/restore feature. It supports backup of ALL skin settings including skin shortcuts (when script.skinshortcuts is also used). 

- Backup all settings to file
- Restore all settings from file
- Reset the skin to default settings (wipe all settings)

#####To backup the skin settings (including preferences for skinshortcuts):
```
RunScript(script.skin.helper.service,action=backup)             
```

It is possible to apply a filter to the backup. In that case only skin settings containing a specific phrase will be back upped.
Can be usefull if you want to use the backup function for something else in your skin.
To use the filter you have to add the filter= argument and supply one or more phrases (separated by |)
For example:
RunScript(script.skin.helper.service,action=backup,filter=color|view|font)    
The filter is not case sensitive


If you want to prompt the user for the filename (instead of auto generating one), you can supply the promptfilename=true parameter to the script.


If you want to silently perform a backup, you can supply the silent= parameter with the full path to the zipfile that has to be created.
RunScript(script.skin.helper.service,action=backup,silent=mypath\backup.zip)    


#####To restore the skin settings:
```
RunScript(script.skin.helper.service,action=restore)             
```

If you want to silently restore a backup, you can supply the silent= parameter with the full path to the zipfile that has to be restored.
RunScript(script.skin.helper.service,action=restore,silent=mypath\backup.zip)    


#####To reset the skin to defaults:
```
RunScript(script.skin.helper.service,action=reset)             
```
This will reset ALL skin settings.
Both the filter and silent arguments will also work with the reset feature.

________________________________________________________________________________________________________
________________________________________________________________________________________________________

### Dynamic content provider
The script also has a plugin entrypoint to provide some dynamic content that can be used for example in widgets.
use the parameter [LIMIT] to define the number of items to show in the list. defaults to 25 if the parameter is not supplied.


#####Next Episodes
```
plugin://script.skin.helper.service/?action=nextepisodes&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload)]
```
Provides a list of the nextup episodes. This can be the first episode in progress from a tv show or the next unwatched from a in progress show.
Note: the reload parameter is needed to auto refresh the widget when the content has changed.

________________________________________________________________________________________________________

#####Recommended Movies
```
plugin://script.skin.helper.service/?action=recommendedmovies&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload)]
```
Provides a list of the in progress movies AND recommended movies based on rating.
Note: the reload parameter is needed to auto refresh the widget when the content has changed.

________________________________________________________________________________________________________

#####Recommended Media
```
plugin://script.skin.helper.service/?action=recommendedmedia&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides a list of recommended media (movies, tv shows, music)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.

________________________________________________________________________________________________________

#####Recent albums
```
plugin://script.skin.helper.service/?action=recentalbums&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreloadmusic)]
```
Provides a list of recently added albums, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.

Optional argument: browse=true --> will open/browse the album instead of playing it
________________________________________________________________________________________________________

#####Recently played albums
```
plugin://script.skin.helper.service/?action=recentplayedalbums&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreloadmusic)]
```
Provides a list of recently played albums, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.

Optional argument: browse=true --> will open/browse the album instead of playing it
________________________________________________________________________________________________________

#####Recommended albums
```
plugin://script.skin.helper.service/?action=recommendedalbums&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreloadmusic)]
```
Provides a list of recommended albums, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.

Optional argument: browse=true --> will open/browse the album instead of playing it
________________________________________________________________________________________________________

#####Recent songs
```
plugin://script.skin.helper.service/?action=recentsongs&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreloadmusic)]
```
Provides a list of recently added songs, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.
________________________________________________________________________________________________________

#####Recently played songs
```
plugin://script.skin.helper.service/?action=recentplayedsongs&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreloadmusic)]
```
Provides a list of recently played songs, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.
________________________________________________________________________________________________________

#####Recommended songs
```
plugin://script.skin.helper.service/?action=recommendedsongs&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreloadmusic)]
```
Provides a list of recommended songs, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.
________________________________________________________________________________________________________

#####Recent Media
```
plugin://script.skin.helper.service/?action=recentmedia&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides a list of recently added media (movies, tv shows, music, tv recordings, musicvideos)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.


________________________________________________________________________________________________________

#####Similar Movies (because you watched...)
```
plugin://script.skin.helper.service/?action=similarmovies&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with movies that are similar to a random watched movie from the library.
TIP: The listitem provided by this list will have a property "similartitle" which contains the movie from which this list is generated. That way you can create a "Because you watched $INFO[Container.ListItem.Property(originaltitle)]" label....
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

The above command will create a similar movies listing based on a random watched movie in the library.
If you want to specify the movie to base the request on yourself you can optionally specify the imdb id to the script:

```
plugin://script.skin.helper.service/?action=similarmovies&amp;imdbid=[IMDBID]&amp;limit=[LIMIT]
```

________________________________________________________________________________________________________

#####Similar Tv Shows (because you watched...)
```
plugin://script.skin.helper.service/?action=similarshows&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with TV shows that are similar to a random in progress show from the library.
TIP: The listitem provided by this list will have a property "similartitle" which contains the movie from which this list is generated. That way you can create a "Because you watched $INFO[Container.ListItem.Property(originaltitle)]" label....
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

The above command will create a similar shows listing based on a random in progress show in the library.
If you want to specify the show to base the request on yourself you can optionally specify the imdb/tvdb id to the script:

```
plugin://script.skin.helper.service/?action=similarshows&amp;imdbid=[IMDBID]&amp;limit=[LIMIT]
```

________________________________________________________________________________________________________

#####Similar Media (because you watched...)
```
plugin://script.skin.helper.service/?action=similarmedia&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with both Movies and TV shows that are similar to a random in progress movie or show from the library.
TIP: The listitem provided by this list will have a property "similartitle" which contains the movie from which this list is generated. That way you can create a "Because you watched $INFO[Container.ListItem.Property(originaltitle)]" label....
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

The above command will create a similar shows listing based on a random in progress show in the library.
If you want to specify the movie/show to base the request on yourself you can optionally specify the imdb/tvdb id to the script:

```
plugin://script.skin.helper.service/?action=similarshows&amp;imdbid=[IMDBID]&amp;limit=[LIMIT]
```

________________________________________________________________________________________________________

#####Top rated Movies in genre
```
plugin://script.skin.helper.service/?action=moviesforgenre&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with movies that for a random genre from the library.
TIP: The listitem provided by this list will have a property "genretitle" which contains the movie from which this list is generated.
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

________________________________________________________________________________________________________

#####Top rated tvshows in genre
```
plugin://script.skin.helper.service/?action=showsforgenre&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with tvshows for a random genre from the library.
TIP: The listitem provided by this list will have a property "genretitle" which contains the movie from which this list is generated.
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

________________________________________________________________________________________________________


#####In progress Media
```
plugin://script.skin.helper.service/?action=inprogressmedia&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload)]
```
Provides a list of all in progress media (movies, tv shows, music, musicvideos)
Note: the reload parameter is needed to auto refresh the widget when the content has changed.


________________________________________________________________________________________________________

#####In progress and Recommended Media
```
plugin://script.skin.helper.service/?action=inprogressandrecommendedmedia&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload)]
```
This combines in progress media and recommended media, usefull to prevent an empty widget when no items are in progress.
Note: the reload parameter is needed to auto refresh the widget when the content has changed.

________________________________________________________________________________________________________

#####Favourite Media
```
plugin://script.skin.helper.service/?action=favouritemedia&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides a list of all media items that are added as favourite (movies, tv shows, songs, musicvideos)
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.

________________________________________________________________________________________________________

#####My TV Shows Airing today
```
plugin://script.skin.helper.service/?action=nextairedtvshows&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides a list of the shows from the library that are airing today - requires script.tv.show.next.aired
The listitems will have the properties as described here: http://kodi.wiki/view/Add-on:TV_Show_-_Next_Aired#Airing_today
For example: ListItem.Property(NextTitle)
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.


________________________________________________________________________________________________________

#####PVR TV Channels widget
```
plugin://script.skin.helper.service/?action=pvrchannels&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides the Kodi TV channels as list content, enriched with the artwork provided by this script (where possible).
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.

________________________________________________________________________________________________________

#####PVR Latest Recordings widget
```
plugin://script.skin.helper.service/?action=pvrrecordings&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides the Kodi TV Recordings (sorted by date) as list content, enriched with the artwork provided by this script (where possible).
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.


________________________________________________________________________________________________________

#####Favourites
```
plugin://script.skin.helper.service/?action=favourites&amp;limit=[LIMIT]&amp;reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides the Kodi favourites as list content.
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.

________________________________________________________________________________________________________

#####Cast Details
```
plugin://script.skin.helper.service/?action=getcast&amp;movie=[MOVIENAME OR DBID]
plugin://script.skin.helper.service/?action=getcast&amp;tvshow=[TVSHOW NAME OR DBID]
plugin://script.skin.helper.service/?action=getcast&amp;movieset=[MOVIESET NAME OR DBID]
plugin://script.skin.helper.service/?action=getcast&amp;episode=[EPISODE NAME OR DBID]
```
Provides the Cast list for the specified media type as a listing.
Label = Name of the actor
Label2 = Role
Icon = Thumb of the actor

You can use the name of the item or the DBID to perform the lookup.
There will also a Window Property be set when you use the above query to the script: SkinHelper.ListItemCast --> It will return the cast list seperated by [CR]

Optional parameter: downloadthumbs=true --> will auto download any missing actor thumbs from IMDB


#####Browse Genres
```
plugin://script.skin.helper.service/?action=browsegenres&amp;type=movie&amp;limit=1000
plugin://script.skin.helper.service/?action=browsegenres&amp;type=tvshow&amp;limit=1000
```
Provides the genres listing for movies or tvshows with artwork properties from movies/shows with the genre so you can build custom genre icons.

ListItem.Art(poster.X) --> poster for movie/show X (start counting at 0) in the genre

ListItem.Art(fanart.X) --> fanart for movie/show X (start counting at 0) in the genre


For each genre, only 5 movies/tvshows are retrieved.
________________________________________________________________________________________________________
________________________________________________________________________________________________________

### Smart shortcuts feature
This feature is introduced to be able to provide quick-access shortcuts to specific sections of Kodi, such as user created playlists and favourites and entry points of some 3th party addons such as Emby and Plex. What it does is provide some Window properties about the shortcut. It is most convenient used with the skin shortcuts script but can offcourse be used in any part of your skin. The most important behaviour of the smart shortcuts feature is that is pulls images from the library path so you can have content based backgrounds.


________________________________________________________________________________________________________

##### Smart shortcuts for playlists
Will only be available if this Skin Bool is true --> SmartShortcuts.playlists

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(playlist.X.label) | Title of the playlist|
| Window(Home).Property(playlist.X.action) | Path of the playlist|
| Window(Home).Property(playlist.X.content) | Contentpath (without activatewindow) of the playlist, to display it's content in widgets.|
| Window(Home).Property(playlist.X.image) | Rotating fanart of the playlist|
--> replace X with the item count, starting at 0.


________________________________________________________________________________________________________


##### Smart shortcuts for Kodi Favourites
Will only be available if this Skin Bool is true --> SmartShortcuts.favorites

Note that only favourites will be processed that actually contain video/audio content.

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(favorite.X.label) | Title of the favourite|
| Window(Home).Property(favorite.X.action) | Path of the favourite|
| Window(Home).Property(favorite.X.content) | Contentpath (without activatewindow) of the favourite, to display it's content in widgets.|
| Window(Home).Property(favorite.X.image) | Rotating fanart of the favourite|
--> replace X with the item count, starting at 0.


________________________________________________________________________________________________________



##### Smart shortcuts for Plex addon (plugin.video.plexbmc)
Will only be available if this Skin Bool is true --> SmartShortcuts.plex

Note that the plexbmc addon must be present on the system for this to function.

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(plexbmc.X.title) | Title of the Plex collection|
| Window(Home).Property(plexbmc.X.path) | Path of the Plex collection|
| Window(Home).Property(plexbmc.X.content) | Contentpath (without activatewindow) of the Plex collection, to display it's content in widgets.|
| Window(Home).Property(plexbmc.X.background) | Rotating fanart of the Plex collection|
| Window(Home).Property(plexbmc.X.type) | Type of the Plex collection (e.g. movies, tvshows)|
| Window(Home).Property(plexbmc.X.recent) | Path to the recently added items node of the Plex collection|
| Window(Home).Property(plexbmc.X.recent.content) | Contentpath to the recently added items node of the Plex collection (for widgets)|
| Window(Home).Property(plexbmc.X.recent.background) | Rotating fanart of the recently added items node|
| Window(Home).Property(plexbmc.X.ondeck) | Path to the in progress items node of the Plex collection|
| Window(Home).Property(plexbmc.X.ondeck.content) | Contentpath to the in progress items node of the Plex collection (for widgets)|
| Window(Home).Property(plexbmc.X.ondeck.background) | Rotating fanart of the in progress items node|
| Window(Home).Property(plexbmc.X.unwatched) | Path to the in unwatched items node of the Plex collection|
| Window(Home).Property(plexbmc.X.unwatched.content) | Contentpath to the unwatched items node of the Plex collection (for widgets)|
| Window(Home).Property(plexbmc.X.unwatched.background) | Rotating fanart of the unwatched items node|
| |
| Window(Home).Property(plexbmc.channels.title) | Title of the Plex Channels collection|
| Window(Home).Property(plexbmc.channels.path) | Path to the Plex Channels|
| Window(Home).Property(plexbmc.channels.content) | Contentpath to the Plex Channels (for widgets)|
| Window(Home).Property(plexbmc.channels.background) | Rotating fanart of the Plex Channels|
| |
| Window(Home).Property(plexfanartbg) | A global fanart background from plex sources|
--> replace X with the item count, starting at 0.



________________________________________________________________________________________________________



##### Smart shortcuts for Emby addon (plugin.video.emby)
Will only be available if this Skin Bool is true --> SmartShortcuts.emby

Note that the Emby addon must be present on the system for this to function.

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(emby.nodes.X.title) | Title of the Emby collection|
| Window(Home).Property(emby.nodes.X.path) | Path of the Emby collection|
| Window(Home).Property(emby.nodes.X.content) | Contentpath of the Emby collection (for widgets)|
| Window(Home).Property(emby.nodes.X.image) | Rotating Fanart of the Emby collection|
| Window(Home).Property(emby.nodes.X.type) | Type of the Emby collection (e.g. movies, tvshows)|
| |
| Window(Home).Property(emby.nodes.X.recent.title) | Title of the recently added node for the Emby collection|
| Window(Home).Property(emby.nodes.X.recent.path) | Path of the recently added node for the Emby collection|
| Window(Home).Property(emby.nodes.X.recent.content) | Contentpath of the recently added node for the Emby collection|
| Window(Home).Property(emby.nodes.X.recent.image) | Rotating Fanart of the recently added node for the Emby collection|
| |
| Window(Home).Property(emby.nodes.X.unwatched.title) | Title of the unwatched node for the Emby collection|
| Window(Home).Property(emby.nodes.X.unwatched.path) | Path of the unwatched node for the Emby collection|
| Window(Home).Property(emby.nodes.X.unwatched.content) | Contentpath of the unwatched node for the Emby collection|
| Window(Home).Property(emby.nodes.X.unwatched.image) | Rotating Fanart of the unwatched node for the Emby collection|
| |
| Window(Home).Property(emby.nodes.X.inprogress.title) | Title of the inprogress node for the Emby collection|
| Window(Home).Property(emby.nodes.X.inprogress.path) | Path of the inprogress node for the Emby collection|
| Window(Home).Property(emby.nodes.X.inprogress.content) | Contentpath of the inprogress node for the Emby collection|
| Window(Home).Property(emby.nodes.X.inprogress.image) | Rotating Fanart of the inprogress node for the Emby collection|
| |
| Window(Home).Property(emby.nodes.X.recentepisodes.title) | Title of the recent episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.recentepisodes.path) | Path of the recent episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.recentepisodes.content) | Contentpath of the recent episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.recentepisodes.image) | Rotating Fanart of the recent episodes node for the Emby collection|
| |
| Window(Home).Property(emby.nodes.X.nextepisodes.title) | Title of the next episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.nextepisodes.path) | Path of the next episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.nextepisodes.content) | Contentpath of the next episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.nextepisodes.image) | Rotating Fanart of the next episodes node for the Emby collection|
| |
| Window(Home).Property(emby.nodes.X.inprogressepisodes.title) | Title of the in progress episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.inprogressepisodes.path) | Path of the in progress episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.inprogressepisodes.content) | Contentpath of the in progress episodes node for the Emby collection|
| Window(Home).Property(emby.nodes.X.inprogressepisodes.image) | Rotating Fanart of the in progress episodes node for the Emby collection|



________________________________________________________________________________________________________



##### Smart shortcuts for Netflix addon (plugin.video.flix2kodi)
Will only be available if this Skin Bool is true --> SmartShortcuts.netflix

Note that the Flix2Kodi addon must be present on the system for this to function.

| property 			| description |
| :----------------------------	| :----------- |
| Window(Home).Property(netflix.generic.title) | Title of the main Netflix entry|
| Window(Home).Property(netflix.generic.path) | Path of the main Netflix entry|
| Window(Home).Property(netflix.generic.content) | Contentpath of the main Netflix entry (for widgets)|
| Window(Home).Property(netflix.generic.image) | Rotating Fanart from Netflix addon|
| |
| Window(Home).Property(netflix.generic.mylist.title) | Title of the Netflix My List entry|
| Window(Home).Property(netflix.generic.mylist.path) | Path of the Netflix My List entry|
| Window(Home).Property(netflix.generic.mylist.content) | Contentpath of the Netflix My List entry (for widgets)|
| Window(Home).Property(netflix.generic.mylist.image) | Rotating Fanart from Netflix My List entry|
| |
| Window(Home).Property(netflix.generic.suggestions.title) | Title of the Netflix Suggestions entry|
| Window(Home).Property(netflix.generic.suggestions.path) | Path of the Netflix Suggestions entry|
| Window(Home).Property(netflix.generic.suggestions.content) | Contentpath of the Netflix Suggestions entry (for widgets)|
| Window(Home).Property(netflix.generic.suggestions.image) | Rotating Fanart from Netflix Suggestions entry|
| |
| Window(Home).Property(netflix.generic.inprogress.title) | Title of the Netflix Continue Watching entry|
| Window(Home).Property(netflix.generic.inprogress.path) | Path of the Netflix Continue Watching entry|
| Window(Home).Property(netflix.generic.inprogress.content) | Contentpath of the Netflix Continue Watching entry (for widgets)|
| Window(Home).Property(netflix.generic.inprogress.image) | Rotating Fanart from Netflix Continue Watching entry|
| |
| Window(Home).Property(netflix.generic.recent.title) | Title of the Netflix Latest entry|
| Window(Home).Property(netflix.generic.recent.path) | Path of the Netflix Latest entry|
| Window(Home).Property(netflix.generic.recent.content) | Contentpath of the Netflix Latest entry (for widgets)|
| Window(Home).Property(netflix.generic.recent.image) | Rotating Fanart from Netflix Latest entry|
| |
| Window(Home).Property(netflix.movies.title) | Title of the Netflix Movies entry|
| Window(Home).Property(netflix.movies.path) | Path of the Netflix Movies entry|
| Window(Home).Property(netflix.movies.content) | Contentpath of the Netflix Movies entry (for widgets)|
| Window(Home).Property(netflix.movies.image) | Rotating Fanart from Netflix Movies entry|
| |
| Window(Home).Property(netflix.movies.mylist.title) | Title of the Netflix Movies Mylist entry|
| Window(Home).Property(netflix.movies.mylist.path) | Path of the Netflix Movies Mylist entry|
| Window(Home).Property(netflix.movies.mylist.content) | Contentpath of the Netflix Movies Mylist entry (for widgets)|
| Window(Home).Property(netflix.movies.mylist.image) | Rotating Fanart from Netflix Movies Mylist entry|
| |
| Window(Home).Property(netflix.movies.suggestions.title) | Title of the Netflix Movies suggestions entry|
| Window(Home).Property(netflix.movies.suggestions.path) | Path of the Netflix Movies suggestions entry|
| Window(Home).Property(netflix.movies.suggestions.content) | Contentpath of the Netflix Movies suggestions entry (for widgets)|
| Window(Home).Property(netflix.movies.suggestions.image) | Rotating Fanart from Netflix Movies suggestions entry|
| |
| Window(Home).Property(netflix.movies.genres.title) | Title of the Netflix Movies genres entry|
| Window(Home).Property(netflix.movies.genres.path) | Path of the Netflix Movies genres entry|
| Window(Home).Property(netflix.movies.genres.content) | Contentpath of the Netflix Movies genres entry (for widgets)|
| Window(Home).Property(netflix.movies.genres.image) | Rotating Fanart from Netflix Movies genres entry|
| |
| Window(Home).Property(netflix.movies.recent.title) | Title of the Netflix Latest movies entry|
| Window(Home).Property(netflix.movies.recent.path) | Path of the Netflix Latest movies entry|
| Window(Home).Property(netflix.movies.recent.content) | Contentpath of the Netflix Latest movies entry (for widgets)|
| Window(Home).Property(netflix.movies.recent.image) | Rotating Fanart from Netflix Latest movies entry|
| |
| Window(Home).Property(netflix.tvshows.title) | Title of the Netflix tvshows entry|
| Window(Home).Property(netflix.tvshows.path) | Path of the Netflix tvshows entry|
| Window(Home).Property(netflix.tvshows.content) | Contentpath of the Netflix tvshows entry (for widgets)|
| Window(Home).Property(netflix.tvshows.image) | Rotating Fanart from Netflix tvshows entry|
| |
| Window(Home).Property(netflix.tvshows.mylist.title) | Title of the Netflix tvshows Mylist entry|
| Window(Home).Property(netflix.tvshows.mylist.path) | Path of the Netflix tvshows Mylist entry|
| Window(Home).Property(netflix.tvshows.mylist.content) | Contentpath of the Netflix tvshows Mylist entry (for widgets)|
| Window(Home).Property(netflix.tvshows.mylist.image) | Rotating Fanart from Netflix tvshows Mylist entry|
| |
| Window(Home).Property(netflix.tvshows.suggestions.title) | Title of the Netflix tvshows suggestions entry|
| Window(Home).Property(netflix.tvshows.suggestions.path) | Path of the Netflix tvshows suggestions entry|
| Window(Home).Property(netflix.tvshows.suggestions.content) | Contentpath of the Netflix tvshows suggestions entry (for widgets)|
| Window(Home).Property(netflix.tvshows.suggestions.image) | Rotating Fanart from Netflix tvshows suggestions entry|
| |
| Window(Home).Property(netflix.tvshows.genres.title) | Title of the Netflix tvshows genres entry|
| Window(Home).Property(netflix.tvshows.genres.path) | Path of the Netflix tvshows genres entry|
| Window(Home).Property(netflix.tvshows.genres.content) | Contentpath of the Netflix tvshows genres entry (for widgets)|
| Window(Home).Property(netflix.tvshows.genres.image) | Rotating Fanart from Netflix tvshows genres entry|
| |
| Window(Home).Property(netflix.tvshows.recent.title) | Title of the Netflix Latest tvshows entry|
| Window(Home).Property(netflix.tvshows.recent.path) | Path of the Netflix Latest tvshows entry|
| Window(Home).Property(netflix.tvshows.recent.content) | Contentpath of the Netflix Latest tvshows entry (for widgets)|
| Window(Home).Property(netflix.tvshows.recent.image) | Rotating Fanart from Netflix Latest tvshows entry|
| |



________________________________________________________________________________________________________
________________________________________________________________________________________________________

### Use with skin shortcuts script
This addon is designed to fully work together with the skinshortcuts script, so it will save you a lot of time because the script provides skinshortcuts with all the info to display contents.
No need to manually skin all those window properties in your skin, just a few lines in your overrides file is enough.

#### Display Smart Shortcuts in skin shortcuts listing

When the smart shortcuts are used together with skinshortcuts it will auto assign the icon and background with rotating fanart and both the widget and submenu (if needed) are assigned by default. The user just adds the shortcut and is all set.

To display the complete listing of Smart Shortcuts in your skin, place the following line in your overrides file, in the groupings section:
```xml
<shortcut label="Smart Shortcuts" type="32010">||BROWSE||script.skin.helper.service/?action=smartshortcuts</shortcut>
```

full example:
```xml
<overrides>
	<groupings>
		<shortcut label="$ADDON[script.skin.helper.service 32062]" type="32010">||BROWSE||script.skin.helper.service/?action=smartshortcuts</shortcut>
	</groupings>
</overrides>	
```
Offcourse you can use a condition parameter to only show the smart shortcuts entry if it's enabled in your skin.
You can also choose to use display the smart shortcuts to be used as widgets, in that case include this line in your overrides.xml file:
```xml
<widget label="Smart Shortcuts" type="32010">||BROWSE||script.skin.helper.service/?action=smartshortcuts</widget>
```

#### Auto display Backgrounds provided by the script in skinshortcuts selector

You can choose to show all backgrounds (including those for smart shortcuts) that are provided by this addon in the skinshortcuts backgrounds selector.

To display all backgrounds automatically in skinshorts you only have to include the line below in your overrides file:
```xml
<background label="smartshortcuts">||BROWSE||plugin://script.skin.helper.service/?action=backgrounds</background>
```

Note: You can still use the default skinshortcuts method to assign a default background to a item by labelID or defaultID.
In that case use the full $INFO path of the background. For example, to assign the "all movies" background to the Movies shortcut:
```xml
<backgrounddefault defaultID="movies">$INFO[Window(Home).Property(SkinHelper.AllMoviesBackground)]</backgrounddefault>
```
For more info, see skinshortcut's documentation.


#### Auto display widgets in skinshortcuts

Coding all widgets in your skin can be a pain, especially to keep up with all the fancy scripts like extendedinfo and library data provider. This addon, combined with skinshortcuts can make things a little easier for you...
By including just one line of code in your skinshortcuts override.xml you can display a whole bunch of widgets, ready to be selected by the user:

```xml
<widget label="Widgets" type="32010">||BROWSE||script.skin.helper.service/?action=widgets&amp;path=skinplaylists,librarydataprovider,scriptwidgets,extendedinfo,smartshortcuts,pvr,smartishwidgets</widget>
```

This will display a complete list of widgets available to select if the user presses the select widget button in skinshortcuts. In the path parameter you can specify which widgettypes should be listed. The widgets will be displayed in the order of which you type them as parameters (comma separated). You can also leave out the whole path parameterm in that case all available widgets will be displayed.

Currently available widgets (more to be added soon):

skinplaylist --> all playlists that are stored in "yourskin\extras\widgetplaylists" or "yourskin\playlists" or "yourskin\extras\playlists"

librarydataprovider --> all widgets that are provided by the Library Data Provider script

scriptwidgets --> the special widgets that are provided by this addon, like favourites and favourite media etc.

extendedinfo --> All widgets that are provided by the Extended info script

smartshortcuts --> all smartshortcuts

pvr --> pvr widgets provided by the script

smartishwidgets --> widget supplied by the smartish widgets addon

favourites --> any browsable nodes in the user's favourites that can be used as widget


Note: the script will auto check the existence of the addons on the system so no need for complex visibility conditions in your skin.



________________________________________________________________________________________________________
________________________________________________________________________________________________________



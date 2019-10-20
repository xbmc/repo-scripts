# FOR SKINNERS

Start the script with RunScript(script.skin.info.service) in startup.xml.  
Properties will be available in the corresponding media windows.

## Window(home).Property(...)
### For Artists
-   'SkinInfo.Artist.Album.%d.Title' % i
-   'SkinInfo.Artist.Album.%d.Label' % i
-   'SkinInfo.Artist.Album.%d.Plot' % i
-   'SkinInfo.Artist.Album.%d.PlotOutline' % i
-   'SkinInfo.Artist.Album.%d.Year' % i
-   'SkinInfo.Artist.Album.%d.Duration' % i
-   'SkinInfo.Artist.Album.%d.Art(discart)' % i
-   'SkinInfo.Artist.Album.%d.Art(thumb)' % i
-   'SkinInfo.Artist.Album.%d.DBID' % i
-   'SkinInfo.Artist.Albums.Newest'
-   'SkinInfo.Artist.Albums.Oldest'
-   'SkinInfo.Artist.Albums.Count'
-   'SkinInfo.Artist.Albums.Playcount'

### For Albums
-   'SkinInfo.Album.Song.%d.Title' % i
-   'SkinInfo.Album.Song.%d.FileExtension' % i
-   'SkinInfo.Album.Songs.TrackList'
-   'SkinInfo.Album.Songs.Discs'
-   'SkinInfo.Album.Songs.Duration'
-   'SkinInfo.Album.Songs.Count'

### For Movie Sets
-   'SkinInfo.Set.Movies.Title'
-   'SkinInfo.Set.Movie.%d.DBID' % i
-   'SkinInfo.Set.Movie.%d.Path' % i
-   'SkinInfo.Set.Movie.%d.Year' % i
-   'SkinInfo.Set.Movie.%d.Duration' % i
-   'SkinInfo.Set.Movie.%d.VideoResolution' % i
-   'SkinInfo.Set.Movie.%d.Art(clearlogo)' % i
-   'SkinInfo.Set.Movie.%d.Art(fanart)' % i
-   'SkinInfo.Set.Movie.%d.Art(poster)' % i
-   'SkinInfo.Set.Movie.%d.Art(discart)' % i
-   'SkinInfo.Set.Movie.%d.MPAA' % i
-   'SkinInfo.Set.Movies.List'
-   'SkinInfo.Set.Movies.Plot'
-   'SkinInfo.Set.Movies.PlotOutline'
-   'SkinInfo.Set.Movies.ExtendedPlot'
-   'SkinInfo.Set.Movies.Runtime'
-   'SkinInfo.Set.Movies.Writer'
-   'SkinInfo.Set.Movies.Director'
-   'SkinInfo.Set.Movies.Genre'
-   'SkinInfo.Set.Movies.Years'
-   'SkinInfo.Set.Movies.Count'
-   'SkinInfo.Set.Movies.Studio'
-   'SkinInfo.Set.Movies.Single.Studio'
-   'SkinInfo.Set.Movies.Country'

### For Movie Years, Directors, Actors, Genres, Studios, Countries and Tags
-   'SkinInfo.Detail.Movie.%d.Path' % i
-   'SkinInfo.Detail.Movie.%d.Art(fanart)' % i
-   'SkinInfo.Detail.Movie.%d.Art(poster)' % i
-   'SkinInfo.Detail.Movie.%d.Art(fanart)' % i
-   'SkinInfo.Detail.Movie.%d.Path' % i

## Window(movieinformation).Property(...)
### For Movies
-   'SkinInfo.AudioLanguage.%d' % i
-   'SkinInfo.AudioCodec.%d' % i
-   'SkinInfo.AudioChannels.%d' % i
-   'SkinInfo.SubtitleLanguage.%d' % i

## Enable JSON Debugging in Script Settings for Logging JSON Output
![JSONDebugExample](https://i.imgur.com/V5fEYVt.png)

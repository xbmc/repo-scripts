######################################################
#####################FOR SKINNERS#####################
######################################################

Start the script with RunScript(script.skin.info.service) in startup.xml
Properties will be available in the corresponding media windows.

New properties:

For artists:
Window(home).Property(...)
    'SkinInfo.Artist.Album.%d.Title' % i
    'SkinInfo.Artist.Album.%d.Plot' % i
    'SkinInfo.Artist.Album.%d.PlotOutline' % i
    'SkinInfo.Artist.Album.%d.Year' % i
    'SkinInfo.Artist.Album.%d.Duration' % i
    'SkinInfo.Artist.Album.%d.Thumb' % i
    'SkinInfo.Artist.Album.%d.ID' % i
    'SkinInfo.Artist.Albums.Newest'
    'SkinInfo.Artist.Albums.Oldest'
    'SkinInfo.Artist.Albums.Count'
    'SkinInfo.Artist.Albums.Playcount'

For Albums:
Window(home).Property(...)
    'SkinInfo.Album.Song.%d.Title' % i
    'SkinInfo.Album.Song.%d.FileExtension' % i
    'SkinInfo.Album.Songs.TrackList'
    'SkinInfo.Album.Songs.Discs'
    'SkinInfo.Album.Songs.Discs'
    'SkinInfo.Album.Songs.Duration'
    'SkinInfo.Album.Songs.Count'

For movie sets:
Window(home).Property(...)
    'SkinInfo.Set.Movie.%d.Art(clearlogo)' % i
    'SkinInfo.Set.Movie.%d.Art(fanart)' % i
    'SkinInfo.Set.Movie.%d.Art(poster)' % i
    'SkinInfo.Set.Movie.%d.Art(discart)' % i
    'SkinInfo.Set.Movies.Plot'
    'SkinInfo.Set.Movies.ExtendedPlot'
    'SkinInfo.Set.Movies.Runtime'
    'SkinInfo.Set.Movies.Writer'
    'SkinInfo.Set.Movies.Director'
    'SkinInfo.Set.Movies.Genre'
    'SkinInfo.Set.Movies.Years'
    'SkinInfo.Set.Movies.Count'

For movie years, directors, actors, genres, studios countries and tags:
Window(home).Property(...)
    'SkinInfo.Detail.Movie.%d.Art(poster)' % i
    'SkinInfo.Detail.Movie.%d.Art(fanart)' % i
    'SkinInfo.Detail.Movie.%d.Path' % i

For movies:
Window(movieinformation).Property(...)
    'SkinInfo.AudioLanguage.%d' % i
    'SkinInfo.AudioCodec.%d' % i
    'SkinInfo.AudioChannels.%d' % i
    'SkinInfo.SubtitleLanguage.%d' % i

Parameters (separated by &amp; ):

limit=#         ; # to limit returned results (default=5)
unplayed=True   ; True to return only items (not supported for albums) that have not been played (default=False)
trailer=True    ; True to play the trailer (if available) (default=False)
alarm=#         ; # number of minutes before running again (default=Off)


For example:
 
XBMC.RunScript(script.randomitems,limit=10&amp;unplayed=True&amp;alarm=30)

will return 10 random, unplayed movies, episodes, albums, songs, artists and addons every 30 minutes.


Labels:

"RandomMovie.%d.Title"
"RandomMovie.%d.Rating"
"RandomMovie.%d.Year"
"RandomMovie.%d.Plot"
"RandomMovie.%d.RunningTime"
"RandomMovie.%d.Path"
"RandomMovie.%d.Trailer"
"RandomMovie.%d.Fanart"
"RandomMovie.%d.Thumb"
"RandomMovie.Count"
 
"RandomEpisode.%d.ShowTitle"
"RandomEpisode.%d.EpisodeTitle"
"RandomEpisode.%d.EpisodeNo"
"RandomEpisode.%d.EpisodeSeason"
"RandomEpisode.%d.EpisodeNumber"
"RandomEpisode.%d.Plot"
"RandomEpisode.%d.Rating"
"RandomEpisode.%d.Path"
"RandomEpisode.%d.Fanart"
"RandomEpisode.%d.Thumb"
"RandomEpisode.Count"

"RandomMusicVideo.%d.Title"
"RandomMusicVideo.%d.Year"
"RandomMusicVideo.%d.Plot"
"RandomMusicVideo.%d.RunningTime"
"RandomMusicVideo.%d.Path"
"RandomMusicVideo.%d.Artist"
"RandomMusicVideo.%d.Fanart"
"RandomMusicVideo.%d.Thumb"
"RandomMusicVideo.Count"

"RandomAlbum.%d.Title"
"RandomAlbum.%d.Year"
"RandomAlbum.%d.Artist"
"RandomAlbum.%d.Path"
"RandomAlbum.%d.Fanart"
"RandomAlbum.%d.Thumb"
"RandomAlbum.%d.Rating"
"RandomAlbum.%d.Album_Description"
"RandomAlbum.Count"

"RandomSong.%d.Title"
"RandomSong.%d.Year"
"RandomSong.%d.Artist"
"RandomSong.%d.Album"
"RandomSong.%d.Path"
"RandomSong.%d.Fanart"
"RandomSong.%d.Thumb"
"RandomSong.%d.Rating"
"RandomSong.Count"

"RandomAddon.%d.Name"
"RandomAddon.%d.Author"
"RandomAddon.%d.Summary"
"RandomAddon.%d.Version"
"RandomAddon.%d.Path"
"RandomAddon.%d.Type"
"RandomAddon.%d.Fanart"
"RandomAddon.%d.Thumb"
"RandomAddon.Count"

"RandomArtist.%d.Title"
"RandomArtist.%d.Artist_Description"
"RandomArtist.%d.Path"
"RandomArtist.%d.Fanart"
"RandomArtist.%d.Thumb"
"RandomArtist.%d.Genre"
"RandomArtist.Count"


For more inforamtion and help please check:
http://wiki.xbmc.org/index.php?title=Add-on:Random_Items_script

http://forum.xbmc.org/showthread.php?tid=79378

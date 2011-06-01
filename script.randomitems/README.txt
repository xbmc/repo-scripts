Parameters (separated by [B]&amp;[/B]) -

limit=#         ; # to limit returned results (default=5)
albums=True         ; True to return albums instead of songs (default=False)
unplayed=True         ; True to return only items that have not been played (default=False)
trailer=True         ; True to play the trailer (if available) (default=False)
alarm=#         ; # number of minutes before running again (default=Off)

For example -
 
XBMC.RunScript(script.randomitems,limit=10&amp;albums=False&amp;unplayed=True&amp;alarm=30)

will return 10 random, unplayed movies, episodes, songs and addons every 30 minutes.


Labels -

"RandomMovie.%d.Title"
"RandomMovie.%d.Rating"
"RandomMovie.%d.Year"
"RandomMovie.%d.RunningTime"
"RandomMovie.%d.Path"
"RandomMovie.%d.Trailer"
"RandomMovie.%d.Fanart"
"RandomMovie.%d.Thumb"
 
"RandomEpisode.%d.ShowTitle"
"RandomEpisode.%d.EpisodeTitle"
"RandomEpisode.%d.EpisodeNo"
"RandomEpisode.%d.EpisodeSeason"
"RandomEpisode.%d.EpisodeNumber"
"RandomEpisode.%d.Rating"
"RandomEpisode.%d.Path"
"RandomEpisode.%d.Fanart"
"RandomEpisode.%d.Thumb"

"RandomSong.%d.Title" <!-- Returns the Song name when albums=False or Returns the Album name when albums=True -->
"RandomSong.%d.Year"
"RandomSong.%d.Artist"
"RandomSong.%d.Album" <!-- Not used when albums=True so can be used as a visible condition for knowing what mode the script is in -->
"RandomSong.%d.Path"
"RandomSong.%d.Fanart"
"RandomSong.%d.Thumb"
"RandomSong.%d.Rating"

"RandomAddon.%d.Name"
"RandomAddon.%d.Author"
"RandomAddon.%d.Summary"
"RandomAddon.%d.Version"
"RandomAddon.%d.Path"
"RandomAddon.%d.Fanart"
"RandomAddon.%d.Thumb"
"Addons.Count"


For more inforamtion and help please check -

http://forum.xbmc.org/showthread.php?t=55907

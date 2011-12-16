
INFORMATION FOR SKINNERS
------------------------


CONTENTS:
1. Introduction
2. Running the addon
3. Available infolabels


1. Introduction:
----------------
This script will return:
- a list containing the first unwatched episode of TV Shows you are watching.
- a list of movies that are partially watched.
- a list of most played albums

The episode list is sorted by watch date of the previous episode:
if you've watched 'South Park' yesterday and 'House' the day before,
'South Park' will be the first item on the list and 'House' the second one.

The movie list is also sorted by watch date.

The album list is sorted by playcount.


2. Running the addon:
---------------------
run the script with the options you need:
RunScript(script.watchlist,movies=true&amp;episodes=true&amp;albums=true&amp;limit=25)


3. Available infolabels:
------------------------
Window(Home).Property(*)

WatchList_Movie.%d.Label		- movie title
WatchList_Movie.%d.Year			- year of release
WatchList_Movie.%d.Genre		- movie genre
WatchList_Movie.%d.Studio		- movie studio
WatchList_Movie.%d.Plot			- movie plot
WatchList_Movie.%d.PlotOutline		- movie plotoutline
WatchList_Movie.%d.Tagline		- movie tagline
WatchList_Movie.%d.Runtime		- duration of the movie
WatchList_Movie.%d.Rating		- movie rating
WatchList_Movie.%d.Fanart		- movie fanart
WatchList_Movie.%d.Thumb		- movie thumbnail
WatchList_Movie.%d.Path			- movie filename and path

WatchList_Episode.%d.Label		- episode title
WatchList_Episode.%d.Episode		- episode number
WatchList_Episode.%d.Season		- season number
WatchList_Episode.%d.EpisodeNo		- season/episode number (sxxexx)
WatchList_Episode.%d.Plot		- episode plot
WatchList_Episode.%d.TVShowTitle	- tv show title
WatchList_Episode.%d.Path		- episode filename and path
WatchList_Episode.%d.Rating		- episode rating
WatchList_Episode.%d.Thumb		- episode thumbnail
WatchList_Episode.%d.SeasonThumb	- season thumbnail
WatchList_Episode.%d.TvshowThumb	- tv show thumbnail
WatchList_Episode.%d.Fanart		- tv show fanart
WatchList_Episode.%d.IsResumable	- indicates if it's a partially watched episode (True/False)

WatchList_Album.%d.Label		- name of the album
WatchList_Album.%d.Artist		- album artist
WatchList_Album.%d.Genre		- album genre
WatchList_Album.%d.Year			- year of release
WatchList_Album.%d.Album_Label		- recordlabel
WatchList_Album.%d.Album_Description	- album review
WatchList_Album.%d.Rating		- rating of the album
WatchList_Album.%d.Thumb		- album thumbnail
WatchList_Album.%d.Fanart		- artist fanart
WatchList_Album.%d.Path			- can be used to play the album: <onclick>$INFO[Window(Home).Property(WatchList_Album.%d.Path)]</onclick>


WatchList_Running			- used by the script internally to check if it's already running


# script.skin.helper.widgets
Addon for Kodi providing widgets for all kinds of media types


### Dynamic content provider
The script implements a plugin entrypoint to provide some dynamic content that can be used for example in widgets.

use the parameter limit=[value] to define the number of items to show in the list. Defaults to the setting defined in the addon settings


All available methods can be explored by navigating to the addon in Kodi's video addons section.
Most important/used methods are listed below:



#####Next Episodes
```
plugin://script.skin.helper.widgets/?action=next&mediatype=episodes&reload=$INFO[Window(Home).Property(widgetreload)]
```
Provides a list of the nextup episodes. This can be the first episode in progress from a tv show or the next unwatched from a in progress show.
Note: the reload parameter is needed to auto refresh the widget when the content has changed.

________________________________________________________________________________________________________

#####Recommended Movies
```
plugin://script.skin.helper.widgets/?action=recommended&mediatype=movies&reload=$INFO[Window(Home).Property(widgetreload-movies)]
```
Provides a list of the in progress movies AND recommended movies based on rating.
Note: the reload parameter is needed to auto refresh the widget when the content has changed.

________________________________________________________________________________________________________

#####Recommended Media
```
plugin://script.skin.helper.widgets/?action=recommended&mediatype=media&reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides a list of recommended media (movies, tv shows, music)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.

________________________________________________________________________________________________________

#####Recent albums
```
plugin://script.skin.helper.widgets/?action=recent&mediatype=albums&reload=$INFO[Window(Home).Property(widgetreload-music)]
```
Provides a list of recently added albums, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.

Optional argument: browse=true --> will open/browse the album instead of playing it
________________________________________________________________________________________________________

#####Recently played albums
```
plugin://script.skin.helper.widgets/?action=recentplayed&mediatype=albums&reload=$INFO[Window(Home).Property(widgetreload-music)]
```
Provides a list of recently played albums, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.

Optional argument: browse=true --> will open/browse the album instead of playing it
________________________________________________________________________________________________________

#####Recommended albums
```
plugin://script.skin.helper.widgets/?action=recommended&mediatype=albums&reload=$INFO[Window(Home).Property(widgetreload-music)]
```
Provides a list of recommended albums, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.

Optional argument: browse=true --> will open/browse the album instead of playing it
________________________________________________________________________________________________________

#####Recent songs
```
plugin://script.skin.helper.widgets/?action=recent&mediatype=songs&reload=$INFO[Window(Home).Property(widgetreload-music)]
```
Provides a list of recently added songs, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.
________________________________________________________________________________________________________

#####Recently played songs
```
plugin://script.skin.helper.widgets/?action=recentplayed&mediatype=songs&reload=$INFO[Window(Home).Property(widgetreload-music)]
```
Provides a list of recently played songs, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.
________________________________________________________________________________________________________

#####Recommended songs
```
plugin://script.skin.helper.widgets/?action=recommended&mediatype=songs&reload=$INFO[Window(Home).Property(widgetreload-music)]
```
Provides a list of recommended songs, including the artwork provided by this script as ListItem.Art(xxxx)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.
________________________________________________________________________________________________________

#####Recent Media
```
plugin://script.skin.helper.widgets/?action=recent&mediatype=media&reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides a list of recently added media (movies, tv shows, music, tv recordings, musicvideos)
Note: You can optionally provide the reload= parameter if you want to refresh the widget on library changes.


________________________________________________________________________________________________________

#####Similar Movies (because you watched...)
```
plugin://script.skin.helper.widgets/?action=similar&mediatype=movies&reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with movies that are similar to a random watched movie from the library.
TIP: The listitem provided by this list will have a property "similartitle" which contains the movie from which this list is generated. That way you can create a "Because you watched $INFO[Container.ListItem.Property(originaltitle)]" label....
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

The above command will create a similar movies listing based on a random watched movie in the library.
If you want to specify the movie to base the request on yourself you can optionally specify the imdb id to the script:

```
plugin://script.skin.helper.widgets/?action=similar&mediatype=movies&imdbid=[IMDBID]
```

________________________________________________________________________________________________________

#####Similar Tv Shows (because you watched...)
```
plugin://script.skin.helper.widgets/?action=similarshows&reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with TV shows that are similar to a random in progress show from the library.
TIP: The listitem provided by this list will have a property "similartitle" which contains the movie from which this list is generated. That way you can create a "Because you watched $INFO[Container.ListItem.Property(originaltitle)]" label....
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

The above command will create a similar shows listing based on a random in progress show in the library.
If you want to specify the show to base the request on yourself you can optionally specify the imdb/tvdb id to the script:

```
plugin://script.skin.helper.widgets/?action=similarshows&imdbid=[IMDBID]
```

________________________________________________________________________________________________________

#####Similar Media (because you watched...)
```
plugin://script.skin.helper.widgets/?action=similar&mediatype=media&reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with both Movies and TV shows that are similar to a random in progress movie or show from the library.
TIP: The listitem provided by this list will have a property "similartitle" which contains the movie from which this list is generated. That way you can create a "Because you watched $INFO[Container.ListItem.Property(originaltitle)]" label....
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

The above command will create a similar shows listing based on a random in progress show in the library.
If you want to specify the movie/show to base the request on yourself you can optionally specify the imdb/tvdb id to the script:

```
plugin://script.skin.helper.widgets/?action=similarshows&imdbid=[IMDBID]
```

________________________________________________________________________________________________________

#####Top rated Movies in genre
```
plugin://script.skin.helper.widgets/?action=forgenre&mediatype=movies&reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with movies that for a random genre from the library.
TIP: The listitem provided by this list will have a property "genretitle" which contains the movie from which this list is generated.
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

________________________________________________________________________________________________________

#####Top rated tvshows in genre
```
plugin://script.skin.helper.widgets/?action=forgenre&mediatype=tvshows&reload=$INFO[Window(Home).Property(widgetreload2)]
```
This will provide a list with tvshows for a random genre from the library.
TIP: The listitem provided by this list will have a property "genretitle" which contains the movie from which this list is generated.
Note: You can optionally provide the widgetreload2 parameter if you want to refresh the widget every 10 minutes. If you want to refresh the widget on other circumstances just provide any changing info with the reload parameter, such as the window title or some window Property which you change on X interval.

________________________________________________________________________________________________________


#####In progress Media
```
plugin://script.skin.helper.widgets/?action=inprogress&mediatype=media&reload=$INFO[Window(Home).Property(widgetreload)]
```
Provides a list of all in progress media (movies, tv shows, music, musicvideos)
Note: the reload parameter is needed to auto refresh the widget when the content has changed.


________________________________________________________________________________________________________

#####In progress and Recommended Media
```
plugin://script.skin.helper.widgets/?action=inprogressandrecommended&mediatype=media&reload=$INFO[Window(Home).Property(widgetreload)]
```
This combines in progress media and recommended media, usefull to prevent an empty widget when no items are in progress.
Note: the reload parameter is needed to auto refresh the widget when the content has changed.

________________________________________________________________________________________________________

#####Favourite Media
```
plugin://script.skin.helper.widgets/?action=favourite&mediatype=media&reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides a list of all media items that are added as favourite (movies, tv shows, songs, musicvideos)
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.

________________________________________________________________________________________________________

#####PVR TV Channels widget
```
plugin://script.skin.helper.widgets/?action=channels&mediatype=pvr&reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides the Kodi TV channels as list content, enriched with the artwork provided by this script (where possible).
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.

________________________________________________________________________________________________________

#####PVR Latest Recordings widget
```
plugin://script.skin.helper.widgets/?action=recordings&mediatype=pvr&reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides the Kodi TV Recordings (sorted by date) as list content, enriched with the artwork provided by this script (where possible).
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.


________________________________________________________________________________________________________

#####Favourites
```
plugin://script.skin.helper.widgets/?mediatype=favourites&reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides the Kodi favourites as list content.
Note: By providing the reload-parameter set to the widgetreload2 property, the widget will be updated every 10 minutes.


________________________________________________________________________________________________________

##### Unaired episodes
```
plugin://script.skin.helper.widgets/?action=unaired&mediatype=episodes&reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides a listing for episodes for tvshows in the Kodi library that are airing within the next 2 months.

All listitem properties should be the same as any other episode listitem, 
all properties should be correctly filled with the correct info.
Just treat the widget as any other episode widget and you should have all the details properly set.
If not, let me know ;-)

Listitem.Title --> title of the episode
Listitem.Season, ListItem.Episode --> season/episode of the episode
ListItem.TvShowTitle --> Name of the show
ListItem.Studio --> Network of the show
ListItem.FirstAired --> Airdate for the episode
ListItem.Art(fanart, poster etc.) --> Artwork from the TV show (in Kodi database)
ListItem.Thumb or Listitem.Art(thumb) --> Episode thumb (if provided by tvdb)

Besides the default Kodi ListItem properties for episodes the following properties will exist:

ListItem.Property(airday) --> The weekday the show will air on the network (e.g. Monday)
ListItem.Property(airtime) --> The time the show will air on the network (e.g. 8:00 PM)
ListItem.Property(airdatetime) --> Combination of airdate and airtime
ListItem.Property(airdatetime.label) --> Combination of airdate, airtime and network
________________________________________________________________________________________________________

##### Next airing episodes
```
plugin://script.skin.helper.widgets/?action=nextaired&mediatype=episodes&reload=$INFO[Window(Home).Property(widgetreload2)]
```
Provides the next unaired episode for each tvshow in the library which is airing within the next 2 months.
Difference with the unaired episodes is that it will only show the first airing episode for each show while unaired episodes shows all airing episodes.
Also, the next airing episodes looks 60 days ahead for airing episodes while the unaired episodes looks 120 days ahead.

For the listitem properties, see the "unaired episodes" plugin path.
________________________________________


#####Browse Genres
```
plugin://script.skin.helper.widgets/?action=browsegenres&mediatype=movie&limit=1000
plugin://script.skin.helper.widgets/?action=browsegenres&mediatype=tvshow&limit=1000
```
Provides the genres listing for movies or tvshows with artwork properties from movies/shows with the genre so you can build custom genre icons.

ListItem.Art(poster.X) --> poster for movie/show X (start counting at 0) in the genre

ListItem.Art(fanart.X) --> fanart for movie/show X (start counting at 0) in the genre


For each genre, only 5 movies/tvshows are retrieved.
Supported types: movie, tvshow (will return 5 items from the library for each genre)
If you use randommovie or randomtvshow as type the library items will be randomized


________________________________________________________________________________________________________
________________________________________________________________________________________________________


#### Widget reload properties
If you need to refresh a widget automatically after the library is changed, you can append these to the widget path.

For example:

```
plugin://myvideoplugin/movies/?latest&reload=$INFO[Window(Home).Property(widgetreload-episodes)]
```

| property 			| description |
|:-----------------------------	| :----------- |
|Window(Home).Property(widgetreload) | will change if any video content is added/changed in the library or after playback stop of any video content (in- or outside of library) |
|Window(Home).Property(widgetreload-episodes) | will change if episodes content is added/changed in the library or after playback stop of episodes content (in- or outside of library) |
|Window(Home).Property(widgetreload-movies) | will change if movies content is added/changed in the library or after playback stop of movies content (in- or outside of library) |
|Window(Home).Property(widgetreload-tvshows) | will change if tvshows content is added/changed in the library |
|Window(Home).Property(widgetreload-music) | will change if any music content is added/changed in the library or after playback stop of music (in- or outside of library) |
|Window(Home).Property(widgetreload2) | will change every 10 minutes (e.g. for pvr widgets or favourites) |



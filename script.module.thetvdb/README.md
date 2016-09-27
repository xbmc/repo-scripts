# script.module.thetvdb
Kodi python module to access the new thetvdb api v2


## Usage

You can use this python library as module within your own Kodi scripts/addons.
Just make sure to import it within your addon.xml:

```xml
<requires>
    <import addon="script.module.thetvdb" version="0.0.1" />
</requires>
```

Now, to use it in your Kodi addon/script, make sure to import it and you can access it's methods.

```
import thetvdb
next_aired_episodes = thetvdb.getKodiSeriesUnairedEpisodesList(False)
for episode in next_aired_episodes:
    #do your stuff here, like creating listitems for all episodes that are returned.
```

The above example will return the next airing episodes from tv shows in the Kodi library.
The result is an json array of objects which contain the information about the episode and the tv show.
If any images are found, they will also be present in the result (thumb, poster, seasonposter, fanart, landscape, banner)

---------------------------------------------------------------------------

## Available methods

###getEpisode(episodeid)
```
    Returns the full information for a given episode id. 
    Deprecation Warning: The director key will be deprecated in favor of the new directors key in a future release.
    Usage: specify the episode ID: getEpisode(episodeid)
```

###getSeries(seriesid,ContinuingOnly=False)
```
    Returns a series record that contains all information known about a particular series id.
    Usage: specify the serie ID: getSeries(seriesid)
```

###getContinuingSeries()
```
    only gets the continuing series, based on which series were recently updated as there is no other api call to get that information
```

###getSeriesActors(seriesid)
```
    Returns actors for the given series id.
    Usage: specify the series ID: getSeriesActors(seriesid)
```

###getSeriesEpisodes(seriesid)
```
    Returns all episodes for a given series.
    Usage: specify the series ID: getSeriesEpisodes(seriesid)
```

###getSeriesEpisodesByQuery(seriesid,absoluteNumber="",airedSeason="",airedEpisode="",dvdSeason="",dvdEpisode="",imdbId="")
```
    This route allows the user to query against episodes for the given series. The response is an array of episode records that have been filtered down to basic information.
    Usage: specify the series ID: getSeriesEpisodesByQuery(seriesid)
    optionally you can specify one or more fields for the query:
    absoluteNumber --> Absolute number of the episode
    airedSeason --> Aired season number
    airedEpisode --> Aired episode number
    dvdSeason --> DVD season number
    dvdEpisode --> DVD episode number
    imdbId --> IMDB id of the series
```

###getSeriesEpisodesSummary(seriesid)
```
    Returns a summary of the episodes and seasons available for the series.
    Note: Season 0 is for all episodes that are considered to be specials.

    Usage: specify the series ID: getSeriesEpisodesSummary(seriesid)
```

###searchSeries(name="",imdbId="",zap2itId="")
```
    Allows the user to search for a series based on one or more parameters. Returns an array of results that match the query.
    Usage: specify the series ID: searchSeries(parameters)
    
    Available parameters:
    name --> Name of the series to search for.
    imdbId --> IMDB id of the series
    zap2itId -->  Zap2it ID of the series to search for.
```

###getRecentlyUpdatedSeries()
```
    Returns all series that have been updated in the last week
```

###getUnAiredEpisodes(seriesid)
```
    Returns the unaired episodes for the specified seriesid
    Usage: specify the series ID: getUnAiredEpisodes(seriesid)
```

###getNextUnAiredEpisode(seriesid)
```
    Returns the first next airing episode for the specified seriesid
    Usage: specify the series ID: getNextUnAiredEpisode(seriesid)
```

###getUnAiredEpisodeList(seriesids)
```
    Returns the next airing episode for each specified seriesid
    Usage: specify the series ID: getNextUnAiredEpisode(list of seriesids)
```

###getKodiSeriesUnairedEpisodesList(singleEpisodePerShow=True):
```
    Returns the next unaired episode for all continuing tv shows in the Kodi library
    Defaults to a single episode (next unaired) for each show, to disable have False as argument.
```
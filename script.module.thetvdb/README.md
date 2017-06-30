# script.module.thetvdb
Kodi python module to access the new thetvdb api v2

The module is supported by the simplecache module to ensure that data is not useless retrieved from the API all the time.

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
from thetvdb import TheTvDb
tvdb = TheTvDb()
next_aired_episodes = tvdb.get_kodi_unaired_episodes(single_episode_per_show=False)
for episode in next_aired_episodes:
    #do your stuff here, like creating listitems for all episodes that are returned.
```

The above example will return the next airing episodes from tv shows in the Kodi library.
The result is an json array of objects which contain the information about the episode and the tv show.
If any images are found, they will also be present in the result (thumb, poster, seasonposter, fanart, landscape, banner)

---------------------------------------------------------------------------

## Available methods

###get_episode(episodeid)
```
    Returns the full information for a given episode id. 
    Deprecation Warning: The director key will be deprecated in favor of the new directors key in a future release.
    Usage: specify the episode ID: get_episode(episodeid)
```

###get_series(seriesid,ContinuingOnly=False)
```
    Returns a series record that contains all information known about a particular series id.
    Usage: specify the serie ID: get_series(seriesid)
    Output is formatted in kodi compatible json format
```

###get_series_by_imdb_id(imdbid)
```
    Returns a series record that contains all information known about a particular series id.
    Usage: specify the IMDBID for the series: get_series_by_imdb_id(seriesid)
```


###get_continuing_series()
```
    only gets the continuing series, based on which series were recently updated as there is no other api call to get that information
```


###get_series_actors(seriesid)
```
    Returns actors for the given series id.
    Usage: specify the series ID: get_series_actors(seriesid)
```

###get_series_episodes(seriesid)
```
    Returns all episodes for a given series.
    Usage: specify the series ID: get_series_episodes(seriesid)
    Note: output is only summary of episode details (non kodi formatted)
```

###get_last_episode_for_series(seriesid)
```
    Returns the last aired episode for a given series.
    Usage: specify the series ID: get_last_episode_for_series(seriesid)
```

###get_series_episodes_by_query(seriesid, query="")
```
    This route allows the user to query against episodes for the given series. The response is an array of episode records.
    Usage: specify the series ID: get_series_episodes_by_query(seriesid, query="imdbid=X")
    You must specify one or more fields for the query (combine multiple with &):
    absolutenumber=X --> Absolute number of the episode
    airedseason=X --> Aired season number
    airedepisode=X --> Aired episode number
    dvdseason=X --> DVD season number
    dvdepisode=X --> DVD episode number
    imdbid=X --> IMDB id of the series
    Note: output is only summary of episode details (non kodi formatted)
```

###get_series_episodes_summary(seriesid)
```
    Returns a summary of the episodes and seasons available for the series.
    Note: Season 0 is for all episodes that are considered to be specials.

    Usage: specify the series ID: get_series_episodes_summary(seriesid)
```

###search_series(query="", prefer_localized=False)
```
    Allows the user to search for a series based the name.
    Returns an array of results that match the query.
    Usage: specify the series ID: TheTvDb().search_series(searchphrase)

    Available parameter:
    prefer_localized --> True if you want to set the current kodi language as preferred in the results
```

###get_recently_updated_series()
```
    Returns all series that have been updated in the last week
```

###get_unaired_episodes(seriesid)
```
    Returns the unaired episodes for the specified seriesid
    Usage: specify the series ID: get_unaired_episodes(seriesid)
```

###get_nextaired_episode(seriesid)
```
    Returns the first next airing episode for the specified seriesid
    Usage: specify the series ID: get_nextaired_episode(seriesid)
```

###get_unaired_episode_list(seriesids)
```
    Returns the next airing episode for each specified seriesid
    Usage: get_unaired_episode_list([list [] of seriesids)
```

###get_continuing_kodi_series(single_episode_per_show=True):
```
    Returns the next unaired episode for all continuing tv shows in the Kodi library
    Defaults to a single episode (next unaired) for each show, to disable have False as argument.
```

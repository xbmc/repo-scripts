# script.module.metadatautils
Kodi python module to retrieve rich artwork and metadata for common kodi media items
The module is integrated with the simplecache module so that information is properly cached

## Usage

You can use this python library as module within your own Kodi scripts/addons.
Just make sure to import it within your addon.xml:

```xml
<requires>
    <import addon="script.module.metadatautils" version="1.0.0" />
</requires>
```

Now, to use it in your Kodi addon/script, make sure to import it and you can access it's methods.


```
from metadatautils import MetadataUtils
metadatautils = MetadataUtils()

#do your stuff here, like like calling any of the available methods
```

NOTE: make sure to use unnamed arguments for all methods to not confuse the cache
e.g. metadatautils.use get_tvdb_details("", "12345") instead of metadatautils.use get_tvdb_details(tvdb_id="12345")

---------------------------------------------------------------------------

## Available methods

###get_extrafanart(file_path, media_type)
```
    retrieve the extrafanart path for a kodi media item
    Parameters: 
    file_path: the full filepath (ListItem.FileNameAndPath) for the media item
    media_type: The container content type e.g. movies/tvshows/episodes/musicvideos/seasons
```


###get_music_artwork(self, artist, album="", track="", disc="")
```
    get music artwork for the given artist/album/song
    Parameters: 
    artist: the name of the artist (required)
    album: name of the album (optional, result will include album details if provided)
    track: name of the track (optional, result will include album details if provided)
    disc: discnumber of the track (optional)
    the more parameters supplied, the more accurate the results will be.
    
    Note: In the addon settings for the kodi module, the user can set personal preferences for the scraper.
```


###music_artwork_options(self, artist, album="", track="", disc="")
```
    Shows a dialog to manually override the artwork by the user for the given media
    Parameters: 
    artist: the name of the artist (required)
    album: name of the album (optional, result will include album details if provided)
    track: name of the track (optional, result will include album details if provided)
    disc: discnumber of the track (optional)
```

###get_extended_artwork(imdb_id="", tvdb_id="", media_type="")
```
    Returns all available artwork from fanart.tv for the kodi video
    Parameters: 
    imdb_id: imdbid of the media
    tvdb_id: tvdbid of the media (can be used instead of imdbid, one of them is required)
    media_type: The container content type --> movies or tvshows
    in case of episodes or seasons, provide the tvshow details
```

###get_tmdb_details(imdb_id="", tvdb_id="", title="", year="", media_type="", manual_select=False)
```
    Returns the complete (kodi compatible formatted) metadata from TMDB
    Parameters: 
    imdb_id: imdbid of the media (strict match if submitted)
    tvdb_id: tvdbid of the media (strict match if submitted)
    title: title of the media if no imdbid/tvdbid is present (search)
    year: year of the media (for more accurate search results if title supplied)
    media_type: The container content type (movies or tvshows) - for more accurate search results if searching by title
    manual_select: will show a select dialog to choose the preferred result (if searching by title)
    
    By default, the search by title will return the most likely result. It is suggested to also submit the year and/or media type for better matching
```

###get_moviesetdetails(set_id)
```
    Returns complete (nicely formatted) information about the movieset and it's movies
    Parameters: 
    set_id: Kodi DBID for the movieset (str/int)
```

###get_streamdetails(db_id, media_type)
```
    Returns complete (nicely formatted) streamdetails (resolutions, audiostreams etc.) for the kodi media item
    Parameters: 
    db_id: Kodi DBID for the item (str/int)
    media_type: movies/episodes/musicvideos
```


###get_pvr_artwork(title, channel="", genre="", manual_select=False)
```
    Returns complete (nicely formatted) metadata including artwork for the given pvr broadcast.
    Uses numerous searches to get the info. Result is localized whenever possible.
    Parameters: 
    title: The title of the PVR entry (required)
    channel: the channelname of the PVR entry (optional, for better matching)
    genre: the genre of the PVR entry (optional, for better matching)
    manual_select: will show a select dialog to choose the preferred result
    
    Note: In the addon settings for the kodi module, the user can set personal preferences for the scraper.
```

###pvr_artwork_options(title, channel="", genre="")
```
    Shows a dialog to manually override/scrape the artwork by the user for the given PVR entry (used for example in contextmenu)
    Parameters: 
    title: The title of the PVR entry (required)
    channel: the channelname of the PVR entry (optional, for better matching)
    genre: the genre of the PVR entry (optional, for better matching)
```

###get_channellogo(channelname)
```
    Returns the channellogo (if found) for the given channel name.
    Looks up kodi PVR addon first, and fallsback to the logo db.
```

###get_studio_logo(studio)
```
    Returns the studio logo for the given studio (searches the artwork paths to find the correct logo)
    Input may be a single studio as string, multiple studios as string or even a list of studios.
    The logos path/resource addon is scanned untill a logo is found for any of the supplied studios.
    
    NOTE: Requires a searchpath to be set, see method below!
```

###studiologos_path(filepath)
```
    Sets/gets the path to look for studio logos, used in above "get_studio_logo" method.
    this can be a path on the filesystem, VFS path or path to a resource addon:
    _metadatautils.studiologos_path("my_path_to_the_studio_logos")
    Can also be used as getter if no value supplied.
```


###get_animated_artwork(imdb_id, manual_select=False)
```
    Get animated artwork (poster and/or fanart) if exists for the given movie by querying the consiliumdb with animatedart.
    For more info, see: http://forum.kodi.tv/showthread.php?tid=215727
    
    Parameters: 
    imdb_id: IMDBID of the movie (may also be TMDBID)
    manual_select: (optional) if True a dialog will be shown to the user to select the preferred result.
    
    NOTE: After scraping the artwork is also stored in the kodi db so it can be accessed by Listitem.Art(animatedposter) and Listitem.Art(animatedfanart)
```


###get_omdb_info(imdb_id="", title="", year="", content_type="")
```
    Get (kodi compatible formatted) metadata from OMDB, including Rotten tomatoes details
    
    Parameters: 
    imdb_id: IMDBID of the movie/tvshow
    title: Title of the movie/tvshow (if imdbid ommitted)
    year: Year of the movie/tvshow (for better search results when searching by title)
    media_type: Mediatype movies/tvshows (for better search results when searching by title)
```

###get_top250_rating(imdb_id)
```
    get the position in the IMDB top250 for the given IMDB ID (tvshow or movie)
```

###get_tvdb_details(imdbid="", tvdbid="")
```
    gets all information for the given tvshow from TVDB, including details of the next airing episode, the last aired episoded and air date and time.
    Input is either the imdbid or the tvdbid.
```


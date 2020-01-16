# script.metadata.editor

Kodi script to edit basic metadata information of library items with support to automatically update the .nfo file.


## Supported .nfo types

The updating of .nfo items is only possible for video library items, because the JSON result doesn't return any path for music entries.

Supported .nfo namings:

* %Filename%.nfo
* tvshow.nfo
* movie.nfo

By default the script is creating a .nfo if missing. This can be disabled in the settings.


## Scrapers

The script is using TMDb (free) and OMDb.

I already have included a TMDb API key (hardcoded).

For OMDb please visit https://omdbapi.com/ and create your own API key and add it to the addon settings.
Please note that the free available OMDb API key is limited to 1.000 calls a day. I highly recommend to become a patreon of the creator of OMDb.
For $1 a month your daily limit gets increased to 100.000 calls / day. Support it and benefit.

TMDb scraper (not used for episodes, because of different global airing dates and episode orders):
* Rating + votes
* MPAA
* Premiered year
* TV show status
* External unique IDs (IMDb, TVDb)

OMDb scraper:
* Rotten ratings (all four of them incl. votes)
* Metacritic (just rating, no votes available)
* IMDb (ID + rating + votes)

Note:
There is a experimental setting available to use title + year for the OMDb call, if the IMDb ID is not available. It's disabled by default, because there is a high chance for false positive returnings and wrong fetched metadata. I do not recommend to enable it.


## Running service

* Updates the watched states in the .nfo automatically if item is played or marked/unmarked as watched (can be disabled)
* Option to rate your movie/episode after it has been played 100% (can be disabled)


## Additional features of the rating updater

* Updates MPAA (can be disabled)
* Updates TV show status
* Updates missing uniqueids
* Updates original title

You can configure the preferred MPAA rating in the addon settings.
It's also possible to skip "not rated" or to enable/disable the fallback to US ratings


## Run the script / context menu

The script can be called with the context menu or RunScript() commands (useful for skinners).
A library updating task can be started by starting the addon itself.

Context menu entries:

* `Metadata Editor` / `Open Editor` = editor dialog or sub menu if more options are available
* `Add/remove available genres` = quickly edit the genres which the item belongs to
* `Add/remove available tags` = quickly edit the tags which the item belongs to
* `Add/remove favourite tag` = shortcut to toggle the library tag `Watchlist`. Can be used to create custom splitted favourite widgets.
* `Update .nfo` = updates the .nfo
* `Update ratings` = will update ratings by using the OMDb and TMDb API


RunScript calls:

*  `RunScript(script.metadata.editor,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = opens editor
*  `RunScript(script.metadata.editor,action=setuserrating,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = sets user rating and updates the nfo if enabled
*  `RunScript(script.metadata.editor,action=setgenres,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = opens genre selector
*  `RunScript(script.metadata.editor,action=settags,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = opens tags selector
*  `RunScript(script.metadata.editor,action=togglewatchlist,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = toggle watchlist tag
*  `RunScript(script.metadata.editor,action=updatenfo,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = updates the .nfo

RunScript calls for updating ratings:
*  `RunScript(script.metadata.editor)` = Shows select dialog to update movies, shows and episodes or all of them
*  `RunScript(script.metadata.editor,action=updaterating,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = Updates rating for the requested item
*  `RunScript(script.metadata.editor,action=updaterating,content=movies)` = Updates all ratings for movies (combination of available TMDb, TVDb, IMDb IDs)
*  `RunScript(script.metadata.editor,action=updaterating,content=tvshows)` = Updates all ratings for TV shows (combination of available TMDb, TVDb, IMDb IDs)
*  `RunScript(script.metadata.editor,action=updaterating,content=episodes)` = Updates all ratings for TV shows (only if IMDb is available)
*  `RunScript(script.metadata.editor,action=updaterating,content=movies+tvshows+episodes)` = Updates all ratings for provided content. Values are splitted by '+'
# script.metadata.editor

Kodi script to edit basic metadata information of library items with support to automatically update the .nfo file.


## Supported .nfo types

The updating of .nfo items is only possible for video library items, because the JSON result doesn't return any path for music entries.

Supported .nfo namings:

* %Filename%.nfo
* tvshow.nfo
* movie.nfo


## Run the script / context menu

The script can be called with the context menu or RunScript() commands (useful for skinners).
A library updating task can be started by starting the addon itself.

Context menu entries:

* `Metadata Editor` / `Open Editor` = Editor dialog or sub menu if more options are available
* `Add/remove available genres` = Quickly edit the genres which the item belongs to
* `Add/remove available tags` = Quickly edit the tags which the item belongs to
* `Add/remove favourite tag` = Shortcut to toggle the library tag `Watchlist`. Can be used to create custom splitted favourite widgets.
* `Update ratings` = Will update ratings by using the OMDb and TMDb API


RunScript calls:

*  `RunScript(script.metadata.editor,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = opens editor
*  `RunScript(script.metadata.editor,action=setgenres,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = opens genre selector
*  `RunScript(script.metadata.editor,action=settags,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = opens tags selector
*  `RunScript(script.metadata.editor,action=togglewatchlist,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = toggle watchlist tag
*  `RunScript(script.metadata.editor,action=updaterating,dbid=$INFO[ListItem.DBID],type=$INFO[ListItem.DBType])` = Updates rating for the requested item

RunScript calls for updating ratings:
*  `RunScript(script.metadata.editor)` = Shows select dialog to update movies, shows and episodes or all of them
*  `RunScript(script.metadata.editor,action=updaterating)` = Updates all movie/TV show ratings (combination of available TMDb, TVDb, IMDb IDs) and episode ratings (only if IMDb is available)
*  `RunScript(script.metadata.editor,action=updaterating,type=movie)` = Updates all ratings for movies (combination of available TMDb, TVDb, IMDb IDs)
*  `RunScript(script.metadata.editor,action=updaterating,type=tvshow)` = Updates all ratings for TV shows (combination of available TMDb, TVDb, IMDb IDs)
*  `RunScript(script.metadata.editor,action=updaterating,type=episode)` = Updates all ratings for TV shows (only if IMDb is available)
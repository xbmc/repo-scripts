# labelID and Localisation

labelID is the system that Skin Shortcuts uses to individually identify menu items. Each menu item will be assigned a unique labelID, which is a non-localised version of the menu items label.

## Common labelID values

The following is a list of many common strings used by available shortcuts and the labelID that will be generated for it. It also includes the icon Skin Shortcuts will use and its English translation.

| label | labelID | Icon | English translation |
| :---: | :-----: | :--: | :-----------------: |
| 10006 | videos | DefaultVideos.png | Videos |
| 342 | movies | DefaultMovies.png | Movies |
| 20343 | tvshows | DefaultTVShows.png | TV Shows |
| 32022 | livetv | DefaultTVShows.png | Live TV |
| 32087 | radio | DefaultAudio.png | Radio |
| 10005 | music | DefaultMusicAlbums.png | Music |
| 20389 | musicvideos | DefaultMusicVideos.png | Music Videos |
| 10002 | pictures | DefaultPicture.png | Pictures |
| 12600 | weather | | Weather |
| 10001 | programs | DefaultProgram.png | Programs |
| 32032 | dvd | DefaultDVDFull.png | DVD |
| 32033 | 32033 | DefaultDVDFull.png | Eject DVD |
| 10004 | settings | | Settings |
| 7 | 7 | DefaultFolder.png | File Manager |
| 13200 | 13200 | UnknownUser.png	 | Profiles |
| 10003 | 10003 | | System Information |
| 32046 | 32046 | | Update video library |
| 32047 | 32047 | | Update audio library |
| 744 | 744 | DefaultFolder.png | Files |
| 136 | 136 | DefaultVideoPlaylists.png | Playlists (video library) |
| 136 | 136 | DefaultMusicPlaylists.png | Playlists (music library) |
| 20386 | 20386 | DefaultRecentlyAddedMovies.png | Recently Added Movies |
| 344 | 344 | DefaultActor.png | Actors |
| 20451 | 20451 | DefaultCountry.png | Countries |
| 20348 | 20348 | DefaultDirector.png | Directors |
| 135 | 135 | DefaultGenre.png | Genres (video library) |
| 135 | 135 | DefaultMusicGenre.png | Genres (music library) |
| 20434 | 20434 | DefaultSets.png	 | Sets |
| 20388 | 20388 | DefaultStudios.png | Studios |
| 20459 | 20459 | DefaultTags.png	 | Tags |
| 369 | 369 | DefaultMovieTitle.png | Title (movies) |
| 369 | 369 | DefaultTVShowTitle.png | Title (tv shows) |
| 369 | 369 | DefaultMusicVideoTitle.png | Title (music videos) |
| 562 | 562 | DefaultYear.png | Year |
| 20387 | 20387 | DefaultRecentlyAddedEpisodes.png | Recently Added Episodes
| 19023 | 19023 | DefaultTVShows.png | TV Channels |
| 19024 | 19024 | DefaultTVShows.png | Radio Channels |
| 19069 | 19069 | DefaultTVShows.png | EPG |
| 19163 | 19163 | DefaultTVShows.png | Recordings |
| 32023 | 32023 | DefaultTVShows.png | Timers |
| 20390 | 20390 | DefaultRecentlyAddedMusicVideos.png | Recently Added Music Videos |
| 626 | 626 | DefaultInProgressShows.png | In Progress TV Shows |
| 20389 | 20389 | DefaultMusicVideos.png | Music Videos |
| 133 | 133 | DefaultMusicArtists.png | Artists |
| 15100 | 15100 | DefaultFolder.png | Library (music library) |
| 132 | 132 | DefaultMusicAlbums.png | Albums |
| 134 | 134 | DefaultMusicSongs.png | Songs |
| 652 | 652 | DefaultMusicYears.png | Years |
| 271 | 271 | DefaultMusicTop100.png | Top 100 |
| 10504 | 10504 | DefaultMusicTop100Songs.png | Top 100 Songs |
| 10505 | 10505 | DefaultMusicTop100Albums.png | Top 100 Albums |
| 359 | 359 | DefaultMusicRecentlyAdded.png | Recently Added Albums |
| 517 | 517 | DefaultMusicRecentlyPlayed.png | Recently Played Albums |
| 1037 | 1037 | DefaultAddonVideo.png | Video Add-ons |
| 1038 | 1038 | DefaultAddonMusic.png | Music Add-ons |
| 1039 | 1039 | DefaultAddonPicture.png | Picture Add-ons |
| 32023 | 32023 | DefaultAddonProgram.png | Programs |

#### Playlists

labelID - Name of playlist (lowercase, without spaces)
icon - DefaultPlaylist.png

#### Favourites

labelID - Name of the the favourite (lowercase, without spaces)
icon	- DefaultPlaylist.png
		  DefaultShortcut.png
thumbnail - the favourites thumbnail
			
#### Add-Ons

labelID - For the root directory of plugins and programs with no arguments, plugin.addon.name or script.addon.name
        - For other plugin directories the name as returned by the add-on or based on the label defined in the defaults
thumbnail - Thumbnail of the add-on
icon - DefaultAddon.png		

## defaultID

Whilst the labelID for a given menu item will change if the shortcut changes, the defaultID - once set - will remain the same. However, it is not guaranteed unique in a given menu.

## Localising strings

Skin Shortcuts has code to ensure that you can use localised strings from your skin throughout. When the menu's are saved, any string provided by a skin is saved in a special format so that the script knows which skin it came from and what its last translation was.

This means that if the user switches skins, the label from the previous skin is still available, though it will no longer localise if the user changes language.

One limitation of it, though, is that it can't manage multiple skin strings combined together, so you should ensure that you are only using a single string at a time.

It's also worth noting that only menu items - not the additional properties associated with the menu items - are shared between skins. This means it is totally safe to use localised strings for backgrounds, widgets, custom properties and so forth.

***Quick links*** - [Readme](../../README.md) - [Getting Started](./started/Getting Started.md) - [Advanced Usage](./advanced/Advanced Usage.md)
# script.videolinks

This kodi script matches songs in your music library with video information from TheAudioDB and
stores the links (usually youtube links) in the music database.  This means you can not only play
the version of the song you have in your local library, you can also play the song video. Please
note that the actual videos are **not** downloaded, just the links to them.

This software is provided under the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

## Users

This script requires skin support and a working youtube plugin

## Skinners

Scraped video links can be found in **ListItem.SongVideoURL** and any 
associated art in **ListItem.Art(videothumb)**

The script can be called from the addons section in which case it will process all artists, or
it can be passed an artist ID in which case it will just process that artist.  It's therefore
possible to skin a button on the artistinfo dialog to fetch video links for that particular artist
using `RunScript(script.videolinks,$INFO[ListItem.DBID])` in the onclick method
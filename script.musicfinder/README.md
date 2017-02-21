# script.musicfinder
A simple script for skinners that lets them create buttons to allow users to move directly to the currently playing artist or album's listing.

- Go to artist
<onclick>Runscript(script.musicfinder,action=artist,title=$INFO[musicplayer.artist],listid=50)</onclick>

- Go to album
<onclick>Runscript(script.musicfinder,action=album,title=$INFO[musicplayer.album],listid=50)</onclick>

The 'listid' parameter refers to the list control used by the artist or album view in your skin.

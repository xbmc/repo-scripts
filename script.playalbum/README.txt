INFO FOR SKINNERS

this script can be used to play an album (for instance from the album or song info dialog)

at album level, use:
RunScript(script.playalbum,albumid=$INFO[ListItem.DBID])

at song level, use:
RunScript(script.playalbum,songid=$INFO[ListItem.DBID])

it's also possible to start playing a specific track, e.g. from the track list in the album info dialog:
RunScript(script.playalbum,albumid=$INFO[ListItem.DBID]&amp;tracknr=$INFO[Container(50).ListItem.TrackNumber])


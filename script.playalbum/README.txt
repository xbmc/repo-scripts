this script can be used to play an album (for instance from the album or song info dialog)

at album level, use:
RunScript(script.playalbum,albumid=$INFO[ListItem.DBID])

at song level, use:
RunScript(script.playalbum,songid=$INFO[ListItem.DBID])


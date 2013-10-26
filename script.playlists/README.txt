INFO FOR SKINNERS

this script will return a list of video or music playlists.

for video playlists:
RunScript(script.playlists,type=video)

for music playlists:
RunScript(script.playlists,type=music)


the script will set the following window properties:
Window(Home).Property(ScriptPlaylist.%d.Name)  - name of the playlist
Window(Home).Property(ScriptPlaylist.%d.Path)  - playlist path

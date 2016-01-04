# Play Random Videos
A Kodi add-on to play random videos. This script can play random episodes from TV shows, movies from genres/sets/years/tags, and videos from playlists, filesystems, and just about anything else, other than plugins. This add-on does not directly add functionality on its own and must be supported by skins or other add-ons. Try the Context item "Play Random Video" add-on to play a random video from any supported list, right from the context menu.

### Settings
There are add-on settings to set the default watched filter for each video library section, 'movies', 'TV shows', and 'music videos'. The available options are 'All videos', only 'Unwatched', only 'Watched', and 'Ask me', which prompts you each time the script is run.

## Skin usage
Skins can use it with an action like so: `RunScript(script.playrandomvideos, "<list path>", "label=<list label>")`.

List path is the path to the list to play, like ListItem.FolderPath, which should be escaped (`$ESCINFO[]`) or wrapped in quotation marks. *label* is the list name, like ListItem.Label, and is required when available, also escaped/quoted. Additional optional arguments are *forcewatchmode*, which overrides the default watch mode selected in the add-on settings, and *limit*, which sets the number of videos to queue up, defaulting to a single video.

In **MyVideoNav.xml** an action like `RunScript(script.playrandomvideos, "$INFO[Container.FolderPath]", "label=$INFO[Container.FolderName]", forcewatchmode=$INFO[Control.GetLabel(10)], limit=50)` makes for a good button in the sidebar or as some other container-focused option. Use `<visible>!IsEmpty(Container.FolderPath) + !SubString(Container.FolderPath, plugin, left) + !SubString(Container.FolderPath, addons, Left) + !SubString(Container.FolderPath, sources, Left)</visible>` to hide it for paths that the script ignores.

A label is available with `$ADDON[script.playrandomvideos 32100]`, 'Play Random'.

### forcewatchmode values
*forcewatchmode* accepts 'All videos', 'Unwatched', 'Watched', and 'Ask me', as well as their localized equivalents with these IDs: `16100`, `16101`, `16102`, and `36521`. In **MyVideoNav.xml**, `forcewatchmode=$INFO[Control.GetLabel(10)]` should always match the behavior of the script to the button that switches between the three, if it is on your window.

### Plugins
It doesn't work for plugin paths. I would like it to, but I can't figure a good way to implement it, considering all the things plugins do.

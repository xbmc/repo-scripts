# Play Random Videos
A Kodi add-on to quickly play random videos from (nearly) any list. This add-on can
play random episodes from TV shows, movies from genres/sets/years/tags, and videos
from playlists, file systems, and just about anything else*.

It adds a [context item] to most playable lists of videos and provides a script
that can be executed by skins with `RunScript` and JSON-RPC with `Addons.ExecuteAddon`.

Install it from the official Kodi repo, under "Context menus", for Kodi 16 Jarvis and newer.  
[Support and feedback thread] on the Kodi Forums.  
Source available on GitHub at [script.playrandomvideos].

[context item]: http://kodi.wiki/view/Context_menu#Contextual_menu
[Support and feedback thread]: https://forum.kodi.tv/showthread.php?tid=238613
[script.playrandomvideos]: https://github.com/rmrector/script.playrandomvideos/

## Skin usage
Skins can use it with an action like so: `RunScript(script.playrandomvideos, <list path>,
"label=<list label>")`.

List path is the path to the list to play, like ListItem.FolderPath, which should be
escaped (`$ESCINFO[ListItem.FolderPath]`). *label* is the list name, like
ListItem.Label or FolderName, and is required when available, also escaped/quoted. There are optional
arguments *watchmode*, which can override the default watch mode selected in the add-on settings,
and *singlevideo* to play just a single video, if you have occasion for such an action.

In **MyVideoNav.xml** an action like `RunScript(script.playrandomvideos, "$INFO[Container.FolderPath]",
"label=$INFO[Container.FolderName]", watchmode=$INFO[Control.GetLabel(10)])`
makes for a good button in the sidebar or as some other container-focused option. Use

    <visible>ListItem.IsFolder + !ListItem.IsParentFolder + !String.Contains(ListItem.FolderPath, plugin, Left) + !String.Contains(ListItem.FolderPath, addons, Left) + !String.Contains(ListItem.FolderPath, sources, Left) + !String.IsEqual(ListItem.FolderPath, add)</visible>

to match the context item's visibility on this window.

A label is available with `$ADDON[script.playrandomvideos 32100]`, 'Play Random'.

*watchmode* accepts 'Unwatched', 'Watched', and 'Ask me', as well
as their localized equivalents with these IDs: `16101`, `16102`, and `36521`.
In **MyVideoNav.xml**, `watchmode=$INFO[Control.GetLabel(10)]` should
match the behavior of the button that switches between watched/unwatched/all,
if it is on your window. *singlevideo* needs no value.

## Button/menu actions

It is also possible to create an action that always plays randomly from one specific list, for use
in a home menu or even as flair on another window, which can be assigned with Skin Shortcuts
or added directly to skin files.

- Play randomly from a list of all movies: `RunScript(script.playrandomvideos, "videodb://movies/")`
- all episodes: `RunScript(script.playrandomvideos, "videodb://tvshows/")`
- all music videos: `RunScript(script.playrandomvideos, "videodb://musicvideos/")`
- from any of your playlists: `RunScript(script.playrandomvideos, "special://playlists/video/<playlist filename>")`
- movies from any genre: `RunScript(script.playrandomvideos, "videodb://movies/genres/xx/", "label=Documentary")`
- episodes from any TV network: `RunScript(script.playrandomvideos, "videodb://tvshows/studios/xx/", "label=Cartoon Network")`

## * Plugins
It doesn't work for plugin paths :(. I would like it to, but I can't figure a good
way to implement it, considering all the things plugins do.

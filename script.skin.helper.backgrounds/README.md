# script.skin.helper.backgrounds
a helper service for Kodi skins providing rotating backgrounds



### Backgrounds provided by the script
The script has a background scanner to provide some rotating fanart backgrounds which can be used in your skin as backgrounds. The backgrounds are available in window properties.

IMPORTANT NOTE:

To enable the rotating images, you must set a skin string in your skin/addon:
Skin.SetString(SkinHelper.RandomFanartDelay, 30)

The value defines the interval for the image rotation.
Setting the value to 0 clearing it disables the background service.
Recommended value is 30 seconds.


| property 			| description |
| :----------------------------	| :----------- |
| SkinHelper.AllMoviesBackground | Random fanart of movies in video database|
| SkinHelper.AllTvShowsBackground | Random fanart of TV shows in video database|
| SkinHelper.AllMusicVideosBackground | Random fanart of music videos in video database|
| SkinHelper.RecentMusicBackground | Random fanart of recently added music|
| SkinHelper.AllMusicBackground | Random fanart of music artists in database|
| SkinHelper.GlobalFanartBackground | Random fanart of all media types|
| SkinHelper.InProgressMoviesBackground | Random fanart of in progress movies|
| SkinHelper.RecentMoviesBackground | Random fanart of in recently added movies|
| SkinHelper.UnwatchedMoviesBackground | Random fanart of unwatched movies|
| SkinHelper.InProgressShowsBackground | Random fanart of in progress tv shows|
| SkinHelper.RecentEpisodesBackground | Random fanart of recently added episodes|
| SkinHelper.AllVideosBackground | Random videos background (movie/show/musicvideo)|
| SkinHelper.RecentVideosBackground | Recent videos background (movie or tvshow)|
| SkinHelper.InProgressVideosBackground | In progress videos background (movie or tvshow)|
| SkinHelper.PvrBackground | Random fanart collected by the PVR thumbs feature|
| SkinHelper.PicturesBackground | Random pictures from all picture sources. By default this pulls images from all picture sources the user has configured. It is however possible to provide a custom source from which the images should be pulled in the addon settings|

Additional properties available for the backgrounds (e.g. SkinHelper.AllMoviesBackground.Poster)

| property 			| description |
| :----------------------------	| :----------- |
| SkinHelper.BACKGROUNDNAME.poster | Poster image for the background (if available)|
| SkinHelper.BACKGROUNDNAME.clearlogo | Clearlogo image for the background (if available)|
| SkinHelper.BACKGROUNDNAME.landscape | Landscape image for the background (if available)|
| SkinHelper.BACKGROUNDNAME.title | Title for the background (if available)|



________________________________________________________________________________________________________


### Wall Backgrounds provided by the script
The service provides pre-built image walls for certain collections. Ready to use in your skin.
The walls are pregenerated once (at first launch) and stored within the addon_data folder.

Important NOTE: Generation of wall backgrounds is resource heavy and disabled by default. 
You must enable it in your skin by setting this skin bool: SkinHelper.EnableWallBackgrounds


NOTE 2: In the addon settings users can configure the rotation speed/interval or even disable the entire service.
Default is 60 seconds.


| property 			| description |
| :----------------------------	| :----------- |
| SkinHelper.AllMoviesBackground.Wall | Collection of Movie fanart images (from the library as wall prebuilt by the script|
| SkinHelper.AllMoviesBackground.Wall.BW | Collection of Movie fanart images (from the library as wall (black and white prebuilt by the script|
| SkinHelper.AllMoviesBackground.Poster.Wall | Collection of Movie poster images (from the library as wall prebuilt by the script|
| SkinHelper.AllMoviesBackground.Poster.Wall.BW | Collection of Movie poster images (from the library as wall (black and white prebuilt by the script|
| SkinHelper.AllMusicBackground.Wall | Collection of Artist fanart images (from the library as wall prebuilt by the script|
| SkinHelper.AllMusicBackground.Wall.BW | Collection of Artist fanart images (from the library as wall (black and white prebuilt by the script|
| SkinHelper.AllMusicSongsBackground.Wall | Collection of Song/Album cover images (from the library as wall prebuilt by the script|
| SkinHelper.AllTvShowsBackground.Wall | Collection of Tv show fanart images (from the library as wall prebuilt by the script|
| SkinHelper.AllTvShowsBackground.Wall.BW | Collection of Tv show fanart images (from the library as wall (black and white prebuilt by the script|
| SkinHelper.AllTvShowsBackground.Poster.Wall | Collection of Tv show poster images (from the library as wall prebuilt by the script|
| SkinHelper.AllTvShowsBackground.Poster.Wall.BW | Collection of Tv show poster images (from the library as wall (black and white prebuilt by the script|


________________________________________________________________________________________________________


### Individual random images for creating image walls yourself in your skin
If you want to create a wall with images yourself in your skin and you need randomly changing images, there is a way to let the script provide these images for you.


You will have to enable the generation of wall images for each SkinHelper provided background by setting a skin string:
Skin.SetString(BACKGROUNDNAME.EnableWallImages, 20)
This value controls the number of images that should be provided by the script, if empty or 0 there will be no images generated.
Once both the global delay and the item-specific limit skinstrings are set, the images will be available like this: 
BACKGROUNDNAME.Wall.X (where X is the number of the image, start counting from 0)

You should be able to enable the wall-images feature for any rotating skinhelper background, including those from the smart shortcuts.
Also note that the additional properties will also be available e.g. SkinHelper.AllMoviesBackground.Wall.1.Poster)

Examples...

```
To get a collection of 10 images from the AllMoviesBackground provided by skinhelper:

Skin.SetString(SkinHelper.AllMoviesBackground.EnableWallImages, 10)

And to get e.g. fanart image 5 from the collection: $INFO[Window(Home).Property(SkinHelper.AllMoviesBackground.Wall.5)]

Or the poster: $INFO[Window(Home).Property(SkinHelper.AllMoviesBackground.Wall.5.Poster)
```


Or to get the images for one of the plex smart shortcuts:

```
Skin.SetString(plexbmc.0.image.EnableWallImages, 10)  --> enable it for 10 images

And to get for example the first fanart image of the collection: $INFO[Window(Home).Property(plexbmc.0.image.Wall.0)]

```





Last example, get the images for playlists (smart shortcuts for playlists should be enabled!)

```
Skin.SetString(playlist.0.image.EnableWallImages, 10  --> enable it for the first playlist and we want 10 images

And to get for example the second fanart image of the collection: $INFO[Window(Home).Property(playlist.0.image.Wall.1)]
```




The dynamic backgrounds for the smartshortcuts (e.g. playlist.X.image should be set individually.

It should be pretty safe if you just enable them for all available options, the script checks if the smartshortcuts actually exists.

So ,you should be fine if you do this:

```

Skin.SetString(playlist.0.image.EnableWallImages, 10)

Skin.SetString(playlist.1.image.EnableWallImages, 10)

Skin.SetString(playlist.2.image.EnableWallImages, 10)

Skin.SetString(playlist.3.image.EnableWallImages, 10)

etc. etc.

```


CAUTION: The script uses the already cached in memory collections of images to provide you the individual images to build your wall, it does add a little overhead but it should not be noticeable.
What you do have to realize is that if you show for example a wall of 20 fanart images in your skin, all 20 fanart images will be cached by Kodi in memory, this WILL impact the performance.
You might run into problems when using this approach on a low powered platform such as the Raspberry Pi.

To have the least impact on performance as possible, you can use the prebuilt wall images that are provided by this script.
These are already resized into 1 image so that Kodi will only have to load 1 fanart image in memory.

________________________________________________________________________________________________________


### Conditional Background overrides
Allows the user to globally override the skin's background on certain date conditions.
For example setup a christmas background at late december etc.
By launching this script entrypoint the user will be presented with a dialog to add, delete and edit conditional overrides.

```
RunScript(script.skin.helper.backgrounds,action=conditionalbackgrounds)            
```

#####To use the conditional background in your skin
If a background is active the window property "SkinHelper.ConditionalBackground)" will be filled by the service.


________________________________________________________________________________________________________


### Smart shortcuts feature
This feature is introduced to be able to provide quick-access shortcuts to specific sections of Kodi, such as user created playlists and favourites and entry points of some 3th party addons such as Emby and Plex. What it does is provide some Window properties about the shortcut. It is most convenient used with the skin shortcuts script but can offcourse be used in any part of your skin. The most important behaviour of the smart shortcuts feature is that is pulls images from the library path so you can have content based backgrounds.


##### Smart shortcuts for playlists
Will only be available if this Skin Bool is true --> SmartShortcuts.playlists

| property 			| description |
| :----------------------------	| :----------- |
| playlist.X.label | Title of the playlist|
| playlist.X.action | Path of the playlist|
| playlist.X.content | Contentpath (without activatewindow of the playlist, to display it's content in widgets.|
| playlist.X.image | Rotating fanart of the playlist|
--> replace X with the item count, starting at 0.


________________________________________________________________________________________________________


##### Smart shortcuts for Kodi Favourites
Will only be available if this Skin Bool is true --> SmartShortcuts.favorites

Note that only favourites will be processed that actually contain video/audio content.

| property 			| description |
| :----------------------------	| :----------- |
| favorite.X.label | Title of the favourite|
| favorite.X.action | Path of the favourite|
| favorite.X.content | Contentpath (without activatewindow of the favourite, to display it's content in widgets.|
| favorite.X.image | Rotating fanart of the favourite|
--> replace X with the item count, starting at 0.


________________________________________________________________________________________________________



##### Smart shortcuts for Plex addon (plugin.video.plexbmc)
Will only be available if this Skin Bool is true --> SmartShortcuts.plex

Note that the plexbmc addon must be present on the system for this to function.

| property 			| description |
| :----------------------------	| :----------- |
| plexbmc.X.title | Title of the Plex collection|
| plexbmc.X.path | Path of the Plex collection|
| plexbmc.X.content | Contentpath (without activatewindow of the Plex collection, to display it's content in widgets.|
| plexbmc.X.image | Rotating fanart of the Plex collection|
| plexbmc.X.type | Type of the Plex collection (e.g. movies, tvshows)|
| plexbmc.X.recent | Path to the recently added items node of the Plex collection|
| plexbmc.X.recent.content | Contentpath to the recently added items node of the Plex collection (for widgets)|
| plexbmc.X.recent.image | Rotating fanart of the recently added items node|
| plexbmc.X.ondeck | Path to the in progress items node of the Plex collection|
| plexbmc.X.ondeck.content | Contentpath to the in progress items node of the Plex collection (for widgets)|
| plexbmc.X.ondeck.image | Rotating fanart of the in progress items node|
| plexbmc.X.unwatched | Path to the in unwatched items node of the Plex collection|
| plexbmc.X.unwatched.content | Contentpath to the unwatched items node of the Plex collection (for widgets)|
| plexbmc.X.unwatched.image | Rotating fanart of the unwatched items node|
| |
| plexbmc.channels.title | Title of the Plex Channels collection|
| plexbmc.channels.path | Path to the Plex Channels|
| plexbmc.channels.content | Contentpath to the Plex Channels (for widgets)|
| plexbmc.channels.image | Rotating fanart of the Plex Channels|
| |
| plexfanartbg | A global fanart background from plex sources|
--> replace X with the item count, starting at 0.



________________________________________________________________________________________________________



##### Smart shortcuts for Emby addon (plugin.video.emby)
Will only be available if this Skin Bool is true --> SmartShortcuts.emby

Note that the Emby addon must be present on the system for this to function.

| property 			| description |
| :----------------------------	| :----------- |
| emby.nodes.X.title | Title of the Emby collection|
| emby.nodes.X.path | Path of the Emby collection|
| emby.nodes.X.content | Contentpath of the Emby collection (for widgets)|
| emby.nodes.X.image | Rotating Fanart of the Emby collection|
| emby.nodes.X.type | Type of the Emby collection (e.g. movies, tvshows)|
| |
| emby.nodes.X.recent.title | Title of the recently added node for the Emby collection|
| emby.nodes.X.recent.path | Path of the recently added node for the Emby collection|
| emby.nodes.X.recent.content | Contentpath of the recently added node for the Emby collection|
| emby.nodes.X.recent.image | Rotating Fanart of the recently added node for the Emby collection|
| |
| emby.nodes.X.unwatched.title | Title of the unwatched node for the Emby collection|
| emby.nodes.X.unwatched.path | Path of the unwatched node for the Emby collection|
| emby.nodes.X.unwatched.content | Contentpath of the unwatched node for the Emby collection|
| emby.nodes.X.unwatched.image | Rotating Fanart of the unwatched node for the Emby collection|
| |
| emby.nodes.X.inprogress.title | Title of the inprogress node for the Emby collection|
| emby.nodes.X.inprogress.path | Path of the inprogress node for the Emby collection|
| emby.nodes.X.inprogress.content | Contentpath of the inprogress node for the Emby collection|
| emby.nodes.X.inprogress.image | Rotating Fanart of the inprogress node for the Emby collection|
| |
| emby.nodes.X.recentepisodes.title | Title of the recent episodes node for the Emby collection|
| emby.nodes.X.recentepisodes.path | Path of the recent episodes node for the Emby collection|
| emby.nodes.X.recentepisodes.content | Contentpath of the recent episodes node for the Emby collection|
| emby.nodes.X.recentepisodes.image | Rotating Fanart of the recent episodes node for the Emby collection|
| |
| emby.nodes.X.nextepisodes.title | Title of the next episodes node for the Emby collection|
| emby.nodes.X.nextepisodes.path | Path of the next episodes node for the Emby collection|
| emby.nodes.X.nextepisodes.content | Contentpath of the next episodes node for the Emby collection|
| emby.nodes.X.nextepisodes.image | Rotating Fanart of the next episodes node for the Emby collection|
| |
| emby.nodes.X.inprogressepisodes.title | Title of the in progress episodes node for the Emby collection|
| emby.nodes.X.inprogressepisodes.path | Path of the in progress episodes node for the Emby collection|
| emby.nodes.X.inprogressepisodes.content | Contentpath of the in progress episodes node for the Emby collection|
| emby.nodes.X.inprogressepisodes.image | Rotating Fanart of the in progress episodes node for the Emby collection|


______________________________________________________________________________________________________
________________________________________________________________________________________________________

### Use with skin shortcuts script
This addon is designed to fully work together with the skinshortcuts script, so it will save you a lot of time because the script provides skinshortcuts with all the info to display contents.
No need to manually skin all those window properties in your skin, just a few lines in your overrides file is enough.

#### Display Smart Shortcuts in skin shortcuts listing

When the smart shortcuts are used together with skinshortcuts it will auto assign the icon and background with rotating fanart and both the widget and submenu (if needed are assigned by default. The user just adds the shortcut and is all set.

To display the complete listing of Smart Shortcuts in your skin, place the following line in your overrides file, in the groupings section:
```xml
<shortcut label="Smart Shortcuts" type="32010">||BROWSE||script.skin.helper.service/?action=smartshortcuts</shortcut>
```

full example:
```xml
<overrides>
	<groupings>
		<shortcut label="$ADDON[script.skin.helper.service 32062]" type="32010">||BROWSE||script.skin.helper.service/?action=smartshortcuts</shortcut>
	</groupings>
</overrides>	
```
Offcourse you can use a condition parameter to only show the smart shortcuts entry if it's enabled in your skin.
You can also choose to use display the smart shortcuts to be used as widgets, in that case include this line in your overrides.xml file:
```xml
<widget label="Smart Shortcuts" type="32010">||BROWSE||script.skin.helper.service/?action=smartshortcuts</widget>
```

#### Auto display Backgrounds provided by the script in skinshortcuts selector

You can choose to show all backgrounds (including those for smart shortcuts that are provided by this addon in the skinshortcuts backgrounds selector.

To display all backgrounds automatically in skinshorts you only have to include the line below in your overrides file:
```xml
<background label="smartshortcuts">||BROWSE||plugin://script.skin.helper.service/?action=backgrounds</background>
```

Note: You can still use the default skinshortcuts method to assign a default background to a item by labelID or defaultID.
In that case use the full $INFO path of the background. For example, to assign the "all movies" background to the Movies shortcut:
```xml
<backgrounddefault defaultID="movies">$INFO[SkinHelper.AllMoviesBackground)]</backgrounddefault>
```
For more info, see skinshortcut's documentation.


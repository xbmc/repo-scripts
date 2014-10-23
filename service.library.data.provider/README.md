plugin.library.data.provider
============================

Python script for use with XBMC

============================

INFORMATION FOR SKINNERS
============================

Include the following in your addon.xml
<import addon="service.library.data.provider" version="0.0.4"/>

Load a list with this content tag to have the list use cached data automatically refresh:
<content target="video">plugin://service.library.data.provider?type=randommovies&amp;reload=$INFO[Window.Property(randommovies)]</content>

To view within the library, create a link omitting the reload parameter:
<onclick>ActivateWindow(Videos,plugin://service.library.data.provider?type=randommovies,return)</onclick>

Available tags:
-   randommovies
-   recentmovies
-   recommendedmovies
-   recommendedepisodes
-   recentepisodes
-   randomepisodes
-   recentvideos (movies and episodes)
-   randomsongs
-   randomalbums
-   recentalbums
-   recommendedalbums
-	playliststats

Available infolabels:
Most of the usual video library infolabels. 
ListItem.Property(type) shows with what option the script was run.

Playliststats is used when a playlist or videonode is set as the onclick action in the (Home) menu.
Example:
Put a list in your Home.xml:
```xml
<control type="list" id="43260">
	<posx>0</posx>
	<posy>0</posy>
	<width>1</width>
	<height>1</height>
	<focusedlayout/>
	<itemlayout/>
	<content>plugin://service.library.data.provider?type=playliststats&amp;id=$INFO[Container(9000).ListItem.Property(Path)]</content>
</control>
```
The Path property has the onclick action defined. 
9000 is the ID of the Home main menu.
The following properties are available when the menu item containing the playlist or video node is highlighted:
-	Window(Home).Property(PlaylistWatched)
-	Window(Home).Property(PlaylistCount)
-	Window(Home).Property(PlaylistTVShowCount)
-	Window(Home).Property(PlaylistInProgress)
-	Window(Home).Property(PlaylistUnWatched)
-	Window(Home).Property(PlaylistEpisodes)
-	Window(Home).Property(PlaylistEpisodesUnWatched)




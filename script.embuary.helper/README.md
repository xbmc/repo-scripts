# script.embuary.helper
Addon for Kodi providing functions to the Embuary skin
________________________________________________________________________________________________________

# Service actions

## Automatically clear playlist

```
<onload>Skin.SetBool(EmbuaryHelperClearPlaylist)</onload>
```

This enables the script background service to clear the playlist after the playback has stopped.

________________________________________________________________________________________________________
## Auto fullscreen on playback

```
<onload>Skin.SetBool(StartPlayerFullscreen)</onload>
```

This will force "action(fullscreen)" once a playback has been started.

________________________________________________________________________________________________________
## PVR channel logo for recordings with thumbs

```
$INFO[Window(home).Property(Player.ChannelLogo)]
```

Returns the channel logo of the playing recording. Useful for recordings that have a thumbnail but you want to display the channel logo instead on the video OSD.

________________________________________________________________________________________________________
## EmbuaryPlayerAudioTracks boolean

```
!String.IsEmpty(EmbuaryPlayerAudioTracks)
```

Returns true if the currently playing video / stream has multiple audio tracks. Useful if you want to display a button to toggle the audio track, but only if multiple are available.



# Utilities

## "Play item"
```
RunScript(script.embuary.helper,action=playitem,item='$ESCINFO[ListItem.Filenameandpath]')
```

Closes all dialogs and goes back to the home window. Once home is active it starts the playback of the provided file.

________________________________________________________________________________________________________
## "Go to path"
```
RunScript(script.embuary.helper,action=goto,path='$ESCINFO[ListItem.Filenameandpath]',target=videos)
```

Closes all dialogs jumps directly to the provided path. If the script is called from a media window the existing container path is updated instead.

Useful for widgets inside of dialogs like a set of TV shows listed in the movieinformation dialog.

If the dialog was activated from a non media window like the home screen:
1. Dialog.Close(all,true)
2. "ActivateWindow($target,$path,return)" is called

If the dialog was activated from a media window like MyVideoNav.xml:
1. Dialog.Close(all,true)
2. "Container.Update($path)" is called

________________________________________________________________________________________________________
## Reset container positions

```
<onload>RunScript(script.embuary.helper,action=resetposition,container=200||201||202)</onload>
```

Will reset the provided container IDs to the first position.

________________________________________________________________________________________________________
## Simple background provider

```
$INFO[Window(home).Property(EmbuaryBackground)]
```

Provides a random fanart image of a random local movie or TV show.
The value is going to be refreshed after 20 seconds.

________________________________________________________________________________________________________
## Jump to show by episode

```
RunScript(script.embuary.helper,action=jumptoshow_by_episode,dbid=$INFO[ListItem.DBID])
```

Option to browse the show based on a DBID of a episode.

________________________________________________________________________________________________________
## Helper to get additional TV show details properties on season level

```
Runscript(script.embuary.helper,action=details_by_season,dbid=$INFO[ListItemAbsolute(0).DBID])
```

Example with a hidden custom dialog:

```
<?xml version="1.0" encoding="UTF-8"?>
<window id="1118" type="dialog">
	<visible>Container.Content(seasons) + String.IsEmpty(Container.Pluginname)</visible>
	<onload condition="!String.IsEmpty(ListItemAbsolute(0).DBID)">Runscript(script.embuary.helper,action=details_by_season,dbid=$INFO[ListItemAbsolute(0).DBID])</onload>
	<onload condition="String.IsEmpty(ListItemAbsolute(0).DBID) + !String.IsEmpty(ListItemAbsolute(1).DBID)">Runscript(script.embuary.helper,action=details_by_season,dbid=$INFO[ListItemAbsolute(1).DBID])</onload>
	<onunload>ClearProperty(tvshow.dbid,home)</onunload>
	<onunload>ClearProperty(tvshow.rating,home)</onunload>
	<onunload>ClearProperty(tvshow.seasons,home)</onunload>
	<onunload>ClearProperty(tvshow.episodes,home)</onunload>
	<onunload>ClearProperty(tvshow.watchedepisodes,home)</onunload>
	<onunload>ClearProperty(tvshow.unwatchedepisodes,home)</onunload>
	<controls/>
</window>
```



# Plugin sources

## In progress movies

```
plugin://script.embuary.helper/?info=getinprogress&amp;type=movie&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

________________________________________________________________________________________________________
## In progress episodes

```
plugin://script.embuary.helper/?info=getinprogress&amp;type=tvshow&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

________________________________________________________________________________________________________
## In progress movies and episodes

```
plugin://script.embuary.helper/?info=getinprogress&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

________________________________________________________________________________________________________
## Next up episodes

```
plugin://script.embuary.helper/?info=getnextup&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

Provides a list with the next unwatched episode of inprogress TV shows.
________________________________________________________________________________________________________
## Get seasons from a TV show

```
plugin://script.embuary.helper/?info=getseasons&amp;dbid=$INFO[ListItem.DBID]&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

```
plugin://script.embuary.helper/?info=getseasons&amp;title='$ESCINFO[ListItem.TvShowTitle]'&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

Provides a list with all available seasons from a TV show.

It's also possible to call the listing with the TV show ID.

________________________________________________________________________________________________________
## Get episodes from the same season

```
plugin://script.embuary.helper/?info=getseasonepisodes&amp;season=$INFO[ListItem.Season]&amp;title='$ESCINFO[ListItem.TvShowTitle]'&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

Provides a list with all episodes from the same TV show season.

It's also possible to call the listing with the TV show ID if it's available for some reason (Window property for example).

```
plugin://script.embuary.helper/?info=getseasonepisodes&amp;season=$INFO[ListItem.Season]&amp;dbid=$INFO[Window(home).Property(TVShowDBID)&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

________________________________________________________________________________________________________
## Recently updated TV shows (mixed TV shows and episodes)

```
plugin://script.embuary.helper/?info=getnewshows&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

Provides a list with recently updated TV shows. If a show has only one new episode it will be listed as episode to directly start the playback. If more new episodes are available the item will link to the TV show instead.

________________________________________________________________________________________________________
## Genres movies / tvshows

```
plugin://script.embuary.helper/?info=getgenre&amp;type=movie&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

```
plugin://script.embuary.helper/?info=getgenre&amp;type=tvshow&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```
Provides a list of all available genres. Each item has stored 4 of the available movie posters in the genre category:
- ListItem.Art(poster.0)
- ListItem.Art(poster.1)
- ListItem.Art(poster.2)
- ListItem.Art(poster.3)

________________________________________________________________________________________________________
## Get cast for movie / tvshow

By title:
```
plugin://script.embuary.helper?info=getcast&amp;type=tvshow&amp;title='$ESCINFO[ListItem.TVShowTitle]'
```

```
plugin://script.embuary.helper?info=getcast&amp;type=movie&amp;title='$ESCINFO[ListItem.Label]'
```

By DBID
```
plugin://script.embuary.helper?info=getcast&amp;dbid=tvshow&amp;dbid=$INFO[ListItem.DBID]
```

```
plugin://script.embuary.helper?info=getcast&amp;type=movie&amp;dbid=$INFO[ListItem.DBID]
```

Results will have no <onlick> command. You have to use a own <onclick> override for the container to enable an action.

________________________________________________________________________________________________________
## Similar movie (because you watched ...)

Based on a random recently watched item:
```
plugin://script.embuary.helper/?info=getsimilar&amp;type=movie&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```
Available ListItem property
- ListItem.Property(similartitle) = Returns the used movie to create headings like "Because you watched '2 Guns'"

Based on a DBID
```
plugin://script.embuary.helper/?info=getsimilar&amp;type=movie&amp;dbid=$INFO[ListItem.DBID]&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

________________________________________________________________________________________________________
## Similar TV show (because you watched ...)

Based on a random recently watched TV show (inprogress or completely watched):
```
plugin://script.embuary.helper/?info=getsimilar&amp;type=tvshow&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```
Available ListItem property
- ListItem.Property(similartitle) = Returns the used movie to create headings like "Because you watched 'Breaking Bad'"

Based on a DBID
```
plugin://script.embuary.helper/?info=getsimilar&amp;type=tvshow&amp;dbid=$INFO[ListItem.DBID]&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]
```

________________________________________________________________________________________________________
## Seasonal widgets

Helper to return movies/episodes for Christmas, Halloween or Star Wars day.

Example:
```
	<variable name="SeasonalSpecial">
		<value condition="System.Date(05-04,05-05) + Window.IsVisible(home)">plugin://script.embuary.helper/?info=getseasonal&amp;list=starwars&amp;limit=15&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]</value>
		<value condition="System.Date(05-04,05-05) + Window.IsVisible(1120)">plugin://script.embuary.helper/?info=getseasonal&amp;list=starwars&amp;type=movie&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]</value>
		<value condition="System.Date(12-01,12-27) + Window.IsVisible(home)">plugin://script.embuary.helper/?info=getseasonal&amp;list=xmas&amp;limit=15&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]</value>
		<value condition="System.Date(12-01,12-27) + Window.IsVisible(1120)">plugin://script.embuary.helper/?info=getseasonal&amp;list=xmas&amp;type=movie&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]</value>
		<value condition="System.Date(12-01,12-27) + Window.IsVisible(1121)">plugin://script.embuary.helper/?info=getseasonal&amp;list=xmas&amp;type=tvshow&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]</value>
		<value condition="System.Date(10-30,11-01) + Window.IsVisible(home)">plugin://script.embuary.helper/?info=getseasonal&amp;list=horror&amp;limit=15&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]</value>
		<value condition="System.Date(10-30,11-01) + Window.IsVisible(1120)">plugin://script.embuary.helper/?info=getseasonal&amp;list=horror&amp;type=movie&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]</value>
		<value condition="System.Date(10-30,11-01) + Window.IsVisible(1121)">plugin://script.embuary.helper/?info=getseasonal&amp;list=horror&amp;type=tvshow&amp;reload=$INFO[Window(home).Property(EmbuaryWidgetUpdate)]</value>
	</variable>
```

________________________________________________________________________________________________________
## Get seasons

```
plugin://script.embuary.helper/?info=getseasons&amp;dbid=$INFO[ListItem.DBID]
```

Can be called by DBID or title. Useful to display seasons in the info dialog

________________________________________________________________________________________________________
## Get episodes from season

```
plugin://script.embuary.helper/?info=getseasonepisodes&amp;title='$ESCINFO[ListItem.TvShowTitle]'&amp;season=$INFO[ListItem.Season]
```

Can be called by DBID or title. Useful to display another episodes from the same season in the episode info dialog.

________________________________________________________________________________________________________
## Jump to letter

```
plugin://script.embuary.helper/?info=jumptoletter&amp;reload=$INFO[Container.NumItems]
````

Provides a list to jump directly to a item inside of list in the media windows.

Available ListItem properties:
- ListItem.Property(NotAvailable)
- ListItem.Property(IsNumber)

Example implementation:
```

<itemlayout height="35" width="45">
	<control type="group">
		<visible>!String.IsEqual(ListItem.Label,Container.ListItem.SortLetter) + !String.IsEqual(ListItem.Property(IsNumber),Container.ListItem.SortLetter)</visible>
		<control type="textbox">
			<width>40</width>
			<height>40</height>
			<font>JumpToLetter</font>
			<align>center</align>
			<aligny>center</aligny>
			<textcolor>text_sublabel</textcolor>
			<label>$INFO[ListItem.Label]</label>
			<visible>String.IsEmpty(ListItem.Property(NotAvailable))</visible>
		</control>
		<control type="textbox">
			<width>40</width>
			<height>40</height>
			<font>JumpToLetter</font>
			<align>center</align>
			<aligny>center</aligny>
			<textcolor>disabled</textcolor>
			<label>$INFO[ListItem.Label]</label>
			<visible>!String.IsEmpty(ListItem.Property(NotAvailable))</visible>
		</control>
	</control>
	<control type="textbox">
		<width>40</width>
		<height>40</height>
		<font>JumpToLetter</font>
		<align>center</align>
		<aligny>center</aligny>
		<textcolor>white</textcolor>
		<label>$INFO[ListItem.Label]</label>
		<visible>String.IsEqual(ListItem.Label,Container.ListItem.SortLetter) | String.IsEqual(ListItem.Property(IsNumber),Container.ListItem.SortLetter)</visible>
	</control>
</itemlayout>
<focusedlayout height="35" width="45">
	<control type="group">
		<visible>!Control.HasFocus($PARAM[id])</visible>
		<control type="group">
			<visible>!String.IsEqual(ListItem.Label,Container.ListItem.SortLetter) + !String.IsEqual(ListItem.Property(IsNumber),Container.ListItem.SortLetter)</visible>
			<control type="textbox">
				<width>40</width>
				<height>40</height>
				<font>JumpToLetter</font>
				<align>center</align>
				<aligny>center</aligny>
				<textcolor>text_sublabel</textcolor>
				<label>$INFO[ListItem.Label]</label>
				<visible>String.IsEmpty(ListItem.Property(NotAvailable))</visible>
			</control>
			<control type="textbox">
				<width>40</width>
				<height>40</height>
				<font>JumpToLetter</font>
				<align>center</align>
				<aligny>center</aligny>
				<textcolor>disabled</textcolor>
				<label>$INFO[ListItem.Label]</label>
				<visible>!String.IsEmpty(ListItem.Property(NotAvailable))</visible>
			</control>
		</control>
		<control type="textbox">
			<width>40</width>
			<height>40</height>
			<font>JumpToLetter</font>
			<align>center</align>
			<aligny>center</aligny>
			<textcolor>white</textcolor>
			<label>$INFO[ListItem.Label]</label>
			<visible>String.IsEqual(ListItem.Label,Container.ListItem.SortLetter) | String.IsEqual(ListItem.Property(IsNumber),Container.ListItem.SortLetter)</visible>
		</control>
	</control>
	<control type="group">
		<visible>Control.HasFocus($PARAM[id])</visible>
		<control type="image">
			<left>-5</left>
			<width>51</width>
			<height>51</height>
			<texture border="20,20,20,20" colordiffuse="accent">items/focus.png</texture>
			<visible>Control.HasFocus($PARAM[id])</visible>
		</control>
		<control type="textbox">
			<width>40</width>
			<height>40</height>
			<font>JumpToLetter</font>
			<align>center</align>
			<aligny>center</aligny>
			<textcolor>white</textcolor>
			<label>$INFO[ListItem.Label]</label>
		</control>
	</control>
</focusedlayout>
```

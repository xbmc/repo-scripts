How to use this addon in your skin:


In MusicVisualisation.xml:

- 1) Set the default control to 999:
<defaultcontrol>999</defaultcontrol>

- 2) Add a button to start the script:
<control type="button" id="999">
	<posx>-10</posx>
	<posy>-10</posy>
	<width>1</width>
	<height>1</height>
	<onfocus>RunScript(script.artistslideshow)</onfocus>
</control>

- 3) Add a multiimage conrol:
<control type="multiimage">
	<posx>0</posx>
	<posy>0</posy>
	<width>1280</width>
	<height>720</height>
	<imagepath background="true">$INFO[Window.Property(ArtistSlideshow)]</imagepath>
	<aspectratio>keep</aspectratio>
	<timeperimage>5000</timeperimage>
	<fadetime>2000</fadetime>
	<randomize>true</randomize>
	<animation effect="fade" start="0" end="100" time="300">Visible</animation>
	<animation effect="fade" start="100" end="0" time="300">Hidden</animation>
	<visible>IsEmpty(Window.Property(ArtistSlideshowRefresh))</visible>
</control>



The script provide two properties to the skin:
- Window.Property(ArtistSlideshow) 
This is the path to the directory containing the downloaded images for the currently playing artist
- Window.Property(ArtistSlideshowRefresh)
This can be used to fade out/fade in the slideshow when the path is refreshed.
The path will refresh after all images for a certain artist have been downloaded.
This is needed since xbmc will not automatically pick up any new images once the multiimage have been loaded.

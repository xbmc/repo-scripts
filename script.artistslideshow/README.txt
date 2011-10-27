
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
	<imagepath background="true">$INFO[Window(Visualisation).Property(ArtistSlideshow)]</imagepath>
	<aspectratio>keep</aspectratio>
	<timeperimage>5000</timeperimage>
	<fadetime>2000</fadetime>
	<randomize>true</randomize>
	<animation effect="fade" start="0" end="100" time="300">Visible</animation>
	<animation effect="fade" start="100" end="0" time="300">Hidden</animation>
	<visible>IsEmpty(Window(Visualisation).Property(ArtistSlideshowRefresh))</visible>
</control>


You can also start this script at startup instead:
- RunScript(script.artistslideshow,daemon=True)
this will keep the script running all the time.


The script provides these properties to the skin:

- Window(Visualisation).Property(ArtistSlideshow)
This is the path to the directory containing the downloaded images for the currently playing artist

- Window(Visualisation).Property(ArtistSlideshowRefresh)
This can be used to fade out/fade in the slideshow when the path is refreshed.
The path will refresh after all images for a certain artist have been downloaded.
This is needed since xbmc will not automatically pick up any new images after the multiimage control has been loaded.

- Window(Visualisation).Property(ArtistSlideshowRunning)
This one is used internally by the script to check if it is already running.
There's no need to use this property in your skin.

- Window(Visualisation).Property(ArtistSlideshow.ArtistBiography)
Artist biography from last.fm

- Window(Visualisation).Property(ArtistSlideshow.%d.SimilarName)
- Window(Visualisation).Property(ArtistSlideshow.%d.SimilarThumb)
Similar artists

- Window(Visualisation).Property(ArtistSlideshow.%d.AlbumName)
- Window(Visualisation).Property(ArtistSlideshow.%d.AlbumThumb)
Albums by the artist


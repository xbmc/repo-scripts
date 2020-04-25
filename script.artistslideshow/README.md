# Artist Slideshow
Artist Slideshow is a Kodi addon that downloads images and additional information from fanart.tv and theaudiodb.com for the currently playing music artist.

## Donations
Donations are **not** accepted for Artist Slideshow.  If you find this addon useful, please consider instead supporting the services that make Artist Slideshow possible.
* fanart.tv: <https://fanart.tv/contribute/>
* theaudiodb: <http://theaudiodb.com> (look for the "donate with PayPal button)
* musicbrainz: <https://metabrainz.org/donate>

## Features
*  displays slideshow as background for music visualization (must use a compatible skin or update skin using the instructions below)
  *  option for a fallback slideshow if no local or remote images are found
  *  option to have a single slideshow displayed regardless of artist playing
  *  options to download artwork from fanart.tv and theaudiodb.com to display as background for music visualization
*  artist images can be downloaded (from fanart.tv and theaudiodb.com) and/or use a local directory of existing artist images
*  option to download artist bio and other additional information from Kodi's internal database, theaudiodb.com, or last.fm (skin must support display of this information)
*  support for overriding the artist bio, discography, and similar artists list with local information
*  option to limit size of download cache
*  support for multiple artists for a single song (as passed by Kodi)
*  also supports iTunes/Amazon standard of song name (feat. artist 2) in title MP3 tag
*  support for internet streams that put the artist name in the Kodi title field
*  support for other addons using Artist Slideshow to provide the background

## How to use this addon

### Find a Compatible Skin
There are a number of skins that support Artist Slideshow, but keeping a running list of them has proved too much work. I'd suggest visiting the Kodi forums and see if the skin you want to use supports Artist Slideshow.  I know the default Kodi skin (Estuary) supports Artist Slideshow (you need to be using Kodi 18.5 or later), as does the default OSMC skin.

### Changes to MusicVisualisation.xml
If you want to manually add support for AS to an existing skin, you need to add/update a few things in MusicVisualization.xml.

To run the script:
```xml
    <onload>RunScript(script.artistslideshow)</onload>
```

On AppleTV if ArtistSlideshow isn't updating after the first artist, use this instead:
```xml
    <onload>RunScript(script.artistslideshow, daemon=True)</onload>
```

You also need to add the XML code below (or update what the skin already has) to the skin's MusicVisualisation.xml.

```xml
    <control type="image">
        <aspectratio>scale</aspectratio>
        <fadetime>400</fadetime>
        <animation effect="fade" start="0" end="100" time="400">WindowOpen</animation>
        <animation effect="fade" start="100" end="0" time="300">WindowClose</animation>
        <texture background="true">$INFO[Player.Art(fanart)]</texture>
        <visible>String.IsEmpty(Window(Visualisation).Property(ArtistSlideshow.Image))</visible>
    </control>
    <control type="image">
        <aspectratio>scale</aspectratio>
        <fadetime>400</fadetime>
        <animation effect="fade" start="0" end="100" time="400">WindowOpen</animation>
        <animation effect="fade" start="100" end="0" time="300">WindowClose</animation>
        <texture background="true">$INFO[Window(Visualisation).Property(ArtistSlideshow.Image)]</texture>
        <visible>!String.IsEmpty(Window(Visualisation).Property(ArtistSlideshow.Image))</visible>
    </control>
```

## Addon settings

### Slideshow
**Delay between slide transitions:** (default 10 seconds)<br />
The time each slide will show on the screen.

**Use override slideshow** (default false)<br />
Tells Kodi to use this folder of images no matter what artist is playing. With this set no artist artwork will ever be downloaded.

*Override slideshow folder:* (default none)<br />
Path to a directory of images that should be used intead of artist artwork. 

**Fade to black during chage in artists:** (default True)<br />
Shows a black screen when transitioning from one artist to another. To allow the skin to show some other image during transition instead, set this to False.

**Include Kodi artist fanart:** (default True)<br />
If Kodi downloaded an artist image during scraping of the music, this image will be included in the slideshow and shown first while other images are loading in the background.

**Include Kodi album fanart:** (default False)<br />
If Kodi downloaded an album fanart image during scraping of the music, this image will be included in the slideshow..

**Disable secondary and featured artist images:** (default false)<br />
When set to false, Artist Slideshow will show images for all artists associated with the playing song.  When set to true, Artist Slideshow will show only images for the primary artist.

**Use fallback slideshow** (default false)<br />
Tells Kodi to use this folder of images if no artwork is found for the playing artist<br />
*Fallback slideshow folder:* (default none)<br />
path to a directory of images that should be used if no local or remote images can be found.

### Storage
**Store artist images in:** (default addon_data folder)<br />
three options: addon_data folder, custom location, Kodi artist information folder<br />
*addon_data folder* uses the default data storage location for Kodi addons. If you select this option you can also limit the size of the downloads to between 128mb and 4gb.<br />
*Custom location* use a location you define. If you select this option you can also specific a different name for the extrafanart folder or even opt not to use an extrafanart folder at all.<br />
*Kodi artist information folder* will use the artist information folder defined in the main Kodi settings. If you select this option and haven't set the artist information folder in Kodi, it will default back to the addon_data folder.

**Store artist information in:** (default addon_data folder)<br />
two options: addon_data folder, custom location<br />
*addon_data folder* uses the default data storage location for Kodi addons.<br />
*Custom location* use a location you define.<br />

### Images
**Download images from fanart.tv:** (default false)<br />
fanart.tv has very high quality (1080p) artwork.  To use this service, you must have the MusicBrainz Artist ID tag in your music files and have that scanned into your Kodi library.

*Client API key* (default empty)<br />
fanart.tv provides the option for individual users to have an API key. For information on the benefits that provides, please see <https://fanart.tv/2015/01/personal-api-keys/>

*Download all images regardless of resolution:* (default false)<br />
Downloads images even if they are not in 16x9 aspect ratio.

*I donate to this service:* (default false)<br />
Set this to true if you donate money to fanart.tv.  This will provide more frequent updates of images. Please don't be an ass and enable this without actually donating.  We've already lost one image source because of funding issues.  We don't need to lose any more.

**Download images from theaudiodb.com:** (default false)<br />
theaudiodb.com has no more than three images per artist, and they are often duplicates of artwork from fanart.tv.  To use this service, you must have the MusicBrainz Artist ID tag in your music files and have that scanned into your Kodi library.

*Download all images regardless of resolution:* (default false)<br />
Downloads images even if they are not in 16x9 aspect ratio.

*I donate to this service:* (default false)<br />
Set this to true if you donate money to fanart.tv.  This will provide more frequent updates of images. Please don't be an ass and enable this without actually donating.  We've already lost one image source because of funding issues.  We don't need to lose any more.

### Album Info
**Download album info from theaudiodb.com** (default false)<br />
Downloads the artist's discography from theaudiodb.com.  To use this service, you must have the MusicBrainz Artist ID tag in your music files and have that scanned into your Kodi library.

*Priority* (range 1 - 10, default 5)<br />
If multiple services are enabled, the service with priority 1 will be used first, and the one with priority 10 will be used last.<br />
**Download album info fromlast.fm** (default false)<br />
Downloads the artist's discography from last.fm.

*Priority* (range 1 - 10, default 5)<br />
If multiple services are enabled, the service with priority 1 will be used first, and the one with priority 10 will be used last.<br />

### Artist Bio
**Preferred language for artist bio:** (default: English)<br />
Sets the language Kodi uses when attempting to download a bio. If no bio for that language is returned, no bio is returned (even if available in other languages).

**Get artist bio from Kodi:** (default: true)<br />
If selected, AS will ask Kodi for the artist bio that was stored when the music library was last scraped.

*Priority* (range 1 - 10, default 5)<br />
If multiple services are enabled, the service with priority 1 will be used first, and the one with priority 10 will be used last.

**Get artist bio from theaudiodb.com** (default: false)<br />
If selected, AS will download the artist bio matching the selected language from theaudiodb.com.

*Priority* (range 1 - 10, default 5)<br />
If multiple services are enabled, the service with priority 1 will be used first, and the one with priority 10 will be used last.

**Get artist bio fromlast.fm** (default: false)<br />
If selected, AS will download the artist bio matching the selected language from last.fm.

*Priority* (range 1 - 10, default 5)<br />
If multiple services are enabled, the service with priority 1 will be used first, and the one with priority 10 will be used last.

### Similar Artists
**Download similar artists fromlast.fm** (default: false)<br />
If selected, AS will download a list of similar artists from last.fm.

*Priority* (range 1 - 10, default 5)<br />
If multiple services are enabled, the service with priority 1 will be used first, and the one with priority 10 will be used last.

### Advanced
AS replaces certain reserved characters in an artist names with an alternate character when looking for a local artist folder.<br />
**Platform for image store** can be Windows, MacOS, or Other.  When set to Windows, the characters <>:"/\|?*and trailing periods are replaced with whatever is set in the settings. When set to MacOS, the character : is replaced with whatever is set in the settings.  If set to other, any characters defined by os.path.sep are replaced with whatever is set in the settings.

*Replace illegal path characters in artist name with* (default _)<br />
This character replaces any illegal characters noted above.

*Replace trailing period in artist name with:* (default BLANK)<br />
This character replaces any trailing period as noted above.

**Slideshow thread sleep time:** (range 1 - 3 seconds, default 1 second)<br >
Artist Slideshow uses a separate thread to rotate the artwork, and on some systems the default sleep time of 1 second causes high CPU usage. You can increase this to decrease CPU usage, and the tradeoff is that the transition from one artist to another may be delayed somewhat.

**Main thread sleep time:** (range 1 - 3 seconds, default 1 second)<br >
Artist Slideshow checks every second by default to see if the song/artist has changed, and on some systems the default sleep time of 1 second causes high CPU usage. You can increase this to decrease CPU usage, and the tradeoff is that the transition from one artist to another may be delayed somewhat.

**Main thread idle sleep time:** (range 5 - 30 seconds, default 10 seconds)<br >
When the skin starts Artist Slideshow in daemon mode, it is always running.  When no music is playing, Artist Slideshow enters an idle mode and only checks every 10 seconds by default to see if music is playing to help reduce CPU load. You can change this to change CPU usage, and the tradeoff is that the longer you set the delay, the longer the slideshow will be delayed after the first song starts.

**Enable debug logging:** (default false)<br />
When enabled, if you have Kodi logging set to DEBUG you will get a very verbose set of information in your log file. You should only need to activate this when troubleshooting issues.

**Move images to Kodi music artist folder**<br />
This will run a script to rename all your artwork to the Kodi music artist folder standard (fanart1, fanart2, etc). It cannot be undone, so please backup your artist images before you do this.

## Overriding Artist Info with Local Information

### Directory Structure
To override the downloaded information, you need to create another directory in the folder you defined in the settings as the Local artist folder. Your folder structure will look something like this:
```xml
    <artistname>
        extrafanart
        override
            albums (folder with artist album art)
                albumname.jpg (any XBMC image type supported)
                anotheralbumname.jpg
            artistbio.nfo (see below for format)
            artistsalbum.nfo (see below for format)
            artistsimilar.nfo (see below for format)
            similar
                artistimage.jpg
                anotherartistimage.jpg
```

### Override nfo file formats
All .nfo files are xml files (pretty simple ones) patterned after the XML files downloaded from last.fm.

Example artistbio.nfo
```xml
   <?xml version="1.0" encoding="utf-8"?>
   <artist>
       <content>This is the artist's bio.</content>
   </artist>
```

Example artistsalbum.nfo
```xml
     <?xml version="1.0" encoding="utf-8"?>
     <topalbums>
         <album>
             <name>Some Album</name>
             <image>albumname.jpg</image>
         </album>
         <album>
             <name>Another Album</name>
             <image>anotheralbumname.jpg</image>
         </album>
     </topalbums>
```

Example artistsimilar.nfo
```xml
   <?xml version="1.0" encoding="utf-8"?>
   <similarartists>
       <artist>
           <name>Some Similar Artist</name>
           <image>artistimage.jpg</image>
       </artist>
       <artist>
           <name>Another Similar Artist</name>
           <image>anotherartistimage.jpg</image>
       </artist>
   </similarartists>
```

## Accessing Script from Other Screens
You might want to use Artist Slideshow to display images somewhere other than on the music visualization. To do that you need to start Artist Slideshow when Kodi starts using daemon mode. To do that use:
```xml
    RunScript(script.artistslideshow, daemon=True)
```

## New skin properties
*Window(Visualisation).Property(ArtistSlideshow.Image)*<br />
This is one of the randomly selected images of the currently playing artist

*Window(Visualisation).Property(ArtistSlideshowRunning)*</br >
This one is used internally by the script to check if it is already running. There's no need to use this property in your skin.

*Window(Visualisation).Property(ArtistSlideshow.ArtistBiography)*<br />
Artist biography from theaudiodb.com (or last.fm as fallback)

*Window(Visualisation).Property(ArtistSlideshow.%d.SimilarName)<br />
Window(Visualisation).Property(ArtistSlideshow.%d.SimilarThumb)*<br />
Similar artists (from last.fm)

*Window(Visualisation).Property(ArtistSlideshow.%d.AlbumName)<br />
Window(Visualisation).Property(ArtistSlideshow.%d.AlbumThumb)*<br />
Albums by the artist (from theaudiodb.com)

## How to call this addon from another addon
To use this addon to provide the background for another addon, the calling addon must create a window that uses a single image control. See the section on changes to MusicVisualisation.xml.

That window must have an infolabel in which the currently playing artist is stored (suggested name is CURRENTARTIST) as well as one for the song title (suggested name is CURRENTTILE). It is the responsibility of the calling addon to change those infolabels when the artist/song changes.

### Calling the addon
Artist Slideshow does not exit after being called. It continues to run to check for changes in the artist infolabel. Becasue of that, the calling addon will have to create another thread for Artist Slideshow. The calling addon needs to import the python theading module for this to work. 

```python
     def runArtistSlideshow(self):
         #startup artistslideshow
         xbmcgui.Window(xbmcgui.getCurrentWindowId()).setProperty("ArtistSlideshow.ExternalCall", "True")
         #assumes addon is using suggested infolabel name of CURRENTARTIST and CURRENTTITLE
         artistslideshow = "RunScript(script.artistslideshow,windowid=%s&artistfield=%s&titlefield=%s&albumfield=%s&mbidfield=%s)"
                            % (xbmcgui.getCurrentWindowId(), "CURRENTARTIST", "CURRENTTITLE", "CURRENTALBUM", "CURRENTMBID")
         xbmc.executebuiltin(artistslideshow)
 
    self.thread = threading.Thread(target=self.runArtistSlideshow)
    self.thread.setDaemon(True)
    self.thread.start()
```

When calling Artist Slideshow, only artistfield and titlefield (and their corresponding information stored in the skin) are required. It would be helpful to have albumfield, as it makes it easier to lookup the Musicbrainz ID. If you happen to have the MusicBrainz ID, you can pass that as well.  The suggestion is for the addon to spawn this thread right after it spawns the window.

### Exiting the addon
When the calling addon is preparing to exit, it must tell Artist Slideshow to stop and wait until it has. This logic should be added *before* the addon's window is destroyed. Failure to include this step will likely cause XBMC to crash.

```python
    #tell ArtistSlideshow to exit
    xbmcgui.Window(xbmcgui.getCurrentWindowId()).clearProperty("ArtistSlideshow.ExternalCall")
    #wait until ArtistSlideshow exits
    while (not xbmcgui.Window(xbmcgui.getCurrentWindowId()).getProperty("ArtistSlideshow.CleanupComplete") == "True"):
        xbmc.sleep(1)
```

### Additional script/skin properties available
*Window.Property(ArtistSlideshow.Image)*<br />
This is one of the randomly selected images for the currently playing artist.

*Window.Property(ArtistSlideshow.ArtistBiography)*<br />
Artist biography from theaudiodb.com (or last.fm as fallback)

*Window.Property(ArtistSlideshow.%d.SimilarName)<br />
Window.Property(ArtistSlideshow.%d.SimilarThumb)*<br />
Similar artists from last.fm

*Window.Property(ArtistSlideshow.%d.AlbumName)<br />
Window.Property(ArtistSlideshow.%d.AlbumThumb)*<br />
Albums by the artist from theaudiodb.com

*Window.Property(ArtistSlideshowRunning)*<br />
This one is used internally by Artist Slideshow to check if it is already running. There's no need to use this property in the calling addon's skin.

*Window.Property(ArtistSlideshow.ExternalCall)*<br />
An external addon needs to set this to True so that Artist Slideshow will run properly when called by an external script. This property should be cleared to tell ArtistSlideshow to stop running.
 
*Window.Property(ArtistSlideshow.CleanupComplete)*<br />
This one is used internally by Artist Slideshow to tell an external script that ArtistSlideshow is done running and is exiting.

## Tips and Tricks

### Using Artist Slideshow with Fanart.tv
In order to download images from fanart.tv, AS must have the MusicBrainz ID for the playing artist.  The easiest way to get that information is to tag your music using MusicBrainz Picard.  Once you have done that rescan your music library to import the new information into Kodi.

### Removing Unwanted Images
An image will only be downloaded once by Artist Slideshow, so if you don't want an image, just delete it.

### Using Artist Slideshow with a Visualization
If you want to see artist images and a visualization, make sure the skin is loading the Artist Slideshow images first (i.e at the top of the XML file). That will ensure the artist image is the furtherest back layer. If you choose to use a visualization, please select one with a significant amount of transparent area or you may not see much of anything. Please contact the skin developer for a clarification on how visualizations interact with Artist Slideshow.

### Using Artist Slideshow with AppleTV
On AppleTV the PAPlayer sometimes stops after each song and restarts at the beginning of a new one. That, by default, causes Artist Slideshow to stop. Once that happens, artist background images no longer update. Please see the changes to MusicVisualisation.xml above for a workaround.

## Getting help
If you need assistance using Artist Slideshow, integrating it a skin, or calling it using another addon, please see the support thread on the Kodi forums at <https://forum.kodi.tv/showthread.php?tid=124880>

## Beta Testing
If you are interested in beta testing new versions of this add on (or just like being on the bleeding edge of up to date), you can install beta versions (Leia or later, there will be no more updates for earlier versions) from my addon beta repository - either [for Leia](https://github.com/pkscout/repository.beta.pkscout/raw/helix/repository.beta.pkscout-1.1.1.zip) or [for Matrix](https://github.com/pkscout/repository.beta.pkscout/raw/matrix/repository.beta.pkscout-1.1.2.zip) (these are zip downloads). You can also monitor the support thread, as links to particular beta releases will be available there as well.
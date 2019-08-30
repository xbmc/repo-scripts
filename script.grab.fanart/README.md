# Grab Fanart
__Kodi Version Compatibility:__ Kodi 18.x (Leia) and above

## About: 

This script uses the Kodi Database, via the JSON-RPC server, to find information regarding video and music files and exposes them via Window Properties so that skinners can still cycle through the art by referencing a single point of reference. 

__Fun Fact:__ This addon was originally intended as a fix for for Kodi (XBMC) Frodo behavior that was breaking some skins I liked to use. In those days all FanArt was kept in a single directory without the need for caching or texture databases!


## Using This Addon: 

This addon is meant to be integrated as part of a skin. Currently it can be configured by calling the RunScript() function within a script. The parameters that can be set are: 

* Refresh Time: How long between property updates. Default is 10 seconds
* Mode: Show fanart for recent items (10), or for random items

An example of setting these parameters using the RunScript function would be:
```
RunScript(script.grab.fanart,mode=random,refresh=10). 
```
If you want to include these settings are part of the regular skin settings you can pass these as parameters to RunScript upon hitting the home screen or in the Startup.xml file. 

### Window Properties: 

Currently the service part of this addon will update Home window properties that can be used by skinners. The properties are refreshed according to the "refresh" interval. 

|  Property | Description |
|--|-------|
| script.grab.fanart.Ready | this property is empty until the service has initialized the array of fanart files. It then holds a value of "true". Useful if you skinners want to delay something until the service has started cycling images. |
| __Global Properties__ | |
| script.grab.fanart.Global.Title | the title of a random music or video file, 30% chance music, 30% TV, 40% movie |
| script.grab.fanart.Global.FanArt | path to the fanart image for this media |
| script.grab.fanart.Global.Logo | path to logo for this media - blank if it doesn't exist |
| __Video Properties__ | | 
| script.grab.fanart.Video.Title | the title of a random video (movie or tv show). There is a 10% chance of this being a TV show. |
| script.grab.fanart.Video.FanArt | the path to the fanart image for this video |
| script.grab.fanart.Video.Poster | path to poster image for this video |
| script.grab.fanart.Video.Logo | path to clear logo for this video - blank if it doesn't exist |
| script.grab.fanart.Video.Plot | plot outline of this video |
| script.grab.fanart.Video.Path | path to the video file |
| __Movie Properties__ | | 
| script.grab.fanart.Movie.Title | title of the selected movie |
| script.grab.fanart.Movie.FanArt | path to movie fanart |
| script.grab.fanart.Movie.Poster | path to movie poster |
| script.grab.fanart.Movie.Logo | path to clear logo for movie - blank if it doesn't exist |
| script.grab.fanart.Movie.Plot | movie plot |
| script.grab.fanart.Movie.Path | path to the movie file |
| __TV Properties__ | | 
| script.grab.fanart.TV.Title | title of selected tv show |
| script.grab.fanart.TV.FanArt | path to tv show fanart |
| script.grab.fanart.TV.Poster | path to tv show poster |
| script.grab.fanart.TV.Logo | path to clear logo for tv show - blank if it doesn't exist |
| script.grab.fanart.TV.Plot | tv show plot description |
|script.grab.fanart.TV.Path  | path to the tv show show (will be the root folder if in "random" mode or the specific episode if in "recent" mode)|
| | _The properties below will only have values when the addon mode is "recent"_ |
| script.grab.fanart.TV.Season | selected tv show season |
| script.grab.fanart.TV.Episode | selected tv show episode number |
| script.grab.fanart.TV.Thumb | path to thumbnail image of this episode |
| __Music Properties__ | | 
|script.grab.fanart.Music.Artist | music artist name |
| script.grab.fanart.Music.FanArt | path to artist fanart |
| script.grab.fanart.Music.Description | artist description |

### Using In A Skin

To use the ```script.grab.fanart.Ready``` property you could use something like this: 

```
!IsEmpty(Window(Home).Property(script.grab.fanart.Ready))
```

To access any of the other properties to load images or display text you can reference the property within your skin files using: 
```
$INFO[Window(Home).Property(script.grab.fanart.Video.Title)]
```
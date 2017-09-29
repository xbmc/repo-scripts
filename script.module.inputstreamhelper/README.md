# script.module.inputstreamhelper #

A simple Kodi module that makes life easier for add-on developers relying on InputStream based add-ons and DRM playback.

## Features ##
* Displays informative dialogs if required InputStream components are unavailable
* Checks if HLS is supported in inputstream.adaptive
* Automatically installs Widevine DRM on supported platforms (optional)

## Example ##

```python
import xbmc
import xbmcgui
import inputstreamhelper

def play_item():
    inputstream_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    stream_url = 'http://yt-dash-mse-test.commondatastorage.googleapis.com/media/car-20120827-manifest.mpd'
    if inputstream_helper.check_inputstream():
        playitem = xbmcgui.ListItem(path=stream_url)
        playitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
        playitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        xbmc.Player().play(item=stream_url, listitem=playitem)

play_item()
```

The Helper class takes two arguments: protocol (the media streaming protocol) and the optional argument 'drm'.

## Accepted protocol arguments: ##
 * mpd
 * ism
 * hls
 * rtmp

## Accepted drm arguments: ##
 * widevine
 * com.widevine.alpha

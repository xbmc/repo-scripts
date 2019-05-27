# script.module.inputstreamhelper #
A simple Kodi module that makes life easier for add-on developers relying on InputStream based add-ons and DRM playback.

## Features ##
* Displays informative dialogs if required InputStream components are unavailable
* Checks if HLS is supported in inputstream.adaptive
* Automatically installs Widevine CDM on supported platforms (optional)
  * Keeps Widevine CDM up-to-date with the latest version available (Kodi 18 and higher)
  * Checks for missing depending libraries by parsing the output from  `ldd` (Linux)

## Example ##

```python
import xbmc
import xbmcgui
import inputstreamhelper

PROTOCOL = 'mpd'
DRM = 'com.widevine.alpha'
STREAM_URL = 'https://demo.unified-streaming.com/video/tears-of-steel/tears-of-steel-dash-widevine.ism/.mpd'
LICENSE_URL = 'https://cwip-shaka-proxy.appspot.com/no_auth'


def play():
    is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
    if is_helper.check_inputstream():
        playitem = xbmcgui.ListItem(path=STREAM_URL)
        playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        playitem.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
        playitem.setProperty('inputstream.adaptive.license_type', DRM)
        playitem.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '||R{SSM}|')
        xbmc.Player().play(item=STREAM_URL, listitem=playitem)

if __name__ == '__main__':
    play()
```

The Helper class takes two arguments: protocol (the media streaming protocol) and the optional argument 'drm'.

It is recommended to not add your InputStream add-on as a dependency in addon.xml. It can cause confusion with users not being able to install your add-on because the InputStream add-on is disabled. InputStream Helper addresses issues such as these and helps the user to install/enable required InputStream components.

## Accepted protocol arguments: ##
 * mpd
 * ism
 * hls
 * rtmp

## Accepted drm arguments: ##
 * widevine
 * com.widevine.alpha

## Support ##
Please report any issues or bug reports on the [GitHub Issues](https://github.com/emilsvennesson/script.module.inputstreamhelper/issues) page.

## License ##
This module is licensed under the **The MIT License**. Please see the [LICENSE.txt](LICENSE.txt) file for details.

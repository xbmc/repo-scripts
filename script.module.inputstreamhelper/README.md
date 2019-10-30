[![GitHub release](https://img.shields.io/github/release/emilsvennesson/script.module.inputstreamhelper.svg)](https://github.com/emilsvennesson/script.module.inputstreamhelper/releases)
[![Build Status](https://travis-ci.org/emilsvennesson/script.module.inputstreamhelper.svg?branch=master)](https://travis-ci.org/emilsvennesson/script.module.inputstreamhelper)
[![Codecov status](https://img.shields.io/codecov/c/github/emilsvennesson/script.module.inputstreamhelper/master)](https://codecov.io/gh/emilsvennesson/script.module.inputstreamhelper/branch/master)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Contributors](https://img.shields.io/github/contributors/emilsvennesson/script.module.inputstreamhelper.svg)](https://github.com/emilsvennesson/script.module.inputstreamhelper/graphs/contributors)

# InputStream Helper #
**script.module.inputstreamhelper** is a simple Kodi module that makes life easier for add-on developers relying on InputStream based add-ons and DRM playback.

## Features ##
- Displays informative dialogs if required InputStream components are unavailable
- Checks if HLS is supported in inputstream.adaptive
- Automatically installs Widevine CDM on supported platforms (optional)
  - Keeps Widevine CDM up-to-date with the latest version available (Kodi 18 and higher)
  - Checks for missing depending libraries by parsing the output from  `ldd` (Linux)

## Example ##

```python
import sys
import xbmcgui
import xbmcplugin
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
        xbmcplugin.setResolvedUrl(handle=sys.argv[1], succeeded=True, listitem=play_item)

if __name__ == '__main__':
    play()
```

The Helper class takes two arguments: protocol (the media streaming protocol) and the optional argument 'drm'.

It is recommended to not add your InputStream add-on as a dependency in addon.xml. It can cause confusion with users not being able to install your add-on because the InputStream add-on is disabled. InputStream Helper addresses issues such as these and helps the user to install/enable required InputStream components.

## Accepted protocol arguments: ##
 * **mpd** -- *MPEG-DASH*
 * **ism** -- *Microsoft Smooth Streaming*
 * **hls** -- *HTTP Live Streaming from Apple*
 * **rtmp** -- *Real-Time Messaging Protocol*

## Accepted drm arguments: ##
 * widevine
 * com.widevine.alpha

## Support ##
Please report any issues or bug reports on the [GitHub Issues](https://github.com/emilsvennesson/script.module.inputstreamhelper/issues) page.

## License ##
This module is licensed under the **The MIT License**. Please see the [LICENSE.txt](LICENSE.txt) file for details.

## Releases
## v0.4.3 (2019-09-25)
- French translation (@brunoduc)
- Updated translations (@vlmaksime, @dagwieers, @pinoelefante, @horstle, @Twilight0, @emilsvennesson)
- Ensure Kodi 19 compatibility (@mediaminister)
- Configurable temporary download directory for devices with limited space (@horstle)
- Configurable Widevine CDM update frequency (@horstle)
- Fix add-on settings crashes when InputStream Adaptive is missing (@mediaminister)
- Improve unicode character support (@mediaminister)

## v0.4.2 (2019-09-03)
- Move release history to readme file (@mediaminister)
- Clean up coverage/codecov config (@dagwieers)
- Add InputStream Helper Information to settings page (@horstle, @dagwieers)
- Make sure addon.xml meets all requirements (@mediaminister)
- Simplify add-on entry point to speed up loading time (@mediaminister)
- Unicode fix for os.walk (@mediaminister)
- Revert "Fix ARM processing in unittest locally" (@mediaminister)
- Fix unresponsive Kodi when opening add-on information pane (@dagwieers, @mediaminister)
- Add-on structure improvements (@dagwieers)

## v0.4.1 (2019-09-01)
- Follow kodi-addon-checker recommended code changes (@mediaminister)
- Implement api using runscript (@mediaminister)
- Fix ARM processing in unittest locally (@dagwieers)
- Add more project information (@dagwieers)
- More coverage improvements (@dagwieers)

## v0.4.0 (2019-09-01)
- Use local url variable (@mediaminister)
- Directly use Kodi CDM directory (@mediaminister)
- Implement settings menu and API (@dagwieers)
- Add integration tests (@dagwieers)
- Add a progress dialog for extraction on ARM (@dagwieers)
- Fix crash when using platform.system() (@dagwieers)
- Fix a python error (@mediaminister)
- Remove legacy Widevine CDM support (@dagwieers)
- Replace requests/urllib3 with urllib/urllib2 (@dagwieers)
- Various unicode fixes (@mediaminister)
- Add proxy support (@dagwieers)
- Add setting to disable inputstreamhelper (@horstle, @JohnPlayerSpecial2018)
- Check Widevine support before all checks (@vlmaksime)
- Support 64-bit kernel with 32-bit userspace (@mrfixit2001)
- Dutch translation (@mediaminister, @basrieter)
- German translation (@flubshi)
- Greek translation (@Twilight0)
- Italian translation (@pinoelefante)
- Russian translation (@vlmaksime)
- Swedish translation (@emilsvennesson)

## v0.3.5 (2019-08-15)
- Auto install inputstream.adaptive (@mediaminister)
- Fix latest Widevine version detection (@dagwieers)
- Check for Widevine updates on new release (@mediaminister)

## v0.3.4 (2019-03-23)
- python2_3 compability (@mediaminister, @Rechi)
- Option to disable inputstreamhelper in settings.xml
- calculate disk space on the tmp folder (@dawez)
- Support for Unicode paths in Windows (@WallyCZ)
- Italian translation (@pinoelefante)
- Dutch translation (@dnicolaas)
- Greek translation (@Twilight0)
- Russian translation (@vlmaksime)

## v0.3.3 (2018-02-21)
- Load loop if it's a kernel module (@mkreisl)
- Fix legacy Widevine CDM update detection
- inputstream_addon is now a public variable
- Notify user that ARM64 needs 32-bit userspace
- Improve logging
- Cosmetics

## v0.3.2 (2018-01-30)
- Fix OSMC arm architecture detection
- Fix ldd permissions error

## v0.3.1 (2018-01-29)
- check_inputstream() return fix

## v0.3.0 (2018-01-29)
- Bug fix: module left xbmcaddon class in memory
- Keep Widevine CDM up-to-date with the latest version available (Kodi 18 and higher)
- Check for missing depending libraries by parsing the output from ldd
- Use older Widevine binaries on Kodi Krypton (fixes nss/nspr dependency issues)

## v0.2.4 (2018.01.01)
- Fix ARM download on systems with sudo (OSMC etc)
- Actually bump version in addon.xml, unlike v0.2.3...

## v0.2.3 (2017-12-30)
- Make sure Kodi and Widevine CDM binary architecture matches
- Minor wording changes/fixes

## v0.2.2 (2017-12-05)
- Fixes for widevine download when using 64-bit Kodi (@gismo112, @asciidisco)

## v0.2.1 (2017-10-15)
- Update German translation (@asciidisco)
- Improve root permissions acquisition

## v0.2.0 (2017-09-29)
- Automatic Widevine CDM download on ARM devices
- Display Widevine EULA during installation procedure
- German translation (thanks to asciidisco)
- New, smaller and less ugly generic icon
- Better exception handling
- Code cleanup

## v0.1.0 (2017-09-13)
- Initial release

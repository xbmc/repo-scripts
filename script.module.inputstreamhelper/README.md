[![GitHub release](https://img.shields.io/github/release/emilsvennesson/script.module.inputstreamhelper.svg)](https://github.com/emilsvennesson/script.module.inputstreamhelper/releases)
[![CI](https://github.com/emilsvennesson/script.module.inputstreamhelper/workflows/CI/badge.svg)](https://github.com/emilsvennesson/script.module.inputstreamhelper/actions?query=workflow:CI)
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
# -*- coding: utf-8 -*-
"""InputStream Helper Demo"""
from __future__ import absolute_import, division, unicode_literals
import sys
import inputstreamhelper
import xbmc
import xbmcgui
import xbmcplugin


PROTOCOL = 'mpd'
DRM = 'com.widevine.alpha'
STREAM_URL = 'https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel-dash-widevine.ism/.mpd'
MIME_TYPE = 'application/dash+xml'
LICENSE_URL = 'https://widevine-proxy.appspot.com/proxy'
KODI_VERSION_MAJOR = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])


def run(addon_url):
    """Run InputStream Helper Demo"""

    # Play video
    if addon_url.endswith('/play'):
        is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=STREAM_URL)
            play_item.setContentLookup(False)
            play_item.setMimeType(MIME_TYPE)

            if KODI_VERSION_MAJOR >= 19:
                play_item.setProperty('inputstream', is_helper.inputstream_addon)
            else:
                play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)

            play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
            play_item.setProperty('inputstream.adaptive.license_type', DRM)
            play_item.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '||R{SSM}|')
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, play_item)

    # Setup menu item
    else:
        xbmcplugin.setContent(int(sys.argv[1]), 'videos')
        list_item = xbmcgui.ListItem(label='InputStream Helper Demo')
        list_item.setInfo('video', {})
        list_item.setProperty('IsPlayable', 'true')
        url = addon_url + '/play'
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, list_item)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

if __name__ == '__main__':
    run(sys.argv[0])
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
### v0.7.0 (2024-09-24)
- Get rid of distutils dependency (@horstle, @emilsvennesson)
- Option to get Widevine from lacros image (@horstle)
- Remove support for Python 2 and pre-Matrix Kodi versions (@horstle)

### v0.6.1 (2023-05-30)
- Performance improvements on Linux ARM (@horstle)
- This will be the last release for Python 2 i.e. Kodi 18 (Leia) and below. The next release will require Python 3 and Kodi 19 (Matrix) or higher.

### v0.6.0 (2023-05-03)
- Initial support for AARCH64 Linux (@horstle)
- Initial support for AARCH64 Macs (@mediaminister)
- New option to install a specific version on most platforms (@horstle)

### v0.5.10 (2022-04-18)
- Fix automatic submission of release (@mediaminister)
- Update German translation (@tweimer)
- Fix update_frequency setting (@horstle)
- Fix install_from (@horstle)
- Improve/Fix Widevine extraction from Chrome OS images (@horstle)

### v0.5.9 (2022-03-22)
- Update Croatian translation (@dsardelic, @muzena)
- Replace deprecated LooseVersion (@mediaminister, @MarkusVolk)
- Fix http_get decode error (@archtur)
- Option to install Widevine from specified source (@horstle)

### v0.5.8 (2021-09-09)
- Simplify Widevine CDM installation on ARM hardware (@horstle, @mediaminister)
- Update Chrome OS ARM hardware id's (@mediaminister)
- Update Japanese and Korean translations (@Thunderbird2086)

### v0.5.7 (2021-07-02)
- Further improve Widevine CDM installation on ARM hardware (@horstle)

### v0.5.6 (2021-06-24)
- Improve Widevine CDM installation on ARM hardware (@mediaminister)
- Postpone Widevine CDM updates when user rejects (@horstle)

### v0.5.5 (2021-06-02)
- Improve Widevine CDM installation on ARM hardware (@mediaminister)

### v0.5.4 (2021-05-27)
- Fix Widevine CDM installation on ARM hardware (@mediaminister)

### v0.5.3 (2021-05-10)
- Temporary fix for Widevine CDM installation on ARM hardware (@mediaminister)
- Fix Widevine CDM installation on 32-bit Linux (@mediaminister)

### v0.5.2 (2020-12-13)
- Update Chrome OS ARM hardware id's (@mediaminister)

### v0.5.1 (2020-10-02)
- Fix incorrect ARM HWIDs: PHASER and PHASER360 (@dagwieers)
- Added Hebrew translations (@haggaie)
- Updated Dutch, Japanese and Korean translations (@michaelarnauts, @Thunderbird2086)

### v0.5.0 (2020-06-25)
- Extract Widevine CDM directly from Chrome OS, minimizing disk space usage and eliminating the need for root access (@horstle)
- Improve progress dialog while extracting Widevine CDM on ARM devices (@horstle, @mediaminister)
- Support resuming interrupted downloads on unreliable internet connections (@horstle, @mediaminister)
- Reshape InputStream Helper information dialog (@horstle, @dagwieers)
- Updated Dutch, English, French, German, Greek, Hungarian, Romanian, Russian, Spanish and Swedish translations (@dagwieers, @horstle, @mediaminister, @tweimer, @Twilight0, @frodo19, @tmihai20, @vlmaksime, @roliverosc, @Sopor)

### v0.4.7 (2020-05-03)
- Fix hardlink on Windows (@BarmonHammer)
- Fix support for unicode chars in paths (@mediaminister)
- Show remaining time during Widevine installation on ARM devices (@horstle)

### v0.4.6 (2020-04-29)
- Compatibility fixes for Kodi 19 Matrix "pre-release" builds (@mediaminister)
- Optimize Widevine CDM detection (@dagwieers)
- Minor fixes for Widevine installation on ARM devices (@dagwieers @mediaminister @horstle)

### v0.4.5 (2020-04-07)
- Added Spanish and Romanian translations (@roliverosc, @tmihai20)
- Added support for Kodi 19 Matrix "pre-release" builds (@mediaminister)
- Fix Widevine backups when using an external drive (@horstle)
- Various fixes for Widevine installation on ARM devices (@horstle)

### v0.4.4 (2020-03-01)
- Added option to restore a previously installed Widevine version (@horstle)
- Improve progress bar when extracting Widevine on ARM devices (@dagwieers)
- Improve Widevine library version detection (@dagwieers, @mediaminister)
- Improve InputStream Helper information (@dagwieers, @mediaminister)
- Increase download reliability for Chrome OS on ARM devices (@horstle, @RolfWojtech)
- Added Japanese, Korean, Croatian and Hungarian translations (@Thunderbird2086, @arvvoid, @frodo19)
- Updated existing translations (@dnicolaas, @Sopor, @tweimer, @horstle, @mediaminister)
- Various small bugfixes for Widevine installation on ARM devices (@dagwieers, @mediaminister, @Twilight0, @janhicken)

### v0.4.3 (2019-09-25)
- French translation (@brunoduc)
- Updated translations (@vlmaksime, @dagwieers, @pinoelefante, @horstle, @Twilight0, @emilsvennesson)
- Ensure Kodi 19 compatibility (@mediaminister)
- Configurable temporary download directory for devices with limited space (@horstle)
- Configurable Widevine CDM update frequency (@horstle)
- Fix add-on settings crashes when InputStream Adaptive is missing (@mediaminister)
- Improve unicode character support (@mediaminister)

### v0.4.2 (2019-09-03)
- Move release history to readme file (@mediaminister)
- Clean up coverage/codecov config (@dagwieers)
- Add InputStream Helper Information to settings page (@horstle, @dagwieers)
- Make sure addon.xml meets all requirements (@mediaminister)
- Simplify add-on entry point to speed up loading time (@mediaminister)
- Unicode fix for os.walk (@mediaminister)
- Revert "Fix ARM processing in unittest locally" (@mediaminister)
- Fix unresponsive Kodi when opening add-on information pane (@dagwieers, @mediaminister)
- Add-on structure improvements (@dagwieers)

### v0.4.1 (2019-09-01)
- Follow kodi-addon-checker recommended code changes (@mediaminister)
- Implement api using runscript (@mediaminister)
- Fix ARM processing in unittest locally (@dagwieers)
- Add more project information (@dagwieers)
- More coverage improvements (@dagwieers)

### v0.4.0 (2019-09-01)
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

### v0.3.5 (2019-08-15)
- Auto install inputstream.adaptive (@mediaminister)
- Fix latest Widevine version detection (@dagwieers)
- Check for Widevine updates on new release (@mediaminister)

### v0.3.4 (2019-03-23)
- python2_3 compability (@mediaminister, @Rechi)
- Option to disable inputstreamhelper in settings.xml
- calculate disk space on the tmp folder (@dawez)
- Support for Unicode paths in Windows (@WallyCZ)
- Italian translation (@pinoelefante)
- Dutch translation (@dnicolaas)
- Greek translation (@Twilight0)
- Russian translation (@vlmaksime)

### v0.3.3 (2018-02-21)
- Load loop if it's a kernel module (@mkreisl)
- Fix legacy Widevine CDM update detection
- inputstream_addon is now a public variable
- Notify user that ARM64 needs 32-bit userspace
- Improve logging
- Cosmetics

### v0.3.2 (2018-01-30)
- Fix OSMC arm architecture detection
- Fix ldd permissions error

### v0.3.1 (2018-01-29)
- check_inputstream() return fix

### v0.3.0 (2018-01-29)
- Bug fix: module left xbmcaddon class in memory
- Keep Widevine CDM up-to-date with the latest version available (Kodi 18 and higher)
- Check for missing depending libraries by parsing the output from ldd
- Use older Widevine binaries on Kodi Krypton (fixes nss/nspr dependency issues)

### v0.2.4 (2018.01.01)
- Fix ARM download on systems with sudo (OSMC etc)
- Actually bump version in addon.xml, unlike v0.2.3...

### v0.2.3 (2017-12-30)
- Make sure Kodi and Widevine CDM binary architecture matches
- Minor wording changes/fixes

### v0.2.2 (2017-12-05)
- Fixes for widevine download when using 64-bit Kodi (@gismo112, @asciidisco)

### v0.2.1 (2017-10-15)
- Update German translation (@asciidisco)
- Improve root permissions acquisition

### v0.2.0 (2017-09-29)
- Automatic Widevine CDM download on ARM devices
- Display Widevine EULA during installation procedure
- German translation (thanks to asciidisco)
- New, smaller and less ugly generic icon
- Better exception handling
- Code cleanup

### v0.1.0 (2017-09-13)
- Initial release

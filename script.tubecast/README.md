# TubeCast

![Kodi Addon-Check (Krypton)](https://github.com/enen92/script.tubecast/workflows/Kodi%20Addon-Check%20(Krypton)/badge.svg)
![Kodi Addon-Check (Matrix)](https://github.com/enen92/script.tubecast/workflows/Kodi%20Addon-Check%20(Matrix)/badge.svg)
![Python tests](https://github.com/enen92/script.tubecast/workflows/Python%20tests/badge.svg)
![License](http://img.shields.io/:license-mit-blue.svg?style=flat)

![fanart](https://github.com/enen92/script.tubecast/blob/matrix/resources/img/fanart.jpg?raw=true)

### What is TubeCast?

TubeCast is a Kodi addon that implements the Cast V1 protocol and enables the Youtube mobile application (Android and iOS) to control the video playback of Kodi's YouTube addon as well as the device volume. It is deeply inspired by [Leapcast](https://github.com/dz0ny/leapcast) and [GoTubecast](https://github.com/CBiX/gotubecast). You can play, stop, pause and queue videos from your phone and fully control the playback from your phone (as in Chromecast).

### What it is not

TubeCast is not a full Chromecast implementation **nor will it ever be**. It only supports the first revision of the Cast protocol and will only keep working while Google keeps backwards compatibility with the Cast V1 protocol in their youtube mobile applications (at least for service discovery).

### Features

* *Device discovery* - Cast V1 protocol relies on the DIAL Protocol over SSDP so the addon answers multicast queries as if it was a real chromecast. It responds to the following search queries: `urn:dial-multiscreen-org:service:dial:1`, `urn:dial-multiscreen-org:device:dial:1`, `ssdp:all`. Kodi should show up in your Youtube application as a valid cast target if your phone and Kodi are in the same network.

* *Manual pairing* - You can disable service discovery in the addon settings and rely on manual paring. This will work even if the two devices are not in the same network. To do this generate a new pairing code by starting the addon and enter the provided code in your Youtube application (via Settings -> Watch on TV under your profile).

### Installation

The addon is available from the Official Kodi repository.

### Errors and issues

Support will only be provided via the forum thread in [Kodi's Forums](https://forum.kodi.tv/showthread.php?tid=329153) or here on Github. If you obtained this addon from third party communities ask them for help.

### Known issues

See [Issues](https://github.com/enen92/script.tubecast/issues)

### Translations

You can help translating this addon at [Kodi's weblate](https://kodi.weblate.cloud/projects/kodi-add-ons-scripts/script-tubecast/)

### Notes

- Tubecast uses the `System.FriendlyName` infolabel to get the name to be advertised to the youtube application. In some systems this value is not available and the value defined for the setting `Kodi advertisement name (fallback)` will be used instead

### License

The addon borrows a part of the code (SSDP) from Leapcast, hence it is licensed as MIT.

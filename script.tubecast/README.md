# TubeCast

![Buildstatus](https://travis-ci.org/enen92/script.tubecast.svg?branch=master)
![License](http://img.shields.io/:license-mit-blue.svg?style=flat)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/767abb2a497c4f608c36e3db0ec6e39e)](https://www.codacy.com/app/92enen/script.tubecast?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=enen92/script.tubecast&amp;utm_campaign=Badge_Grade)

![fanart](https://github.com/enen92/script.tubecast/blob/master/resources/img/fanart.jpg?raw=true)

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

* If you have a video queue set and attempt to stop playback from Kodi the next video on the queue will be played. Make sure you clear the playlist from the youtube application itself

* Kodi will hang if closed while having a established connection. Unpair the device first.


### Disclaimer

*This is not a full chromecast implementation nor will never be. Please refrain from suggesting it as a feature request.*

### License

The addon borrows a part of the code (SSDP) from Leapcast, hence it is licensed as MIT.

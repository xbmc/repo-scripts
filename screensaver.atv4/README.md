# screensaver.atv4

## Apple Aerial screensavers for Kodi 19 (Matrix)

This addon adds the Apple Aerial screensavers to Kodi Entertainment Center. It can be installed via the Kodi official repository.

## Plugin Features

- JSON-based video playlist fetching and playback
  - Custom JSON by default to include all scenes Apple ever published
  - Configurable to download the latest Apple JSON on each run
- Display Power Management Signaling (DPMS) configurable
  - When the display is supposed to go to sleep, pause/stop the Aerials video and turn the display off or put it into standby via HDMI CEC
- Choose from playback of:
  - HEVC H.265 or AVC H.264 codec (H.264 default)
  - 4K or 1080p resolution (1080p default)
  - High Dynamic Range (HDR) Dolby Vision or Standard Dynamic Range (SDR default)
- Filtering of videos by location/scene
- Offline caching of selected video quality
  - Download location by location or all at once
  - Full offline mode to prevent all network calls, using only local videos and JSON
  - Checksum validation to prevent unnecessary re-downloading of cached videos
- Custom JSON file count and gigabytes per quality level:
  - H.264 1080P SDR: 122 files, 39.4GB
  - H.265 1080P SDR: 116 files, 24.5GB
  - H.265 1080P HDR: 116 files, 37.8GB
  - H.265 4K SDR: 116 files, 48.9GB
  - H.265 4K HDR: 116 files, 75.3GB

## Aerials History
- When the Apple TV first came out with Aerials screensavers, Apple published a [V1 JSON manifest](http://a1.phobos.apple.com/us/r1000/000/Features/atv/AutumnResources/videos/entries.json) with all the different videos. Locations featured San Francisco, New York, China, Hong Kong, Greenland, Dubai, Los Angeles, and others. They were published in 1080p H.264 format
  - This JSON also included a `timeOfDay` key indicating if the video was shot during the day or night 
  - Later on, Apple changed the URL to a [V2 JSON manifest](http://a1.v2.phobos.apple.com.edgesuite.net/us/r1000/000/Features/atv/AutumnResources/videos/entries.json). As of March 2021, V1 and V2 contents are identical
- Later on in October 2018, Apple published a large refresh of Aerials in 4K resolution with HDR color space and in a more modern H.265 "HEVC" codec. 
  - While this included re-colored, extended versions of some of the original set of videos, it also retired others.
- Through the rest of 2018 and up until the beginning of 2020, Apple continued to release new 4K HDR Aerials scenes. 20+ underwater vistas, new scenes from existing locations, and globe-spanning shots from the International Space Station are all now included.
- At some point, Apple started vending the JSON manifest at a [new URL](https://sylvan.apple.com/Aerials/resources.tar) and bundled into a tarball `resources.tar`. (Thanks to the [other](https://github.com/JohnCoates/Aerial/issues/463#issuecomment-423128752) big Aerials project for this)
  - As part of this update, Apple removed the `timeOfDay` key so this plugin's filtering based on time of day is no longer possible without manually adding JSON keys for each scene
  - The new JSON contained new URLs for the original videos, possibly behind a Content Delivery Network (CDN). For example, a Greenland video's URL changed from http://a1.phobos.apple.com/us/r1000/000/Features/atv/AutumnResources/videos/comp_GL_G004_C010_v03_6Mbps.mov to http://a1.v2.phobos.apple.com.edgesuite.net/us/r1000/000/Features/atv/AutumnResources/videos/comp_GL_G004_C010_v03_6Mbps.mov (adding `.v2` and `.edgesuite.net`)
- [Benjamin Mayo](https://github.com/benjaminmayo) published a [Google Doc](https://docs.google.com/spreadsheets/d/1bboTohF06r-fafrImTExAPqM9m6h2m2lgJyAkQuYVJI/edit?usp=sharing) with a historical record of all the Aerials videos and links to all their different variants (H264, HDR, 4K, etc.) and also hosts a [website](https://bzamayo.com/watch-all-the-apple-tv-aerial-video-screensavers) for streaming all the different options
  - Videos added to Apple's catalog after January 2020 don't seem to be reflected here, as of January 2022
- Apple started appending the tvOS version number to the URL of the tarball, so as of 2022-01-01 and tvOS 15 [this URL](https://sylvan.apple.com/Aerials/resources-15.tar) is the link to get the latest `entries.json`

# Screenshots

![Screenshot1](https://raw.githubusercontent.com/enen92/screensaver.atv4/master/resources/screenshots/screenshot-01.jpg)

![Screenshot2](https://raw.githubusercontent.com/enen92/screensaver.atv4/master/resources/screenshots/screenshot-02.jpg)

![Screenshot3](https://raw.githubusercontent.com/enen92/screensaver.atv4/master/resources/screenshots/screenshot-03.jpg)

![Screenshot4](https://raw.githubusercontent.com/enen92/screensaver.atv4/master/resources/screenshots/screenshot-04.jpg)


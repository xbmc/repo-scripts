# BlackBarsNever Kodi Addon - Remove black bars

# How it works

This is an addon that eliminates black bars on KODI, whether hardcoded or the video is just wide format

With addon installed and enabled, it will automatically analyze media on playback and determine
if there are any black bars. The addon will then zoom the media exactly enough to cover the display.

The picture will not be distorted in any way as the zoom is linear,
however, on most media, small parts on the left and right will be cut off. Luckily, everything that's
important tends to fall in the middle of the scene 99% of the time. The advantages of experiencing an
immersive picture that fills the periphery should be enough to overweigh the disdvantage of missing sides.

# Supported platforms

- [x] Linux
- [x] Windows
- [x] macOS and iOS
- [x] Android & Embedded Systems - with workaround method

# Android & Embedded Systems like \*ELEC

Currently, Kodi can't capture sreenshots in Android and Embedded Systems if hardware accelertion is enabled due to some technical limitations. This may change in future and when that happens the addon will work properly like in other platforms. For now there's two options:

1. Disable hardware acceleration (turn off MediaCodec Surface in Android). The problem with this is that Kodi will now use CPU for decoding and playback may be affected to the point of being unwatchable, especially for high bitrate media. Also in the devices I tested, HDR won't work on Android if hardware acceleration is turned on, I am not sure if this affects all of Android.

2. Enable the Android & Embedded Systems Workaround from the addon settings. This feature requires an internet connection to fetch media metadata, and works best if your library adopts a decent naming pattern i.e `Title Year`. Also works properly only if media aspect ratio is unchanged from original (i.e has not been cropped from the original)

# Installation

Download the zip file from [releases](https://github.com/osumoclement/script.black.bars.never/releases)

Launch Kodi >> Add-ons >> Get More >> Install from zip file

You might want to turn off Overscan if your display is a TV by going to settings-> Aspect Ratio -> Just Scan

Feel free to ask any questions, submit feature/bug reports

# Multiple Aspect Ratios in Media

For media with multiple aspect ratios, the addon will notify you of this, and will do nothing. In such cases, I recommend you watch the media as is, since if you change the aspect ratio manually, you may not know where in the media the ratio changes in order to adjust again.
This feature requires internet to work

# Customization

There are a few ways to customize the addon
By default, the addon automatically removes black bars. If you want to change this behavior, you can turn this off in the addon settings. You would then need to manually trigger the addon by manually calling it from elsewhere in Kodi (ie from a Skin) like this `RunScript(script.black.bars.never,toggle)`. You could even map this to a key for convenience

To check the addon status elsewhere from Kodi, use this `xbmcgui.Window(10000).getProperty('blackbarsnever_status')`. The result is either `on` or `off`

# License

BlackBarsNever is [GPLv3 licensed](https://github.com/osumoclement/script.black.bars.never/blob/main/LICENSE). You may use, distribute and copy it under the license terms.

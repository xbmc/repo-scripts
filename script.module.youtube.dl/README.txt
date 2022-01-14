This addon was originally written to provide the popular youtube-dl tool for Kodi
addons. A relatively small amount of additional code was written to integrate
youtube-dl with Kodi .

In 2021 the youtube-dl project stalled and the yt-dlp project stepped in to
carry on the the maintenance and development of youtube-dl. This addon was
modified slightly to utilize yt-dlp. At this time no effort has been made
to exploit any of the newer capabilities of yt-dlp.

Several items of interest to maintainers of this addon:
* To facilitate upgrading the yt-dlp to newer builds, the yt-dlp project is
a sub-module of this project and is attached/mounted at the top level
export directory. Instructions for copying the release and bumping the version
are in UPDATE_YT_DLP.sh.

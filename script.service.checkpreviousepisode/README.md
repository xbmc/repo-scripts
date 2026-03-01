
Kodi Check Previous Episode
===================================

`script.service.checkpreviousepisode`

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/bossanova808) 

Kodi script to prevent accidental spoilers by checking you have actually watched the previous episode (i.e. as recorded in the Kodi library).

You can mark shows where episode order doesn't matter as shows to be ignored (and unmark them in the add-on settings if you change your mind), and if you're in the habit of e.g. deleting seasons you have watched, you can force it to only check when the prior episode is actually in your library.

If it detects you've started playback of an episode you probably shouldn't have, the video will be paused, and you'll get a pop up window with options to stop playback, carry on on this occasion, or carry on and also mark the show as one to ignore from now on.

Skinners can even skin the select dialogue by listening to a Window property `CheckPreviousEpisode` which is set to `MissingPreviousEpisode` when the select dialogue is showing (search the [Confluence repo](https://github.com/xbmc/skin.confluence) for `CheckPreviousEpisode` for an example of how this can be done).

Support via the forum thread: <https://forum.kodi.tv/showthread.php?tid=355464>, or open an issue here.

Available form  the main Kodi repository (legacy Python 2 version for Kodi Leia and below, Python 3 version for Kodi Matrix and on).


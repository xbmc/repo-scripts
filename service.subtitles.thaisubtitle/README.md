service.subtitles.thaisubtitle
==========================

thaisubtitle.com subtitle service plugin for XBMC
Searches subtitles from http://www.thaisubtitle.com for 
the currently playing media.

Thanks to those who created and contributed translations on thaisubtitle.com.

Thanks also to manacker, the auther of https://github.com/manacker/service.subtitles.subscene
whose code I borrowed.

Installation
------------

Currently not in a repo so git clone into your plugins directory and restart XBMC. The plugin
should appear in your subtitle download menu.

Alternatively you can use the [instructions to install an addon from a zip file](http://wiki.xbmc.org/index.php?title=Add-on_manager#How_to_install_from_a_ZIP_file), after you download [service.subtitles.thaisubtitle.zip](https://github.com/djay/service.subtitles.thaisubtitle/archive/master.zip?file=service.subtitles.thaisubtitle.zip)

How to contribute
-----------------

This plugin is a work in progress. Thaisubtitle.com doesn't provide searching by id so creating
searches to find subtitles can be challenging. If the plugin can't find subtitles that you
know are available, and you know python, then consider improving this plugin. Pull requests are
welcome.

You can run manual searches from the command line via

```
  python thaisubtitles.py "My Show Name"
```

You can also put XBMC into debug mode and view the log file for debug info about searches you
perform.

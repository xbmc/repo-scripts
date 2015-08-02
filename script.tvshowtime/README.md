script.tvshowtime
=================

Kodi plugin for [TVShow Time](http://www.tvshowtime.com)

This plugin will set TV shows episodes you've seen as watched on TVShow Time.
It will also add the new TV show to your account if it was not already there.

install
=======

This plugin has been submitted to the [official Kodi repository](http://addons.xbmc.org/show/script.tvshowtime/).
To install it, just follow this [HOW-TO](http://kodi.wiki/view/HOW-TO:Install_add-ons).
After that, launch the add-on to login.

build
=====

If you want to build it manually, here is a simple script to do so:
```sh
#!/bin/bash

dest=script.tvshowtime
version=$(grep -E "^\s+version" addon.xml | cut -f2 -d'"')

if [ -d $dest ]; then
    rm -r $dest
fi

mkdir $dest
cp addon.xml $dest/
cp *.txt $dest/
cp icon.png $dest/
cp *.py $dest/
cp -r resources $dest/

if [ -f $dest-$version.zip ]; then
    rm $dest-$version.zip
fi

zip -r $dest-$version.zip $dest
rm -r $dest
````
It will create a zip file that you can install directly within Kodi.
Using the GUI of Kodi, choose to install your plugin as a zip file, find your zip file and it's done !

download
========

If you want to download the release package because you can't or don't want to build it, you can do it on this link:
http://addons.xbmc.org/show/script.tvshowtime/
or
[download](here) the latests version.

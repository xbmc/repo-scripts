script.myepisodes
=================

XBMC plugin for [MyEpisodes](http://myepisodes.com)

This plugin will set TV shows episodes you've seen as watched on MyEpisodes.
It will also add the the TV show to your account if it was not already there.

This was done mainly because I'm too lazy to do it by hand and I watch 98% of
my video through XBMC.

build
=====
If you really want to build it, here is a simple script to do so:
```sh
#!/bin/bash

dest=script.myepisodes
version=$(grep "^\s\+version" addon.xml | cut -f2 -d'"')

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
It will create a zip file that you can install directly within XBMC.

install
=======

Using the GUI of XBMC, choose to install your plugin as a zip file, find your
zip file, and you're done !

download
========
If you can't or don't want to build this plugin, look at the release tab.
You can download the last plugin from there.

[Download](https://github.com/maximeh/script.myepisodes/releases/download/1.2.7/script.myepisodes-1.2.7.zip?raw=true) the latests version.

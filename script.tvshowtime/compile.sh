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

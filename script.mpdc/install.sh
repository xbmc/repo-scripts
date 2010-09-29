#/bin/sh
DESTDIR=~/.xbmc/addons/script.mpdc

rm -rf ${DESTDIR}
mkdir -p ${DESTDIR}
cp -a * ${DESTDIR}

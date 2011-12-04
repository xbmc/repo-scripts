#!/bin/sh

URL="http://launchpad.net/myconnpy/0.3/0.3.2/+download/mysql-connector-python-0.3.2-devel.tar.gz"
wget $URL
tar xf mysql-connector-python-*.tar.gz
cp -r mysql-connector-python-*/* .
rm -r mysql-connector-python-*

# rename python2 folder
rm -r lib
mv python2 lib
mv COPYING LICENSE.txt

# delete stuff we don't need
rm -r python3
rm metasetupinfo.py PKG-INFO setup.cfg setup.py unittests.py


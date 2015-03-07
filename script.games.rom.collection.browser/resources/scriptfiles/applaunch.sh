#!/bin/bash
# App Launch script - Quit Kodi to launch another program
# Thanks to rodalpho @ # http://xbmc.org/forum/showthread.php?t=34635
# By Redsandro 	2008-07-07
# By ryosaeba87	2010-08-24 (Added support for MacOSX)
# By malte 2015-01-22 (change from XBMC to Kodi)


# Check for agruments
if [ -z "$*" ]; then
	echo "No arguments provided."
	echo "Usage:"
	echo "launcher.sh [/path/to/]executable [arguments]"
	exit
fi


case "$(uname -s)" in
	Darwin)
		Kodi_PID=$(ps -A | grep Kodi.app | grep -v Helper | grep -v grep | awk '{print $1}')
		Kodi_BIN=$(ps -A | grep Kodi.app | grep -v Helper | grep -v grep | awk '{print $5}')
		;;
	Linux)
		Kodi_PID=$(pidof kodi.bin)
		Kodi_BIN="kodi"
		;;	
	*)
		echo "I don't support this OS!"
		exit 1
		;;
esac


# Is Kodi running?
if [ -n $Kodi_PID ]
then
	kill $Kodi_PID # Shutdown nice
	echo "Shutdown nice"
else
	echo "This script should only be run from within Kodi."
	exit
fi

# Wait for the kill
# sleep 


# Is Kodi still running?
if [ -n $Kodi_PID ]
then
    kill -9 $Kodi_PID # Force immediate kill
	echo "Shutdown hard"	
fi

echo "$@"

# Launch app - escaped!
"$@"


# SOMETIMES Kodi starts too fast, and on some hardware if there is still a millisecond of sound being used, Kodi starts witout sound and some emulators say there is a problem with the sound hardware. If so, remove comment:
#sleep 1


# Done? Restart Kodi
$Kodi_BIN &
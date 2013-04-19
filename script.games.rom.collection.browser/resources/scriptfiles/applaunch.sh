#!/bin/bash
# App Launch script - Quit XBMC to launch another program
# Thanks to rodalpho @ # http://xbmc.org/forum/showthread.php?t=34635
# By Redsandro 	2008-07-07
# By ryosaeba87	2010-08-24 (Added support for MacOSX)
# 


# Check for agruments
if [ -z "$*" ]; then
	echo "No arguments provided."
	echo "Usage:"
	echo "launcher.sh [/path/to/]executable [arguments]"
	exit
fi


case "$(uname -s)" in
	Darwin)
		XBMC_PID=$(ps -A | grep XBMC.app | grep -v Helper | grep -v grep | awk '{print $1}')
		XBMC_BIN=$(ps -A | grep XBMC.app | grep -v Helper | grep -v grep | awk '{print $5}')
		;;
	Linux)
		XBMC_PID=$(pidof xbmc.bin)
		XBMC_BIN="xbmc"
		;;	
	*)
		echo "I don't support this OS!"
		exit 1
		;;
esac


# Is XBMC running?
if [ -n $XBMC_PID ]
then
	kill $XBMC_PID # Shutdown nice
	echo "Shutdown nice"
else
	echo "This script should only be run from within XBMC."
	exit
fi

# Wait for the kill
# sleep 


# Is XBMC still running?
if [ -n $XBMC_PID ]
then
    kill -9 $XBMC_PID # Force immediate kill
	echo "Shutdown hard"	
fi

echo "$@"

# Launch app - escaped!
"$@"


# SOMETIMES xbmc starts too fast, and on some hardware if there is still a millisecond of sound being used, XBMC starts witout sound and some emulators say there is a problem with the sound hardware. If so, remove comment:
#sleep 1


# Done? Restart XBMC
$XBMC_BIN &
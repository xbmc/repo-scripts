#!/bin/bash
# App Launch script - Temporarily quit XBMC to launch another program
# Tx to rodalpho @ # http://xbmc.org/forum/showthread.php?t=34635
# By Redsandro 	2008-07-07
# Updated:		2008-02-28


# Check for agruments
if [ -z "$*" ]; then
	echo "No arguments provided."
	echo "Usage:"
	echo "launcher.sh [/path/to/]executable [arguments]"
	exit
fi



# Is XBMC running?
if pidof xbmc.bin; then
	pidof xbmc.bin|xargs kill # Shutdown nice
	echo "Shutdown nice"
else
	echo "This script should only be run from within XBMC."
	exit
fi

# Wait for the kill
sleep 



# Is XBMC still running?
if pidof xbmc.bin; then
	pidof xbmc.bin|xargs kill -9 # Force immediate kill
	echo "Shutdown hard"	
fi

echo "$@"

# Launch app - escaped!
"$@"


# SOMETIMES xbmc starts too fast, and on some hardware if there is still a millisecond of sound being used, XBMC starts witout sound and some emulators say there is a problem with the sound hardware. If so, remove comment:
#sleep 1


# Done? Restart XBMC
xbmc



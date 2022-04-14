# Kodi PulseEqualizer GUI Addon

PulseEqualizer GUI provides a graphical frontend for Kodi on linux systems to control pulse audio equalizer. 

Version 2.1.4

This includes:

*	Graphical configuration of the pulseaudio equalizer
*	Digital Room Correction
*	Management of profiles (add, remove and change)
*	Automatic profile switching based on output device
*	Audio latency-offset slider and automatic switch (for video/audio sync)
*	Control system volume (needed if a compressor is used in the filter chain)
*	Mini keymap editor

Tested on i386 Linux Mint / Debian 10/11 headless / Raspberry PI 2b and 3b / Ubuntu 18 headless

2022 wastis

![Pulse Equalizer](/resources/images/Equalizer.png)

## Installation

This addon requires pulseaudio-equalizer installed on the system

	sudo apt install pulseaudio-equalizer	

### Install Addon in Kodi

Launch *Kodi >> Add-ons >> Get More >> .. >> Install from zip file*

### Configuration

In Kodi, select a pulseaudio hardware ouptut device and start a playback. Select an equalizer profile. The equalizer is then automatically inserted into the playback stream. 

More information can be found on [Wiki](https://github.com/wastis/PulseEqualizerGui/wiki)

Help can be found in the Kodi forum within this [thread](https://forum.kodi.tv/showthread.php?tid=360514&pid=3076706#pid3076706)


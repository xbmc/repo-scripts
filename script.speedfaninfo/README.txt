ABOUT
This XBMC plugin parses and displays information from the SpeedFan log. While this plugin works on any platform, SpeedFan only works on Windows, so it is optimally built for people using XBMC on Windows.

GETTING SPEEDFAN
SpeedFan is available at: <http://www.almico.com/speedfan.php>

COMPATIBILITY
This plugin has been tested with SpeedFan 4.44. It should work with any version of SpeedFan that outputs the log file in the same format as 4.44. It has been tested on XBMC Eden (11.0) betas 2 and 3 on Windows and Macintosh. It has not been tested on Dharma (10.1) and likely will not work on Dharma.

SPECIAL LOG CONFIGURATION CONSIDERATIONS
This readme is not meant to be a tutorial on how to setup SpeedFan or enable logging.  The SpeedFan web site is available to help you with that.  To get SpeedFanInfo to properly parse the log file, you do need to label the various SpeedFan items in a specific way.

SpeedFanInfo knows about four kinds of log items: temperatures, fan speeds, voltages, and fan speed percentages.

Temperatures
This is the first tab in the SpeedFan configuration window (labeled Temperatures).  Any item you are logging needs it's label to end with .temp (not case sensitive) for SpeedFanInfo to parse it.  (i.e. CPU.temp)

Fan Speeds
This is the second tab in the SpeedFan configuration window (labeled Fans).  Any item you are logging needs it's label to end with .speed (not case sensitive) for SpeedFanInfo to parse it.  (i.e. CPU Fan.speed)

Voltages
This is the third tab in the SpeedFan configuration window (labeled Voltages).  Any item you are logging needs it's label to end with .voltage (not case sensitive) for SpeedFanInfo to parse it.  (i.e. +12V.voltage)

Fan Speed Percentages
This is the fourth tab in the SpeedFan configuration window (labeled Speeds).  Any item you are logging needs it's label to end with .percent (not case sensitive) for SpeedFanInfo to parse it.  (i.e. CPU Fan.percent)  A special note about fan speed percentages.  They will only show on the SpeedFanInfo screen if you are logging the same number of fan speeds as you are fan percentages.  SpeedFan logs these in a predictable order, so as long as you don't log four of your five fan speeds and then a different four of your five fan speed percentages, you should be fine.

SETUP
After you install this plugin, go to the plugin settings.  There are four options to set.

SpeedFan Log Folder
The folder in which the SpeedFan log file resides.  Be default SpeedFan stores this file in C:\Program Files\SpeedFan\

Log Temperature Scale
This should be set to match the temperature scale to which you have SpeedFan set.  This setting just tells the plugin what to put after the integer value for the temperature.  This plugin will not convert from Celcius to Farenheit (or vice versa).

Window Update Interval (in seconds)
The number of seconds between updates to the screen.  Please note that SpeedFan will sometimes get it's logging a little out of sync, so sometimes the fan speed and fan speed percentages don't actually match.  This only happens when your fan speeds are fluctuating pretty rapidly, so if you wait through a couple of screen refreshes, the numbers usually start matching again.

Enable Verbose Logging
This drops a metric crapload of stuff into the XBMC log file.  It's really only useful for debugging, so I wouldn't enable it unless you're asked to do so by the developer to assist with troubleshooting.

GETTING HELP
Please see the thread in the XBMC forums for assistance.
<http://forum.xbmc.org/showthread.php?p=1014479>
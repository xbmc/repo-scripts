# SpeedFan Information Display

## Information
SpeedFan Information Display is a Kodi addon that shows you current log information from the Windows program SpeedFan (or any other program that outputs a compatible log file) either as a full window or a compact window on the side of the screen.

### Getting SpeedFan
SpeedFan is a Windows program and is available at <http://www.almico.com/speedfan.php>

### Compatibility
This plugin has been tested with SpeedFan 4.44. It should work with any version of SpeedFan that outputs the log file in the same format as 4.44. The add-on will run on any platform using Kodi Krypton or later (although testing and active support is only done on the current production version of Kodi), but SpeedFan is a Windows only program.

## SpeedFan Setup
This readme is not meant to be a tutorial on how to setup SpeedFan or enable logging. The SpeedFan web site is available to help you with that. To get SpeedFanInfo to properly parse the log file, you do need to label the various SpeedFan items in a specific way.  SpeedFan Information Display knows about five kinds of log items: temperatures, fan speeds, voltages, fan speed percentages, and a catch all 'other.'

### Temperatures
This is the first tab in the SpeedFan configuration window (labeled Temperatures). Any item you are logging needs it's label to end with .temp (not case sensitive) for SpeedFanInfo to parse it. (i.e. CPU.temp).

### Fan Speeds
This is the second tab in the SpeedFan configuration window (labeled Fans). Any item you are logging needs it's label to end with .speed (not case sensitive) for SpeedFanInfo to parse it. (i.e. CPU Fan.speed)

### Voltages
This is the third tab in the SpeedFan configuration window (labeled Voltages). Any item you are logging needs it's label to end with .voltage (not case sensitive) for SpeedFanInfo to parse it. (i.e. +12V.voltage)

### Fan Speed Percentages
This is the fourth tab in the SpeedFan configuration window (labeled Speeds). Any item you are logging needs it's label to end with .percent (not case sensitive) for SpeedFanInfo to parse it. (i.e. CPU Fan.percent) A special note about fan speed percentages. They will only show on the SpeedFanInfo screen if you name the percentage the sam as the fan speeds (i.e. CPU.speed and CPU.percent). If there is no corresponding percentage for a given speed, only the speed will be displayed.

### Other
If you want any other log item to show up on the SpeedFan display, you can label it ending with .other.  These items will show up in the OTHER section exactly as stored in the log.

## Addon Options
After you install this plugin, go to the plugin settings. There are a few options to set.

### General
*Primary Log File Title:* (default empty)<br />
The name to display at the top of the information summary.  Useful if you're showing the logs from more than one machine.

*Log File Location:* (default empty)<br />
The folder where SpeedFan is storing the log file. By default this will likely be C:/Program Files/SpeedFan/

*Use Compact Display*<br />
When selected you get a smaller sidebar style display of readings rather than the fullscreen version. If you select this option you will get a slider to select the transparency level of the background. This is a nice option if you want to be able to peek at the information while watching other media.

*Log Temperature Scale*<br />
This should be set to match the temperature scale to which you have SpeedFan set. This setting just tells the plugin what to put after the integer value for the temperature. This add-on will not convert from Celcius to Farenheit (or vice versa).

*Window Update Interval (in seconds)*<br />
The number of seconds between updates to the screen. Please note that SpeedFan will sometimes get it's logging a little out of sync, so sometimes the fan speed and fan speed percentages don't actually match. This only happens when your fan speeds are fluctuating pretty rapidly, so if you wait through a couple of screen refreshes, the numbers usually start matching again.

### Additional Logs
*Use Log File x:* (default false)<br />
Enable one or both of these to monitor other SpeedFan logs. Once enabled, you need to provide a title and location for the log.

### Advanced
*Set Line Read Size:* (default 256)<br />
You shouldn't ever really need to change this unless you're using an external script to generate a copy cat log file (see below).  Changing this will change the amount of data read at one time by the add-on.

*Enable debug logging:* (default false)<br />
When enabled, if you have Kodi logging set the DEBUG you will get a very verbose set of information in your log file. You should only need to activate this when troubleshooting issues.

## Tips and Tricks

### Setting a Keyboard Shortcut
If you are using the compact display, you will probably want to assign a keyboard shortcut to launch SpeedFanInfo (and then map that to a key on your remote). To do that you need to add a custom key mapping. Information on key mapping is available at <http://wiki.xbmc.org/index.php?title=Keymap>. Here's an example of assigning SpeedFanInfo to launch when you press F1.

```xml
    <keymap>
        <global>
            <keyboard>
                <f1>RunAddon(script.speedfaninfo)</f1>
            </keyboard>
        </global>
    </keymap>
```

## Getting Help
Please see the thread in the Kodi forums for assistance.

<https://forum.kodi.tv/showthread.php?tid=122481>

## Beta Testing
If you are interested in beta testing new versions of this add on (or just like being on the bleeding edge of up to date), you can install beta versions (Leia or later, there will be no more updates for earlier versions) from [my addon beta repository](https://github.com/pkscout/repository.beta.pkscout/raw/helix/repository.beta.pkscout-1.1.1.zip) (this is a zip download). You can also monitor the support thread, as links to particular beta releases will be available there as well.
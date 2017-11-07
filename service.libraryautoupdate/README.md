## Library Updater

The Library Updater will update your music and/or video libraries according to times specified by you. Please note that this is just a fancy timer that calls out to the normal Kodi Library Scanning functions. All of the processes associated with scanning are all handed off to Kodi. 

_Thanks to pkscuot for several small tweaks to this addon!_

### General Settings: 

* Startup Delay - if an update should run on startup (dependant on the time the last update has ran) this will delay it from running for a few minutes to allow other XBMC process to function. 
* Show Notifications - shows notifications when the updater will run again
* Run During Playback - should the addon run when you are playing media (yes/no)
* Only run when idle - restricts the scanning process to when the screensaver is active
* Disable Manual Run Prompt - disables the dialog box when selecting Manual Run and just goes right to the libary update

### Video Settings: 

Enabling this will turn on scanning for the Video Library. This is the same as calling "Update Library" from within the Video menus of Kodi. There are a few options you can tweak regarding how often you want the scanner to run. 

__Custom Paths__

Custom paths are a special advanced feature for the Video library. It allows you to specify different schedules for individual paths in your library. This editor is limited to the Cron style syntax for scheduling. The path you select must already be in the video database and have content selected. The path must also match your source path exactly. 

### Music Settings

Enabled this will turn on scanning for the Music Library. This is the same as calling "Update Library" from within the Music menus of Kodi. There are a few options you can tweak regarding how often you want the scanner to run. 

### Timer Options: 

For both Video and Music library scanning there are two types of timers to choose from. 

__Standard Timer__

Specify an interval to run the library update process. It will be launched every X hours within the interval unless on of the conditions specified by you as been met (don't run during media playback, etc) in which case it will be run at the next earliest convenience. 

__Advanced Timer__

Specify a cron expression to use as an interval for the update process. By default the expression will run at the top of every hour. More advanced expressions can be configured such as: 

```

    .--------------- minute (0 - 59)
    |   .------------ hour (0 - 23)
    |   |   .--------- day of month (1 - 31)
    |   |   |   .------ month (1 - 12) or Jan, Feb ... Dec
    |   |   |   |  .---- day of week (0 - 6) or Sun(0 or 7)
    V   V   V   V  V
    *   *   *   *  *
```

Example:
1. 0 */5 ** 1-5 - runs update every five hours Monday - Friday
2. 0,15,30,45 0,15-18 * * * - runs update every quarter hour during midnight hour and 3pm-6pm


Read up on cron (http://en.wikipedia.org/wiki/Cron) for more information on how to create these expressions

### Cleaning the Library:

Cleaning the Music/Video Libraries is not enabled by default. If you choose to do this you can select from a few options to try and reduce the likelyhood that a DB clean wile hose your database.

* Library to Clean - You can clean your video library, music library, or both.
* Prompt User Before Cleaning - you must confirm that you want to clean the library before it will happen. Really only useful for "After Update" as a condition. 
* Frequency - There are several frequency options. 
  * "After Update" will run a clean immediately following a scan on the selected library. 
  * The Day/Week/Month options will schedule a clean task to happen. Cleaning the Video Library is hardcoded for midnight and the music library at 2am. Weekly updates occur on Sunday and Monthly updates occur on the first of each month - these values are hardcoded. 
  * You can also choose to enter a custom cron timer for video and music library cleaning. These work the same as any of the other cron timers for the other schedules.


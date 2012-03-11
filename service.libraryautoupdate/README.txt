The XBMC Library Updater will update your music and/or video libraries according to times specified by you. 

Thanks to pkscuot for several small tweaks to this addon!

General Settings: 

Update video - updates video library
update music - updates music library
Show Notifications - shows notifications when the updater will run again
Run During Playback - should the addon run when you are playing media

Timers:

Standard Timer - specify an interval to run the library update process. It will be launched every X hours within the interval unless on of the conditions specified by you as been met (don't run during media playback, etc) in which case it will be run at the next earliest convenience. There is also a startup delay that can be used on XBMC startup

Advanced Timer - specify a cron expression to use as an interval for the update process. By default the expression will run at the top of every hour. More advanced expressions can be configured such as: 

    .--------------- minute (0 - 59)
    |   .------------ hour (0 - 23)
    |   |   .--------- day of month (1 - 31)
    |   |   |   .------ month (1 - 12) or Jan, Feb ... Dec
    |   |   |   |  .---- day of week (0 - 6) or Sun(0 or 7), Mon(1) ... Sat(6)
    V   V   V   V  V
    *   *   *   *  *
Example:
	0 */5 ** 1-5 - runs update every five hours Monday - Friday
	0,15,30,45 0,15-18 * * * - runs update every quarter hour during midnight hour and 3pm-6pm


Read up on cron (http://en.wikipedia.org/wiki/Cron) for more information on how to create these expressions
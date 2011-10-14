PseudoTV for XBMC


-----------
What is it?
-----------
    It's channel-surfing for your media center.  Never again will you have to
actually pick what you want to watch.  Use an electronic program guide (EPG)
to view what's on or select a show to watch.  This script will let you create
your own channels and, you know, watch them.  Doesn't actually sound useful
when I have to write it in a readme.  Eh, try it and decide if it works for
you.


------------
Requirements
------------
    This ONLY uses your existing video library to play video.  It will NOT play
video from the internet.  If you do not have a significant number of videos in
your library, then this script probably isn't for you.  Sorry.


--------
Features
--------
    - Automatic channel creation based on your library.
    - Optionally customize the channels you want with the channel configuration
        tool.
    - Utilize the XBMC smart playlist editor to create advanced channel setups.
    - Use an EPG and view what was on, is on, and will be on.  Would you rather
        see something that will be on later?  Select it and watch it now!
    - Want to pause a channel while you watch another?  And then come back to
        it and have it be paused still?  Sounds like a weird request to me, but
        if you want to do it you certainly can.  It's a feature!
    - An idle-timer makes sure you aren't spinning a hard-drive needlessly all
        night.
    - Discover the other features on your own (so that I don't have to list
        them all...I'm lazy).


-----
Setup
-----
    First, install it.  This is self-explanatory (hopefully).  Really, that's
all that is necessary.  Default channels will be created without any
intervention.  You can choose to setup channels (next step) if you wish.
    Instructions to create your own channels.  Inside of the addon config, you
may open the channel configuration tool.  Inside of here you can select a
channel to modify.  You may then select it's type and any options.  For a basic
setup, that's all you need to do.  It's worth noting that you may create a
playlist using the smart playlist editor and then select that playlist in the
channel config tool (Custom Playlist channel type).
    Additionally, you may select to add advanced rules to a certain channel.
There are quite a few rules that are currently available, and hopefully they
should be relatively self-explanitory.  This is a readme and should include
descriptions of them all...who knows, maybe it will some day.


--------
Controls
--------
    There are only a few things you need to know in order to control every-
thing.  First of all, the Stop button ('X') stops the video and exits the
script.  You may also press the Previous Menu ('Escape') button to do this
(don't worry, it will prompt you to verify first).  Scroll through channels
using the arrow up and down keys, or alternatively by pressing Page up or down.
    To open the EPG, press the Select key ('Enter').  Move around using
the arrow keys.  Start a program by pressing Select.  Pressing Previous
Menu ('Escape') will close the EPG.
    Press 'I' to display or hide the info window.  When it is displayed,
you can look at the previous and next shows on this channel using arrow left
and right.


--------
Settings
--------

General Settings -

    Configure Channels: This is the channel configuration tool.  From here you
can modify the settings for each individual channel.

    Auto-off Timer: The amount of time (in minutes) of idle time before the script
is automatically stopped.

    Force Channel Reset: If you want your channels to be reanalyzed then you
can turn this on.

    Time Between Channel Resets: This is how often your channels will be reset.
Generally, this is done automatically based on the duration of the individual
channels and how long they've been watched.  You can change this to reset every
certain time period (day, week, month).

    Default channel times at startup: This affects where the channels start
playing when the script starts.  Resume will pick everything up where it left
off.  Random will start each channel in a random spot.  Real-Time will act like
the script was never shut down, and will play things at the time the EPG said
they would play.

    Background Updating: The script uses multiple threads to keep channels up-
to-date while other channels are playing.  In general, this is fine.  If your
computer is too slow, though, it may cause stuttering in the video playback.
This setting allows you to minimize or disable the use of these background
threads.

    Enable Channel Sharing: Share the same configuration and channel list
between multiple computers.  If you're using real-time mode (the default) then
you can stop watching one show on one computer and pick it up on the other.  Or
you can have both computers playing the same lists at the same time.

    Shared Channels Folder: If channel sharing is enabled, this is the location
available from both computers that will keep the settings and channel infor-
mation.


Visual Settings -

    Info when Changing Channels: Pops up a small window on the bottom of the
screen where the current show information is displayed when changing channels.

    Always show channel logo: Always display the current channel logo.

    Channel Logo Folder: The place where channel logos are stored.

    Clock Display: Select between a 12-hour or 24-hour clock in the EPG.

    Show Coming Up Next box: A little box will notify you of what's coming up
next when the current show is nearly finished.

    Hide very short videos: Don't show clips shorter than 60 seconds in the
EPG, coming up next box, or info box.  This is helpful if you use bumpers or
commercials.


-------
Credits
-------
Developer: Jason102
Code Additions: Sranshaft, TheOddLinguist
Skins: Sranshaft, Zepfan, Steveb
Preset Images: Jtucker1972
Languages: CyberXaz, Machine-Sanctum

No more forgotten football matches or formula one races! Avoid discussion with your better half and let kodi switch to the channels you want! Or let they switch to their favorite shows at a given time!

This service adds items to the context menu of the pvr osd guide window (PVROSDGuide) automatically (add switchtimer, delete all switchtimer). Currently the skins Aeon Flex, Destiny and a Confluence Mod from Kodinerds fully supports this service with additional
windows but other skins can this service implement too. Hints for integration see below here. If you aren't a skinner or don't need special windows for editing/deleting switchtimers just ignore the skinners section and install this service as usual. All can be done with the context menu of pvr osd guide.

Skinners only:

If you want or need to call this service inside of another window different from PVROSDGuide, use:

    <label>$ADDON[service.kn.switchtimer 30040]</label>
    <visible>System.HasAddon(service.kn.switchtimer) + Window.IsVisible(tvguide)</visible>
    <onclick>RunScript(service.kn.switchtimer,action=add,channel=channelname,icon=icon,date=datestring,title=title)</onclick>

You have to provide the needed parameters, comparsion is done via valid Channelname and Datetime. Format of Datetime must be the same as used in Kodi settings:

    channelname (e.g. $INFO[ListItem.Channelname])
    icon (e.g. $INFO[ListItem.Icon])
    datestring (e.g. $INFO[ListItem.Date])
    title (e.g. $INFO[ListItem.Title])

If you want buttons for deleting one or all timers just use:

    <onclick>RunScript(service.kn.switchtimer,action=del,timer=tx)</onclick>

where tx is a timer from t0 to t9, or delete all timers with

    <label>$ADDON[service.kn.switchtimer 30041]</label>
    <onclick>RunScript(service.kn.switchtimer,action=delall)</onclick>

Timers are stored as strings in the settings of the skin (guisettings.xml/skinsettings.xml) as follows. Empty strings are inactive timers. All timers are sorted by datetime where t0 is the nearest and t9 the latest timer.

    t0:channel      # channel name
    t0:icon         # channel icon
    t0:date         # datetime of broadcast
    t0:title        # title of broadcast
    ...
    t9:channel
    t9:icon
    t9:date
    t9:title

    SwitchTimerActiveItems: # of active timers

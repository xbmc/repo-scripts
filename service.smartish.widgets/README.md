#Smart(ish) Widgets - Widgets with a built in recommendation system.

Smart(ish) Widgets monitor what you watch and listen to, and provide widgets with personal recommendations of what media you are likely to want to play next based on your habits at that day and time.

##Privacy and security

Smart(ish) Widgets saves information about what you have played - things like the genre, actors and so on. This information is only stored - and always remains - local.

The widgets open a port to enable communication between the background service and Kodi's widget requests, as well as to enable server/client communication. By default this is port 45354, and firewalls should be double-checked to ensure this port is not accessible to the outside world.

## Integrating into skin

First, the skin must indicate that it supports the widgets (otherwise they will not generate any widgets, only listen for habits). Include in home.xml:

`<onload>Skin.SetBool(enable.smartish.widgets)</onload>`

Then, include one of the following in the <content /> tag of the list that will display the widget:

`plugin://service.smartish.widgets?type=movies&amp;reload=$INFO[Window.Property(smartish.movies)]`
`plugin://service.smartish.widgets?type=episodes&amp;reload=$INFO[Window.Property(smartish.episodes)]`
'plugin://service.smartish.widgets?type=albums&amp;reload=$INFO[Window.Property(smartish.albums)]'
'plugin://service.smartish.widgets?type=pvr&amp;reload=$INFO[Window.Property(smartish.pvr)]'

##Server/Client function

If you have multiple Kodi machines which share a single library via MySQL, it is possible to designate one machine the server, and others as clients. In this configuration, all habits from each machine are stored only on the server, and the server takes all responsibility for querying the library and building widgets. In this way, your habits are shared amongst machines, and time displaying widgets on client startup is dramatically improved.

By default all machines are set up as a server. To set up a machine as a client, in the script settings toggle 'Role' to client, and input the IP address of the server. The server and clients must all use the same port, and it is not supported to have multiple clients which connect to the server from the same ip address (e.g. internet connection sharing).
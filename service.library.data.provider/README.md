plugin.library.data.provider
============================

Python script for use with XBMC

============================

INFORMATION FOR SKINNERS
============================

Include the following in your addon.xml
<import addon="service.library.data.provider" version="0.0.1"/>

Load a list with this content tag:
<content target="video">plugin://service.library.data.provider?type=randommovies</content>

Load a list with this content tag to have the list automatically refresh:
<content target="video">plugin://service.library.data.provider?type=randommovies&amp;reload=$INFO[Window.Property(randommovies)]</content>

Available tags:
-   randommovies
-   recentmovies
-   recommendedmovies
-   recommendedepisodes
-   recentepisodes
-   randomepisodes
-   randomsongs
-   randomalbums
-   recentalbums
-   recommendedalbums

Available infolabels:
Most of the usual video library infolabels. 
ListItem.Property(type) shows with what option the script was run.

TODO:
Artist/Musicvideo/Addons support.


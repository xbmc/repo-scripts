plugin.library.data.provider
============================

Python script for use with XBMC

============================

INFORMATION FOR SKINNERS
============================

Include the following in your addon.xml
<import addon="service.library.data.provider" version="0.0.4"/>

Load a list with this content tag to have the list use cached data automatically refresh:
<content target="video">plugin://service.library.data.provider?type=randommovies&amp;reload=$INFO[Window.Property(randommovies)]</content>

To view within the library, create a link omitting the reload parameter:
<onclick>ActivateWindow(Videos,plugin://service.library.data.provider?type=randommovies,return)</onclick>

Available tags:
-   randommovies
-   recentmovies
-   recommendedmovies
-   recommendedepisodes
-   recentepisodes
-   randomepisodes
-   recentvideos (movies and episodes)
-   randomsongs
-   randomalbums
-   recentalbums
-   recommendedalbums

Available infolabels:
Most of the usual video library infolabels. 
ListItem.Property(type) shows with what option the script was run.

Limiting results:
To only return partial results, add the parameter "limit", for example limit=5.

TODO:
Artist/Musicvideo/Addons support.


script.watchlist
================

Script to provide watchlist functionality in library view for reFocus 1.x.x

INFORMATION FOR SKINNERS
============================

Include the following in your addon.xml

 <import addon="script.watchlist" version="0.0.1"/>

Use with

 <onclick>ActivateWindow(Videos,plugin://script.watchlist?type=[type],return)</onclick>

Where type is one of the following:
-   movies
-   episodes

Script is based upon service.library.data.provider, itself based upon service.skin.widgets

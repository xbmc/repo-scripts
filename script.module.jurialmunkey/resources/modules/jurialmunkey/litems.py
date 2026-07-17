# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html


INFOLABEL_MAP = {
    "title": "title",
    "artist": "artist",
    "albumartist": "albumartist",
    "genre": "genre",
    "year": "year",
    "rating": "rating",
    "album": "album",
    "track": "tracknumber",
    "duration": "duration",
    "runtime": "duration",
    "playcount": "playcount",
    "director": "director",
    "trailer": "trailer",
    "tagline": "tagline",
    "plot": "plot",
    "plotoutline": "plotoutline",
    "originaltitle": "originaltitle",
    "lastplayed": "lastplayed",
    "writer": "writer",
    "studio": "studio",
    "mpaa": "mpaa",
    "country": "country",
    "premiered": "premiered",
    "set": "set",
    "setid": "setid",
    "top250": "top250",
    "votes": "votes",
    "firstaired": "aired",
    "season": "season",
    "episode": "episode",
    "showtitle": "tvshowtitle",
    "sorttitle": "sorttitle",
    "episodeguide": "episodeguide",
    "dateadded": "dateadded",
    "id": "dbid",
    "songvideourl": "songvideourl",
}


class ContainerDirectory():
    def __init__(self, handle, paramstring, **params):
        self.handle = handle
        self.paramstring = paramstring
        self.params = params

    @staticmethod
    def get_list_item(label='', label2='', path='', offscreen=True, is_folder=True):
        from xbmcgui import ListItem
        return (
            path,
            ListItem(label=label, label2=label2, path=path, offscreen=offscreen),
            is_folder,
        )

    def add_items(self, items, update_listing=False, plugin_category='', container_content=''):
        if self.handle is None:
            return
        import xbmcplugin
        xbmcplugin.addDirectoryItems(handle=self.handle, items=items)
        xbmcplugin.setPluginCategory(self.handle, plugin_category)  # Container.PluginCategory
        xbmcplugin.setContent(self.handle, container_content)  # Container.Content
        xbmcplugin.endOfDirectory(self.handle, updateListing=update_listing)

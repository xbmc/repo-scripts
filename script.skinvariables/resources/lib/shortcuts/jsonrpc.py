from resources.lib.shortcuts.common import GetDirectoryCommon
from resources.lib.kodiutils import get_localized


DIRECTORY_PROPERTIES_BASIC = ["title", "art", "file", "fanart"]
DIRECTORY_SOURCES = {
    "sources://video/": "video",
    "sources://music/": "music",
    "sources://pictures/": "pictures",
    "sources://programs/": "programs",
    "sources://files/": "files",
    "sources://games/": "game",
}


class GetDirectoryJSONRPC(GetDirectoryCommon):
    def get_directory_path(self):
        from jurialmunkey.jsnrpc import get_directory
        return get_directory(self.path, DIRECTORY_PROPERTIES_BASIC)

    def get_directory_source(self):
        from contextlib import suppress
        from jurialmunkey.jsnrpc import get_jsonrpc
        response = get_jsonrpc("Files.GetSources", {"media": DIRECTORY_SOURCES[self.path]})
        with suppress(KeyError):
            result = response['result']['sources']
        return result or [{}]

    def get_directory(self):
        if not self.path:
            return []

        if self.path in DIRECTORY_SOURCES:
            func = self.get_directory_source
        else:
            func = self.get_directory_path

        self._directory = func()

        return self._directory

    def get_items(self):

        from resources.lib.lists.filterdir import ListItemJSONRPC

        def _make_item(i):
            if not i:
                return
            listitem_jsonrpc = ListItemJSONRPC(i, library=self.library, dbtype=self.dbtype)
            listitem_jsonrpc.infolabels['title'] = listitem_jsonrpc.label
            listitem_jsonrpc.infoproperties['nodetype'] = self.target or ''
            listitem_jsonrpc.artwork = self.get_artwork_fallback(listitem_jsonrpc)
            listitem_jsonrpc.label2 = listitem_jsonrpc.path
            item = (listitem_jsonrpc.path, listitem_jsonrpc.listitem, listitem_jsonrpc.is_folder, )
            return item

        from resources.lib.kodiutils import ProgressDialog
        with ProgressDialog('Skin Variables', f'{get_localized(32053)}...\n{self.path}', total=1, logging=2, background=False):
            if not self.directory:
                return []
            return [j for j in (_make_item(i) for i in self.directory) if j]

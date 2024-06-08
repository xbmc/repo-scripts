from xbmc import getCondVisibility
from resources.lib.shortcuts.common import GetDirectoryCommon
from resources.lib.kodiutils import get_localized


class GetDirectoryGrouping(GetDirectoryCommon):
    def get_directory(self):
        if not self.path:
            return []
        try:
            self._directory = self.definitions[self.path]
        except KeyError:
            return []
        return self._directory

    def get_items(self):
        from xbmcgui import ListItem
        from jurialmunkey.parser import boolean
        from resources.lib.kodiutils import ProgressDialog

        def _make_item(i):
            if i.get('rule') and not getCondVisibility(i['rule']):
                return
            listitem = ListItem(label=i['name'], label2=i['path'], path=i['path'], offscreen=True)
            listitem.setArt({'icon': i['icon'], 'thumb': i['icon']})
            listitem_isfolder = True
            listitem_nodetype = i.get('node') or self.target or ''
            if boolean(i['link']):
                listitem_nodetype = 'link'
                listitem_isfolder = False
            listitem.setProperty('nodetype', listitem_nodetype)
            item = (i['path'], listitem, listitem_isfolder, )
            return item

        with ProgressDialog('Skin Variables', f'{get_localized(32053)}...\n{self.path}', total=1, logging=2, background=False):
            if not self.directory:
                return []
            items = []
            for i in self.directory:
                if not i:
                    continue
                if isinstance(i, dict):
                    j = _make_item(i)
                    items.append(j) if j else None
                    continue
                if '://' not in i:
                    continue
                DirectoryClass = GetDirectoryGrouping
                if not i.startswith('grouping://'):
                    from resources.lib.shortcuts.jsonrpc import GetDirectoryJSONRPC
                    DirectoryClass = GetDirectoryJSONRPC
                directory = DirectoryClass(i, definitions=self.definitions, target=self.target)
                new_items = directory.get_items() or []
                items += new_items
            return items

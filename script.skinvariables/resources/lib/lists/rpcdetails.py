# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmcgui import ListItem
from jurialmunkey.jsnrpc import get_jsonrpc
from jurialmunkey.litems import Container


JSON_RPC_LOOKUPS = {
    'addonid': {
        'method': "Addons.GetAddonDetails",
        'properties': [
            "name", "version", "summary", "description", "path", "author", "thumbnail", "disclaimer", "fanart",
            "dependencies", "broken", "extrainfo", "rating", "enabled", "installed", "deprecated"],
        'key': "addon",
    },
    'setid': {
        'method': "VideoLibrary.GetMovieSetDetails",
        'properties': ["title", "plot", "playcount", "fanart", "thumbnail", "art"],
        'key': "setdetails",
    },
    'movieid': {
        'method': "VideoLibrary.GetMovieDetails",
        'properties': ["title", "plot", "genre", "director", "writer", "studio", "cast", "country", "fanart", "thumbnail", "tag", "art", "ratings"],
        'key': "moviedetails",
    },
    'tvshowid': {
        'method': "VideoLibrary.GetTVShowDetails",
        'properties': ["title", "plot", "genre", "studio", "cast", "fanart", "thumbnail", "tag", "art", "ratings", "runtime"],
        'key': "tvshowdetails",
    },
    'seasonid': {
        'method': "VideoLibrary.GetSeasonDetails",
        'properties': ["title", "plot", "fanart", "thumbnail", "tvshowid", "art"],
        'key': "seasondetails",
    },
    'episodeid': {
        'method': "VideoLibrary.GetEpisodeDetails",
        'properties': ["title", "plot", "writer", "director", "cast", "fanart", "thumbnail", "tvshowid", "art", "seasonid", "ratings"],
        'key': "episodedetails",
    },
}


class ListGetItemDetails(Container):
    jrpc_method = ""
    jrpc_properties = []
    jrpc_id = ""
    jrpc_idtype = int
    jrpc_key = ""
    jrpc_sublookups = []

    @staticmethod
    def make_item(i, sub_lookups=None):
        try:
            label = i.get('label') or ''
        except AttributeError:
            return  # NoneType

        label2 = ''
        path = f'plugin://script.skinvariables/'
        sub_lookups = sub_lookups or []

        artwork = i.pop('art', {})
        artwork.setdefault('fanart', i.pop('fanart', ''))
        artwork.setdefault('thumb', i.pop('thumbnail', ''))

        def _iter_dict(d, prefix='', sub_lookups=False):
            ip = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    ip.update(_iter_dict(v, prefix=f'{prefix}{k}.', sub_lookups=sub_lookups))
                    continue
                if isinstance(v, list):
                    ip[f'{prefix}{k}.count'] = f'{len(v)}'
                    for x, j in enumerate(v):
                        if isinstance(j, dict):
                            ip.update(_iter_dict(j, prefix=f'{prefix}{k}.{x}.', sub_lookups=sub_lookups))
                            continue
                        ip[f'{prefix}{k}.{x}'] = f'{j}'
                    continue
                ip[f'{prefix}{k}'] = f'{v}'

                if not sub_lookups or k not in sub_lookups or k not in JSON_RPC_LOOKUPS:
                    continue

                try:
                    lookup = JSON_RPC_LOOKUPS[k]
                    method = lookup['method']
                    params = {k: int(v), "properties": lookup['properties']}
                    response = get_jsonrpc(method, params)
                    item = response['result'][lookup['key']] or {}
                    ip.update(_iter_dict(item, prefix=f'{prefix}item.', sub_lookups=False))
                except (KeyError, AttributeError):
                    pass

            return ip

        infoproperties = {}
        infoproperties.update(_iter_dict(i, sub_lookups=sub_lookups))
        infoproperties['isfolder'] = 'false'

        # kodi_log(f'ip {infoproperties}', 1)

        listitem = ListItem(label=label, label2=label2, path=path, offscreen=True)
        listitem.setProperties(infoproperties)
        listitem.setArt(artwork)

        return listitem

    def get_items(self, dbid, **kwargs):
        def _get_items():
            method = self.jrpc_method
            params = {
                self.jrpc_id: self.jrpc_idtype(dbid),
                "properties": self.jrpc_properties
            }
            response = get_jsonrpc(method, params) or {}
            item = response.get('result', {}).get(self.jrpc_key)

            return [self.make_item(item, self.jrpc_sublookups)]

        items = [
            (li.getPath(), li, li.getProperty('isfolder').lower() == 'true', )
            for li in _get_items() if li] if dbid else []

        return items

    def get_directory(self, dbid, **kwargs):
        items = self.get_items(dbid, **kwargs)
        self.add_items(items)


class ListGetAddonDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['addonid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['addonid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['addonid']['key']
    jrpc_id = "addonid"
    jrpc_idtype = str

    def get_directory(self, dbid, convert_path=False, **kwargs):
        if convert_path:
            if not dbid.startswith('plugin://'):
                return
            import re
            result = re.search('plugin://(.*)/', dbid)
            return result.group(1) if result else None

        items = self.get_items(dbid, **kwargs)
        self.add_items(items)


class ListGetMovieSetDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['setid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['setid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['setid']['key']
    jrpc_id = "setid"
    jrpc_sublookups = ["movieid"]


class ListGetMovieDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['movieid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['movieid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['movieid']['key']
    jrpc_id = "movieid"


class ListGetTVShowDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['tvshowid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['tvshowid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['tvshowid']['key']
    jrpc_id = "tvshowid"


class ListGetSeasonDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['seasonid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['seasonid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['seasonid']['key']
    jrpc_id = "seasonid"


class ListGetEpisodeDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['episodeid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['episodeid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['episodeid']['key']
    jrpc_id = "episodeid"

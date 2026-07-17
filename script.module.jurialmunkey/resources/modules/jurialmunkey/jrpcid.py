# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmcgui import ListItem
from jurialmunkey.jsnrpc import get_jsonrpc
from jurialmunkey.litems import ContainerDirectory, INFOLABEL_MAP
from infotagger.listitem import ListItemInfoTag


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
        'properties': [
            "title", "plot", "playcount",
            "fanart", "thumbnail", "art"],
        'key': "setdetails",
    },
    'movieid': {
        'method': "VideoLibrary.GetMovieDetails",
        'properties': [
            "file", "title", "plot", "playcount", "year", "trailer", "tagline", "originaltitle", "mpaa", "runtime", "set", "setid", "lastplayed", "premiered", "dateadded", "userrating", "rating", "votes", "top250",
            "genre", "director", "writer", "studio", "cast", "country",
            "fanart", "thumbnail", "art", "ratings", "uniqueid", "streamdetails"],
        'key': "moviedetails",
    },
    'tvshowid': {
        'method': "VideoLibrary.GetTVShowDetails",
        'properties': [
            "file", "title", "plot", "playcount", "year", "lastplayed", "premiered", "originaltitle", "watchedepisodes", "dateadded", "userrating", "rating", "votes", "mpaa", "season", "episode",
            "genre", "studio", "cast",
            "fanart", "thumbnail", "art", "ratings", "uniqueid"],
        'key': "tvshowdetails",
    },
    'seasonid': {
        'method': "VideoLibrary.GetSeasonDetails",
        'properties': [
            "title", "showtitle", "playcount", "watchedepisodes", "season", "episode",
            "tvshowid",
            "fanart", "thumbnail", "art"],
        'key': "seasondetails",
    },
    'episodeid': {
        'method': "VideoLibrary.GetEpisodeDetails",
        'properties': [
            "file", "showtitle", "title", "plot", "playcount", "firstaired", "runtime", "productioncode", "lastplayed", "dateadded", "season", "episode", "originaltitle", "userrating", "rating", "votes",
            "tvshowid", "seasonid",
            "writer", "director", "cast",
            "fanart", "thumbnail", "art", "ratings", "uniqueid", "streamdetails"],
        'key': "episodedetails",
    },
}


class ListItemMaker():
    def __init__(self, meta, dbid, dbtype, library=None, sublookups=None):
        self._meta = meta
        self._dbid = dbid
        self._dbtype = dbtype
        self._library = library
        self._sublookups = sublookups or []

    @property
    def meta(self):
        return self._meta

    @property
    def dbid(self):
        return self._dbid

    @property
    def dbtype(self):
        return self._dbtype

    @property
    def library(self):
        return self._library

    @property
    def sublookups(self):
        return self._sublookups

    @property
    def listitem(self):
        try:
            return self._listitem
        except AttributeError:
            self._listitem = ListItem(label=self.label, label2=self.label2, path=self.path, offscreen=True)
            return self._listitem

    @property
    def info_tag(self):
        try:
            return self._info_tag
        except AttributeError:
            self._info_tag = ListItemInfoTag(self.listitem, self.library)
            return self._info_tag

    @property
    def base_collector(self):
        try:
            return self._base_collector
        except AttributeError:
            self._base_collector = {}
            return self._base_collector

    @property
    def infolabels(self):
        try:
            return self._infolabels
        except AttributeError:
            self._infolabels = {}
            return self._infolabels

    @property
    def infoproperties(self):
        try:
            return self._infoproperties
        except AttributeError:
            self._infoproperties = {}
            return self._infoproperties

    @property
    def artwork(self):
        try:
            return self._artwork
        except AttributeError:
            self._artwork = {}
            return self._artwork

    @artwork.setter
    def artwork(self, value: dict):
        self._artwork = value

    @property
    def label(self):
        try:
            return self._label
        except AttributeError:
            self._label = ''
            return self._label

    @label.setter
    def label(self, value: str):
        self._label = value

    @property
    def label2(self):
        try:
            return self._label2
        except AttributeError:
            self._label2 = ''
            return self._label2

    @label2.setter
    def label2(self, value: str):
        self._label2 = value

    @property
    def path(self):
        try:
            return self._path
        except AttributeError:
            self._path = self.get_path()
            return self._path

    @path.setter
    def path(self, value: str):
        self._path = value

    def get_path(self):
        if self.dbtype == 'movie':
            return f'videodb://movies/titles/{self.dbid}'
        if self.dbtype == 'set':
            return f'videodb://movies/sets/{self.dbid}/'
        if self.dbtype == 'tvshow':
            return f'videodb://tvshows/titles/{self.dbid}/'
        if self.dbtype == 'season':
            return f'videodb://tvshows/titles/{self.meta.get("tvshowid")}/{self.meta.get("season")}/'
        if self.dbtype == 'episode':
            return f'videodb://tvshows/titles/{self.meta.get("tvshowid")}/{self.meta.get("season")}/{self.dbid}'
        return ''

    @staticmethod
    def format_key_value(k, v):
        if isinstance(v, float):
            return (
                (f'{k}', f'{v}', ),
                (f'{k}_integer', f'{int(v)}'),
                (f'{k}_percentage', f'{v / 10:.0%}'),  # Ratings stored out of 10
                (f'{k}_rounded', f'{v:.1f}'),
                (f'{k}_rounded_2dp', f'{v:.2f}'),
            )
        return ((k, f'{v}', ), )

    def iter_dict(self, d, prefix='', sub_lookups=False):
        ip = {}
        for k, v in d.items():

            if isinstance(v, dict):
                ip.update(self.iter_dict(v, prefix=f'{prefix}{k}.', sub_lookups=sub_lookups))
                continue

            if isinstance(v, list):
                ip[f'{prefix}{k}.count'] = f'{len(v)}'
                collector = {}
                for x, j in enumerate(v):
                    if isinstance(j, dict):
                        ip.update(self.iter_dict(j, prefix=f'{prefix}{k}.{x}.', sub_lookups=sub_lookups))
                        continue
                    for key, value in self.format_key_value(k, j):
                        ip[f'{prefix}{key}.{x}'] = f'{value}'
                        collector.setdefault(f'{prefix}{key}', set()).add(f'{value}')
                        self.base_collector.setdefault(f'{key}', set()).add(f'{value}')
                for key, value in collector.items():
                    ip[f'{key}.collection'] = ' / '.join(sorted(value))
                    ip[f'{key}.collection.count'] = f'{len(value)}'
                continue

            for key, value in self.format_key_value(k, v):
                ip[f'{prefix}{key}'] = f'{value}'
                self.base_collector.setdefault(f'{key}', set()).add(f'{value}')

            if not sub_lookups or k not in sub_lookups or k not in JSON_RPC_LOOKUPS:
                continue

            try:
                lookup = JSON_RPC_LOOKUPS[k]
                method = lookup['method']
                params = {k: int(v), "properties": lookup['properties']}
                response = get_jsonrpc(method, params)
                item = response['result'][lookup['key']] or {}
                ip.update(self.iter_dict(item, prefix=f'{prefix}item.'))
            except (KeyError, AttributeError):
                pass

        return ip

    def make_item(self):
        try:
            self.label = self.meta.get('label') or ''
        except AttributeError:
            return  # NoneType

        self.artwork = self.meta.get('art', {})
        self.artwork.setdefault('fanart', self.meta.get('fanart', ''))
        self.artwork.setdefault('thumb', self.meta.get('thumbnail', ''))

        self.infoproperties.update(self.iter_dict(self.meta, sub_lookups=self.sublookups))
        self.infoproperties['isfolder'] = 'true'

        for key, value in self.base_collector.items():
            self.infoproperties[f'{key}.collection'] = ' / '.join(sorted(value))
            self.infoproperties[f'{key}.collection.count'] = f'{len(value)}'

        if self.library == 'video':
            self.infolabels.update({INFOLABEL_MAP[k]: v for k, v in self.meta.items() if v and k in INFOLABEL_MAP and v != -1})
            self.infolabels['dbid'] = self.dbid
            self.infolabels['mediatype'] = self.dbtype
            self.info_tag.set_info(self.infolabels)
            self.info_tag.set_unique_ids(self.meta.get('uniqueid') or {})
            self.info_tag.set_stream_details(self.meta.get('streamdetails') or {})

        if self.dbtype in ('tvshow', 'season'):
            self.infoproperties['totalepisodes'] = int(self.infolabels.get('episode') or 0)
            self.infoproperties['unwatchedepisodes'] = int(self.infoproperties['totalepisodes']) - int(self.infoproperties.get('watchedepisodes') or 0)

        if self.dbtype == 'tvshow':
            self.infoproperties['totalseasons'] = int(self.infolabels.get('season') or 0)

        self.listitem.setProperties(self.infoproperties)
        self.listitem.setArt(self.artwork)

        return self.listitem


class ListGetItemDetails(ContainerDirectory):
    jrpc_method = ""
    jrpc_properties = []
    jrpc_id = ""
    jrpc_idtype = int
    jrpc_key = ""
    jrpc_sublookups = []
    item_dbtype = None
    item_library = None
    container_content = ''

    def get_items(self, dbid, **kwargs):
        def _get_items():
            method = self.jrpc_method
            params = {
                self.jrpc_id: self.jrpc_idtype(dbid),
                "properties": self.jrpc_properties
            }
            response = get_jsonrpc(method, params) or {}
            item = response.get('result', {}).get(self.jrpc_key)

            return [ListItemMaker(item, dbid, self.item_dbtype, self.item_library, self.jrpc_sublookups).make_item()]

        items = [
            (li.getPath(), li, li.getProperty('isfolder').lower() == 'true', )
            for li in _get_items() if li] if dbid else []

        return items

    def get_directory(self, dbid, **kwargs):
        items = self.get_items(dbid, **kwargs)
        self.add_items(items, container_content=self.container_content)


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
    item_dbtype = "set"
    item_library = "video"
    container_content = 'sets'


class ListGetMovieDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['movieid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['movieid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['movieid']['key']
    jrpc_id = "movieid"
    item_dbtype = "movie"
    item_library = "video"
    container_content = 'movies'


class ListGetTVShowDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['tvshowid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['tvshowid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['tvshowid']['key']
    jrpc_id = "tvshowid"
    item_dbtype = "tvshow"
    item_library = "video"
    container_content = 'tvshows'


class ListGetSeasonDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['seasonid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['seasonid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['seasonid']['key']
    jrpc_sublookups = ["tvshowid"]
    jrpc_id = "seasonid"
    item_dbtype = "season"
    item_library = "video"
    container_content = 'seasons'


class ListGetEpisodeDetails(ListGetItemDetails):
    jrpc_method = JSON_RPC_LOOKUPS['episodeid']['method']
    jrpc_properties = JSON_RPC_LOOKUPS['episodeid']['properties']
    jrpc_key = JSON_RPC_LOOKUPS['episodeid']['key']
    jrpc_sublookups = ["seasonid", "tvshowid"]
    jrpc_id = "episodeid"
    item_dbtype = "episode"
    item_library = "video"
    container_content = 'episodes'

# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmcgui import ListItem
from jurialmunkey.jsnrpc import get_jsonrpc
from jurialmunkey.litems import Container


PLAYERSTREAMS = {
    'audio': {'key': 'audiostreams', 'cur': 'currentaudiostream'},
    'subtitle': {'key': 'subtitles', 'cur': 'currentsubtitle'}
}


class ListGetPlayerStreams(Container):
    def get_directory(self, stream_type=None, **kwargs):

        def _get_items(stream_type):
            def make_item(i):
                label = i.get("language", "UND")
                label2 = i.get("name", "")
                path = f'plugin://script.skinvariables/?info=set_player_streams&stream_index={i.get("index")}&stream_type={stream_type}'
                infoproperties = {f'{k}': f'{v}' for k, v in i.items() if v}
                if cur_strm == i.get('index'):
                    infoproperties['iscurrent'] = 'true'
                infoproperties['isfolder'] = 'false'
                listitem = ListItem(label=label, label2=label2, path=path, offscreen=True)
                listitem.setProperties(infoproperties)
                return listitem

            ps_def = PLAYERSTREAMS.get(stream_type)
            if not ps_def:
                return []

            method = "Player.GetProperties"
            params = {"playerid": 1, "properties": [ps_def['key'], ps_def['cur']]}
            response = get_jsonrpc(method, params) or {}
            response = response.get('result', {})
            all_strm = response.get(ps_def['key']) or []
            if not all_strm:
                return []

            cur_strm = response.get(ps_def['cur'], {}).get('index', 0)
            return [make_item(i) for i in all_strm if i]

        if not stream_type:
            return

        items = [
            (li.getPath(), li, li.getProperty('isfolder').lower() == 'true', )
            for li in _get_items(stream_type) if li]

        self.add_items(items)


class ListSetPlayerStreams(Container):
    def get_directory(self, stream_type=None, stream_index=None, **kwargs):
        if not stream_type or stream_index is None:
            return
        if stream_type == 'audio':
            from resources.lib.method import set_player_audiostream
            set_player_audiostream(stream_index)
            return
        if stream_type == 'subtitle':
            from resources.lib.method import set_player_subtitle
            set_player_subtitle(stream_index)
            return

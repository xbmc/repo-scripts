# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

class Plugin():
    routes = {
        'get_player_streams': {
            'module_name': 'resources.lib.lists.playerstreams',
            'import_attr': 'ListGetPlayerStreams'},
        'set_player_streams': {
            'module_name': 'resources.lib.lists.playerstreams',
            'import_attr': 'ListSetPlayerStreams'},
        'get_dbitem_movieset_details': {
            'module_name': 'jurialmunkey.jrpcid',
            'import_attr': 'ListGetMovieSetDetails'},
        'get_dbitem_movie_details': {
            'module_name': 'jurialmunkey.jrpcid',
            'import_attr': 'ListGetMovieDetails'},
        'get_dbitem_tvshow_details': {
            'module_name': 'jurialmunkey.jrpcid',
            'import_attr': 'ListGetTVShowDetails'},
        'get_dbitem_season_details': {
            'module_name': 'jurialmunkey.jrpcid',
            'import_attr': 'ListGetSeasonDetails'},
        'get_dbitem_episode_details': {
            'module_name': 'jurialmunkey.jrpcid',
            'import_attr': 'ListGetEpisodeDetails'},
        'get_dbitem_addon_details': {
            'module_name': 'jurialmunkey.jrpcid',
            'import_attr': 'ListGetAddonDetails'},
        'get_number_sum': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetNumberSum'},
        'get_refresh_counter': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetRefreshCounter'},
        'get_split_string': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetSplitString'},
        'get_argb_colors': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetARGBColors'},
        'get_jsonrpc': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetJSONRPC'},
        'get_encoded_string': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetEncodedString'},
        'get_file_exists': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetFileExists'},
        'get_selected_item': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetSelectedItem'},
        'get_dotted_properties': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListGetDottedProperties'},
        'run_executebuiltin': {
            'module_name': 'resources.lib.lists.koditools',
            'import_attr': 'ListRunExecuteBuiltin'},
        'get_filter_files': {
            'module_name': 'resources.lib.lists.filterdir',
            'import_attr': 'ListGetFilterFiles'},
        'get_filter_dir': {
            'module_name': 'resources.lib.lists.filterdir',
            'import_attr': 'ListGetFilterDir'},
        'set_filter_dir': {
            'module_name': 'resources.lib.lists.filterdir',
            'import_attr': 'ListSetFilterDir'},
        'get_container_labels': {
            'module_name': 'resources.lib.lists.filterdir',
            'import_attr': 'ListGetContainerLabels'},
        'get_shortcuts_node': {
            'module_name': 'resources.lib.shortcuts.node',
            'import_attr': 'ListGetShortcutsNode'},
        'get_skin_user': {
            'module_name': 'resources.lib.lists.skinusers',
            'import_attr': 'ListGetSkinUser'},
        'add_skin_user': {
            'module_name': 'resources.lib.lists.skinusers',
            'import_attr': 'ListAddSkinUser'},
    }

    def __init__(self, handle, paramstring):
        # plugin:// params configuration
        self.handle = handle  # plugin:// handle
        self.parse_paramstring(paramstring)

    def parse_paramstring(self, paramstring):
        from jurialmunkey.parser import parse_paramstring
        self.paramstring, *secondary_params = paramstring.split('&&')  # plugin://plugin.video.themoviedb.helper?paramstring
        self.params = parse_paramstring(self.paramstring)  # paramstring dictionary
        self.decode_secondary_params(secondary_params)

    def decode_secondary_params(self, secondary_params):
        if not secondary_params:
            return

        from jurialmunkey.parser import boolean
        if boolean(self.params.get('unencoded_paths', 'false')):
            self.params['paths'] = secondary_params
            return

        from urllib.parse import unquote_plus
        self.params['paths'] = [unquote_plus(i) for i in secondary_params]

    def get_container(self, info):
        from jurialmunkey.modimp import importmodule
        return importmodule(**self.routes[info])

    def get_directory(self):
        container = self.get_container(self.params.get('info', 'get_filter_files'))(self.handle, self.paramstring, **self.params)
        return container.get_directory(**self.params)

    def run(self):
        if self.params.get('info') == 'get_params_file':
            from resources.lib.shortcuts.futils import read_meta_from_file
            path = self.params.get('path') or self.params.get('paths', [None])[0] or ''
            self.params = read_meta_from_file(path) if path else {}
        self.get_directory()

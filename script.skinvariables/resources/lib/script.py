# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from jurialmunkey.modimp import importmodule


class Script(object):
    def __init__(self, *args, paramstring=None):
        def map_args(arg):
            if '=' in arg:
                key, value = arg.split('=', 1)
                value = value.strip('\'').strip('"') if value else None
                return (key, value)
            return (arg, True)

        self.params = {}

        if paramstring:
            args = [i for i in args] + paramstring.split('&')

        for arg in args:
            k, v = map_args(arg)
            self.params[k] = v

    routing_table = {
        'set_animation':
            lambda **kwargs: importmodule('resources.lib.method', 'set_animation')(**kwargs),
        'set_slider':
            lambda **kwargs: importmodule('resources.lib.method', 'set_slider')(**kwargs),
        'run_executebuiltin':
            lambda **kwargs: importmodule('resources.lib.method', 'run_executebuiltin')(**kwargs),
        'run_dialog':
            lambda **kwargs: importmodule('resources.lib.method', 'run_dialog')(**kwargs),
        'run_progressdialog':
            lambda **kwargs: importmodule('resources.lib.method', 'run_progressdialog')(**kwargs),
        'set_player_subtitle':
            lambda **kwargs: importmodule('resources.lib.method', 'set_player_subtitle')(**kwargs),
        'set_player_audiostream':
            lambda **kwargs: importmodule('resources.lib.method', 'set_player_audiostream')(**kwargs),
        'set_editcontrol':
            lambda **kwargs: importmodule('resources.lib.method', 'set_editcontrol')(**kwargs),
        'set_dbid_tag':
            lambda **kwargs: importmodule('resources.lib.method', 'set_dbid_tag')(**kwargs),
        'get_jsonrpc':
            lambda **kwargs: importmodule('resources.lib.method', 'get_jsonrpc')(**kwargs),
        'add_skinstring_history':
            lambda **kwargs: importmodule('resources.lib.method', 'add_skinstring_history')(**kwargs),
        'set_shortcut':
            lambda **kwargs: importmodule('resources.lib.shortcuts.method', 'set_shortcut')(**kwargs),
        'copy_menufile':
            lambda **kwargs: importmodule('resources.lib.shortcuts.method', 'copy_menufile')(**kwargs),
        'copy_menufolder':
            lambda **kwargs: importmodule('resources.lib.shortcuts.method', 'copy_menufolder')(**kwargs),
        'set_listitem_to_menunode':
            lambda **kwargs: importmodule('resources.lib.shortcuts.method', 'set_listitem_to_menunode')(**kwargs),
        'add_skinshortcut':
            lambda **kwargs: importmodule('resources.lib.shortcuts.skinshortcuts', 'get_skinshortcuts_menu')(route='add_skinshortcut', **kwargs),
        'del_skinshortcut':
            lambda **kwargs: importmodule('resources.lib.shortcuts.skinshortcuts', 'get_skinshortcuts_menu')(route='del_skinshortcut', **kwargs),
        'mod_skinshortcut':
            lambda **kwargs: importmodule('resources.lib.shortcuts.skinshortcuts', 'get_skinshortcuts_menu')(route='mod_skinshortcut', **kwargs),
        'imp_skinshortcut':
            lambda **kwargs: importmodule('resources.lib.shortcuts.skinshortcuts', 'get_skinshortcuts_menu')(route='imp_skinshortcut', **kwargs),
        'mov_skinshortcut':
            lambda **kwargs: importmodule('resources.lib.shortcuts.skinshortcuts', 'get_skinshortcuts_menu')(route='mov_skinshortcut', **kwargs),
    }

    def run(self):
        if not self.params:
            return
        routes_available, params_given = set(self.routing_table.keys()), set(self.params.keys())
        try:
            route_taken = set.intersection(routes_available, params_given).pop()
        except KeyError:
            return self.router()
        return self.routing_table[route_taken](**self.params)

    def router(self):
        if self.params.get('action') == 'buildviews':
            from resources.lib.viewtypes import ViewTypes
            return ViewTypes().update_xml(skinfolder=self.params.get('folder'), **self.params)

        if self.params.get('action') == 'buildtemplate':
            from resources.lib.shortcuts.template import ShortcutsTemplate
            return ShortcutsTemplate(template=self.params.get('template')).update_xml(**self.params)

        from resources.lib.skinvariables import SkinVariables
        return SkinVariables(template=self.params.get('template'), skinfolder=self.params.get('folder')).update_xml(**self.params)

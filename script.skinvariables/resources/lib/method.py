# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import jurialmunkey.futils
import jurialmunkey.parser
ADDONDATA = 'special://profile/addon_data/script.skinvariables/'


class FileUtils(jurialmunkey.futils.FileUtils):
    addondata = ADDONDATA   # Override module addon_data with plugin addon_data


boolean = jurialmunkey.parser.boolean
parse_localize = jurialmunkey.parser.parse_localize


def set_animation_list(animations):
    import xbmcgui
    win_id = xbmcgui.getCurrentWindowId()
    window = xbmcgui.Window(win_id)
    for control_id, event, effect in animations:
        control = window.getControl(int(control_id))
        control.setAnimations([(event, effect,)])


def set_animation(set_animation, **kwargs):
    set_animation_list([
        (control_id, event, effect,)
        for i in set_animation.split('||')
        for control_id, event, effect in i.split('|')
    ])


def set_slider(window_id, control_id, value):
    import xbmcgui
    win = xbmcgui.Window(int(window_id))
    con = win.getControl(int(control_id))
    con.setPercent(int(value))


def run_executebuiltin_list(builtins):
    import xbmc
    for builtin in builtins:
        if builtin.startswith('sleep='):
            xbmc.Monitor().waitForAbort(float(builtin[6:]))
            continue
        if builtin.startswith('route='):
            from resources.lib.script import Script
            Script(paramstring=builtin[6:]).run()
            continue
        if builtin.startswith('animation='):
            animation = builtin[10:]
            control_id, event, effect = animation.split('|')
            set_animation_list([(control_id, event, effect, )])
            continue
        xbmc.executebuiltin(builtin)


def run_executebuiltin(run_executebuiltin=None, use_rules=False, **kwargs):
    if not run_executebuiltin:
        return
    if not boolean(use_rules):
        return run_executebuiltin_list(run_executebuiltin.split('||'))

    from json import loads
    from jurialmunkey.futils import load_filecontent
    from resources.lib.operations import RuleOperations

    try:
        meta = loads(str(load_filecontent(run_executebuiltin)))
    except Exception:
        raise Exception(f'Unable to load {run_executebuiltin} !')

    rule_operations = RuleOperations(meta, **kwargs)
    actions_list = rule_operations.get_actions_list(rule_operations.meta['actions'])
    return run_executebuiltin_list(actions_list)


def get_paramstring_tuplepairs(paramstring):
    if not paramstring:
        return []
    return [tuple(i.split(';')) for i in paramstring.split(';;')]


def executebuiltin(executebuiltin='', index=None, values=None, **kwargs):
    if index == -1 or index is False:
        return

    if isinstance(index, int):
        executebuiltin = kwargs.get(f'executebuiltin_{index}') or executebuiltin
        value = values[index] if values else index
    else:
        value = index

    if not executebuiltin:
        return

    run_executebuiltin_list([builtin.format(x=index, v=value) for builtin in executebuiltin.split('||')])


def run_progressdialog(run_progressdialog, background=False, heading='', message='', polling='0.1', message_info='', progress_info='', timeout='200', max_value='100', **kwargs):
    import xbmc
    import xbmcgui

    func = xbmcgui.DialogProgressBG if boolean(background) else xbmcgui.DialogProgress
    dialog = func()

    polling = float(polling)
    timeout = int(timeout)
    max_value = int(max_value)

    monitor = xbmc.Monitor()
    dialog.create(heading, message)

    x = 0
    while x < max_value and timeout > 0 and not monitor.abortRequested():
        x += 1
        timeout -= 1
        if progress_info:
            x = int(xbmc.getInfoLabel(progress_info) or 0)
        if message_info:
            message = str(xbmc.getInfoLabel(message_info) or '')
        progress = int((x / max_value) * 100)
        dialog.update(progress, message=message)
        monitor.waitForAbort(polling)
    dialog.close()
    del dialog
    del monitor


class DialogSelectPreselectedItems():

    empty = -1

    def __init__(self, preselected_values, list_items):
        self.preselected_values = preselected_values
        self.list_items = list_items

    def get_preselected_value(self, value):
        try:
            return int(value)
        except TypeError:
            return
        except ValueError:
            pass

        from contextlib import suppress
        with suppress(ValueError):
            return self.list_items.index(value)

    def get_preselected_output(self):
        preselected_index = self.get_preselected_value(self.preselected_values[0])
        if preselected_index is None:
            return self.empty
        return preselected_index

    @property
    def preselected_items(self):
        if not self.preselected_values:  # Skinner has not specified a preselected value
            return self.empty

        if not self.list_items or len(self.list_items) == 0:  # List has no list_items so we dont preselect anything
            return self.empty

        return self.get_preselected_output()


class DialogMultiSelectPreselectedItems(DialogSelectPreselectedItems):

    empty = (-1, )

    def get_preselected_output(self):
        preselected_indicies = [j for j in (self.get_preselected_value(i) for i in self.preselected_values) if j is not None]
        if not preselected_indicies:
            return self.empty
        return preselected_indicies


def run_dialog(run_dialog, separator=' / ', **kwargs):
    import xbmcgui

    def _split_items(items):
        return items.split(separator)

    def _get_path_or_str(string):
        if not boolean(kwargs.get('load_file')):
            return str(string)
        from jurialmunkey.futils import load_filecontent
        return str(load_filecontent(string))

    def _get_dialog_select_preselected_items(string):
        list_items = _split_items(kwargs.get('list') or '')
        preselected_values = _split_items(string or '')
        return DialogSelectPreselectedItems(preselected_values, list_items).preselected_items

    def _get_dialog_multiselect_preselected_items(string):
        list_items = _split_items(kwargs.get('options') or '')
        preselected_values = _split_items(string or '')
        return DialogMultiSelectPreselectedItems(preselected_values, list_items).preselected_items

    dialog = xbmcgui.Dialog()

    dialog_standard_routes = {
        'ok': {
            'func': dialog.ok,
            'params': (
                ('heading', str, ''), ('message', _get_path_or_str, ''), )
        },
        'yesno': {
            'func': dialog.yesno,
            'params': (
                ('heading', str, ''), ('message', _get_path_or_str, ''), ('nolabel', str, 'No'), ('yeslabel', str, 'Yes'),
                ('defaultbutton', int, xbmcgui.DLG_YESNO_YES_BTN), ('autoclose', int, 0), )
        },
        'yesnocustom': {
            'func': dialog.yesnocustom,
            'params': (
                ('heading', str, ''), ('message', _get_path_or_str, ''), ('nolabel', str, 'No'), ('yeslabel', str, 'Yes'), ('customlabel', str, 'Custom'),
                ('defaultbutton', int, xbmcgui.DLG_YESNO_YES_BTN), ('autoclose', int, 0), )
        },
        'textviewer': {
            'func': dialog.textviewer,
            'params': (
                ('heading', str, ''), ('text', _get_path_or_str, ''),
                ('usemono', boolean, True), )
        },
        'notification': {
            'func': dialog.notification,
            'params': (
                ('heading', str, ''), ('message', str, ''), ('icon', str, ''),
                ('time', int, 5000), ('sound', boolean, True), )
        },
        'numeric': {
            'func': dialog.numeric,
            'params': (
                ('heading', str, ''), ('defaultt', str, ''),
                ('type', int, 0), ('bHiddenInput', boolean, False), )
        },
        'input': {
            'func': dialog.input,
            'params': (
                ('heading', str, ''), ('defaultt', str, ''),
                ('type', int, xbmcgui.INPUT_ALPHANUM), ('option', int, 0), ('autoclose', int, 0), )
        },
        'browse': {
            'func': dialog.browse,
            'params': (
                ('heading', str, ''), ('shares', str, ''), ('mask', str, ''), ('defaultt', str, ''),
                ('type', int, 0), ('useThumbs', boolean, True), ('treatAsFolder', boolean, True), ('enableMultiple', boolean, True), )
        },
        'colorpicker': {
            'func': dialog.colorpicker,
            'params': (
                ('heading', str, ''), ('selectedcolor', str, ''), ('colorfile', str, ''), )
        },
        'contextmenu': {
            'func': dialog.contextmenu,
            'params': (
                ('list', _split_items, ''), )
        },
        'select': {
            'func': dialog.select,
            'params': (
                ('heading', str, ''),
                ('list', _split_items, ''),
                ('autoclose', int, 0), ('preselect', _get_dialog_select_preselected_items, None), ('useDetails', boolean, False), ),
            'values': 'list'
        },
        'multiselect': {
            'func': dialog.multiselect,
            'params': (
                ('heading', str, ''),
                ('options', _split_items, ''),
                ('autoclose', int, 0), ('preselect', _get_dialog_multiselect_preselected_items, None), ('useDetails', boolean, False), ),
            'values': 'options'
        },
    }

    route = dialog_standard_routes[run_dialog]
    params = {k: func(kwargs.get(k) or fallback) for k, func, fallback in route['params']}
    output = route['func'](**params)
    values = params.get(route.get('values'))
    if not isinstance(output, (tuple, list)):
        output = (output, )
    for x in output:
        executebuiltin(index=x, values=values, **kwargs)


def set_player_subtitle(set_player_subtitle, reload_property='UID', **kwargs):
    import time
    import xbmc
    from jurialmunkey.jsnrpc import get_jsonrpc
    from jurialmunkey.parser import try_int
    method = "Player.SetSubtitle"
    params = {"playerid": 1, "subtitle": try_int(set_player_subtitle), "enable": True}
    get_jsonrpc(method, params)
    xbmc.executebuiltin(f'SetProperty({reload_property},{time.time()})')


def set_player_audiostream(set_player_audiostream, reload_property='UID', **kwargs):
    import time
    import xbmc
    from jurialmunkey.jsnrpc import get_jsonrpc
    from jurialmunkey.parser import try_int
    method = "Player.SetAudioStream"
    params = {"playerid": 1, "stream": try_int(set_player_audiostream)}
    get_jsonrpc(method, params)
    xbmc.executebuiltin(f'SetProperty({reload_property},{time.time()})')


def set_editcontrol(set_editcontrol, text=None, window_id=None, setfocus=None, setfocus_wait='00:00', **kwargs):
    import xbmc
    from jurialmunkey.jsnrpc import get_jsonrpc
    xbmc.executebuiltin(f'SetFocus({set_editcontrol})')
    get_jsonrpc("Input.SendText", {"text": text or '', "done": True})
    xbmc.executebuiltin(f'AlarmClock(Refocus,SetFocus({setfocus}),{setfocus_wait},silent)') if setfocus else None


def add_skinstring_history(add_skinstring_history, value, separator='|', use_window_prop=False, window_id='', toggle=False, **kwargs):
    import xbmc

    def _get_info_str() -> str:
        if not use_window_prop:
            return 'Skin.String({})'
        if window_id:
            return f'Window({window_id}).Property({{}})'
        return 'Window.Property({})'

    values = xbmc.getInfoLabel(_get_info_str().format(add_skinstring_history)) or ''
    values = values.split(separator)
    if not values:
        return
    try:
        values.remove(value)
        remove = True
    except ValueError:
        remove = False
    if not toggle or not remove:
        values.insert(0, value)

    def _get_exec_str() -> str:
        if not use_window_prop:
            return 'Skin.SetString({},{})'
        if window_id:
            return f'SetProperty({{}},{{}},{window_id})'
        return 'SetProperty({},{})'

    xbmc.executebuiltin(_get_exec_str().format(add_skinstring_history, separator.join(filter(None, values))))


def set_dbid_tag(set_dbid_tag, dbtype, dbid, **kwargs):
    from jurialmunkey.jsnrpc import set_tags
    set_tags(int(dbid), dbtype, [set_dbid_tag])


def get_jsonrpc(get_jsonrpc, textviewer=False, filewrite=True, **kwargs):
    from jurialmunkey.jsnrpc import get_jsonrpc as _get_jsonrpc
    result = _get_jsonrpc(get_jsonrpc, kwargs)

    if textviewer:
        from xbmcgui import Dialog
        Dialog().textviewer(f'GET {get_jsonrpc}', f'PARAMS\n{kwargs}\n\nRESULT\n{result}')

    if filewrite:
        filename = '_'.join([f'{k}-{v}' for k, v in kwargs.items()])
        filename = jurialmunkey.futils.validify_filename(f'{get_jsonrpc}_{filename}.json')
        FileUtils().dumps_to_file({'method': get_jsonrpc, 'params': kwargs, 'result': result}, 'log_request', filename)

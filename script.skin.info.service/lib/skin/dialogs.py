"""Dialog utilities for skin RunScript integration."""
from __future__ import annotations

import xbmc
import xbmcgui

from lib.kodi.client import log, ADDON
from lib.kodi.utilities import (
    resolve_infolabel as _resolve_infolabel,
    parse_pipe_list as _parse_list,
)
from lib.infrastructure.dialogs import DialogProgress

TEST_DEFAULTS = {
    'heading': 'Test Dialog',
    'message': 'This is a test message for skinning purposes.',
    'text': ('This is test text content.\nLine 2\nLine 3\n'
             'You can test the scrolling and appearance of the text viewer dialog.'),
    'items': 'Option 1|Option 2|Option 3|Option 4|Option 5',
    'nolabel': 'No',
    'yeslabel': 'Yes',
    'customlabel': 'Custom',
}


def _parse_bool(value: str, default: bool = False) -> bool:
    """Parse boolean string parameter."""
    if value is None or value == '':
        return default
    return str(value).lower() in ('true', '1', 'yes')


def _parse_int(value: str, default: int = 0) -> int:
    """Parse integer string parameter."""
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default


def _execute_builtin_list(builtins: str) -> None:
    """Execute pipe-separated list of builtins."""
    if not builtins:
        return
    for builtin in _parse_list(builtins, '|'):
        if builtin:
            log('Dialogs', f"Executing builtin: {builtin}", xbmc.LOGDEBUG)
            xbmc.executebuiltin(builtin)


def _format_template(template: str, index: int, value: str) -> str:
    """Format template string with {index}/{value} or {x}/{v} placeholders."""
    if not template:
        return ''
    return template.format(index=index, value=value, x=index, v=value)


def _clear_dialog_properties(window: str = 'home') -> None:
    """Clear all Dialog.N.* properties used in property mode."""
    for i in range(1, 100):
        xbmc.executebuiltin(f'ClearProperty(Dialog.{i}.Label,{window})')
        xbmc.executebuiltin(f'ClearProperty(Dialog.{i}.Label2,{window})')
        xbmc.executebuiltin(f'ClearProperty(Dialog.{i}.Icon,{window})')
        xbmc.executebuiltin(f'ClearProperty(Dialog.{i}.Builtin,{window})')


def _show_error(message: str) -> None:
    """Show error notification for invalid dialog parameters."""
    xbmcgui.Dialog().notification(
        ADDON.getLocalizedString(32561), message, xbmcgui.NOTIFICATION_ERROR, 5000
    )


def _read_property_mode_items(window: str = 'home') -> tuple:
    """Read `Dialog.N.{Label,Icon,Label2,Builtin}` window props; return `(listitems, builtins)`."""
    listitems = []
    builtins = []

    for i in range(1, 100):
        label = xbmc.getInfoLabel(f'Window({window}).Property(Dialog.{i}.Label)')

        if not label:
            break

        if label in ('none', '-'):
            continue

        label2 = xbmc.getInfoLabel(f'Window({window}).Property(Dialog.{i}.Label2)')
        icon = xbmc.getInfoLabel(f'Window({window}).Property(Dialog.{i}.Icon)')
        builtin = xbmc.getInfoLabel(f'Window({window}).Property(Dialog.{i}.Builtin)')

        listitem = xbmcgui.ListItem(label=label, label2=label2, offscreen=True)
        listitem.setArt({'icon': icon})

        listitems.append(listitem)
        builtins.append(builtin if builtin else None)

    return listitems, builtins


def dialog_yesno(
    heading: str = '',
    message: str = '',
    yesaction: str = '',
    noaction: str = '',
    cancel_action: str = '',
    yeslabel: str = '',
    nolabel: str = '',
    autoclose: str = '',
    **kwargs
) -> None:
    """Show Yes/No dialog. `yesaction`/`noaction`/`cancel_action` are pipe-separated builtins."""
    heading = _resolve_infolabel(heading) or TEST_DEFAULTS['heading']
    message = _resolve_infolabel(message) or TEST_DEFAULTS['message']
    yeslabel = yeslabel or TEST_DEFAULTS['yeslabel']
    nolabel = nolabel or TEST_DEFAULTS['nolabel']
    autoclose_ms = _parse_int(autoclose, 0)

    log('Dialogs', f"dialog_yesno: heading='{heading}', autoclose={autoclose_ms}", xbmc.LOGDEBUG)

    result = xbmcgui.Dialog().yesno(
        heading,
        message,
        nolabel=nolabel,
        yeslabel=yeslabel,
        autoclose=autoclose_ms
    )

    if result:
        log('Dialogs', "dialog_yesno: User selected Yes", xbmc.LOGDEBUG)
        _execute_builtin_list(yesaction)
    else:
        if autoclose_ms > 0:
            log('Dialogs', "dialog_yesno: Dialog auto-closed or cancelled", xbmc.LOGDEBUG)
            _execute_builtin_list(cancel_action)
        else:
            log('Dialogs', "dialog_yesno: User selected No", xbmc.LOGDEBUG)
            _execute_builtin_list(noaction)


def dialog_yesnocustom(
    heading: str = '',
    message: str = '',
    yesaction: str = '',
    noaction: str = '',
    customaction: str = '',
    cancel_action: str = '',
    yeslabel: str = '',
    nolabel: str = '',
    customlabel: str = '',
    autoclose: str = '',
    **kwargs
) -> None:
    """Show a Yes/No/Custom 3-button dialog. `*action` args are pipe-separated builtins."""
    heading = _resolve_infolabel(heading) or TEST_DEFAULTS['heading']
    message = _resolve_infolabel(message) or TEST_DEFAULTS['message']
    yeslabel = yeslabel or TEST_DEFAULTS['yeslabel']
    nolabel = nolabel or TEST_DEFAULTS['nolabel']
    customlabel = customlabel or TEST_DEFAULTS['customlabel']
    autoclose_ms = _parse_int(autoclose, 0)

    result = xbmcgui.Dialog().yesnocustom(
        heading,
        message,
        customlabel=customlabel,
        nolabel=nolabel,
        yeslabel=yeslabel,
        autoclose=autoclose_ms
    )

    if result == 1:
        _execute_builtin_list(yesaction)
    elif result == 0:
        _execute_builtin_list(noaction)
    elif result == 2:
        _execute_builtin_list(customaction)
    else:
        _execute_builtin_list(cancel_action)


def dialog_ok(heading: str = '', message: str = '', okaction: str = '', **kwargs) -> None:
    """Show an OK dialog. `okaction` is pipe-separated builtins to run."""
    heading = _resolve_infolabel(heading) or TEST_DEFAULTS['heading']
    message = _resolve_infolabel(message) or TEST_DEFAULTS['message']

    xbmcgui.Dialog().ok(heading, message)
    _execute_builtin_list(okaction)


def dialog_select(
    heading: str = '',
    items: str = '',
    separator: str = '|',
    executebuiltin: str = '',
    cancel_action: str = '',
    preselect: str = '',
    usedetails: str = 'false',
    autoclose: str = '',
    window: str = 'home',
    **kwargs
) -> None:
    """Show a single-select dialog.

    `items="properties"` reads from `Dialog.N.Label` window props; otherwise parse `items`
    on `separator`. `executebuiltin` template uses `{index}`/`{value}` placeholders; per-index
    overrides via `executebuiltin_N` kwargs.
    """
    heading = _resolve_infolabel(heading) or TEST_DEFAULTS['heading']
    autoclose_ms = _parse_int(autoclose, 0)
    use_details = _parse_bool(usedetails, False)

    is_property_mode = items == 'properties'
    item_list = []

    if is_property_mode:
        listitems, property_builtins = _read_property_mode_items(window)
        if not listitems:
            _show_error('Property mode requires Dialog.N.Label properties')
            return
    else:
        items_resolved = _resolve_infolabel(items) or TEST_DEFAULTS['items']
        item_list = _parse_list(items_resolved, separator)
        if not item_list:
            _show_error('Select dialog requires items parameter')
            return
        listitems = item_list
        property_builtins = None

    preselect_index = _parse_int(preselect, -1)
    if preselect_index < 0 and preselect and not is_property_mode and item_list:
        try:
            preselect_index = item_list.index(preselect)
        except (ValueError, NameError):
            preselect_index = -1

    log('Dialogs',
        f"dialog_select: heading='{heading}', items={len(listitems)}, "
        f"property_mode={is_property_mode}", xbmc.LOGDEBUG)

    result = xbmcgui.Dialog().select(
        heading,
        listitems,
        autoclose=autoclose_ms,
        preselect=preselect_index,
        useDetails=use_details
    )

    if is_property_mode:
        _clear_dialog_properties(window)

    if result < 0:
        log('Dialogs', "dialog_select: User cancelled", xbmc.LOGDEBUG)
        _execute_builtin_list(cancel_action)
        return

    log('Dialogs', f"dialog_select: User selected index {result}", xbmc.LOGDEBUG)

    if is_property_mode and property_builtins and property_builtins[result]:
        _execute_builtin_list(property_builtins[result])
        return

    index_specific_key = f'executebuiltin_{result}'
    if index_specific_key in kwargs and kwargs[index_specific_key]:
        _execute_builtin_list(kwargs[index_specific_key])
        return

    if executebuiltin:
        value = listitems[result].getLabel() if is_property_mode else listitems[result]
        formatted = _format_template(executebuiltin, result, value)
        _execute_builtin_list(formatted)


def dialog_multiselect(
    heading: str = '',
    items: str = '',
    separator: str = '|',
    executebuiltin: str = '',
    cancel_action: str = '',
    preselect: str = '',
    usedetails: str = 'false',
    autoclose: str = '',
    window: str = 'home',
    **kwargs
) -> None:
    """Show multiselect dialog. `executebuiltin` runs per selected item with `{index}`/`{value}`."""
    heading = _resolve_infolabel(heading) or TEST_DEFAULTS['heading']
    autoclose_ms = _parse_int(autoclose, 0)
    use_details = _parse_bool(usedetails, False)

    is_property_mode = items == 'properties'
    item_list = []

    if is_property_mode:
        listitems, _ = _read_property_mode_items(window)
        if not listitems:
            _show_error('Property mode requires Dialog.N.Label properties')
            return
    else:
        items_resolved = _resolve_infolabel(items) or TEST_DEFAULTS['items']
        item_list = _parse_list(items_resolved, separator)
        if not item_list:
            _show_error('Multiselect dialog requires items parameter')
            return
        listitems = item_list

    preselect_list = []
    if preselect:
        preselect_parts = _parse_list(preselect, separator)
        for part in preselect_parts:
            idx = _parse_int(part, -1)
            if idx >= 0:
                preselect_list.append(idx)
            elif not is_property_mode and item_list:
                try:
                    idx = item_list.index(part)
                    preselect_list.append(idx)
                except (ValueError, NameError):
                    pass

    log('Dialogs',
        f"dialog_multiselect: heading='{heading}', items={len(listitems)}, "
        f"property_mode={is_property_mode}", xbmc.LOGDEBUG)

    results = xbmcgui.Dialog().multiselect(
        heading,
        listitems,
        autoclose=autoclose_ms,
        preselect=preselect_list,
        useDetails=use_details
    )

    if is_property_mode:
        _clear_dialog_properties(window)

    if results is None:
        log('Dialogs', "dialog_multiselect: User cancelled", xbmc.LOGDEBUG)
        _execute_builtin_list(cancel_action)
        return

    log('Dialogs', f"dialog_multiselect: User selected {len(results)} items", xbmc.LOGDEBUG)

    for result_idx in results:
        value = listitems[result_idx].getLabel() if is_property_mode else listitems[result_idx]
        if executebuiltin:
            formatted = _format_template(executebuiltin, result_idx, value)
            _execute_builtin_list(formatted)


def dialog_contextmenu(
    items: str = '',
    separator: str = '|',
    executebuiltin: str = '',
    cancel_action: str = '',
    **kwargs
) -> None:
    """Show a context-menu popup. Per-index actions via `executebuiltin_N` kwargs."""
    items_resolved = _resolve_infolabel(items) or TEST_DEFAULTS['items']
    item_list = _parse_list(items_resolved, separator)

    if not item_list:
        _show_error('Context menu requires items parameter')
        return

    log('Dialogs', f"dialog_contextmenu: items={len(item_list)}", xbmc.LOGDEBUG)

    result = xbmcgui.Dialog().contextmenu(item_list)

    if result < 0:
        log('Dialogs', "dialog_contextmenu: User cancelled", xbmc.LOGDEBUG)
        _execute_builtin_list(cancel_action)
        return

    log('Dialogs', f"dialog_contextmenu: User selected index {result}", xbmc.LOGDEBUG)

    index_specific_key = f'executebuiltin_{result}'
    if index_specific_key in kwargs and kwargs[index_specific_key]:
        _execute_builtin_list(kwargs[index_specific_key])
        return

    if executebuiltin:
        formatted = _format_template(executebuiltin, result, item_list[result])
        _execute_builtin_list(formatted)


def dialog_input(
    heading: str = '',
    type: str = 'alphanum',
    default: str = '',
    hidden: str = 'false',
    doneaction: str = '',
    cancel_action: str = '',
    autoclose: str = '',
    **kwargs
) -> None:
    """`type` input (alphanum/numeric/date/time/ipaddress/password); `doneaction` subs `{value}`."""
    heading = _resolve_infolabel(heading) or TEST_DEFAULTS['heading']
    default = _resolve_infolabel(default)
    is_hidden = _parse_bool(hidden, False)
    autoclose_ms = _parse_int(autoclose, 0)

    type_map = {
        'alphanum': xbmcgui.INPUT_ALPHANUM,
        'numeric': xbmcgui.INPUT_NUMERIC,
        'date': xbmcgui.INPUT_DATE,
        'time': xbmcgui.INPUT_TIME,
        'ipaddress': xbmcgui.INPUT_IPADDRESS,
        'password': xbmcgui.INPUT_PASSWORD,
    }

    input_type = type_map.get(type.lower(), xbmcgui.INPUT_ALPHANUM)
    option = (xbmcgui.ALPHANUM_HIDE_INPUT
              if (input_type == xbmcgui.INPUT_ALPHANUM and is_hidden) else 0)

    log('Dialogs',
        f"dialog_input: heading='{heading}', type={type}, hidden={is_hidden}", xbmc.LOGDEBUG)

    result = xbmcgui.Dialog().input(
        heading,
        defaultt=default,
        type=input_type,
        option=option,
        autoclose=autoclose_ms
    )

    if not result:
        log('Dialogs', "dialog_input: User cancelled or empty input", xbmc.LOGDEBUG)
        _execute_builtin_list(cancel_action)
        return

    log('Dialogs', f"dialog_input: User entered value (length={len(result)})", xbmc.LOGDEBUG)
    if doneaction:
        formatted = _format_template(doneaction, 0, result)
        _execute_builtin_list(formatted)


def dialog_numeric(
    heading: str = '',
    type: str = '0',
    default: str = '',
    hidden: str = 'false',
    doneaction: str = '',
    cancel_action: str = '',
    **kwargs
) -> None:
    """Show numeric input. `type` is 0=number/1=date/2=time/3=ipaddress/4=password."""
    heading = _resolve_infolabel(heading) or TEST_DEFAULTS['heading']
    default = _resolve_infolabel(default)
    numeric_type = _parse_int(type, 0)
    is_hidden = _parse_bool(hidden, False)

    result = xbmcgui.Dialog().numeric(
        numeric_type,
        heading,
        defaultt=default,
        bHiddenInput=is_hidden
    )

    if not result:
        _execute_builtin_list(cancel_action)
        return

    if doneaction:
        formatted = _format_template(doneaction, 0, result)
        _execute_builtin_list(formatted)


def dialog_textviewer(
    heading: str = '',
    text: str = '',
    file: str = '',
    usemono: str = 'false',
    **kwargs
) -> None:
    """Show a textviewer dialog. `file` (if given) takes priority over `text`."""
    import xbmcvfs

    heading = _resolve_infolabel(heading) or TEST_DEFAULTS['heading']
    use_mono = _parse_bool(usemono, False)

    if file:
        file_path = _resolve_infolabel(file)
        try:
            if not xbmcvfs.exists(file_path):
                xbmcgui.Dialog().ok(xbmc.getLocalizedString(257),
                                    ADDON.getLocalizedString(32562).format(file_path))
                log('Dialogs', f"textviewer: File not found '{file_path}'", xbmc.LOGERROR)
                return
            with xbmcvfs.File(file_path, 'r') as f:
                content = f.read()
            xbmcgui.Dialog().textviewer(heading, content, usemono=use_mono)
        except Exception as e:
            xbmcgui.Dialog().ok(xbmc.getLocalizedString(257),
                                ADDON.getLocalizedString(32563).format(str(e)))
            log('Dialogs', f"textviewer: Error reading file '{file_path}': {str(e)}", xbmc.LOGERROR)
    else:
        text = _resolve_infolabel(text) or TEST_DEFAULTS['text']
        xbmcgui.Dialog().textviewer(heading, text, usemono=use_mono)


def dialog_notification(
    heading: str = '',
    message: str = '',
    icon: str = 'info',
    time: str = '5000',
    sound: str = 'true',
    **kwargs
) -> None:
    """Show a toast notification. `icon` accepts `info`/`warning`/`error` or a custom image path."""
    heading = _resolve_infolabel(heading) or 'Test'
    message = _resolve_infolabel(message) or 'Notification'
    icon_resolved = _resolve_infolabel(icon)
    time_ms = _parse_int(time, 5000)
    play_sound = _parse_bool(sound, True)

    icon_map = {
        'info': xbmcgui.NOTIFICATION_INFO,
        'warning': xbmcgui.NOTIFICATION_WARNING,
        'error': xbmcgui.NOTIFICATION_ERROR,
    }

    icon_value = icon_map.get(icon_resolved.lower(), icon_resolved)

    xbmcgui.Dialog().notification(heading, message, icon_value, time_ms, play_sound)


def dialog_browse(
    type: str = 'file',
    heading: str = '',
    shares: str = '',
    mask: str = '',
    default: str = '',
    multiple: str = 'false',
    doneaction: str = '',
    cancel_action: str = '',
    **kwargs
) -> None:
    """Browse `type` directory/file/image/writable; `multiple=true` allows multi-pick."""
    heading = _resolve_infolabel(heading) or 'Choose File'
    shares_str = _resolve_infolabel(shares)
    default_path = _resolve_infolabel(default)
    is_multiple = _parse_bool(multiple, False)

    type_map = {
        'directory': 0,
        'file': 1,
        'image': 2,
        'writable': 3,
    }

    browse_type = type_map.get(type.lower(), 1)

    log('Dialogs',
        f"dialog_browse: type={type}, multiple={is_multiple}, heading='{heading}'", xbmc.LOGDEBUG)

    if is_multiple:
        result = xbmcgui.Dialog().browseMultiple(
            browse_type,
            heading,
            shares=shares_str,
            mask=mask,
            useThumbs=True,
            treatAsFolder=False,
            defaultt=default_path
        )

        if not result:
            log('Dialogs', "dialog_browse: User cancelled (multiple)", xbmc.LOGDEBUG)
            _execute_builtin_list(cancel_action)
            return

        log('Dialogs', f"dialog_browse: User selected {len(result)} items", xbmc.LOGDEBUG)

        for path in result:
            if doneaction:
                formatted = _format_template(doneaction, 0, path)
                _execute_builtin_list(formatted)
    else:
        result = xbmcgui.Dialog().browseSingle(
            browse_type,
            heading,
            shares=shares_str,
            mask=mask,
            useThumbs=True,
            treatAsFolder=False,
            defaultt=default_path
        )

        if not result or result == default_path:
            log('Dialogs', "dialog_browse: User cancelled (single)", xbmc.LOGDEBUG)
            _execute_builtin_list(cancel_action)
            return

        log('Dialogs', f"dialog_browse: User selected path (length={len(result)})", xbmc.LOGDEBUG)

        if doneaction:
            formatted = _format_template(doneaction, 0, result)
            _execute_builtin_list(formatted)


def dialog_colorpicker(
    heading: str = '',
    default: str = '',
    doneaction: str = '',
    cancel_action: str = '',
    **kwargs
) -> None:
    """Show Kodi's built-in color picker. `default` is AARRGGBB hex."""
    heading = _resolve_infolabel(heading) or 'Choose Color'
    default_color = _resolve_infolabel(default)

    result = xbmcgui.Dialog().colorpicker(heading, selectedcolor=default_color)

    if not result:
        _execute_builtin_list(cancel_action)
        return

    if doneaction:
        formatted = _format_template(doneaction, 0, result)
        _execute_builtin_list(formatted)


def dialog_progress(
    heading: str = '',
    message: str = '',
    message_info: str = '',
    progress_info: str = '',
    max_value: str = '100',
    timeout: str = '200',
    polling: str = '0.1',
    background: str = 'false',
    **kwargs
) -> None:
    """Show a progress dialog that polls an InfoLabel (`progress_info`) for the current value.

    Closes when value >= `max_value` or after `timeout` polling cycles.
    `background=true` uses `DialogProgressBG`.
    """
    heading = _resolve_infolabel(heading) or 'Progress'
    message = _resolve_infolabel(message) or 'Please wait...'
    max_val = _parse_int(max_value, 100)
    timeout_cycles = _parse_int(timeout, 200)
    poll_interval = float(polling) if polling else 0.1
    is_background = _parse_bool(background, False)

    if not progress_info:
        progress_info = '50'

    if is_background:
        dialog_bg = xbmcgui.DialogProgressBG()
        dialog_bg.create(heading, message)
        dialog_normal = None
    else:
        dialog_normal = DialogProgress()
        dialog_normal.create(heading)
        dialog_normal.update(0, message)
        dialog_bg = None

    try:
        cycles = 0
        monitor = xbmc.Monitor()
        while cycles < timeout_cycles:
            if monitor.abortRequested():
                break
            if not is_background and dialog_normal and dialog_normal.iscanceled():
                break

            progress_str = (xbmc.getInfoLabel(progress_info)
                            if progress_info.startswith('$') else progress_info)
            try:
                progress_val = int(progress_str)
            except (ValueError, TypeError):
                progress_val = 0

            percentage = int((progress_val / max_val) * 100) if max_val > 0 else 0
            percentage = min(100, max(0, percentage))

            dynamic_message = xbmc.getInfoLabel(message_info) if message_info else message

            if is_background and dialog_bg:
                dialog_bg.update(percentage, dynamic_message)
            elif dialog_normal:
                dialog_normal.update(percentage, dynamic_message)

            if progress_val >= max_val:
                break

            monitor.waitForAbort(poll_interval)
            cycles += 1

    finally:
        if is_background and dialog_bg:
            dialog_bg.close()
        elif dialog_normal:
            dialog_normal.close()



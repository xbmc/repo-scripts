import xbmc


DIALOG_ID_EXCLUDELIST = (9999, None)


def get_current_window(get_dialog=True):
    import xbmcgui
    dialog = xbmcgui.getCurrentWindowDialogId() if get_dialog else None
    return dialog if dialog not in DIALOG_ID_EXCLUDELIST else xbmcgui.getCurrentWindowId()


def get_property(name, set_property=None, clear_property=False, window_id=None, prefix=None, is_type=None):
    import xbmcgui
    from jurialmunkey.parser import try_type

    if prefix != -1:
        prefix = prefix or 'TMDbHelper'
        name = f'{prefix}.{name}'
    if window_id == 'current':
        window_id = get_current_window()
    try:
        window = xbmcgui.Window(window_id or 10000)  # Fallback to home window id=10000
    except RuntimeError:  # If window id does not exist
        return
    ret_property = set_property or window.getProperty(name)
    if clear_property:
        window.clearProperty(name)
    if set_property is not None:
        window.setProperty(name, f'{set_property}')
    return try_type(ret_property, is_type or str)


def set_to_windowprop(text, x, window_prop, window_id=None):
    if not window_prop:
        return
    if x == 0:
        xbmc.executebuiltin(f'SetProperty({window_prop},{text}{f",{window_id}" if window_id else ""})')
    xbmc.executebuiltin(f'SetProperty({window_prop}.{x},{text}{f",{window_id}" if window_id else ""})')


def _property_is_value(name, value):
    if not value and not get_property(name):
        return True
    if value and get_property(name) == value:
        return True
    return False


def wait_for_property(name, value=None, set_property=False, poll=1, timeout=10):
    """
    Waits until property matches value. None value waits for property to be cleared.
    Will set property to value if set_property flag is set. None value clears property.
    Returns True when successful.
    """
    xbmc_monitor = xbmc.Monitor()
    if set_property:
        get_property(name, value) if value else get_property(name, clear_property=True)
    while (
            not xbmc_monitor.abortRequested() and timeout > 0
            and not _property_is_value(name, value)):
        xbmc_monitor.waitForAbort(poll)
        timeout -= poll
    del xbmc_monitor
    if timeout > 0:
        return True


def is_visible(window_id):
    return xbmc.getCondVisibility(f'Window.IsVisible({window_id})')


def close(window_id):
    return xbmc.executebuiltin(f'Dialog.Close({window_id})')


def activate(window_id):
    return xbmc.executebuiltin(f'ActivateWindow({window_id})')


def _is_base_active(window_id):
    if window_id and not is_visible(window_id):
        return False
    return True


def _is_updating(container_id):
    from jurialmunkey.parser import try_int
    is_updating = xbmc.getCondVisibility(f"Container({container_id}).IsUpdating")
    is_numitems = try_int(xbmc.getInfoLabel(f"Container({container_id}).NumItems"))
    if is_updating or not is_numitems:
        return True


def _is_inactive(window_id, invert=False):
    if is_visible(window_id):
        return True if invert else False
    return True if not invert else False


def wait_until_active(window_id, instance_id=None, poll=1, timeout=30, invert=False, xbmc_monitor=None):
    """
    Wait for window ID to open (or to close if invert set to True). Returns window_id if successful.
    Pass instance_id if there is also a base window that needs to be open underneath
    """
    _xbmc_monitor = xbmc_monitor or xbmc.Monitor()
    while (
            not _xbmc_monitor.abortRequested() and timeout > 0
            and _is_inactive(window_id, invert)
            and _is_base_active(instance_id)):
        _xbmc_monitor.waitForAbort(poll)
        timeout -= poll
    if not xbmc_monitor:
        del _xbmc_monitor
    if timeout > 0 and _is_base_active(instance_id):
        return window_id


def wait_until_updated(container_id=9999, instance_id=None, poll=1, timeout=60, xbmc_monitor=None):
    """
    Wait for container to update. Returns container_id if successful
    Pass instance_id if there is also a base window that needs to be open underneath
    """
    _xbmc_monitor = xbmc_monitor or xbmc.Monitor()
    while (
            not _xbmc_monitor.abortRequested() and timeout > 0
            and _is_updating(container_id)
            and _is_base_active(instance_id)):
        _xbmc_monitor.waitForAbort(poll)
        timeout -= poll
    if not xbmc_monitor:
        del _xbmc_monitor
    if timeout > 0 and _is_base_active(instance_id):
        return container_id


class WindowProperty():
    def __init__(self, *args, prefix='TMDbHelper'):
        """ ContextManager for setting a WindowProperty over duration """
        import xbmcgui
        self.property_pairs = args
        self.prefix = prefix
        self.window = xbmcgui.Window(10000)

        for k, v in self.property_pairs:
            if not k or not v:
                continue
            self.window.setProperty(f'{self.prefix}.{k}', f'{v}')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        for k, v in self.property_pairs:
            self.window.clearProperty(f'{self.prefix}.{k}')

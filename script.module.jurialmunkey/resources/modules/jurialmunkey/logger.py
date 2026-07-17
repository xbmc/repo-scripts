import xbmc
from timeit import default_timer as timer


def kodi_try_except_internal_traceback(log_msg):
    """ Decorator to catch exceptions and notify error for uninterruptable services """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                self.kodi_traceback(exc, log_msg)
        return wrapper
    return decorator


class Logger():
    def __init__(
            self,
            log_name: str = '',
            notification_head: str = '',
            notification_text: str = '',
            debug_logging: bool = False):
        self._addon_logname = log_name
        self._debug_logging = debug_logging
        self._notification_head = notification_head
        self._notification_text = notification_text

    def kodi_log(self, value, level=0):
        try:
            if isinstance(value, list):
                value = ''.join(map(str, value))
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            logvalue = f'{self._addon_logname}{value}'
            if level == 3 and self._debug_logging:
                import traceback
                xbmc.log(f'{logvalue}\n{traceback.print_stack()}', level=xbmc.LOGINFO)
            elif level == 2 and self._debug_logging:
                xbmc.log(logvalue, level=xbmc.LOGINFO)
            elif level == 1:
                xbmc.log(logvalue, level=xbmc.LOGINFO)
            else:
                xbmc.log(logvalue, level=xbmc.LOGDEBUG)
        except Exception as exc:
            xbmc.log(f'Logging Error: {exc}', level=xbmc.LOGINFO)

    def kodi_traceback(self, exception_object, log_msg=None, log_level=1, notification=True):
        """ Method for logging caught exception_objects and notifying user """
        if notification:
            from xbmcgui import Dialog
            Dialog().notification(self._notification_head, self._notification_text)
        msg = f'Error Type: {type(exception_object).__name__}\nError Contents: {exception_object.args!r}'
        msg = [log_msg, '\n', msg, '\n'] if log_msg else [msg, '\n']
        try:
            import traceback
            self.kodi_log(msg + traceback.format_tb(exception_object.__traceback__), log_level)
        except Exception as exc:
            self.kodi_log(f'ERROR WITH TRACEBACK!\n{exc}\n{msg}', log_level)

    def kodi_try_except(self, log_msg):
        """ Decorator to catch exceptions and notify error for uninterruptable services """
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    self.kodi_traceback(exc, log_msg)
            return wrapper
        return decorator

    def log_timer_report(self, timer_lists, paramstring, logging=True):
        _threaded = [
            'item_api', 'item_tmdb', 'item_ftv', 'item_map', 'item_cache',
            'item_set', 'item_get', 'item_getx', 'item_non', 'item_nonx', 'item_art',
            'item_abc', 'item_xyz']
        total_log = timer_lists.pop('total', 0)
        timer_log = ['DIRECTORY TIMER REPORT\n', paramstring, '\n']
        timer_log.append('------------------------------\n')
        for k, v in timer_lists.items():
            if k[:4] == 'name':
                continue
            elif k in _threaded:
                avg_time = f'{sum(v) / len(v):7.3f} sec avg | {max(v):7.3f} sec max | {len(v):3}' if v else '  None'
                timer_log.append(f' - {k:12s}: {avg_time}\n')
            elif k[:4] == 'item':
                avg_time = f'{sum(v) / len(v):7.3f} sec avg | {sum(v):7.3f} sec all | {len(v):3}' if v else '  None'
                timer_log.append(f' - {k:12s}: {avg_time}\n')
            else:
                tot_time = f'{sum(v) / len(v):7.3f} sec' if v else '  None'
                timer_log.append(f'{k:15s}: {tot_time}\n')
        timer_log.append('------------------------------\n')
        tot_time = f'{sum(total_log) / len(total_log):7.3f} sec' if total_log else '  None'
        timer_log.append(f'{"Total":15s}: {tot_time}\n')

        def get_timer_name(k, x):
            try:
                name = timer_lists[f'name_{k}'][x]
                diff = timer_lists[k][x] - timer_lists[k][x - 1] if x > 0 else 0
                name = f's = {name:<12}[{diff:^9.3f}]\n'
                return name
            except(AttributeError, NameError, IndexError, KeyError, TypeError):
                return ''

        for k, v in timer_lists.items():
            if k[:4] == 'name':
                continue
            if v and k in _threaded:
                timer_log.append(f'\n{k}:\n{"".join([f"  {i:.3f}{get_timer_name(k, x)}" for x, i in enumerate(v)])}\n')
        if logging:
            self.kodi_log(timer_log, 1)
        return timer_log


class TimerList():
    def __init__(self, dict_obj, list_name, log_threshold=0.001, logging=True, item_name=None):
        """ ContextManager for timing code blocks and storing in a list """
        self.list_obj = dict_obj.setdefault(list_name, [])
        self.name_obj = dict_obj.setdefault(f'name_{list_name}', []) if item_name else None
        self.item_name = item_name
        self.log_threshold = log_threshold
        self.timer_a = timer() if logging else None

    @property
    def total_time(self):
        try:
            return self._total_time
        except AttributeError:
            self._total_time = timer() - self.timer_a
            return self._total_time

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if not self.timer_a:
            return
        if self.total_time > self.log_threshold:
            self.list_obj.append(self.total_time)
            self.name_obj.append(self.item_name) if self.item_name else None


class TimerFunc():
    kodi_log = None

    def __init__(self, timer_name, log_threshold=0.05, inline=False, kodi_log=None):
        """ ContextManager for timing code blocks and outputing to log """
        self.inline = ' ' if inline else '\n'
        self.timer_name = timer_name
        self.log_threshold = log_threshold
        self.kodi_log = self.kodi_log or kodi_log or Logger().kodi_log
        self.timer_a = timer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        timer_z = timer()
        total_time = timer_z - self.timer_a
        if total_time <= self.log_threshold:
            return
        self.kodi_log(f'{self.timer_name}{self.inline}{total_time:.3f} sec', 1)

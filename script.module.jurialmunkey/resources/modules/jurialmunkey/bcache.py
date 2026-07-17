from jurialmunkey.plugin import format_name
from jurialmunkey.futils import get_filecache_name
from jurialmunkey.logger import kodi_try_except_internal_traceback
import jurialmunkey.scache


class BasicCache():
    _simplecache = jurialmunkey.scache.SimpleCache
    _queue_limit = 20

    def __init__(self, filename=None):
        self._filename = filename
        self._cache = None

    @staticmethod
    def kodi_traceback(exc, log_msg):
        from xbmc import getLocalizedString
        from jurialmunkey.logger import Logger
        Logger(
            log_name='[script.module.jurialmunkey]\n',
            notification_head=f'Module {getLocalizedString(257)}',
            notification_text=getLocalizedString(2104)).kodi_traceback(exc, log_msg)

    @kodi_try_except_internal_traceback('lib.addon.cache ret_cache')
    def ret_cache(self):
        if not self._cache:
            self._simplecache._queue_limit = self._queue_limit
            self._cache = self._simplecache(filename=self._filename)
        return self._cache

    @kodi_try_except_internal_traceback('lib.addon.cache get_cache')
    def get_cache(self, cache_name, cache_only=False):
        self.ret_cache()
        cur_time = -1 if cache_only else None  # Set negative time value if cache_only so we always get cache even if expired
        cache_name = get_filecache_name(cache_name or '')
        return self._cache.get(cache_name, cur_time=cur_time)

    @kodi_try_except_internal_traceback('lib.addon.cache set_cache')
    def set_cache(self, my_object, cache_name, cache_days=14, force=False, fallback=None):
        """ set object to cache via thread """
        self._set_cache(my_object, cache_name, cache_days, force, fallback)
        return my_object

    def _set_cache(self, my_object, cache_name, cache_days=14, force=False, fallback=None):
        """ set object to cache """
        self.ret_cache()
        cache_name = get_filecache_name(cache_name or '')
        if force and (not my_object or not cache_name or not cache_days):
            my_object = my_object or fallback
            cache_days = force if isinstance(force, int) else cache_days
        self._cache.set(cache_name, my_object, cache_days=cache_days)

    @kodi_try_except_internal_traceback('lib.addon.cache del_cache')
    def del_cache(self, cache_name):
        self.ret_cache()
        cache_name = get_filecache_name(cache_name or '')
        self._cache.set(cache_name, None, cache_days=0)

    @kodi_try_except_internal_traceback('lib.addon.cache use_cache')
    def use_cache(
            self, func, *args,
            cache_days=14, cache_name='', cache_only=False, cache_force=False, cache_strip=[], cache_fallback=False,
            cache_refresh=False, cache_combine_name=False, headers=None,
            **kwargs):
        """
        Simplecache takes func with args and kwargs
        Returns the cached item if it exists otherwise does the function
        """
        if not cache_name or cache_combine_name:
            cache_name = format_name(cache_name, *args, **kwargs)
            for k, v in cache_strip:
                cache_name = cache_name.replace(k, v)

        my_cache = None
        if cache_only or not cache_refresh:
            my_cache = self.get_cache(cache_name, cache_only=cache_only)

        if my_cache:
            return my_cache

        if not cache_only:
            if headers:
                kwargs['headers'] = headers
            my_object = func(*args, **kwargs)
            return self.set_cache(my_object, cache_name, cache_days, force=cache_force, fallback=cache_fallback)


def use_simple_cache(cache_days=None):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            kwargs['cache_days'] = cache_days or kwargs.get('cache_days', None)
            kwargs['cache_combine_name'] = True
            kwargs['cache_name'] = f'{func.__name__}.'
            kwargs['cache_name'] = f'{self.__class__.__name__}.{kwargs["cache_name"]}'
            return self._cache.use_cache(func, self, *args, **kwargs)
        return wrapper
    return decorator

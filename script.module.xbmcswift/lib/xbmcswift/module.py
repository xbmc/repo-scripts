def _requires_plugin(f):
    '''A decorator to trap errors when the module hasn't been initialized.'''
    def wrapped(module, *args, **kwargs):
        if module._plugin:
            return f(module, *args, **kwargs)
        raise Exception, 'Must register module with an application to use this method.'
    return wrapped

class Module(object):
    # All modules will keep their method names local, so without their module name prefixed
    # the show_videos module in mit will be called show_videos, not mit.show_videos

    def __init__(self, namespace):
        self._namespace = namespace.split('.')[-1] # Get rid of package prefixes
        self._view_functions = {}
        self._routes = []
        self._register_funcs = []
        self._plugin = None

    def route(self, url_rule, default=False, name=None, **options):
        def decorator(f):
            view_name = name or f.__name__
            self.add_url_rule(url_rule, f, name=view_name, default=default, **options)
            return f
        return decorator

    def url_for(self, endpoint, **items):
        #full_endpoint = '%s.%s' % (self._namespace, endpoint)
        full_endpoint = endpoint

        try:
            return self._plugin.url_for(full_endpoint, **items)
        except AttributeError:
            raise Exception, 'Must register_module with an application.'

    def add_url_rule(self, url_rule, view_func, name, default=False, **options):
        name = '%s.%s' % (self._namespace, name)

        def register_rule(plugin, url_prefix):
            full_url_rule = url_prefix + url_rule
            plugin.add_url_rule(full_url_rule, view_func, name, default, **options)

        self._register_funcs.append(register_rule)


    @property
    def qs_args(self):
        if not self._plugin:
            raise Exception, 'Not registered with any app.'
        return self._plugin.qs_args

    @property
    def routes(self):
        return self._routes

    @property
    def view_functions(self):
        return self._view_functions

    @property
    def namespace(self):
        return self._namespace

    @property
    def url_prefix(self):
        return self._url_prefix

    # Proxies to parent plugin
    @_requires_plugin
    def get_string(self, stringid):
        return self._plugin.get_string(stringid)

    @_requires_plugin
    def set_content(self, content):
        return self._plugin.set_content(content)

    @_requires_plugin
    def add_items(self, iterable):
        return self._plugin.add_items(iterable)

    @_requires_plugin
    def add_to_playlist(self, items, playlist='video'):
        return self._plugin.add_to_playlist(items, playlist)

    @_requires_plugin
    def set_resolved_url(self, url):
        return self._plugin.set_resolved_url(url)

    @_requires_plugin
    def get_setting(self, key):
        return self._plugin.get_setting(key)

    @_requires_plugin
    def set_setting(self, key, val):
        return self._plugin.set_setting(key, val)





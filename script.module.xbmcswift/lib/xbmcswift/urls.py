import re
from common import pickle_dict, unpickle_dict
from urllib import urlencode, unquote_plus, quote_plus

class AmbiguousUrlException(Exception):
    pass

class NotFoundException(Exception):
    pass

class UrlRule(object):
    def __init__(self, url_rule, view_func, name, **options):
        self._name = name
        self._url_rule = url_rule
        self._view_func = view_func
        self._options = options
        self._keywords = re.findall(r'\<(.+?)\>', url_rule)

        #change <> to {} for use with str.format()
        self._url_format = self._url_rule.replace('<', '{').replace('>', '}')

        # Make a regex pattern for matching incoming URLs
        p = self._url_rule.replace('<', '(?P<').replace('>', '>[^/]+?)')

        try:
            self._regex = re.compile('^' + p + '$')
        except re.error, e: 
            #print e
            raise ValueError, 'Invalid URL rule.'

    def __eq__(self, other):
        return (
            (self._name, self._url_rule, self._view_func, self._options) ==
            (other._name, other._url_rule, other._view_func, other._options)
        )

    def __ne__(self, other):
        return not self.__eq__(other)
        

    def match(self, path):
        # Cna't return none or a tyuple, must raise a no match error or something instead
        '''Attempts to match a url to the given path. Returns a tuple
        of (method, items_dictionary) if successful or None.'''
        m = self._regex.search(path)
        if not m:
            raise NotFoundException

        # urlunencode the values
        items = dict((key, unquote_plus(val)) for key, val in m.groupdict().items())

        #unpickel items
        items = unpickle_dict(items)

        # We need to update our dictionary with default values provided in options if 
        # the keys don't already exist.
        [items.setdefault(key, val) for key, val in self._options.items()]
        
        return self._view_func, items

    def _make_path(self, items):
        for key, val in items.items():
            assert isinstance(val, basestring), 'URL params must be instances of basestring.'
            items[key] = quote_plus(val)

        try:
            path = self._url_format.format(**items)
        except AttributeError:
            # Old version of python
            path = self._url_format
            for key, val in items.items():
                path = path.replace('{%s}' % key, val)
        return path

    def _make_qs(self, items):
        # Pickle any non basestring arguments
        items = pickle_dict(items)
        qs = urlencode(items)
        return qs

    def make_path_qs(self, items):
        # (1) Plug items into url that are included in self._keywords
        # (2) Separate extra items
        # (3) pickle any items not basetring
        # (4) Append query string
        url_items = dict((key, val) for key, val in items.items() if key in self._keywords)

        # Create the path
        path = self._make_path(url_items)

        # Extra arguments get tacked on to the query string
        qs_items = dict((key, val) for key, val in items.items() if key not in self._keywords)
        qs = self._make_qs(qs_items)

        #return path, qs
        if qs:
            return '?'.join([path, qs])
        return path
        #url = urlunsplit((self.protocol, self.netloc, path, qs, None))
        #return url

    @property
    def regex(self):
        return self._regex

    @property
    def view_func(self):
        return self._view_func

    @property
    def url_format(self):
        return self._url_format

    @property
    def name(self):
        return self._name

    @property
    def keywords(self):
        return self._keywords

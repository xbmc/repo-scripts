'''Contains core classes and functions for creating and manipulating API
objects.

'''
import urllib
from datetime import datetime


def get_item(resp, cls):
    '''Converts a response dictionary to a class instance.

    Returns cls(**resp).
    
    '''
    try:
        params = dict((str(key), val) for key, val in resp.items())
    except AttributeError:
        # Don't have a dict
        return cls(resp)
    return cls(**params)


class Connection(object):
    '''Augments requests to the API with the auth token.'''
    def __init__(self, token):
        self.token = token

    def _request(self, url, data=None):
        '''Returns a response for the given url and data.'''
        conn = urllib.urlopen(url, data)
        resp = conn.read()
        conn.close()
        return resp

    def get_request(self, url, params=None):
        '''Returns a response for a given url and an optional dictionary of
        query string parameters.

        This method calls urlencode on the params and augments params with the
        auth token.

        '''
        if params is None:
            params = {}
        params.update({'token': self.token})
        data = urllib.urlencode(params)
        url = '%s?%s' % (url, data)
        return self._request(url)


class Field(object):
    '''Basic API Field subclass.'''
    def __init__(self, help=None):
        self.help = help

    def to_python(self, value):
        return value

    from_python = to_python


class DateTimeField(Field):
    '''Handles conversion from milliseconds to python datetime.'''
    def to_python(self, value):
        return datetime.fromtimestamp(int(value) / 1000)

    def from_python(self, value):
        return str(int(value.strftime('%s')) * 1000)


class ListField(Field):
    '''A field composed of a python list of another Field instance.'''
    def __init__(self, item_cls, help=None):
        self.help = help
        self.item_cls = item_cls

    def to_python(self, value):
        return [get_item(item, self.item_cls) for item in value]

    def from_python(self, value):
        return [item.from_python() for item in value]


class EnumField(Field):
    def __init__(self, enum_cls, help=None):
        self.help = help
        self.enum_cls = enum_cls

    def to_python(self, value):
        for field in self.enum_cls._fields:
            if field == value:
                return value
        raise Exception('Invalid Enum: %s' % field)

    def from_python(self, value):
        return value


class APIObjectMeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(APIObjectMeta, cls).__new__

        _meta = dict([(attr_name, attr_value)
                        for attr_name, attr_value in attrs.items()
                            if isinstance(attr_value, Field)])

        # Now create Field objects for everything listed in _fields but not
        # already explicity declared as a field
        if '_fields' in attrs.keys():
            _meta.update(dict((attr_name, Field()) for attr_name in
                         attrs['_fields'] if attr_name not in _meta.keys()))
            del attrs['_fields']

        attrs['_meta'] = _meta
        attributes = _meta.keys()
        attrs.update(dict([(attr_name, None)
                        for attr_name in attributes]))

        def _contribute_method(name, func):
            func.func_name = name
            attrs[name] = func

        def constructor(self, **kwargs):
            for attr_name, attr_value in kwargs.items():
                attr = self._meta.get(attr_name)
                if attr:
                    setattr(self, attr_name, attr.to_python(attr_value))
                else:
                    setattr(self, attr_name, attr_value)
        _contribute_method("__init__", constructor)

        def from_python(self):
            ret = {}
            for attr_name, attr_value in vars(self).items():
                if attr_value is None:
                    continue
                attr = self._meta.get(attr_name)
                if attr:
                    ret[attr_name] = attr.from_python(attr_value)
                else:
                    ret[attr_name] = attr_value
            return ret
        _contribute_method('from_python', from_python)

        def iterate(self):
            not_empty = lambda e: e[1] is not None
            return iter(filter(not_empty, vars(self).items()))
        _contribute_method("__iter__", iterate)

        result_cls = super_new(cls, name, bases, attrs)
        #result_cls.__doc__ = doc_generator(result_cls.__doc__, _meta)
        return result_cls


## API Objects
class APIObject(object):
    __metaclass__ = APIObjectMeta

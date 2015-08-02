import re
import collections
from urllib import quote_plus


def to_params(hash):
    normalized = map(lambda (k, v): normalize_param(k, v), hash.iteritems())
    return dict((k, v) for d in normalized for (k, v) in d.items())


def normalize_param(key, value):
    """Convert a set of key, value parameters into a dictionary suitable for
    passing into requests. This will convert lists into the syntax required
    by SoundCloud. Heavily lifted from HTTParty.

    >>> normalize_param('playlist', {
    ...  'title': 'foo',
    ...  'sharing': 'private',
    ...  'tracks': [
    ...    {id: 1234}, {id: 4567}
    ...  ]})  # doctest:+ELLIPSIS
    {u'playlist[tracks][][<built-in function id>]': [1234, 4567], u'playlist[sharing]': 'private', u'playlist[title]': 'foo'}

    >>> normalize_param('oauth_token', 'foo')
    {'oauth_token': 'foo'}

    >>> normalize_param('playlist[tracks]', [1234, 4567])
    {u'playlist[tracks][]': [1234, 4567]}
    """
    params = {}
    stack = []
    if isinstance(value, list):
        normalized = map(lambda e: normalize_param(u"{0[key]}[]".format(dict(key=key)), e), value)
        keys = [item for sublist in tuple(h.keys() for h in normalized) for item in sublist]

        lists = {}
        if len(keys) != len(set(keys)):
            duplicates = [x for x, y in collections.Counter(keys).items() if y > 1]
            for dup in duplicates:
                lists[dup] = [h[dup] for h in normalized]
                for h in normalized:
                    del h[dup]

        params.update(dict((k, v) for d in normalized for (k, v) in d.items()))
        params.update(lists)
    elif isinstance(value, dict):
        stack.append([key, value])
    else:
        params.update({key: value})

    for (parent, hash) in stack:
        for (key, value) in hash.iteritems():
            if isinstance(value, dict):
                stack.append([u"{0[parent]}[{0[key]}]".format(dict(parent=parent, key=key)), value])
            else:
                params.update(normalize_param(u"{0[parent]}[{0[key]}]".format(dict(parent=parent, key=key)), value))

    return params

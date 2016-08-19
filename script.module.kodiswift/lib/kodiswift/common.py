# -*- coding: utf-8 -*-
"""
kodiswift.common
-----------------

This module contains some common helpful functions.

:copyright: (c) 2012 by Jonathan Beluch
:license: GPLv3, see LICENSE for more details.
"""
from __future__ import absolute_import

import urllib

try:
    import cPickle as pickle
except ImportError:
    import pickle

__all__ = ['clean_dict', 'kodi_url', 'unpickle_args', 'pickle_dict',
           'unpickle_dict', 'download_page', 'Modes']


class Modes(object):
    ONCE = 'ONCE'
    CRAWL = 'CRAWL'
    INTERACTIVE = 'INTERACTIVE'


def kodi_url(url, **options):
    """Appends key/val pairs to the end of a URL. Useful for passing arbitrary
    HTTP headers to Kodi to be used when fetching a media resource, e.g.
    cookies.

    Args:
        url (str):
        **options (dict):

    Returns:
        str:
    """
    options = urllib.urlencode(options)
    if options:
        return url + '|' + options
    return url


def clean_dict(data):
    """Remove keys with a value of None

    Args:
        data (dict):

    Returns:
        dict:
    """
    return dict((k, v) for k, v in data.items() if v is not None)


def pickle_dict(items):
    """Convert `items` values into pickled values.

    Args:
        items (dict): A dictionary

    Returns:
        dict: Values which aren't instances of basestring are pickled. Also,
            a new key '_pickled' contains a comma separated list of keys
            corresponding to the pickled values.
    """
    ret = {}
    pickled_keys = []
    for k, v in items.items():
        if isinstance(v, basestring):
            ret[k] = v
        else:
            pickled_keys.append(k)
            ret[k] = pickle.dumps(v)
    if pickled_keys:
        ret['_pickled'] = ','.join(pickled_keys)
    return ret


def unpickle_args(items):
    """Takes a dict and un-pickles values whose keys are found in a '_pickled'
    key.

    >>> unpickle_args({'_pickled': ['foo'], 'foo': ['I3%0A.']})
    {'foo': 3}

    Args:
        items (dict): A pickled dictionary.

    Returns:
        dict: Dict with values un-pickled.
    """
    # Technically there can be more than one _pickled value. At this point
    # we'll just use the first one
    pickled = items.pop('_pickled', None)
    if pickled is None:
        return items

    pickled_keys = pickled[0].split(',')
    ret = {}
    for k, v in items.items():
        if k in pickled_keys:
            ret[k] = [pickle.loads(val) for val in v]
        else:
            ret[k] = v
    return ret


def unpickle_dict(items):
    """un-pickles a dictionary that was pickled with `pickle_dict`.

    Args:
        items (dict): A pickled dictionary.

    Returns:
        dict: An un-pickled dictionary.
    """
    pickled_keys = items.pop('_pickled', '').split(',')
    ret = {}
    for k, v in items.items():
        if k in pickled_keys:
            ret[k] = pickle.loads(v)
        else:
            ret[k] = v
    return ret


def download_page(url, data=None):
    """Returns the response for the given url. The optional data argument is
    passed directly to urlopen.

    Args:
        url (str): The URL to read.
        data (Optional[any]): If given, a POST request will be made with
            :param:`data` as the POST body.

    Returns:
        str: The results of requesting the URL.
    """
    conn = urllib.urlopen(url, data)
    resp = conn.read()
    conn.close()
    return resp

'''
    xbmcswift2.constants
    --------------------

    This module contains some helpful constants which ease interaction
    with KODI.

    :copyright: (c) 2012 by Jonathan Beluch
    :license: GPLv3, see LICENSE for more details.
'''
from xbmcswift2 import xbmcplugin


class SortMethod(object):
    '''Static class to hold all of the available sort methods. The
    sort methods are dynamically imported from xbmcplugin and added as
    attributes on this class. The prefix of 'SORT_METHOD_' is
    automatically stripped.

    e.g. SORT_METHOD_TITLE becomes SortMethod.TITLE
    '''

    @classmethod
    def from_string(cls, sort_method):
        '''Returns the sort method specified. sort_method is case insensitive.
        Will raise an AttributeError if the provided sort_method does not
        exist.

        >>> SortMethod.from_string('title')
        '''
        return getattr(cls, sort_method.upper())


PREFIX = 'SORT_METHOD_'
for attr_name, attr_value in xbmcplugin.__dict__.items():
    if attr_name.startswith(PREFIX):
        setattr(SortMethod, attr_name[len(PREFIX):], attr_value)

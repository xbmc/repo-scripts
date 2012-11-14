# Copyright 2011 Jonathan Beluch. 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from urllib import unquote_plus, quote_plus
from urlparse import urlparse
from cStringIO import StringIO
import urllib2
import asyncore, socket
from urlparse import urlparse
import pickle

#from . import xbmc
#from . import xbmcgui
#from . import xbmcplugin
#from . import xbmcaddon

#import xbmc
#import xbmcgui
#import xbmcplugin
#import xbmcaddon
from xbmcswift import xbmc, xbmcgui, xbmcplugin, xbmcaddon

#def urlparse(url):
    #protocol, remainder = url.split('://', 1)
    #netloc, path = remainder.split('/', 1)
    #return (protocol, netloc, '/' + path)

def urlparse(url):
    '''Takes a url and returns a 3 tuple of scheme, netloc and path'''
    scheme, remainder = url.split('://', 1)
    netloc, path = remainder.split('/', 1)
    return scheme, netloc, '/' + path

def clean_dict(d):
    '''Verifies none of the values are None, otherwise XBMC wll break'''
    if not d:
        return None

    # Filter out items whose value is None
    ret = filter(lambda pair: pair[1] is not None, d.items())

    # Make sure we have at least one item left
    if len(ret) == 0:
        return None
    
    # We have at least one item, return a dict
    return dict(ret)

def pickle_dict(items):
    ret = {}
    for key, val in items.items():
        if isinstance(val, basestring):
            ret[key] = val
        else:
            ret['_%s' % key] = pickle.dumps(val)
    return ret

def unpickle_dict(items):
    ret = {}
    for key, val in items.items():
        if key.startswith('_'):
            ret[key[1:]] = pickle.loads(val)
        else:
            ret[key] = val
    return ret

def download_page(url, data=None):
    # Must check cache using httplib2 here!
    u = urllib2.urlopen(url, data)
    r = u.read()
    u.close()
    return r

def parse_url_qs(url, pickled_fragment=False):
    '''Returns a dict of key/vals parsed from a query string.  If
    pickled_fragment=True, the method unpickles python objects stored in the
    fragment portion of the url and adds them to the returned dictionary.
    '''
    parts = urlparse(url)
    qs = parts[4]
    fragment = parts[5]

    #parse qs
    params = parse_qs(qs)

    #unpickle the fragment and update params with the pickled dict
    if pickled_fragment and len(fragment) > 0:
        params.update(pickle.loads(unquote_plus(fragment)))
    return params

    
def parse_qs(qs):
    '''Takes a query string and returns a {} with key/vals.  If more than
    one instance of a key is specified, the last value will be returned.'''
    if qs is None or len(qs) == 0:
        return {}

    pairs = [s2 for s1 in qs.split('&') for s2 in s1.split(';')]
    r ={} 

    for pair in pairs:
        parts = pair.split('=', 1)
        if len(parts) != 2:
            raise ValueError, 'bad query field: %r' % (pair)
        r[unquote_plus(parts[0])] = unquote_plus(parts[1])
    return r



class XBMCVideoPluginException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class XBMCDialogCancelled(Exception):
    pass


#Code modeled after python's urllib.unquote
_hextochr = dict(('%02x' % i, chr(i)) for i in range(256))
_hextochr.update(('%02X' % i, chr(i)) for i in range(256))

def unhex(s):
    '''unquote(r'abc\x20def') -> 'abc def'.'''
    res = s.split(r'\x')
    for i in xrange(1, len(res)):
        item = res[i]
        try:
            res[i] = _hextochr[item[:2]] + item[2:]
        except KeyError:
            res[i] = '%' + item
        except UnicodeDecodeError:
            res[i] = unichr(int(item[:2], 16)) + item[2:]
    return ''.join(res)

    






















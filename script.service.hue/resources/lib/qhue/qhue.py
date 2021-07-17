# Qhue is (c) Quentin Stafford-Fraser 2017
# but distributed under the GPL v2.

import json
import re
import sys

#from .. import logger

#from builtins import input
#from builtins import object
#from builtins import str
from socket import getfqdn

import requests

# for hostname retrieval for registering with the bridge
__all__ = ('Bridge', 'QhueException')

# menu timeout in seconds
_DEFAULT_TIMEOUT = 5


class Resource(object):

    def __init__(self, url, timeout=_DEFAULT_TIMEOUT, object_pairs_hook=None):
        self.url = url
        self.address = url[url.find('/api'):]
        # Also find the bit after the username, if there is one
        self.short_address = None
        post_username_match = re.search(r'/api/[^/]*(.*)', url)
        if post_username_match is not None:
            self.short_address = post_username_match.group(1)
        self.timeout = timeout
        self.object_pairs_hook = object_pairs_hook

    def __call__(self, *args, **kwargs):
        # Preprocess args and kwargs
        url = self.url
        for a in args:
            url += "/" + str(a)
        http_method = kwargs.pop('http_method',
            'get' if not kwargs else 'put').lower()

        # From each keyword, strip one trailing underscore if it exists,
        # then send them as parameters to the bridge. This allows for
        # "escaping" of keywords that might conflict with Python syntax
        # or with the specially-handled keyword "http_method".
        kwargs = {(k[:-1] if k.endswith('_') else k): v for k, v in list(kwargs.items())}
        if http_method == 'put':
            #r = requests.put(url, data=json.dumps(kwargs, default=list), timeout=self.timeout)
            r = requests.put(url, data=json.dumps(kwargs, separators=(',', ':'), default=list), timeout=self.timeout)
        elif http_method == 'post':
            #r = requests.post(url, data=json.dumps(kwargs, default=list), timeout=self.timeout)
            r = requests.post(url, data=json.dumps(kwargs, separators=(',', ':'), default=list), timeout=self.timeout)
        elif http_method == 'delete':
            r = requests.delete(url, timeout=self.timeout)
        else:
            r = requests.get(url, timeout=self.timeout)

        if r.status_code != 200:
            if r.status_code == 500:
                errors = []
                errors.append(500)
                errors.append(500)
                raise QhueException(errors)
            raise QhueException("Received response {c} from {u}".format(c=r.status_code, u=url))
        resp = r.json(object_pairs_hook=self.object_pairs_hook)
        if type(resp) == list:
            errors = []
            for m in resp:
                if 'error' in m:
                    errors.append(m['error']['type'])
                    errors.append(m['error']['description'])
            if errors:
                raise QhueException(errors)
        return resp

    def __getattr__(self, name):
        return Resource(self.url + "/" + str(name), timeout=self.timeout,
                object_pairs_hook=self.object_pairs_hook)

    __getitem__ = __getattr__


def _api_url(ip, username=None):
    if username is None:
        return "http://{}/api".format(ip)
    else:
        return "http://{}/api/{}".format(ip, username)

#===============================================================================
# 
# def create_new_username(ip, devicetype=None, timeout=_DEFAULT_TIMEOUT):
#     """Interactive helper function to generate a new anonymous username.
# 
#     Args:
#         ip: ip address of the bridge
#         devicetype (optional): devicetype to register with the bridge. If
#             unprovided, generates a device type based on the local hostname.
#         timeout (optional, menu=5): request timeout in seconds
#     Raises:
#         QhueException if something went wrong with username generation (for
#             example, if the bridge button wasn't pressed).
#     """
#     res = Resource(_api_url(ip), timeout)
#     prompt = "Press the Bridge button, then press Return: "
#     # Deal with one of the sillier python3 changes
#     if sys.version_info.major == 2:
#         _ = eval(input(prompt))
#     else:
#         _ = eval(input(prompt))
# 
#     if devicetype is None:
#         devicetype = "qhue#{}".format(getfqdn())
# 
#     # raises QhueException if something went wrong
#     response = res(devicetype=devicetype, http_method="post")
# 
#     return response[0]["success"]["username"]
#===============================================================================

class Bridge(Resource):

    def __init__(self, ip, username, timeout=_DEFAULT_TIMEOUT, object_pairs_hook=None):
        """Create a new connection to a hue bridge.

        If a whitelisted username has not been generated yet, use
        create_new_username to have the bridge interactively generate
        a random username and then pass it to this function.

        Args:
            ip: ip address of the bridge
            username: valid username for the bridge
            timeout (optional, menu=5): request timeout in seconds
            object_pairs_hook (optional): function called by JSON decoder with
                the result of any object literal as an ordered list of pairs.
        """
        self.ip = ip
        self.username = username
        url = _api_url(ip, username)
        super(Bridge, self).__init__(url, timeout=timeout, object_pairs_hook=object_pairs_hook)


class QhueException(Exception):
    pass

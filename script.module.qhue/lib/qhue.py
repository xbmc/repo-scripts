# Qhue is (c) Quentin Stafford-Fraser 2021
# but distributed under the GPL v2.
# It expects Python v3.

import re
import json

# for hostname retrieval for registering with the bridge
from socket import getfqdn

import requests

__all__ = ("Bridge", "QhueException", "create_new_username")

# default timeout in seconds
_DEFAULT_TIMEOUT = 5


class Resource(object):
    """
    A Resource represents an object or collection of objects in the Hue world,
    such as a light or a group of lights.
    It encapsulates an API method that can be called to examine or modify
    those objects, and makes it easy to construct the URLs needed.
    When you create a Resource, you are building a URL.
    When you call a Resource, you are making a request to that URL with some
    parameters.
    """
    def __init__(self, url, session, timeout=_DEFAULT_TIMEOUT, object_pairs_hook=None):
        self.url = url
        self.session = session
        self.address = url[url.find("/api"):]
        # Also find the bit after the username, if there is one
        self.short_address = None
        post_username_match = re.search(r"/api/[^/]*(.*)", url)
        if post_username_match is not None:
            self.short_address = post_username_match.group(1)
        self.timeout = timeout
        self.object_pairs_hook = object_pairs_hook

    def __call__(self, *args, **kwargs):
        # Preprocess args and kwargs
        url = self.url
        for a in args:
            url += "/" + str(a)
        http_method = kwargs.pop("http_method", "get" if not kwargs else "put").lower()

        # From each keyword, strip one trailing underscore if it exists,
        # then send them as parameters to the bridge. This allows for
        # "escaping" of keywords that might conflict with Python syntax
        # or with the specially-handled keyword "http_method".
        kwargs = {(k[:-1] if k.endswith("_") else k): v for k, v in kwargs.items()}
        if http_method == "put":
            r = self.session.put(url, data=json.dumps(kwargs, default=list), timeout=self.timeout)
        elif http_method == "post":
            r = self.session.post(url, data=json.dumps(kwargs, default=list), timeout=self.timeout)
        elif http_method == "delete":
            r = self.session.delete(url, timeout=self.timeout)
        else:
            r = self.session.get(url, timeout=self.timeout)
        if r.status_code != 200:
            raise QhueException("Received response {c} from {u}".format(c=r.status_code, u=url))
        resp = r.json(object_pairs_hook=self.object_pairs_hook)
        if type(resp) == list:
            # In theory, you can get more than one error from a single call
            # so they are returned as a list.
            errors = [m["error"] for m in resp if "error" in m]
            if errors:
                # In general, though, there will only be one error per call
                # so we return the type and address of the first one in the 
                # exception, to keep the exception type simple.
                raise QhueException(
                    message=",".join(e["description"] for e in errors),
                    type_id=",".join(str(e["type"]) for e in errors),
                    address=errors[0]['address']
                )
        return resp

    def __getattr__(self, name):
        return Resource(
            self.url + "/" + str(name),
            self.session,
            timeout=self.timeout,
            object_pairs_hook=self.object_pairs_hook,
        )

    __getitem__ = __getattr__


def _local_api_url(ip, username=None):
    if username is None:
        return "http://{}/api".format(ip)
    return "http://{}/api/{}".format(ip, username)


def create_new_username(ip, devicetype=None, timeout=_DEFAULT_TIMEOUT):
    """Interactive helper function to generate a new anonymous username.

    Args:
        ip: ip address of the bridge
        devicetype (optional): devicetype to register with the bridge. If
            unprovided, generates a device type based on the local hostname.
        timeout (optional, default=5): request timeout in seconds
    Raises:
        QhueException if something went wrong with username generation (for
            example, if the bridge button wasn't pressed).
    """
    res = Resource(_local_api_url(ip), requests.Session(), timeout)
    prompt = "Press the Bridge button, then press Return: "
    input(prompt)

    if devicetype is None:
        devicetype = "qhue#{}".format(getfqdn())

    # raises QhueException if something went wrong
    response = res(devicetype=devicetype, http_method="post")

    return response[0]["success"]["username"]


class Bridge(Resource):
    """
    A Bridge is a Resource that represents the top-level connection to a
    Philips Hue Bridge (or 'Hub').
    It is the basis for building other Resources that represent the things
    managed by that Bridge.
    """
    def __init__(self, ip, username, timeout=_DEFAULT_TIMEOUT, object_pairs_hook=None):
        """
        Create a new connection to a hue bridge.

        If a whitelisted username has not been generated yet, use
        create_new_username to have the bridge interactively generate
        a random username and then pass it to this function.

        Args:
            ip: ip address of the bridge
            username: valid username for the bridge
            timeout (optional, default=5): request timeout in seconds
            object_pairs_hook (optional): function called by JSON decoder with
                the result of any object literal as an ordered list of pairs.
        """
        self.ip = ip
        self.username = username
        url = _local_api_url(ip, username)
        self.session = requests.Session()
        super().__init__(url, self.session, timeout=timeout, object_pairs_hook=object_pairs_hook)


class QhueException(Exception):
    def __init__(self, message, type_id=None, address=None):
        self.message = message
        self.type_id = type_id
        self.address = address

        super().__init__(self.message)

    def __str__(self):
        return f'QhueException: {self.type_id} -> {self.message}'

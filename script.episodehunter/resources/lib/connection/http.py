import socket
import json
from resources import config
from resources.lib import helper

try:
    import urllib2 as urllib_request  # for python 2
except ImportError:
    import urllib.request as urllib_request  # for python 3


class Http(object):

    def __init__(self, base_url=config.__BASE_URL__):
        super(Http, self).__init__()
        socket.setdefaulttimeout(config.__HTTP_TIMEOUT__)
        self.__base_url = base_url

    def make_request(self, data=None):
        helper.debug('Making request to: ' + str(self.__base_url))
        data = data or {}
        data = json.dumps(data, default=lambda o: o.__dict__)
        data = str(data)
        data = data.encode('utf-8')

        request = urllib_request.Request(self.__base_url, data, {
            'Content-Type': 'application/json'})
        try:
            urllib_request.urlopen(request)
        except (Exception) as error:
            helper.debug(error)
            pass

import socket
import urllib2
import json

from resources.exceptions import ConnectionExceptions, SettingsExceptions
from resources import config


class Http(object):

    def __init__(self, base_url=config.__BASE_URL__):
        super(Http, self).__init__()
        socket.setdefaulttimeout(config.__HTTP_TIMEOUT__)
        self.__base_url = base_url

    def make_request(self, api_endpoint, data=None):
        """
        Create an POST request and returning the result
        :param api_endpoint:string
        :param data:json string
        :return:dictionary
        """
        data = data or {}
        request = urllib2.Request(self.__base_url + api_endpoint, data, {'Content-Type': 'application/json'})
        try:
            response = urllib2.urlopen(request)
            return json.load(response)
        except urllib2.HTTPError, error:
            self.error_handler(error)
        except urllib2.URLError, error:
            raise ConnectionExceptions(error.reason)

    def error_handler(self, error):
        """
        Handel http errors
        :rtype : None
        :param error:urllib2.HTTPError
        :raise error:urllib2.HTTPError
        """
        if error.code == 403:
            try:
                raise SettingsExceptions(json.load(error)['data'])
            except KeyError:
                raise SettingsExceptions()
        elif error.code == 400:
            try:
                raise ConnectionExceptions(json.load(error)['data'])
            except KeyError:
                raise ConnectionExceptions()
        else:
            raise ConnectionExceptions(str(error))

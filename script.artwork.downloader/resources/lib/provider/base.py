import socket
import sys
from urllib2 import HTTPError, URLError, urlopen
from resources.lib.script_exceptions import HTTP404Error, HTTP503Error, DownloadError, HTTPTimeout


### adjust default timeout to stop script hanging
timeout = 20
socket.setdefaulttimeout(timeout)

class BaseProvider:

    """
    Creates general structure for all fanart providers.  This will allow us to
    very easily add multiple providers for the same media type.
    """
    name = ''
    api_key = ''
    api_limits = False
    url = ''
    data = {}
    fanart_element = ''
    fanart_root = ''
    url_prefix = ''
    
    
    def get_xml(self, url):
        try:
            client = urlopen(url)
            data = client.read()
            client.close()
            return data
        except HTTPError, e:
            if e.code == 404:
                raise HTTP404Error(url)
            elif e.code == 503:
                raise HTTP503Error(url)
            else:
                raise DownloadError(str(e))
        except URLError:
            raise HTTPTimeout(url)
        except socket.timeout, e:
            raise HTTPTimeout(url)


    def get_image_list(self, media_id):
        pass

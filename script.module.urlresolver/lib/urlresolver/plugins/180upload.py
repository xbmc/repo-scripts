'''
180upload urlresolver plugin
Copyright (C) 2011 anilkuj

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
from lib import jsunpack
import re, urllib2, os, xbmcgui, xbmc
from lib import captcha_lib

net = Net()

class OneeightyuploadResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "180upload"
    domains = ["180upload.com"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        # try embedded link first to avoid captcha, try direct link if it doesn't work
            stream_url = self.__get_link('http://180upload.com/embed-%s.html' % media_id)
            if not stream_url:
                stream_url = self.__get_link(self.get_url(host, media_id))
            return stream_url

    def __get_link(self, url):
        try:
            common.addon.log_debug('180upload: get_link: %s' % (url))
            html = net.http_GET(url).content

            #Re-grab data values
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)"', html)

            if r:
                for name, value in r:
                    data[name] = value
            else:
                raise Exception('Unable to resolve 180Upload Link')

            # ignore captchas in embedded pages
            if 'embed' not in url:
                #Check for SolveMedia Captcha image
                solvemedia = re.search('<iframe src="(http://api.solvemedia.com.+?)"', html)
                recaptcha = re.search('<script type="text/javascript" src="(http://www.google.com.+?)">', html)

                if solvemedia:
                    data.update(captcha_lib.do_solvemedia_captcha(solvemedia.group(1)))
                elif recaptcha:
                    data.update(captcha_lib.do_recaptcha(recaptcha.group(1)))

            common.addon.log_debug('180Upload - Requesting POST URL: %s with data: %s' % (url, data))
            data['referer'] = url
            html = net.http_POST(url, data).content

            # try download link
            link = re.search('id="lnk_download[^"]*" href="([^"]+)', html)
            if link:
                common.addon.log_debug('180Upload Download Found: %s' % link.group(1))
                return link.group(1)
            else:
                # try flash player link
                packed = re.search('id="player_code".*?(eval.*?)</script>', html, re.DOTALL)
                if packed:
                    js = jsunpack.unpack(packed.group(1))
                    link = re.search('name="src"\s*value="([^"]+)', js.replace('\\', ''))
                    if link:
                        common.addon.log_debug('180Upload Src Found: %s' % link.group(1))
                        return link.group(1)
                    else:
                        link = re.search("'file'\s*,\s*'([^']+)", js.replace('\\', ''))
                        if link:
                            common.addon.log_debug('180Upload Link Found: %s' % link.group(1))
                            return link.group(1)

                raise Exception('Unable to resolve 180Upload Link')
        except urllib2.URLError as e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' % (e.code, url))
            return self.unresolvable(code=3, msg=e)
        except Exception as e:
            common.addon.log_error('**** 180upload Error occured: %s' % e)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://www.180upload.com/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('http://(.+?)/embed-([\w]+)-', url)
        if r:
            return r.groups()
        else:
            r = re.search('//(.+?)/([\w]+)', url)
            if r:
                return r.groups()
            else:
                return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?180upload.com/' +
                         '[0-9A-Za-z]+', url) or
                         '180upload' in host)

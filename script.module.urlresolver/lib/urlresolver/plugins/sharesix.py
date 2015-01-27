'''
sharesix urlresolver plugin
Copyright (C) 2014 tknorris

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
import re, urllib2, os, xbmcgui
from urlresolver import common

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

USER_AGENT='Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:30.0) Gecko/20100101 Firefox/30.0'

class SharesixResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "sharesix"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        try:
            headers = {
                'User-Agent': USER_AGENT,
                'Referer': web_url
            }
           # Otherwise just use the original url to get the content. For sharesix
            html = self.net.http_GET(web_url).content
            
            data = {}
            r = re.findall(r'type="hidden"\s*name="(.+?)"\s*value="(.*?)"', html)
            for name, value in r:
                data[name] = value
            #data[u"method_premium"] = "Premium"; 
            data[u"method_free"] = "Free"; 
            data[u"op"] = "download1"; data[u"referer"] = web_url; data[u"usr_login"] = "";
            html = self.net.http_POST(web_url, data, headers=headers).content
            
            r = re.search("var\s+lnk1\s*=\s*'(.*?)'", html)
            if r:
                stream_url=r.group(1)+'|User-Agent=%s' % (USER_AGENT)
                return stream_url
            else:
                raise Exception('Unable to locate link')
            
            if 'file you were looking for could not be found' in html:
                raise Exception ('File Not Found or removed')

        except urllib2.HTTPError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log_error('**** Sharesix Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]SHARESIX[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://%s/%s' % (host, media_id)
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?sharesix.com/' +
                         '[0-9A-Za-z]+', url) or
                         'sharesix' in host)

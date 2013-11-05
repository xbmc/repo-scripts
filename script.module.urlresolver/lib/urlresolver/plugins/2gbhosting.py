'''
2gbhosting urlresolver plugin
Copyright (C) 2011 t0mm0, DragonWin, jas0npc

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
from lib import jsunpack
import re, urllib2, os
from urlresolver import common

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = common.addon_path + '/resources/images/redx.png'

class TwogbhostingResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "2gbhosting"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        data = {}
        try:
            html = self.net.http_GET(web_url).content
            r = re.search('<input type="hidden" name="k" value="(.+?)" />', html)
            if not r:
                raise Exception ('File Not Found or removed') 
            if r:
                sid = r.group(1)
                common.addon.log_debug('eg-hosting: found k' + sid)
                data = { 'k' : sid,'submit' : 'Click Here To Continue', }
                common.addon.show_countdown(10, 'Please Wait', 'Resolving')
                html = self.net.http_POST(web_url, data).content
                r = re.findall("text/javascript'>\n.+?(eval\(function\(p,a,c,k,e,d\).+?)\n.+?</script>",html,re.I|re.M)
                if r:
                    unpacked = jsunpack.unpack(r[0])
                    unpacked = str(unpacked).replace('\\','')
                    r = re.findall(r"file\':\'(.+?)\'",unpacked)
                    return r[0]
                if not r:
                    raise Exception ('File Not Found or removed')

        except urllib2.URLError, e:
            common.addon.log_error('2gb-hosting: http error %d fetching %s' %
                                    (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)

        except Exception, e:
            common.addon.log_error('**** 2GB-hosting Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]2GBHOSTING[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://www.2gb-hosting.com/videos/%s' % media_id + '.html'
        
        
    def get_host_and_id(self, url):
        r = re.search('//(.+?)/[videos|v]/([0-9a-zA-Z/]+)', url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?2gb-hosting.com/[videos|v]/' +
                         '[0-9A-Za-z]+/[0-9a-zA-Z]+.*', url) or
                         '2gb-hosting' in host)

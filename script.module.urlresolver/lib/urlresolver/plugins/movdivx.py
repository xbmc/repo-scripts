"""
    urlresolver XBMC Addon
    Copyright (C) 2012 Bstrdsmkr

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib2
from urlresolver import common
from lib import jsunpack

# Custom imports
import re
import os

error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class MovDivxResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "movdivx"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        #e.g. http://movdivx.com/trrrw4r6bjqu/American_Dad__s_1_e_3_p1-1.flv.html
        self.pattern = 'http://(movdivx.com)/(.+?).html'


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        try:
            html = self.net.http_GET(web_url).content

            r =  'name="op" value="(.+?)">.+?'
            r += 'name="usr_login" value="(.+?)?">.+?'
            r += 'name="id" value="(.+?)".+?'
            r += 'name="fname" value="(.+?)".+?'
    
            r = re.search(r,html,re.DOTALL)
            op,usr_login,id,fname = r.groups()
            data =  {'op':op}
            data['usr_login'] = usr_login
            data['id'] = id
            data['fname'] = fname
            data['referer'] = web_url
            data['method_free'] = 'Continue to Stream'

            html = self.net.http_POST(web_url, data).content

            # get url from packed javascript
            sPattern =  '<script type=(?:"|\')text/javascript(?:"|\')>'
            sPattern += '(eval\(function\(p,a,c,k,e,d\).*?)</script>'
            
            matches = re.findall(sPattern, html, re.DOTALL + re.IGNORECASE)
            
            if matches:
                sJavascript=matches[-1]
                sUnpacked = jsunpack.unpack(sJavascript)
                sUnpacked = sUnpacked.replace('\\','')
                sPattern = "\('file','([^']+)"
                r = re.search(sPattern, sUnpacked)
                if r:
                    return r.group(1)

            raise Exception ('failed to parse link')

        except urllib2.URLError, e:
            common.addon.log_error('Movdivx: got http error %d fetching %s' %
                                  (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        
        except Exception, e:
            common.addon.log_error('**** Movdivx Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]MOVDIVX[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)


    def get_url(self, host, media_id):
            return 'http://movdivx.com/%s.html' % (media_id)

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host

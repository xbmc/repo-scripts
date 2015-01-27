"""
    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0

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

"""
RogerThis - 14/8/2011
Site: http://www.movshare.net
movshare hosts both avi and flv videos
"""

import re, urllib2, os
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
from lib import unwise
from lib import jsunpack

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')

class MovshareResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "movshare"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        """ Human Verification """
        try:
            self.net.http_HEAD(web_url)
            html = self.net.http_GET(web_url).content
            """movshare can do both flv and avi. There is no way I know before hand
            if the url going to be a flv or avi. So the first regex tries to find 
            the avi file, if nothing is present, it will check for the flv file.
            "param name="src" is for avi
            "flashvars.file=" is for flv
            """
            r = re.search('<param name="src" value="(.+?)"', html)
            if not r:
                filekey = re.search('flashvars.filekey="(.+?)";', html).group(0)

                #get stream url from api
                api = 'http://www.movshare.net/api/player.api.php?key=%s&file=%s' % (filekey, media_id)
                html = self.net.http_GET(api).content
                r = re.search('url=(.+?)&title', html)
            if r:
                stream_url = r.group(1)
            else:
                raise Exception ('File Not Found or removed')
            
            return stream_url
        except urllib2.HTTPError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log_error('**** Movshare Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]MOVSHARE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://www.movshare.net/video/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:video|embed)/([0-9a-z]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(?:www.)?movshare.net/(?:video|embed)/',
                        url) or 'movshare' in host

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

from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
import urllib2, re, os
from urlresolver import common
from lib import jsunpack

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')


class FilenukeResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "filenuke"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
        #e.g. http://www.filenuke.com/embed-rw52re7f5aul.html
        # http://www.filenuke.com/w8w7ow5nqu7r
        self.pattern = 'http://((?:www.)?filenuke.com)/([0-9a-zA-Z]+)'


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        try:
            resp = self.net.http_GET(web_url)
            html = resp.content
            post_url = resp.get_url()
            form_values = {}

            for i in re.finditer('<input type="hidden" name="(.+?)" value="(.+?)">', html):
                form_values[i.group(1)] = i.group(2)

            for i in re.finditer('<input type="submit" name="(.+?)" class="btn-big2-2" style="border: none;" value="(.+?)">', html):
                form_values[i.group(1)] = i.group(2)
                
            form_values[u'usr_login'] = u''
            form_values[u'referer'] = u''
            form_values[u'op'] = u'download1'
            html = self.net.http_POST(post_url, form_data=form_values).content
            r = re.findall('return p}\(\'(.+?);\',\d+,\d+,\'(.+?)\'\.split',html)
            if r:
                p = r[1][0]
                k = r[1][1]
            else:
                raise Exception ('File Not Found or removed')

            decrypted_data = unpack_js(p, k)
            #First checks for a flv url, then the if statement is for the avi url
            r = re.search('file.\',.\'(.+?).\'', decrypted_data)
            if not r:
                r = re.search('src="(.+?)"', decrypted_data)
            if r:
                stream_url = r.group(1)
            else:
                raise Exception ('File Not Found or removed')

            return stream_url

        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log_error('**** Filenuke Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]FILENUKE[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
            return 'http://filenuke.com/%s' % (media_id)# removed www. as it was causing 502 errors.

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url)
        if r:
            return r.groups()
        else:
            return False


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match(self.pattern, url) or self.name in host
        
def unpack_js(p, k):
    '''emulate js unpacking code'''
    k = k.split('|')
    for x in range(len(k) - 1, -1, -1):
        if k[x]:
            p = re.sub('\\b%s\\b' % base36encode(x), k[x], p)
    return p


def base36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvwxyz'):
    """Convert positive integer to a base36 string. (from wikipedia)"""
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')
 
    # Special case for zero
    if number == 0:
        return alphabet[0]

    base36 = ''

    sign = ''
    if number < 0:
        sign = '-'
        number = - number

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


'''
vidplay urlresolver plugin
Copyright (C) 2013 Lynx187

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
from lib import captcha_lib
import re, urllib2, os, xbmcgui, xbmc

net = Net()

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')
datapath = common.profile_path

class VidplayResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidplay"
    
    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        try:
            puzzle_img = os.path.join(datapath, "vidplay_puzzle.png")
            html = net.http_GET(web_url).content
            
            if re.search('File Not Found ',html):
                msg = 'File Not Found or removed'
                common.addon.show_small_popup(title='[B][COLOR white]VIDPLAY[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' 
                % msg, delay=5000, image=error_logo)
                return self.unresolvable(code = 1, msg = msg)
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)

            if r:
                for name, value in r:
                    data[name] = value
            else:
                raise Exception('Unable to resolve vidplay Link')
        
            #Check for SolveMedia Captcha image
            solvemedia = re.search('<iframe src="(http://api.solvemedia.com.+?)"', html)
            recaptcha = re.search('<script type="text/javascript" src="(http://www.google.com.+?)">', html)
    
            if solvemedia:
                data.update(captcha_lib.do_solvemedia_captcha(solvemedia.group(1), puzzle_img))
            elif recaptcha:
                data.update(captcha_lib.do_recaptcha(recaptcha.group(1)))
            else:
                captcha = re.compile("left:(\d+)px;padding-top:\d+px;'>&#(.+?);<").findall(html)
                result = sorted(captcha, key=lambda ltr: int(ltr[0]))
                solution = ''.join(str(int(num[1])-48) for num in result)
                data.update({'code':solution})

            common.addon.log('VIDPLAY - Requesting POST URL: %s with data: %s' % (web_url, data))
            html = net.http_POST(web_url, data).content
            sPattern = '''<div id="player_code">.*?<script type='text/javascript'>(eval.+?)</script>'''
            r = re.findall(sPattern, html, re.DOTALL|re.I)
            if r:
                sUnpacked = jsunpack.unpack(r[0])
                sUnpacked = sUnpacked.replace("\\'","")
                r = re.findall('file,(.+?)\)\;s1',sUnpacked)
                if not r:
                   r = re.findall('name="src"[0-9]*="(.+?)"/><embed',sUnpacked)
                if not r:
                    r = re.findall('<param name="src"value="(.+?)"/>', sUnpacked)
                return r[0]
            else:
                common.addon.log('***** VidPlay - Cannot find final link')
                raise Exception('Unable to resolve VidPlay Link')

        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log_error('**** Vidplay Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]VIDPLAY[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

        
    def get_url(self, host, media_id):
        return 'http://vidplay.net/%s' % media_id 
        
        
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
        return (re.match('http://(www.)?vidplay.net/' +
                         '[0-9A-Za-z]+', url) or
                         'vidplay' in host)

'''
Vidhog urlresolver plugin
Copyright (C) 2013 Vinnydude

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
import re, time
from urlresolver import common

net = Net()

class VidhogResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidhog"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        try:
            url = self.get_url(host, media_id)
            html = self.net.http_GET(url).content
            check = re.compile('fname').findall(html)
            if check:
                data = {}
                r = re.findall(r'type="(?:hidden|submit)?" name="(.+?)"\s* value="?(.+?)">', html)
                for name, value in r:
                    data[name] = value
                html = net.http_POST(url, data).content
    
            else:
                data = {}
                r = re.findall(r'type="(?:hidden|submit)?" name="(.+?)"\s* value="?(.+?)">', html)
                for name, value in r:
                    data[name] = value
                    
                captchaimg = re.search('<img src="(http://www.vidhog.com/captchas/.+?)"', html)
                if captchaimg:
                    img = xbmcgui.ControlImage(550,15,240,100,captchaimg.group(1))
                    wdlg = xbmcgui.WindowDialog()
                    wdlg.addControl(img)
                    wdlg.show()
                    time.sleep(3)
                    kb = xbmc.Keyboard('', 'Type the letters in the image', False)
                    kb.doModal()
                    capcode = kb.getText()
                    if (kb.isConfirmed()):
                        userInput = kb.getText()
                        if userInput != '':
                                capcode = kb.getText()
                        elif userInput == '':
                                raise Exception ('You must enter text in the image to access video')
                    wdlg.close()
                    common.addon.show_countdown(10, title='Vidhog', text='Loading Video...')
                    
                    data.update({'code':capcode})
    
                else:
                    common.addon.show_countdown(20, title='Vidhog', text='Loading Video...')
                    
            html = net.http_POST(url, data).content
            if re.findall('err', html):
                raise Exception('Wrong Captcha')
    
            match = re.search("product_download_url=(.+?)'", html)
    
            if not match:
                raise Exception('could not find video')
            return match.group(1)
        
        except Exception, e:
            common.addon.log('**** Muchshare Error occured: %s' % e)
            common.addon.show_small_popup('Error', str(e), 5000, '')
            return self.unresolvable(code=0, msg='Exception: %s' % e)
        
    def get_url(self, host, media_id):
        return 'http://www.vidhog.com/%s' % media_id 
        

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?vidhog.com/' +
                         '[0-9A-Za-z]+', url) or
                         'vidhog' in host)

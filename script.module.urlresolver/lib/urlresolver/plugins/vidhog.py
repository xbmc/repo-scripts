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
import re
import urllib2, xbmcgui, time, xbmc
from urlresolver import common
import os

net = Net()

class VidhogResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "vidhog"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        print 'Vidhog: in get_media_url %s %s' % (host, media_id)
        url = self.get_url(host, media_id)
        html = self.net.http_GET(url).content
        #Show dialog box so user knows something is happening
        dialog = xbmcgui.DialogProgress()
        dialog.create('Resolving', 'Resolving Vidhog Link...')       
        dialog.update(0)

        op = re.search('<input type="hidden" name="op" value="(.+?)">', html).group(1)
        usr_login = ''
        postid = re.search('<input type="hidden" name="id" value="(.+?)">', html).group(1)
        fname = re.search('<input type="hidden" name="fname" value="(.+?)">', html).group(1)
        method_free = 'Free Download'

        data = {'op': op, 'usr_login': usr_login, 'id': postid, 'fname': fname, 'referer': url, 'method_free': method_free}

        print 'Vidhog - Requesting POST URL: %s DATA: %s' % (url, data)
        html = net.http_POST(url, data).content

        captchaimg = re.search('<img src="(http://www.vidhog.com/captchas/.+?)"', html).group(1)
        img = xbmcgui.ControlImage(550,15,240,100,captchaimg)
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
                        Notify('big', 'No text entered', 'You must enter text in the image to access video', '')
        wdlg.close()

        dialog.create('Resolving', 'Resolving Vidhog Link...') 
        dialog.update(50)

        op = 'download2'
        postid = re.search('<input type="hidden" name="id" value="(.+?)">', html).group(1)
        rand = re.search('<input type="hidden" name="rand" value="(.+?)">', html).group(1)
        method_free = 'Free Download'
        down_direct = 1

        time.sleep(10)
        
        data = {'op': op, 'id': postid, 'rand': rand, 'referer': url, 'method_free': method_free, 'down_direct': down_direct, 'code': capcode}

        print 'Vidhog - Requesting POST URL: %s DATA: %s' % (url, data)
        html = net.http_POST(url, data).content

        match = re.search("product_download_url=(.+?)'", html)

        if not match:
            print 'could not find video'
            return False
        return match.group(1)
    
        
    def get_url(self, host, media_id):
        print 'vidhog: in get_url %s %s' % (host, media_id)
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

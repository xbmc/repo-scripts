'''
Billionuploads urlresolver plugin
Copyright (C) 2013 jas0npc

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

import re,cookielib,xbmcplugin,xbmcgui,xbmcaddon,xbmc
import urllib2,time
from urlresolver import common
from t0mm0.common.net import Net 
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
net = Net()

class billionuploads(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "billionuploads"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        try:
            url = 'http://'+host+'/'+media_id
            #Show dialog box so user knows something is happening
            dialog = xbmcgui.DialogProgress()
            dialog.create('Resolving', 'Resolving BillionUploads Link...')       
            dialog.update(0)
        
            print 'BillionUploads - Requesting GET URL: %s' %url
            html = net.http_GET(url).content
               
            #Check page for any error msgs
            if re.search('This server is in maintenance mode', html):
                print '***** BillionUploads - Site reported maintenance mode'
                raise Exception('File is currently unavailable on the host')

            #Captcha
            captchaimg = re.search('<img src="((http://)?[bB]illion[uU]ploads.com/captchas/.+?)"', html).group(1)
        
            dialog.close()
        
            #Grab Image and display it
            img = xbmcgui.ControlImage(550,15,240,100,captchaimg)
            wdlg = xbmcgui.WindowDialog()
            wdlg.addControl(img)
            wdlg.show()
        
            #Small wait to let user see image
            time.sleep(3)
        
            #Prompt keyboard for user input
            kb = xbmc.Keyboard('', 'Type the letters in the image', False)
            kb.doModal()
            capcode = kb.getText()
        
            #Check input
            if (kb.isConfirmed()):
              userInput = kb.getText()
              if userInput != '':
                  capcode = kb.getText()
              elif userInput == '':
                   Notify('big', 'No text entered', 'You must enter text in the image to access video', '')
                   return None
            else:
                return None
            wdlg.close()

            #They need to wait for the link to activate in order to get the proper 2nd page
            dialog.close()
            #do_wait('Waiting on link to activate', '', 3)
            time.sleep(3)  
            dialog.create('Resolving', 'Resolving BillionUploads Link...') 
            dialog.update(50)
        
            #Set POST data values
            op = 'download2'
            rand = re.search('<input type="hidden" name="rand" value="(.+?)">', html).group(1)
            postid = re.search('<input type="hidden" name="id" value="(.+?)">', html).group(1)
            method_free = re.search('<input type="hidden" name="method_free" value="(.*?)">', html).group(1)
            down_direct = re.search('<input type="hidden" name="down_direct" value="(.+?)">', html).group(1)
                
            data = {'op': op, 'rand': rand, 'id': postid, 'referer': url, 'method_free': method_free, 'down_direct': down_direct, 'code': capcode}
        
            print 'BillionUploads - Requesting POST URL: %s DATA: %s' % (url, data)
            html = net.http_POST(url, data).content
            dialog.update(100)
            link = re.search('&product_download_url=(.+?)"', html).group(1)
            link = link + "|referer=" + url
            dialog.close()
            mediaurl = link
        
            return mediaurl

        except Exception, e:
            print '**** BillionUploads Error occured: %s' % e
            raise
    

    def get_url(self, host, media_id):
        return 'http://www.BillionUploads.com/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return ('host', 'media_id')

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?[bB]illion[uU]ploads.com/' +
                         '[0-9A-Za-z]+', url) or
                         '[bB]illion[uU]ploads' in host)

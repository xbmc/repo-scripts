'''
Hugefiles urlresolver plugin
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
import re, os, urllib2
from urlresolver import common
from lib import jsunpack
import xbmc, xbmcgui

error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')
net = Net()

class HugefilesResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "hugefiles"


    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()


    def get_media_url(self, host, media_id):
        try:
            url = self.get_url(host, media_id)
            puzzle_img = os.path.join(common.profile_path, "hugefiles_puzzle.png")

            #Show dialog box so user knows something is happening
            dialog = xbmcgui.DialogProgress()
            dialog.create('Resolving', 'Resolving HugeFiles Link...')       
            dialog.update(0)
            
            common.addon.log('HugeFiles - Requesting GET URL: %s' % url)
            html = self.net.http_GET(url).content
            r = re.findall('File Not Found',html)
            if r:
                raise Exception ('File Not Found or removed')
                            
            dialog.update(50)
            
            #Check page for any error msgs
            if re.search('<b>File Not Found</b>', html):
                common.addon.log('***** HugeFiles - File Not Found')
                raise Exception('File Not Found')
    
            #Set POST data values
            data = {}
            r = re.findall(r'type="hidden" name="(.+?)" value="(.+?)">', html)
            
            if r:
                for name, value in r:
                    data[name] = value
            else:
                common.addon.log('***** HugeFiles - Cannot find data values')
                raise Exception('Unable to resolve HugeFiles Link')
            
            data['method_free'] = 'Free Download'
            file_name = data['fname']
    
            #Check for SolveMedia Captcha image
            solvemedia = re.search('<iframe src="(http://api.solvemedia.com.+?)"', html)
            recaptcha = re.search('<script type="text/javascript" src="(http://www.google.com.+?)">', html)
    
            if solvemedia:
               dialog.close()
               html = self.net.http_GET(solvemedia.group(1)).content
               hugekey=re.search('id="adcopy_challenge" value="(.+?)">', html).group(1)
               open(puzzle_img, 'wb').write(net.http_GET("http://api.solvemedia.com%s" % re.search('<img src="(.+?)"', html).group(1)).content)
               img = xbmcgui.ControlImage(450,15,400,130, puzzle_img)
               wdlg = xbmcgui.WindowDialog()
               wdlg.addControl(img)
               wdlg.show()
            
               xbmc.sleep(3000)
    
               kb = xbmc.Keyboard('', 'Type the letters in the image', False)
               kb.doModal()
               capcode = kb.getText()
       
               if (kb.isConfirmed()):
                   userInput = kb.getText()
                   if userInput != '':
                       solution = kb.getText()
                   elif userInput == '':
                       Notify('big', 'No text entered', 'You must enter text in the image to access video', '')
                       return False
               else:
                   return False
                   
               wdlg.close()
               dialog.create('Resolving', 'Resolving HugeFiles Link...') 
               dialog.update(50)
               if solution:
                   data.update({'adcopy_challenge': hugekey,'adcopy_response': solution})

            elif recaptcha:
                dialog.close()
                html = self.net.http_GET(recaptcha.group(1)).content
                part = re.search("challenge \: \\'(.+?)\\'", html)
                captchaimg = 'http://www.google.com/recaptcha/api/image?c='+part.group(1)
                img = xbmcgui.ControlImage(450,15,400,130,captchaimg)
                wdlg = xbmcgui.WindowDialog()
                wdlg.addControl(img)
                wdlg.show()
        
                xbmc.sleep(3000)
        
                kb = xbmc.Keyboard('', 'Type the letters in the image', False)
                kb.doModal()
                capcode = kb.getText()
        
                if (kb.isConfirmed()):
                    userInput = kb.getText()
                    if userInput != '':
                        solution = kb.getText()
                    elif userInput == '':
                        raise Exception ('You must enter text in the image to access video')
                else:
                    raise Exception ('Captcha Error')
                wdlg.close()
                dialog.close() 
                dialog.create('Resolving', 'Resolving HugeFiles Link...') 
                dialog.update(50)
                data.update({'recaptcha_challenge_field':part.group(1),'recaptcha_response_field':solution})

            else:
                captcha = re.compile("left:(\d+)px;padding-top:\d+px;'>&#(.+?);<").findall(html)
                result = sorted(captcha, key=lambda ltr: int(ltr[0]))
                solution = ''.join(str(int(num[1])-48) for num in result)
                data.update({'code':solution})

            common.addon.log('HugeFiles - Requesting POST URL: %s DATA: %s' % (url, data))
            html = net.http_POST(url, data).content
            
            #Get download link
            dialog.update(100)
    
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
                common.addon.log('***** HugeFiles - Cannot find final link')
                raise Exception('Unable to resolve HugeFiles Link')
        

        except urllib2.HTTPError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 5000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log_error('**** Hugefiles Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]HUGEFILES[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)
        finally:
            dialog.close()
        
    def get_url(self, host, media_id):
        return 'http://hugefiles.net/%s' % media_id 
        

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/([0-9a-zA-Z]+)',url)
        if r:
            return r.groups()
        else:
            return False
        return('host', 'media_id')


    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return (re.match('http://(www.)?hugefiles.net/' +
                         '[0-9A-Za-z]+', url) or
                         'hugefiles' in host)

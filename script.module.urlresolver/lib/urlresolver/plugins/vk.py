#-*- coding: utf-8 -*-

"""
VK urlresolver XBMC Addon
Copyright (C) 2013 JUL1EN094

Version 0.0.1 

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
"""
import urllib2, os, re, xbmcgui
from t0mm0.common.net import Net
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from urlresolver import common
import simplejson as json

#SET ERROR_LOGO# THANKS TO VOINAGE, BSTRDMKR, ELDORADO
error_logo = os.path.join(common.addon_path, 'resources', 'images', 'redx.png')
#SET OK_LOGO#
ok_logo = os.path.join(common.addon_path, 'resources', 'images', 'greeninch.png')
    
    
class VKResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "VK.com"

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()
            
    def get_media_url(self, host, media_id):
        base_url = self.get_url(host, media_id)
        try:
            soup   = self.net.http_GET(base_url).content
            html   = soup.decode('cp1251')
            vars_s = re.findall("""var vars = (.+)""",html)
            if vars_s :
                jsonvars        = json.loads(vars_s[0])
                purged_jsonvars = {}
                for item in jsonvars :
                    if re.search('url[0-9]+', str(item)) :
                        purged_jsonvars[item] = jsonvars[item]               
                lines  = []
                ls_url = []
                best='0'
                for item in purged_jsonvars :
                    ls_url.append(item)
                    quality = item.lstrip('url')
                    lines.append(str(quality))
                    if int(quality)>int(best): best=quality

                if len(ls_url) == 1 :
                    return purged_jsonvars[ls_url[0]].encode('utf-8')
                else:
                    if self.get_setting('auto_pick')=='true':
                        return purged_jsonvars['url%s' % (str(best))].encode('utf-8')
                    else:
                        result = xbmcgui.Dialog().select('Choose the link', lines)
                if result != -1 :
                    return purged_jsonvars[ls_url[result]].encode('utf-8')
                else :
                    return self.unresolvable(0,'No link selected')
            else :
                return self.unresolvable(0,'No var_s found')
        except urllib2.URLError, e:
            common.addon.log_error(self.name + ': got http error %d fetching %s' %
                                   (e.code, web_url))
            common.addon.show_small_popup('Error','Http error: '+str(e), 8000, error_logo)
            return self.unresolvable(code=3, msg=e)
        except Exception, e:
            common.addon.log('**** VK Error occured: %s' % e)
            common.addon.show_small_popup(title='[B][COLOR white]VK[/COLOR][/B]', msg='[COLOR red]%s[/COLOR]' % e, delay=5000, image=error_logo)
            return self.unresolvable(code=0, msg=e)

    def get_url(self, host, media_id):
        return 'http://%s.com/video_ext.php?%s' % (host, media_id)

    def get_host_and_id(self, url):
        r = re.search('http[s]*://(?:www.)?(.+?).com/video_ext.php\?(.+)', url)
        if r :
            ls = r.groups()
            if ls[0] == 'www.' or ls[0] == None :
                ls = (ls[1],ls[2])
            return ls
        else :
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': 
            return False
        return re.match('http[s]*://(?:www.)?vk.com/video_ext.php\?.+',url) or 'vk' in host    

    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting id="%s_auto_pick" type="bool" label="Automatically pick best quality" default="false" visible="true"/>' % (self.__class__.__name__)   
        return xml

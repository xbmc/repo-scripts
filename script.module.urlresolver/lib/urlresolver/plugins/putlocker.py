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

import re
import os
import xbmcgui
import xbmc
from t0mm0.common.net import Net
import urllib2
import urllib
from urlresolver import common
from urlresolver.plugnplay.interfaces import UrlResolver
from urlresolver.plugnplay.interfaces import PluginSettings
from urlresolver.plugnplay import Plugin
from threading import Thread
import time

class PutlockerResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "putlocker"
    domains = [ "putlocker.com", "filedrive.com", "firedrive.com" ]
    profile_path = common.profile_path
    cookie_file = os.path.join(profile_path, 'putlocker.cookies')

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        if self.get_setting('login') == 'true':
            if self.login_stale():
                self.login()
        self.net.set_cookies(self.cookie_file)
        web_url = self.get_url(host, media_id)
        if web_url[-1:1] == "#": web_url.replace("#", "");

        # find session_hash
        html = self.net.http_GET(web_url).content
        if ">This file doesn't exist, or has been removed.<" in html: raise Exception (host + ": This file doesn't exist, or has been removed.")
        elif "This file might have been moved, replaced or deleted.<" in html: raise Exception (host + ": This file might have been moved, replaced or deleted.")
        # Shortcut for logged in users
        pattern = '<a href="(/.+?)" class="download_file_link" style="margin:0px 0px;">Download File</a>'
        link = re.search(pattern, html)
        if link:
            common.addon.log('Direct link found: %s' % link.group(1))
            if 'putlocker' in host:
                return 'http://www.filedrive.com%s' % link.group(1)
                # return 'http://www.putlocker.com%s' % link.group(1)
            elif 'filedrive' in host:
                return 'http://www.filedrive.com%s' % link.group(1)
            elif 'firedrive' in host:
                return 'http://www.firedrive.com%s' % link.group(1)

        if ('firedrive' in host) or ('filedrive' in host) or ('putlocker' in host):
            try:
                data = {}; r = re.findall(r'type="hidden" name="(.+?)"\s* value="?(.+?)"/>', html);  # data['usr_login']=''
                for name, value in r: data[name] = value
                # data['imhuman']='Proceed to video'; data['btn_download']='Proceed to video'
                # xbmc.sleep(2000)
                html = self.net.http_POST(web_url, data).content
            except urllib2.URLError, e:
                common.addon.log_error(host + ': got http error %d fetching 2nd url %s' % (e.code, web_url))
                return self.unresolvable(code=3, msg='Exception: %s' % e)  # return False
            if "file: '" in html:
                r = re.search("file\s*:\s*'(.+?)'", html)
                if r: return urllib.unquote_plus(r.group(1))
            if '" target="_blank" ' + "id='top_external_download' title='Download This File'>" in html:
                r = re.search('<a href="(.+?)" target="_blank" ' + "id='top_external_download' title='Download This File'>", html)
                if r: return urllib.unquote_plus(r.group(1))
            if "id='external_download' title='Download This File'>" in html:
                r = re.search('<a href="(.+?)" id=\'external_download\' title=\'Download This File\'>', html)
                if r: return urllib.unquote_plus(r.group(1))
            if "<a id='fd_vid_btm_download_front' title='Copy to my computer' class='video_bottom_buttons' target='_blank' href='" in html:
                r = re.search("<a id='fd_vid_btm_download_front' title='Copy to my computer' class='video_bottom_buttons' target='_blank' href='(.+?)'>", html)
                if r: return urllib.unquote_plus(r.group(1))
            # if r:
            #    return urllib.unquote_plus(r.group(1))
            # else:
            #    common.addon.log_error(host+': stream url not found')
            #    return self.unresolvable(code=0, msg='no file located') #return False
            r = re.search("$.post('(.+?)', function(data) {", html)
            if r:
                return urllib.unquote_plus(r.group(1))
            else:
                common.addon.log_error(host + ': stream url not found')
                return self.unresolvable(code=0, msg='no file located')  # return False
        else:
            r = re.search('value="([0-9a-f]+?)" name="hash"', html)
            if r:
                session_hash = r.group(1)
            else:
                raise Exception ('putlocker: session hash not found')
            # post session_hash
            html = self.net.http_POST(web_url, form_data={'hash': session_hash,
                                                       'confirm': 'Continue as Free User'}).content

        # find playlist code
        r = re.search('\?stream=(.+?)\'', html)
        if r:
            playlist_code = r.group(1)
        else:
            r = re.search('key=(.+?)&', html)
            playlist_code = r.group(1)

        # find download link
        q = self.get_setting('quality')

        # Try to grab highest quality link available
        if q == '1':
            # download & return link.
            if 'putlocker' in host:
                Avi = "http://putlocker.com/get_file.php?stream=%s&original=1" % playlist_code
                html = self.net.http_GET(Avi).content
                final = re.compile('url="(.+?)"').findall(html)[0].replace('&amp;', '&')
                return "%s|User-Agent=%s" % (final, 'Mozilla%2F5.0%20(Windows%20NT%206.1%3B%20rv%3A11.0)%20Gecko%2F20100101%20Firefox%2F11.0')
            elif 'filedrive' in host:
                Avi = "http://filedrive.com/get_file.php?stream=%s&original=1" % playlist_code
                html = self.net.http_GET(Avi).content
                final = re.compile('url="(.+?)"').findall(html)[0].replace('&amp;', '&')
                return "%s|User-Agent=%s" % (final, 'Mozilla%2F5.0%20(Windows%20NT%206.1%3B%20rv%3A11.0)%20Gecko%2F20100101%20Firefox%2F11.0')
            elif 'firedrive' in host:
                Avi = "http://firedrive.com/get_file.php?stream=%s&original=1" % playlist_code
                html = self.net.http_GET(Avi).content
                final = re.compile('url="(.+?)"').findall(html)[0].replace('&amp;', '&')
                return "%s|User-Agent=%s" % (final, 'Mozilla%2F5.0%20(Windows%20NT%206.1%3B%20rv%3A11.0)%20Gecko%2F20100101%20Firefox%2F11.0')


        # Else grab standard flv link
        else:
            xml_url = re.sub('/(file|embed)/.+', '/get_file.php?stream=', web_url)
            xml_url += playlist_code
            html = self.net.http_GET(xml_url).content

            r = re.search('url="(.+?)"', html)
            if r:
                flv_url = r.group(1)
            else:
                raise Exception ('putlocker: stream url not found')

            return "%s|User-Agent=%s" % (flv_url.replace('&amp;', '&'), 'Mozilla%2F5.0%20(Windows%20NT%206.1%3B%20rv%3A11.0)%20Gecko%2F20100101%20Firefox%2F11.0')

    def get_url(self, host, media_id):
            if 'putlocker' in host:
                host = 'www.putlocker.com'
                host = 'www.firedrive.com'
                media_id = media_id.replace("#", "");
            elif 'filedrive' in host:
                host = 'www.filedrive.com'
            elif 'firedrive' in host:
                host = 'www.firedrive.com'
            else:
                host = 'www.firedrive.com'
                media_id = media_id.replace("#", "");
            return 'http://%s/file/%s' % (host, media_id)


    def get_host_and_id(self, url):
            r = re.search('//(.+?)/(?:file|embed)/([0-9A-Z]+)', url)
            if r:
                return r.groups()
            else:
                return False

    def valid_url(self, url, host):
            if self.get_setting('enabled') == 'false': return False
            return (re.match('http://(?:www.)?(putlocker|filedrive|firedrive)?\.com/' + '(file|embed)?/[0-9A-Z]+', url) or 'putlocker' in host or 'sockshare' in host or 'filedrive' in host or 'firedrive' in host)

    def login_stale(self):
            url = 'http://www.putlocker.com/cp.php'
            if not os.path.exists(self.cookie_file):
                return True
            self.net.set_cookies(self.cookie_file)
            source = self.net.http_GET(url).content
            if re.search('(?:<span class=pro_user>\( Pro \)</span>|<span class="free_user">\( Free \)</span>)', source):
                common.addon.log('Putlocker account appears to be logged in.')
                return False
            else:
                return True

    # SiteAuth methods
    def login(self):
        if self.login_stale():
            url = 'http://www.putlocker.com/authenticate.php?login'
            source = self.net.http_GET(url).content
            self.net.save_cookies(self.cookie_file)
            self.net.set_cookies(self.cookie_file)
            captcha_img = re.search('<td>CAPTCHA</td>.+?<td><img src="(.+?)" /><br>', source, re.DOTALL).group(1)
            captcha_img = 'http://www.putlocker.com%s' % re.sub('&amp;', '&', captcha_img)
            local_captcha = os.path.join(common.profile_path, "captcha.img")
            localFile = open(local_captcha, "wb")
            localFile.write(self.net.http_GET(captcha_img).content)
            localFile.close()
            solver = InputWindow(captcha=local_captcha)
            solution = solver.get()
            if solution:
                common.addon.log('Solution provided: %s' % solution)
                data = {'user':self.get_setting('username'), 'pass':self.get_setting('password'), 'captcha_code':solution, 'remember':1, 'login_submit':'Login'}
                response = self.net.http_POST(url, form_data=data)
                self.net.save_cookies(self.cookie_file)
                self.net.set_cookies(self.cookie_file)
            else:
                common.addon.log('Dialog was canceled')
                return False


            if re.search('OK', source):
                self.net.save_cookies(self.cookie_file)
                self.net.set_cookies(self.cookie_file)
                xbmc.executebuiltin("Notification(' Putlocker Pro ', ' Login successful')")
                return True
            else: return False
        else: return True

    # PluginSettings methods
    def get_settings_xml(self):
        xml = PluginSettings.get_settings_xml(self)
        xml += '<setting label="Highest Quality" id="%s_quality" ' % self.__class__.__name__
        xml += 'type="enum" values="FLV|Maximum" default="0" />\n'
        xml += '<setting id="%s_login" ' % self.__class__.__name__
        xml += 'type="bool" label="login" default="false"/>\n'
        xml += '<setting id="%s_username" enable="eq(-1,true)" ' % self.__class__.__name__
        xml += 'type="text" label="username" default=""/>\n'
        xml += '<setting id="%s_password" enable="eq(-2,true)" ' % self.__class__.__name__
        xml += 'type="text" label="password" option="hidden" default=""/>\n'
        xml += '<setting id="%s_notify" ' % self.__class__.__name__
        xml += 'type="bool" label="Notify on login" default="false"/>\n'
        return xml

class InputWindow(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.cptloc = kwargs.get('captcha')
        self.img = xbmcgui.ControlImage(335, 30, 624, 60, self.cptloc)
        self.addControl(self.img)
        self.kbd = xbmc.Keyboard()

    def get(self):
        self.show()
        time.sleep(5)
        self.kbd.doModal()
        if (self.kbd.isConfirmed()):
            text = self.kbd.getText()
            self.close()
            return text
        self.close()
        return False

"""
    urlresolver XBMC Addon
    Copyright (C) 2014 tknorris

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
from urlresolver import common
import urllib2, urllib
from time import sleep
import re
import xbmc

class BestreamsResolver(Plugin, UrlResolver, PluginSettings):
    implements = [UrlResolver, PluginSettings]
    name = "bestreams"
    domains = ["bestreams.net"]

    def __init__(self):
        p = self.get_setting('priority') or 100
        self.priority = int(p)
        self.net = Net()

    def get_media_url(self, host, media_id):
        try:
            web_url = self.get_url(host, media_id)
            html = self.net.http_GET(web_url).content
            headers = {
                'Referer': web_url
            }

            data = {}
            r = re.findall(r'type="hidden"\s*name="(.+?)"\s*value="(.*?)"', html)
            for name, value in r: data[name] = value
            data.update({'referer': web_url})
            data.update({'imhuman': 'Proceed to video'})

            # parse cookies from file as they are only useful for this interaction
            cookies = {}
            for match in re.finditer("\$\.cookie\('([^']+)',\s*'([^']+)", html):
                key, value = match.groups()
                cookies[key] = value
            headers['Cookie'] = urllib.urlencode(cookies)

            xbmc.sleep(2000)  # POST seems to fail is submitted too soon after GET. Page Timeout?
            #sleep(2)

            html = self.net.http_POST(web_url, data, headers=headers).content
            ##print html #<< has character errors
            #htmlA=html.splitlines() #<< to print as much as possible, skipping lines with unhandable characters.
            #for htmlAa in htmlA:
            #	try: print htmlAa
            #	except: pass

            #sleep(6)
            r = re.search('file\s*:\s*"(http://.+?)"', html) #Incase they start using this again.
            if r:
                return r.group(1)
            r = re.search('streamer\s*:\s*"(\D+://.+?)"', html)
            r2 = re.search('file\s*:\s*"([^"]+)', html)
            if r and r2:
                return r.group(1)+" Playpath="+r2.group(1)+" swfUrl=http://bestreams.net/player/player.swf pageUrl=http://bestreams.net swfVfy=1" # live=false timeout=30
            if r:
                return r.group(1)
            raise Exception("File Link Not Found")

        except urllib2.URLError, e:
            common.addon.log_error('bestreams: got http error %d fetching %s' %
                                  (e.code, web_url))
            return self.unresolvable(code=3, msg=e)

        except Exception, e:
            common.addon.log_error('bestreams: general error occured: %s' % e)
            return self.unresolvable(code=0, msg=e)

        return False

    def get_url(self, host, media_id):
        return 'http://bestreams.net/%s' % media_id

    def get_host_and_id(self, url):
        r = re.search('//(.+?)/(?:embed-)?([A-Za-z0-9]+)', url)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if self.get_setting('enabled') == 'false': return False
        return re.match('http://(www.)?bestreams.net/(embed-)?[A-Za-z0-9]+', url) or "bestreams.net" in host


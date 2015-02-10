#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
#
# https://docs.google.com/document/d/1_rs5BXklnLqGS6g6eAjevVHsPafv4PXDCi_dAM2b7G0/edit?pli=1
#
import cookielib
import urllib2
try:
    import json
except:
    import simplejson as json

API_URL = 'http://api.yousee.tv/rest'
API_KEY = 'HCN2BMuByjWnrBF4rUncEfFBMXDumku7nfT3CMnn'

AREA_TVGUIDE = 'tvguide'

class YouSeeApi(object):
    COOKIE_JAR = cookielib.LWPCookieJar()

    def __init__(self):
        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor(self.COOKIE_JAR)))

    def _invoke(self, area, function, params=dict()):
        url = API_URL + '/' + area + '/' + function
        for key, value in params.items():
            url += '/' + key + '/' + str(value)
        url += '/format/json'

        print 'Invoking URL: ' + url

        r = urllib2.Request(url, headers = {'X-API-KEY' : API_KEY})
        u = urllib2.urlopen(r)
        data = u.read()
        u.close()

        return json.loads(data)


class YouSeeTVGuideApi(YouSeeApi):
    def channelsInCategory(self, category):
        channels = self.channels()

        for channel in channels:
            if channel['name'] == category:
                return channel['channels']

        return None

    def channels(self):
        """
        Returns complete channel list ordered in channel packages.

        Note: the channel package "Mine Kanaler" contains the default channels a user should have in her favorites, until overwritten by the user herself.
        """
        return self._invoke(AREA_TVGUIDE, 'channels')

    def categories(self):
        """
        Returns complete list of categories
        """
        return self._invoke(AREA_TVGUIDE, 'categories')

    def programs(self, channelId= None, offset = None, tvdate = None):
        """
        Returns program list

        @param:channel_id (optional)
        @param: offset (optional) default -1 (yesterday)
        @param: tvdate (optional) format: yyyy-mm-dd (overrides offset)
        @type: tvdate datetime.datetime
        """

        params = dict()
        if channelId is not None:
            params['channel_id'] = channelId
        if tvdate is not None:
            params['tvdate'] = tvdate.strftime('%Y-%m-%d')
        elif offset is not None:
            params['offset'] = offset

        return self._invoke(AREA_TVGUIDE, 'programs', params)



if __name__ == '__main__':
    api = YouSeeTVGuideApi()
    data = api.channels()

    entries = dict()

    for channels in data:
        for channel in channels['channels']:
            if not entries.has_key(channel['name']):
                entries[channel['name']] = 'plugin://plugin.video.yousee.tv/?channel=%s' % channel['id']

    for e in sorted(entries.keys()):
        print e + '=' + entries[e]

    #s = simplejson.dumps(json, sort_keys=True, indent='    ')
    #print '\n'.join([l.rstrip() for l in  s.splitlines()])


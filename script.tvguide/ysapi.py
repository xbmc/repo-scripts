"""
https://docs.google.com/document/d/1_rs5BXklnLqGS6g6eAjevVHsPafv4PXDCi_dAM2b7G0/edit?pli=1
"""

import cookielib
import urllib2
import simplejson

API_URL = 'http://api.yousee.tv/rest'
API_KEY = 'HCN2BMuByjWnrBF4rUncEfFBMXDumku7nfT3CMnn'

AREA_TVGUIDE = 'tvguide'

class YouSeeApi(object):
    COOKIE_JAR = cookielib.LWPCookieJar()

    def __init__(self):
        print 'YouSeeApi.__init__'
        print self.COOKIE_JAR
        urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor(self.COOKIE_JAR)))

    def _invoke(self, area, function, params=dict()):
        url = API_URL + '/' + area + '/' + function
        for key, value in params.items():
            url += '/' + key + '/' + str(value)
        url += '/format/json'

        print 'Invoking URL: ' + url

        r = urllib2.Request(url, headers = {'X-API-KEY' : API_KEY})
        u = urllib2.urlopen(r)
        json = u.read()
        u.close()

        return simplejson.loads(json)



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

    def programs(self, channelId, offset = 0):
        """
        Returns program list
        """
        return self._invoke(AREA_TVGUIDE, 'programs', {
            'channel_id' : channelId,
            'offset' : 0
        })



if __name__ == '__main__':
    api = YouSeeTVGuideApi()
    json = api.channels()

    #api = YouSeeMovieApi()
    #print api.moviesInGenre('action')['movies'][0]

    s = simplejson.dumps(json, sort_keys=True, indent='    ')
    print '\n'.join([l.rstrip() for l in  s.splitlines()])


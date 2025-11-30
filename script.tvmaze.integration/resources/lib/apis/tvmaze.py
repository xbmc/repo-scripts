# v.0.5.2

import json
from . import url

headers = {}
headers['Content-Type'] = 'application/json'
headers['Accept'] = 'application/json'
JSONURL = url.URL('json', headers=headers)
TXTURL = url.URL()


class API(object):

    def __init__(self, user='', apikey=''):
        """Create a TV Maze API object."""
        self.PUBLICURL = 'https://api.tvmaze.com'
        self.USER = user
        self.APIKEY = apikey
        if user and apikey:
            self.AUTHURL = 'https://api.tvmaze.com/v1/user'
        else:
            self.AUTHURL = self.PUBLICURL

    def getShow(self, tvmazeid, params=None):
        return self._call('shows/%s' % tvmazeid, params)

    def getEpisode(self, episodeid, params=None):
        return self._call('episodes/%s' % episodeid, params)

    def getEpisodeBySeasonEpNumber(self, tvmazeid, params):
        return self._call('shows/%s/episodebynumber' % tvmazeid, params)

    def getFollowedShows(self, params=None):
        return self._call('follows/shows', params, auth=True)

    def getTaggedShows(self, tag, params=None):
        return self._call('tags/%s/shows' % tag, params, auth=True)

    def getTags(self, params=None):
        return self._call('tags', params, auth=True)

    def findSingleShow(self, showname):
        params = {'q': showname}
        return self._call('/singlesearch/shows', params)

    def followShow(self, showid, params=None):
        return self._call('follows/shows/%s' % showid, params, thetype='put', auth=True)

    def markEpisode(self, episodeid, marked_as=0, marked_at=0, params=None):
        if marked_as == -1:
            return self._call('episodes/%s' % episodeid, params, thetype='delete', auth=True)
        payload = {'episode_id': 0, 'type': marked_as, 'marked_at': marked_at}
        return self._call('episodes/%s' % episodeid, params, data=json.dumps(payload), thetype='put', auth=True)

    def tagShow(self, showid, tagid, params=None):
        return self._call('tags/%s/shows/%s' % (tagid, showid), params, auth=True, thetype='put')

    def unTagShow(self, showid, tagid, params=None):
        return self._call('tags/%s/shows/%s' % (tagid, showid), params, auth=True, thetype='delete')

    def unFollowShow(self, showid, params=None):
        return self._call('follows/shows/%s' % showid, params, thetype='delete', auth=True)

    def _call(self, url_end, params, data=None, auth=False, thetype="get"):
        loglines = []
        if not params:
            params = {}
        if not data:
            data = {}
        if auth:
            if self.AUTHURL == self.PUBLICURL:
                loglines.append(
                    'authorization credentials required but not supplied')
                return False, loglines, {}
            url_base = self.AUTHURL
            auth = (self.USER, self.APIKEY)
        else:
            url_base = self.PUBLICURL
        theurl = '%s/%s' % (url_base, url_end)
        if thetype == 'get':
            status, j_loglines, results = JSONURL.Get(
                theurl, auth=auth, params=params)
        if thetype == 'put':
            status, j_loglines, results = JSONURL.Put(
                theurl, auth=auth, params=params, data=data)
        if thetype == 'delete':
            status, j_loglines, results = TXTURL.Delete(
                theurl, auth=auth, params=params)
        loglines.extend(j_loglines)
        return status == 200, loglines, results

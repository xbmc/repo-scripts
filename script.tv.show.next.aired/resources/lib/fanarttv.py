import sys, urllib
try:
    import simplejson as json
except ImportError:
    import json

# This uses the artwork-downloader API key -- I assume that is OK for this XBMC script.
API_KEY = '586118be1ac673f74963cc284d46bd8e'
API_URL_TV = 'http://api.fanart.tv/webservice/series/%s/%s/json/%s/'

class FanartTV(object):
    def __init__(self):
        pass

    @staticmethod
    def find_artwork(tvdb_id, art_type, lang = 'en'):
        # We need both clearlogo and hdtvlogo for clearlogo. Otherwise tvposter or tvbanner.
        if art_type == 'clearlogo':
            req_type = 'all'
            find_types = [ 'hdtvlogo', 'clearlogo' ]
        else:
            req_type = 'tv' + art_type
            find_types = [ req_type ]
        url = API_URL_TV % (API_KEY, tvdb_id, req_type)
        data = json.load(urllib.urlopen(url))
        if not data:
            return None

        ret = None
        for show_name, info in data.iteritems():
            for find in find_types:
                logos = info.get(find, [])
                for logo in logos:
                    if logo['lang'] == lang:
                        return logo['url']
                    # We'll accept the wrong language as a fallback, as they are sometimes mislabeled.
                    if not ret:
                        ret = logo['url']
        return ret

# Some helper code to check on the data to see how our queries are working.
if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stdout.write("%s\n" % FanartTV.find_artwork(83462, 'clearlogo'))
    else:
        sys.stdout.write("%s\n" % FanartTV.find_artwork(sys.argv[1], sys.argv[2]))

# vim: sw=4 ts=8 et

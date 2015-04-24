from Utils import *

BASE_URL = "http://www.omdbapi.com/?tomatoes=true&plot=full&r=json&"


def GetOmdbMovieInfo(imdb_id):
    try:
        url = 'i=%s' % (imdb_id)
        results = Get_JSON_response(BASE_URL + url)
        for (key, value) in results.iteritems():
            if value == "N/A":
                results[key] = ""
        return results
    except:
        results = None
        log("Exception: Error when fetching Omdb data from net")
    if results is not None:
        return results
    else:
        return {}

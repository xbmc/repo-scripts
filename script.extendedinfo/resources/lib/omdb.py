from Utils import *

base_url = "http://www.omdbapi.com/?tomatoes=true&plot=full&r=json&"

def GetOmdbMovieInfo(imdb_id):
    try:
        url = 'i=%s' % (imdb_id)
        results = Get_JSON_response(base_url + url)
        for (key, value) in results.iteritems():
            if value == "N/A":
                results[key] = ""
    except:
        results = None
        log("Exception: Error when fetching Omdb data from net")
    count = 1
    if results is not None:
        return results
    else:
        return {}



    return results

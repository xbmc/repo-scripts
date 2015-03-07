from Utils import *

rottentomatoes_key = '63sbsudx936yedd2wdmt6tkn'
base_url = "http://api.rottentomatoes.com/api/public/v1.0/lists/"


def GetRottenTomatoesMovies(movietype):
    movies = []
    url = movietype + '.json?apikey=%s' % (rottentomatoes_key)
    results = Get_JSON_response(base_url + url)
    if results is not None and "movies" in results:
        for item in results["movies"]:
            if "alternate_ids" in item:
                imdbid = str(item["alternate_ids"]["imdb"])
            else:
                imdbid = ""
            poster = "http://" + item["posters"]["original"].replace("tmb", "ori")[64:]
            if addon.getSetting("infodialog_onclick") != "false":
                path = 'plugin://script.extendedinfo/?info=extendedinfo&&imdbid=%s' % imdbid
            else:
                path = "plugin://script.extendedinfo/?info=playtrailer&&imdbid=" + imdbid
            movie = {'Title': item["title"],
                     'Art(poster)': item["posters"]["original"],
                     'imdbid': imdbid,
                     'Thumb': poster,
                     'Poster': poster,
                     'Runtime': item["runtime"],
                     'Duration': item["runtime"],
                     'Year': item["year"],
                     'path': path,
                     'Premiered': item["release_dates"]["theater"],
                     'mpaa': item["mpaa_rating"],
                     'Rating': item["ratings"]["audience_score"] / 10.0,
                     'Plot': item["synopsis"]}
            if imdbid:
                movies.append(movie)
    return movies

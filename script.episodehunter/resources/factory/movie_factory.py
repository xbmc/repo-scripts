import time

def movie_factory(xbmc_movie):
    model = {
        'imdb_id': xbmc_movie['imdbnumber'],
        'title': xbmc_movie['title'] or xbmc_movie['originaltitle'],
        'year': xbmc_movie['year'],
        'plays': 1
    }
    if 'lastplayed' not in xbmc_movie or xbmc_movie['lastplayed'] == '':
        model['time'] = int(time.time())
    else:
        try:
            model['time'] = int(time.mktime(time.strptime(xbmc_movie['lastplayed'], '%Y-%m-%d %H:%M:%S')))
        except ValueError:
            model['time'] = int(time.time())
    return model

from tvdb import TVDBProvider
from tmdb import TMDBProvider
from fanarttv import FTV_TVProvider
#from fanarttv import FTV_MovieProvider

def get_providers():
    movie_providers = []
    tv_providers = []
    providers = {}

    tv_providers.append(TVDBProvider())
    movie_providers.append(TMDBProvider())
    tv_providers.append(FTV_TVProvider())
    #movie_providers.append(FTV_MovieProvider())

    providers['movie_providers'] = movie_providers
    providers['tv_providers'] = tv_providers

    return providers
### import libraries
from tvdb import TVDBProvider
from tmdb import TMDBProvider
from fanarttv import FTV_TVProvider
from fanarttv import FTV_MovieProvider

def get_providers():
    movie_providers = []
    tv_providers = []
    musicvideo_providers = []
    providers = {}

    tv_providers.append(TVDBProvider())
    tv_providers.append(FTV_TVProvider())
    
    movie_providers.append(TMDBProvider())
    movie_providers.append(FTV_MovieProvider())
    
    musicvideo_providers.append(TMDBProvider())

    providers['movie_providers'] = movie_providers
    providers['tv_providers'] = tv_providers
    providers['musicvideo_providers'] = musicvideo_providers

    return providers
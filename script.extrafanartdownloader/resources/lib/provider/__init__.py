from tvdb import TVDBProvider
from tmdb import TMDBProvider
#from fanarttv import FTVMusicProvider, FTVProvider

def get_providers():
    movie_providers = []
    tv_providers = []
    music_providers = []
    providers = {}

    tv_providers.append(TVDBProvider())
    movie_providers.append(TMDBProvider())
    #tv_providers.append(FTVProvider())
    #music_providers.append(FTVMusicProvider())

    providers['movie_providers'] = movie_providers
    providers['tv_providers'] = tv_providers
    providers['music_providers'] = music_providers

    return providers

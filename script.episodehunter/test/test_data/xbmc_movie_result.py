import copy
from resources.model import movie_model

MOVIES = [
    {
        'movieid': '1',
        'imdbnumber': 'tt1392170',
        'playcount': '3',
        'originaltitle': 'The Hunger Games',
        'title': 'The Hunger Games',
        'year': '2011',
        'lastplayed': '2014-10-10 20:03:31'
    }, {
        'movieid': '2',
        'imdbnumber': 'tt1440129',
        'playcount': '1',
        'originaltitle': 'Battleship',
        'title': 'Battleship',
        'year': '2011',
        'lastplayed': '1989-09-27 11:20:31'
    }, {
        'movieid': '3',
        'imdbnumber': 'tt0905372',
        'playcount': '1',
        'originaltitle': 'The Thing',
        'title': 'The Thing',
        'year': '2011',
        'lastplayed': '2014-12-01 22:03:31'
    }, {
        'movieid': '4',
        'imdbnumber': 'tt2788710',
        'playcount': '0',
        'originaltitle': 'The Interview',
        'title': 'The Interview',
        'year': '2014'
    }, {
        'movieid': '5',
        'imdbnumber': 'tt0816692',
        'playcount': '0',
        'originaltitle': 'Interstellar',
        'title': 'Interstellar',
        'year': '2014'
    }
]


def get(*args, **kargs):
    """
    Returning a list of movies according to xbmc's model
    :rtype : list
    :param args:str names of movies
    :param kargs:list   remove_attr, list of attr to remove
    :return: list
    """
    return_list = [copy.copy(x) for x in MOVIES if x['title'] in args]

    if 'remove_attr' in kargs:
        return_list = [{i: m[i] for i in m if i not in kargs['remove_attr']} for m in return_list]
    return return_list


def get_as_model(*args, **kargs):
    return [movie_model.create_from_xbmc(m) for m in get(*args, **kargs)]

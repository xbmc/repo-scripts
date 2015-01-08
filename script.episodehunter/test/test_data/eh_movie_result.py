MOVIES = [
    {
        'imdb_id': 'tt1392170',
        'plays': '3',
        'title': 'The Hunger Games'
    }, {
        'imdb_id': 'tt1440129',
        'plays': '1',
        'title': 'Battleship'
    }, {
        'imdb_id': 'tt0905372',
        'plays': '1',
        'title': 'The Thing'
    }, {
        'imdb_id': 'tt2788710',
        'plays': '1',
        'title': 'The Interview'
    }, {
        'imdb_id': 'tt0816692',
        'plays': '1',
        'title': 'Interstellar'
    }
]


def get(*args):
    return [x for x in MOVIES if x['title'] in args]

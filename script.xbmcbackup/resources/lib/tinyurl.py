# this is duplicated in snipppets of code from all over the web, credit to no one
# in particular - to all those that have gone before me!
from future.moves.urllib.request import urlopen


def shorten(aUrl):
    tinyurl = 'http://tinyurl.com/api-create.php?url='
    req = urlopen(tinyurl + aUrl)
    data = req.read()

    # should be a tiny url
    return data

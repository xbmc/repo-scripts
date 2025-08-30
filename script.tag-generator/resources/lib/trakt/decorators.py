"""Decorators to handle HTTP methods magically"""

__author__ = 'Elan Ruusamäe'

from functools import wraps

from trakt.core import api


def _get_first(f, *args, **kwargs):
    """Extract the first value from the provided generator function *f*

    :param f: A generator function to extract data from
    :param args: Non keyword args for the generator function
    :param kwargs: Keyword args for the generator function
    :return: The full url for the resource, a generator, and either a data
        payload or `None`
    """
    generator = f(*args, **kwargs)
    uri = next(generator)
    if not isinstance(uri, (str, tuple)):
        # Allow properties to safely yield arbitrary data
        return uri
    if isinstance(uri, tuple):
        uri, data = uri
        return uri, generator, data
    else:
        return uri, generator, None


def get(f):
    """Perform a HTTP GET request using the provided uri yielded from the
    *f* co-routine. The processed JSON results are then sent back to the
    co-routine for post-processing, the results of which are then returned

    :param f: Generator co-routine that yields uri, args, and processed
        results
    :return: The results of the generator co-routine
    """

    @wraps(f)
    def inner(*args, **kwargs):
        resp = _get_first(f, *args, **kwargs)
        if not isinstance(resp, tuple):
            # Handle cached property responses
            return resp
        url, generator, _ = resp
        json_data = api().get(url)
        try:
            return generator.send(json_data)
        except StopIteration:
            return None

    return inner


def delete(f):
    """Perform an HTTP DELETE request using the provided uri

    :param f: Function that returns a uri to delete to
    """

    @wraps(f)
    def inner(*args, **kwargs):
        generator = f(*args, **kwargs)
        url = next(generator)
        api().delete(url)

    return inner


def post(f):
    """Perform an HTTP POST request using the provided uri and optional
    args yielded from the *f* co-routine. The processed JSON results are
    then sent back to the co-routine for post-processing, the results of
    which are then returned

    :param f: Generator co-routine that yields uri, args, and processed
        results
    :return: The results of the generator co-routine
    """

    @wraps(f)
    def inner(*args, **kwargs):
        url, generator, data = _get_first(f, *args, **kwargs)
        json_data = api().post(url, data)
        try:
            return generator.send(json_data)
        except StopIteration:
            return None

    return inner


def put(f):
    """Perform an HTTP PUT request using the provided uri and optional args
    yielded from the *f* co-routine. The processed JSON results are then
    sent back to the co-routine for post-processing, the results of which
    are then returned

    :param f: Generator co-routine that yields uri, args, and processed
        results
    :return: The results of the generator co-routine
    """

    @wraps(f)
    def inner(*args, **kwargs):
        url, generator, data = _get_first(f, *args, **kwargs)
        json_data = api().put(url, data)
        try:
            return generator.send(json_data)
        except StopIteration:
            return None

    return inner

import requests

_session = requests.Session()


def post(*args, **kw):
    return _session.post(*args, **kw)


def get(*args, **kw):
    return _session.get(*args, **kw)


__all__ = ['post', 'get']

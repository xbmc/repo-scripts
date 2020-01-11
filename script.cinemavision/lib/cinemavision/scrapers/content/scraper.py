import os
from ... import util
from .. import _scrapers


def getFiles(path, sub=None):
    ID = sub and '{0}:'.format(sub) or ''
    files = util.vfs.listdir(path)
    ret = []
    for p in files:
        full = util.pathJoin(path, p)
        if util.isDir(full):
            ret += getFiles(full, p)
            continue
        title, ext = os.path.splitext(p)
        nfoPath = util.pathJoin(path, title + '.nfo')
        nfo = nfoPath if util.vfs.exists(nfoPath) else None
        if ext.lower() in util.videoExtensions:
            ret.append({'url': full, 'ID': ID + p, 'title': title, 'nfo': nfo})
    return ret


def getTrailers():
    path = util.pathJoin(_scrapers.CONTENT_PATH, 'Trailers')

    if not path:
        return []

    try:
        return getFiles(path)
    except:
        util.ERROR()
        return []

import os
import sys
import urlparse
import xbmc
import xbmcaddon

addon = xbmcaddon.Addon()
resourcelibs = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
resourcelibs = os.path.join(resourcelibs, u'resources', u'lib')
sys.path.append(resourcelibs)

import playrandom

from pykodi import log

ignoredtypes = ('', 'addons', 'sources', 'plugin')

def main():
    if len(sys.argv) < 2:
        runscript = 'RunScript(script.playrandomvideos, "<list path>", "label=<list label>", limit=<limit>, forcewatchmode=<watch mode>)'
        log("See README.md for usage: '%s'" % runscript, xbmc.LOGNOTICE)
        xbmc.executebuiltin('Notification(See README.md for usage: script.playrandomvideos, %s, 10000)' % runscript)
        return
    if not sys.argv[1]:
        return

    pathinfo = get_pathinfo()
    if pathinfo['type'] in ignoredtypes:
        return
    limit = int(pathinfo.get('limit', 1))
    randomplayer = playrandom.RandomPlayer(limit)
    randomplayer.play_randomvideos_from_path(pathinfo)

def get_pathinfo():
    pathinfo = {}
    for i in range(2, len(sys.argv)):
        arg = sys.argv[i].split("=", 1)
        pathinfo[arg[0].strip().lower()] = arg[1].strip() if len(arg) > 1 else True

    pathinfo['full path'] = sys.argv[1]

    path_type, db_path = pathinfo['full path'].split('://')
    db_path = db_path.split('?', 1)
    query = urlparse.parse_qs(db_path[1]) if len(db_path) > 1 else None
    db_path = db_path[0].rstrip('/').split('/')

    pathinfo['path'] = db_path
    pathinfo['type'] = path_type
    pathinfo['query'] = query

    return pathinfo

if __name__ == '__main__':
    main()

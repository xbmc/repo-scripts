import sys
import xbmc

from lib import playrandom
from lib.pykodi import log, get_pathinfo

def main():
    if len(sys.argv) < 2:
        runscript = 'RunScript(script.playrandomvideos, "<list path>", "label=<list label>")'
        log("See README.md for full usage: '%s'" % runscript, xbmc.LOGNOTICE)
        return
    if not sys.argv[1]:
        return

    pathinfo = get_arginfo()
    if not pathinfo:
        return
    playrandom.play(pathinfo)

def get_arginfo():
    pathinfo = {}
    for i in range(2, len(sys.argv)):
        arg = sys.argv[i].split("=", 1)
        pathinfo[arg[0].strip().lower()] = arg[1].strip() if len(arg) > 1 else True

    pathinfo['full path'] = sys.argv[1]
    pathinfo.update(get_pathinfo(pathinfo['full path']))
    return pathinfo

if __name__ == '__main__':
    main()

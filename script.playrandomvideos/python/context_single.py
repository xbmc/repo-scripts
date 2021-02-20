import sys
import xbmc

from lib import playrandom
from lib.pykodi import get_pathinfo

if __name__ == '__main__':
    path = sys.listitem.getPath()
    label = sys.listitem.getLabel()
    watchmode = xbmc.getInfoLabel('Control.GetLabel(10)')
    if path and label:
        pathinfo = {'full path': path, 'label': label, 'watchmode': watchmode, 'singlevideo': True}
        pathinfo.update(get_pathinfo(path))
        playrandom.play(pathinfo)

import sys
import xbmc

if __name__ == '__main__':
    path = sys.listitem.getfilename()

    label = sys.listitem.getLabel()
    builtin = 'RunScript(script.playrandomvideos, "%s", "label=%s")' % (path, label)
    xbmc.executebuiltin(builtin)

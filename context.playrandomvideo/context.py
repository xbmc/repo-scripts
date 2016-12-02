import sys
import xbmc

if __name__ == '__main__':
    path = sys.listitem.getfilename()
    label = sys.listitem.getLabel()
    watchmode = xbmc.getInfoLabel('Control.GetLabel(10)')
    builtin = 'RunScript(script.playrandomvideos, "{0}", "label={1}", watchmode={2})'.format(path.replace('\\', '\\\\'), label, watchmode)
    xbmc.executebuiltin(builtin)

import xbmc
import sys


def main():
    if not hasattr(sys, 'listitem'):
        xbmc.log('context.cinemavision: Not launched as a context menu - aborting')
        return
    xbmc.executebuiltin('RunScript(script.cinemavision,experience)')

if __name__ == '__main__':
    main()

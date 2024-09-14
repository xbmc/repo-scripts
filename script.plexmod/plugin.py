from __future__ import absolute_import
from lib.kodi_util import ensureHome, xbmc


def main():
    # This is a hack since it's both a plugin and a script. My Addons and Shortcuts otherwise can't launch the add-on
    ensureHome()
    xbmc.executebuiltin('RunScript(script.plexmod)')


main()

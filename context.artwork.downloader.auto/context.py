import sys
import xbmc

def main():
    if xbmc.getCondVisibility('Container.Content(tvshows)'):
        mediatype = 'tvshow'
    elif xbmc.getCondVisibility('Container.Content(movies)'):
        mediatype = 'movie'
    elif xbmc.getCondVisibility('Container.Content(musicvideos)'):
        mediatype = 'musicvideo'
    else:
        log("Content type not supported, not looking up '%s'." % sys.listitem.getLabel())
        return

    infolabel = xbmc.getInfoLabel('ListItem.Label')
    truelabel = sys.listitem.getLabel()
    mismatch = infolabel != truelabel
    if mismatch:
        log("InfoLabel does not match selected item: InfoLabel('ListItem.Label'): '%s', sys.listitem '%s'" % (infolabel, truelabel), xbmc.LOGWARNING)
        dbid = get_realdbid(sys.listitem)
    else:
        dbid = xbmc.getInfoLabel('ListItem.DBID')

    xbmc.executebuiltin('RunScript(script.artwork.downloader, mediatype=%s, dbid=%s)' % (mediatype, dbid))

    if mismatch:
        xbmc.sleep(1000)
        xbmc.executebuiltin('Notification(Corrected InfoLabel mismatch, "Real: %s, InfoLabel: %s", 00:06, DefaultIconInfo.png)' % (truelabel, infolabel))

def get_realdbid(listitem):
    return listitem.getfilename().split('?')[0].rstrip('/').split('/')[-1]

def log(message, level=xbmc.LOGNOTICE):
    xbmc.log('[context.artwork.downloader.gui] %s' % message, level)

if __name__ == '__main__':
    main()

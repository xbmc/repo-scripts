import os
import sys
import urlparse
import urllib

import xbmc
import xbmcgui
import xbmcplugin

from addon import Addon, log, SCRAPERS_PATH
from resources.lib.scrapers.scraper import ScraperManager


def get_scrapers():
    log('plugin.get_scrapers started')
    manager = get_scraper_manager()
    scrapers = manager.get_scrapers()
    return [{'title': scraper['title'],
             'pic': '',
             'id': scraper['id']} for scraper in scrapers]


def get_albums(scraper_id):
    log('plugin.get_albums started with scraper_id=%s' % scraper_id)
    manager = get_scraper_manager()
    manager.switch_to_given_id(scraper_id)
    albums = manager.get_albums()
    return [{'title': album['title'],
             'pic': album['pic'],
             'id': album['album_url']} for album in albums]


def get_photos(scraper_id, album_url):
    log('plugin.get_photos started with scraper_id=%s, album_url=%s'
        % (scraper_id, album_url))
    manager = get_scraper_manager()
    manager.switch_to_given_id(scraper_id)
    photos = manager.get_photos(album_url)
    return [{'title': photo['title'],
             'pic': photo['pic']} for photo in photos]


def show_scrapers():
    log('plugin.show_scrapers started')
    scrapers = get_scrapers()
    for scraper in scrapers:
        liz = xbmcgui.ListItem(scraper['title'], iconImage='DefaultImage.png',
                               thumbnailImage='DefaultFolder.png')
        params = {'mode': 'albums',
                  'scraper_id': scraper['id']}
        url = 'plugin://%s/?%s' % (Addon.getAddonInfo('id'),
                                   urllib.urlencode(params))
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url,
                                    listitem=liz, isFolder=True)
    log('plugin.show_scrapers finished')


def show_albums(scraper_id):
    log('plugin.show_albums started with scraper_id=%s' % scraper_id)
    albums = get_albums(scraper_id)
    for album in albums:
        liz = xbmcgui.ListItem(album['title'], iconImage='DefaultImage.png',
                               thumbnailImage=album['pic'])
        liz.setInfo(type='image', infoLabels={'Title': album['title']})
        params = {'mode': 'photos',
                  'scraper_id': scraper_id,
                  'album_url': album['id']}
        url = 'plugin://%s/?%s' % (Addon.getAddonInfo('id'),
                                   urllib.urlencode(params))
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url,
                                    listitem=liz, isFolder=True)
    log('plugin.show_albums finished')


def show_photos(scraper_id, album_url):
    log('plugin.show_photos started with scraper_id=%s, album_url=%s'
        % (scraper_id, album_url))
    photos = get_photos(scraper_id, album_url)
    for photo in photos:
        liz = xbmcgui.ListItem(photo['title'], iconImage='DefaultImage.png',
                               thumbnailImage=photo['pic'])
        liz.setInfo(type='image', infoLabels={'Title': photo['title']})
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=photo['pic'],
                                    listitem=liz, isFolder=False)


def decode_params():
    params = {}
    p = urlparse.parse_qs(sys.argv[2][1:])
    for key, value in p.iteritems():
        params[key] = value[0]
    log('plugin.decode_params got params=%s' % params)
    return params


def get_scraper_manager():
    return ScraperManager(SCRAPERS_PATH)


def run():
    p = decode_params()
    if not 'mode' in p:
        log('plugin.run started in scrapers-mode')
        show_scrapers()
    elif p['mode'] == 'albums':
        scraper_id = int(p['scraper_id'])
        log('plugin.run started in albums-mode')
        show_albums(scraper_id)
    elif p['mode'] == 'photos':
        log('plugin.run started in photos-mode')
        scraper_id = int(p['scraper_id'])
        album_url = p['album_url']
        show_photos(scraper_id, album_url)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

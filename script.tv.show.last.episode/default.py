import sys, unicodedata, urlparse
import xbmc, xbmcgui, xbmcaddon, xbmcvfs, xbmcplugin, simplejson

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, 'tvshows')

addon = xbmcaddon.Addon('script.tv.show.last.episode')
path = xbmc.translatePath(addon.getAddonInfo('path'))

def jsonrpc(method, resultKey, params):
  query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "' + method + '", "params": ' + params + ', "id": 1}')
  result = simplejson.loads(unicode(query, 'utf-8', errors='ignore'))
  if result.has_key('result') and result['result'] != None and result['result'].has_key(resultKey):
    return result['result'][resultKey]
  else:
    return []


def get_tv_show_list():
  tvshows = jsonrpc('VideoLibrary.GetTVShows', 'tvshows', '{ "properties": ["title", "thumbnail"] }, "id": "libTvShows"}')
  tvshowList = []
  for tvshow in tvshows:
    episodes = jsonrpc(
      'VideoLibrary.GetEpisodes',
      'episodes',
      '{"tvshowid": %d, "properties": ["title", "season", "episode", "firstaired"]}'%tvshow['tvshowid']
    )

    lastEpisode = None
    lastSeasonNr = 0
    lastEpisodeNr = 0
    for episode in episodes:
      if (episode['season'] > lastSeasonNr):
          lastSeasonNr = episode['season']
          lastEpisodeNr = episode['episode']
          lastEpisode = episode
      elif (episode['season'] == lastSeasonNr and episode['episode'] > lastEpisodeNr):
          lastEpisodeNr = episode['episode']
          lastEpisode = episode

    if lastEpisode != None:
      tvshowList.append({
        'title': tvshow['title'],
        'season': ("%.2d" % float(lastEpisode['season'])),
        'thumbnail' : tvshow['thumbnail'],
        'episode': {
          'number': ("%.2d" % float(lastEpisode['episode'])),
          'title': lastEpisode['title'],
          'firstAired': lastEpisode['firstaired'],
          'episodeDBId': lastEpisode['episodeid']
        }
      })

  return tvshowList


def display_sort_order_selection():
  fanart = addon.getAddonInfo('fanart')

  firstAired = xbmcgui.ListItem(addon.getLocalizedString(32010), iconImage=xbmc.translatePath(path + '/resources/media/calendar.png'))
  firstAired.setProperty('fanart_image', fanart)
  xbmcplugin.addDirectoryItem(
    handle=addon_handle,
    url=base_url + '?order=firstAired',
    listitem=firstAired,
    isFolder=True
  )

  seriesTitle = xbmcgui.ListItem(addon.getLocalizedString(32011), iconImage=xbmc.translatePath(path + '/resources/media/keyboard.png'))
  seriesTitle.setProperty('fanart_image', fanart)
  xbmcplugin.addDirectoryItem(
    handle=addon_handle,
    url=base_url + '?order=seriesTitle',
    listitem=seriesTitle,
    isFolder=True
  )

  episodeDBId = xbmcgui.ListItem(addon.getLocalizedString(32012), iconImage=xbmc.translatePath(path + '/resources/media/plus-circle.png'))
  episodeDBId.setProperty('fanart_image', fanart)
  xbmcplugin.addDirectoryItem(
    handle=addon_handle,
    url=base_url + '?order=episodeDBId',
    listitem=episodeDBId,
    isFolder=True
  )
  xbmcplugin.endOfDirectory(addon_handle)


def display_episode_list(seriesList):
  for series in seriesList:
    episode = series['episode']
    label = u"S%sE%s - %s (%s, %s)"%(series['season'], episode['number'], series['title'], episode['title'], episode['firstAired'])
    li = xbmcgui.ListItem(label, iconImage='DefaultFolder.png', thumbnailImage=xbmc.translatePath(series['thumbnail']))
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=base_url, listitem=li, isFolder=False)
  xbmcplugin.endOfDirectory(addon_handle)

# check settings
if args:
  order = args['order'][0]
else:
  order = None
  addOnSetting = addon.getSetting('sortOrder')
  if addOnSetting == '1':
    order = 'seriesTitle'
  if addOnSetting == '2':
    order = 'firstAired'
  if addOnSetting == '3':
    order = 'episodeDBId'

# sort tv show list
if order:
  unsortedEpisodeList = get_tv_show_list()
  if order in 'seriesTitle':
    sortedEpisodeList = sorted(unsortedEpisodeList, key=lambda x: x['title'])
  if order in 'firstAired':
    sortedEpisodeList = sorted(unsortedEpisodeList, key=lambda x: x['episode']['firstAired'], reverse=True)
  if order in 'episodeDBId':
    sortedEpisodeList = sorted(unsortedEpisodeList, key=lambda x: x['episode']['episodeDBId'], reverse=True)
  display_episode_list(sortedEpisodeList)
else:
  display_sort_order_selection()

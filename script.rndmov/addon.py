import xbmc,xbmcaddon,xbmcgui,json,random

def getAllMovies(randomType):
  rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies', 'params': { 'properties': [ 'file' ] }, 'id': 'libMovies'}

  if (randomType == '1'):
    rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies', 'params': { 'filter': { 'field': 'playcount', 'operator': 'greaterthan', 'value': '0' }, 'properties': [ 'file' ] }, 'id': 'libMovies'}
  if (randomType == '2'):
    rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies', 'params': { 'filter': { 'field': 'playcount', 'operator': 'lessthan', 'value': '1' }, 'properties': [ 'file' ] }, 'id': 'libMovies'}

  rpccmd = json.dumps(rpccmd)
  result = xbmc.executeJSONRPC(rpccmd)
  result = json.loads(result)
  return result

addon     = xbmcaddon.Addon()
addonName = addon.getAddonInfo('name')
addonIcon = addon.getAddonInfo('icon')

randomType         = addon.getSetting('randomType')
askForTypeOnLaunch = addon.getSetting('askForTypeOnLaunch')

if (askForTypeOnLaunch == 'true'):
  randomType = xbmcgui.Dialog().select(addon.getLocalizedString(32002), [addon.getLocalizedString(32004), addon.getLocalizedString(32005), addon.getLocalizedString(32006), addon.getLocalizedString(32007)])

if (randomType == '3') or (randomType == 3):
  quit()
else:
  movies = getAllMovies(randomType)
  movie  = random.choice(movies['result']['movies'])
  time   = 10000

  xbmc.executebuiltin('PlayMedia(%s)'%(movie['file']))
  xbmc.executebuiltin('Notification(%s, %s %s, %d, %s)'%(addonName,"Playing ",movie['label'],time,addonIcon))
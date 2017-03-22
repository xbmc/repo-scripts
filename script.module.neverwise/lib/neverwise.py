#!/usr/bin/python
import gzip, HTMLParser, json, os, re, StringIO, sys, urllib, urllib2, urlparse, xbmc, xbmcaddon, xbmcgui, xbmcplugin
from BeautifulSoup import BeautifulSoup

_idPlugin = 'script.module.neverwise'
addon = xbmcaddon.Addon()
addonName = addon.getAddonInfo('name')
icon_path = os.path.join(addon.getAddonInfo('path'), 'icon.png')


def getResponseJson(url, headers = {}):

  result = getResponse(url, headers)

  if result.isSucceeded and len(result.body) > 0:
    result.body = json.loads(result.body)
  else:
    result.isSucceeded = False

  return result


def getResponseBS(url, headers = {}):

  result = getResponse(url, headers)

  if result.isSucceeded:
    result.body = result.body.replace('&nbsp;', ' ')
    result.body = normalizeResponse(result.body)
    result.body = BeautifulSoup(result.body, convertEntities = BeautifulSoup.HTML_ENTITIES) # For BS 3, in BS 4, entities get decoded automatically.

  return result


def getResponseForRegEx(url, headers = {}):

  result = getResponse(url, headers)

  if result.isSucceeded:
    result.body = htmlDecode(result.body)
    result.body = normalizeResponse(result.body)

  return result


def getResponse(url, headers = {}):

  defaultHeaders = {
    'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0',
    'Accept-Encoding' : 'gzip, deflate'
  }

  for key, value in defaultHeaders.iteritems():
    if key not in headers:
      headers[key] = value

  req = urllib2.Request(url, headers = headers)

  result = Response()
  try:
    response = urllib2.urlopen(req)
  except:
    result.isSucceeded = False
    showConnectionError()
  else:
    result.body = response.read()
    encoding = response.info().get('Content-Encoding')
    if encoding == 'gzip':
      result.body = gzip.GzipFile(fileobj = StringIO.StringIO(result.body)).read()
    elif encoding == 'deflate':
      result.body = zlib.decompress(result.body)

    charset = response.headers.getparam('charset')
    if charset != None:
      result.body = result.body.decode(charset)

    response.close()

    if result.body.find(b'\0') > -1: # null bytes, if there's, the response is wrong.
      result.isSucceeded = False
      showResponseError()

  return result


def normalizeResponse(body):
  body = re.sub('\s+', ' ', body)
  return body.replace('" />', '"/>')


def showNotification(message, time = 5000, header = addonName, image = icon_path):
  notify = u'XBMC.Notification({0},{1},{2},{3})'.format(header, message, time, image)
  xbmc.executebuiltin(notify.encode('utf-8'))


def showConnectionError():
  showNotification(getTranslation(33001, _idPlugin))


def showVideoNotAvailable():
  showNotification(getTranslation(33002, _idPlugin))


def showResponseError():
  showNotification(getTranslation(33003, _idPlugin))


def getTranslation(translationId, addonId = ''):
  return xbmcaddon.Addon(addonId).getLocalizedString(translationId)


# Convert parameters encoded in a URL to a dict.
def urlParametersToDict(parameters):
  if len(parameters) > 0 and parameters[0] == '?':
    parameters = parameters[1:]
  return dict(urlparse.parse_qsl(parameters))


def createListItem(label, label2 = '', iconImage = None, thumbnailImage = None, path = None, fanart = None, streamtype = None, infolabels = None, duration = '', isPlayable = False):
  li = xbmcgui.ListItem(label, label2)

  if iconImage:
    li.setIconImage(iconImage)

  if thumbnailImage:
    li.setThumbnailImage(thumbnailImage)

  if path:
    li.setPath(path)

  if fanart:
    li.setProperty('fanart_image', fanart)

  if streamtype:
    li.setInfo(streamtype, infolabels)

  if streamtype == 'video' and duration:
    li.addStreamInfo(streamtype, {'duration': duration})

  if isPlayable:
    li.setProperty('IsPlayable', 'true')

  return li


def formatUrl(parameters, domain = sys.argv[0]):
  return '{0}?{1}'.format(domain, urllib.urlencode(encodeDict(parameters)))


def createNextPageItem(handle, pageNum, urlDictParams):
  title = '{0} {1} >'.format(getTranslation(33000, _idPlugin), pageNum)
  xbmcplugin.addDirectoryItem(handle, formatUrl(urlDictParams), createListItem(title, thumbnailImage = 'DefaultVideoPlaylists.png'), True)


def createAudioVideoItems(handle):
  xbmcplugin.addDirectoryItem(handle, formatUrl({ 'content_type' : 'video' }), createListItem(getTranslation(33004, _idPlugin), thumbnailImage = 'DefaultMovies.png'), True)
  xbmcplugin.addDirectoryItem(handle, formatUrl({ 'content_type' : 'audio' }), createListItem(getTranslation(33005, _idPlugin), thumbnailImage = 'DefaultMusicSongs.png'), True)


def encodeDict(oldDict):
  newDict = {}
  for k, v in oldDict.iteritems():
    if isinstance(v, unicode):
      v = v.encode('utf8')
    elif isinstance(v, str):
      # Must be encoded in UTF-8
      v.decode('utf8')
    newDict[k] = v
  return newDict


def playStream(handle, label, thumbnailImage = None, path = None, streamtype = None, infolabels = None):
  li = createListItem(label, thumbnailImage = thumbnailImage, path = path, streamtype = streamtype, infolabels = infolabels)
  xbmcplugin.setResolvedUrl(handle, True, li)


def stripTags(text):
  text = re.sub('<[^<]+?>', '', text)
  return text.strip()


def htmlDecode(text):
  try:
    text = text.decode('utf-8')
  except:
    pass
  return HTMLParser.HTMLParser().unescape(text)


class Response(object):
  body = None
  isSucceeded = True

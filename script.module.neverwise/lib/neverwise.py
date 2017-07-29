#!/usr/bin/python
import cookielib, datetime, gzip, HTMLParser, json, os, re, StringIO, sys, urllib, urllib2, urlparse, xbmc, xbmcaddon, xbmcgui, xbmcplugin
import time # Workaround bug.
from bs4 import BeautifulSoup
from dateutil import tz

_idPlugin = 'script.module.neverwise'
addon = xbmcaddon.Addon()
addonName = addon.getAddonInfo('name')
icon_path = os.path.join(addon.getAddonInfo('path'), 'icon.png')
date_format = xbmc.getRegion('dateshort')
time_format = xbmc.getRegion('time')
datetime_format = '{0} {1}'.format(date_format, time_format)


def getResponseJson(url, headers = {}, show_error_msg = True):

  result = getResponse(url, headers, show_error_msg)

  if result.isSucceeded and len(result.body) > 0:
    try:
      result.body = json.loads(result.body)
    except:
      result.isSucceeded = False
      if show_error_msg:
        showResponseError()
  else:
    result.isSucceeded = False

  return result


def getResponseBS(url, headers = {}, show_error_msg = True, parser = 'html.parser'):

  result = getResponse(url, headers, show_error_msg)

  if result.isSucceeded:
    result.body = result.body.replace('&nbsp;', ' ')
    result.body = normalizeResponse(result.body)
    result.body = BeautifulSoup(result.body, parser)

  return result


def getResponseForRegEx(url, headers = {}, show_error_msg = True):

  result = getResponse(url, headers, show_error_msg)

  if result.isSucceeded:
    result.body = htmlDecode(result.body)
    result.body = normalizeResponse(result.body)

  return result


def getResponse(url, headers = {}, show_error_msg = True):

  defaultHeaders = {
    'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0',
    'Accept-Encoding' : 'gzip, deflate'
  }

  for key, value in defaultHeaders.iteritems():
    if key not in headers:
      headers[key] = value

  cookies = cookielib.CookieJar()
  opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
  urllib2.install_opener(opener)

  req = urllib2.Request(url, headers = headers)

  result = Response()
  try:
    response = urllib2.urlopen(req)
    result.cookies = cookies
  except:
    result.isSucceeded = False
    if show_error_msg:
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
      if show_error_msg:
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


def createListItem(label, label2 = '', iconImage = None, thumbnailImage = None, path = None, fanart = None, streamtype = None, infolabels = None, duration = '', isPlayable = False, contextMenu = None):
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

  if contextMenu and len(contextMenu) > 0:
    li.addContextMenuItems(contextMenu)

  return li


def formatUrl(parameters, domain = sys.argv[0]):
  return '{0}?{1}'.format(domain, urllib.urlencode(encodeDict(parameters)))


def createNextPageItem(handle, pageNum, urlDictParams, fanart = None):
  title = '{0} {1} >'.format(getTranslation(33000, _idPlugin), pageNum)
  xbmcplugin.addDirectoryItem(handle, formatUrl(urlDictParams), createListItem(title, thumbnailImage = 'DefaultVideoPlaylists.png', fanart = fanart), True)


def createAudioVideoItems(handle, fanart = None):
  xbmcplugin.addDirectoryItem(handle, formatUrl({ 'content_type' : 'video' }), createListItem(getTranslation(33004, _idPlugin), thumbnailImage = 'DefaultMovies.png', fanart = fanart), True)
  xbmcplugin.addDirectoryItem(handle, formatUrl({ 'content_type' : 'audio' }), createListItem(getTranslation(33005, _idPlugin), thumbnailImage = 'DefaultMusicSongs.png', fanart = fanart), True)


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


def getDownloadContextMenu(action, text = None):
  default_text = getTranslation(33006, _idPlugin)
  if text and len(text) > 0:
    return [(u'{0} {1}'.format(default_text, text), action)]
  else:
    return [(default_text, action)]


def strptime(date_string, date_format_string):
  try:
    return datetime.datetime.strptime(date_string, date_format_string)
  except TypeError:
    return datetime.datetime(*(time.strptime(date_string, date_format_string)[0:6])) # Workaround bug.


def gettz(name):
  return tz.gettz(name)


def gettzlocal():
  result = None

  tzKodi = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": {"setting": "locale.timezone"}, "id": 1}'))
  if not 'error' in tzKodi:
    result = tz.gettz(tzKodi['result']['value'])

  if result == None:
    result = tz.tzlocal()

  if result == None:
    result = tz.tzutc()

  return result


class Response(object):
  body = None
  cookies = None
  isSucceeded = True

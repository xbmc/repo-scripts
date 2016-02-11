#!/usr/bin/python
import sys, urllib, urllib2, urlparse, xbmcplugin, xbmcgui, xbmcaddon, gzip, StringIO, json
from BeautifulSoup import BeautifulSoup

class Util(object):

  _idPlugin = 'script.module.neverwise'
  _addonName = xbmcaddon.Addon().getAddonInfo('name')


  @staticmethod
  def getResponseJson(url, headers = {}):

    result = Util.getResponse(url, headers)

    if result.isSucceeded and len(result.body) > 0:
      result.body = json.loads(result.body)
    else:
      result.isSucceeded = False

    return result

  @staticmethod
  def getResponseBS(url, headers = {}):

    result = Util.getResponseForRegEx(url, headers)

    if result.isSucceeded:
      result.body = BeautifulSoup(result.body, convertEntities = BeautifulSoup.HTML_ENTITIES) # For BS 3, in BS 4, entities get decoded automatically.

    return result

  @staticmethod
  def getResponseForRegEx(url, headers = {}):

    result = Util.getResponse(url, headers)

    if result.isSucceeded:
      result.body = result.body.replace('\t', '').replace('\r\n', '').replace('\n', '').replace('\r', '').replace('" />', '"/>')
      while result.body.find('  ') > -1: result.body = result.body.replace('  ', ' ')

    return result

  @staticmethod
  def getResponse(url, headers = {}):

    defaultHeaders = {
      'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:44.0) Gecko/20100101 Firefox/44.0',
      'Accept-Encoding' : 'gzip, deflate'
    }

    for key, value in defaultHeaders.iteritems():
      if key not in headers:
        headers[key] = value

    req = urllib2.Request(url, headers = headers)

    result = Response()
    try:
      response = urllib2.urlopen(req, timeout = 60)
    except:
      result.isSucceeded = False
      Util.showConnectionErrorDialog()
    else:
      result.body = response.read()
      ce = response.info().get('Content-Encoding')
      if ce == 'gzip':
        result.body = gzip.GzipFile(fileobj = StringIO.StringIO(result.body)).read()
      elif ce == 'deflate':
        result.body = zlib.decompress(result.body)

      response.close()

      if result.body.find(b'\0') > -1: # null bytes, if there's, the response is wrong.
        result.isSucceeded = False
        Util.showResponseErrorDialog()

    return result


  @staticmethod
  def showConnectionErrorDialog():
    xbmcgui.Dialog().ok(Util._addonName, Util.getTranslation(33001, Util._idPlugin))


  @staticmethod
  def showVideoNotAvailableDialog():
    xbmcgui.Dialog().ok(Util._addonName, Util.getTranslation(33002, Util._idPlugin))


  @staticmethod
  def showResponseErrorDialog():
    xbmcgui.Dialog().ok(Util._addonName, Util.getTranslation(33003, Util._idPlugin))


  @staticmethod
  def getTranslation(translationId, addonId = ''):
    return xbmcaddon.Addon(addonId).getLocalizedString(translationId)


  # Convert parameters encoded in a URL to a dict.
  @staticmethod
  def urlParametersToDict(parameters):
    if len(parameters) > 0 and parameters[0] == '?':
      parameters = parameters[1:]
    return dict(urlparse.parse_qsl(parameters))


  @staticmethod
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


  @staticmethod
  def formatUrl(parameters, domain = sys.argv[0]):
    return '{0}?{1}'.format(domain, urllib.urlencode(Util.encodeDict(parameters)))


  @staticmethod
  def createNextPageItem(handle, pageNum, urlDictParams):
    title = '{0} {1} >'.format(Util.getTranslation(33000, Util._idPlugin), pageNum)
    xbmcplugin.addDirectoryItem(handle, Util.formatUrl(urlDictParams), Util.createListItem(title, thumbnailImage = 'DefaultVideoPlaylists.png'), True)


  @staticmethod
  def createAudioVideoItems(handle):
    xbmcplugin.addDirectoryItem(handle, Util.formatUrl({ 'content_type' : 'video' }), Util.createListItem(Util.getTranslation(33004, Util._idPlugin), thumbnailImage = 'DefaultMovies.png'), True)
    xbmcplugin.addDirectoryItem(handle, Util.formatUrl({ 'content_type' : 'audio' }), Util.createListItem(Util.getTranslation(33005, Util._idPlugin), thumbnailImage = 'DefaultMusicSongs.png'), True)


  @staticmethod
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


  @staticmethod
  def playStream(handle, label, thumbnailImage = None, path = None, streamtype = None, infolabels = None):
    li = Util.createListItem(label, thumbnailImage = thumbnailImage, path = path, streamtype = streamtype, infolabels = infolabels)
    xbmcplugin.setResolvedUrl(handle, True, li)


class Response(object):
  body = None
  isSucceeded = True

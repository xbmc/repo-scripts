#!/usr/bin/python
import re, sys, urllib, urllib2, urlparse, xbmcplugin, xbmcgui, xbmcaddon, BeautifulSoup, CommonFunctions, gzip, StringIO

class Util(object):

  _idPlugin = 'script.module.neverwise'
  _addonName = xbmcaddon.Addon().getAddonInfo('name')


  @staticmethod
  def getHtml(url, showErrorDialog = False):
    bsHtml = None
    req = urllib2.Request(url, headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0' })
    req.add_header('Accept-Encoding', 'gzip, deflate')

    try:
      response = urllib2.urlopen(req)
    except:
      bsHtml = None
    else:
      bsHtml = response.read()
      ce = response.info().get('Content-Encoding')
      if ce == 'gzip':
        bsHtml = gzip.GzipFile(fileobj = StringIO.StringIO(bsHtml)).read()
      elif ce == 'deflate':
        bsHtml = zlib.decompress(bsHtml)

      response.close()

      if bsHtml.find(b'\0') > -1: # null bytes, if there's, the response is wrong.
        bsHtml = None

    if bsHtml != None:
      bsHtml = bsHtml.replace('\t', '').replace('\r\n', '').replace('\n', '').replace('\r', '').replace('" />', '"/>')
      while bsHtml.find('  ') > -1: bsHtml = bsHtml.replace('  ', ' ')
      bsHtml = BeautifulSoup.BeautifulSoup(bsHtml)
    elif showErrorDialog:
      Util.showConnectionErrorDialog()

    return bsHtml


  @staticmethod
  def showConnectionErrorDialog():
    xbmcgui.Dialog().ok(Util._addonName, Util.getTranslation(33001, Util._idPlugin))


  @staticmethod
  def showVideoNotAvailableDialog():
    xbmcgui.Dialog().ok(Util._addonName, Util.getTranslation(33002, Util._idPlugin))


  @staticmethod
  def getTranslation(translationId, addonId = ''):
    return xbmcaddon.Addon(addonId).getLocalizedString(translationId).encode('utf-8')


  @staticmethod
  def normalizeText(text):
    if isinstance(text, str):
      text = text.decode('utf-8')
    return CommonFunctions.replaceHTMLCodes(text).strip()


  @staticmethod
  def trimTags(html):
    html = re.sub('<script.+?>.+?</script>', '', html)
    html = re.sub('<script>.+?</script>', '', html)
    return re.sub('<.+?>', '', html)


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
  def createItemPage(pageNum):
    title = '{0} {1} >'.format(Util.getTranslation(33000, Util._idPlugin), pageNum)
    return Util.createListItem(title)


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

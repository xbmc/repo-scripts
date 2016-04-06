# *-* coding: utf-8 *-*

import urllib, urllib2, base64, StringIO, sys, xbmc, xbmcaddon
from xml.dom import minidom


class SubTiToolHelper:
    def __init__(self, filename, md5hash):
        self.info = {}
        self.filename = filename
        self.url = "http://www.subtitool.com/api/"
        self.md5hash = md5hash

    def search(self, item, t, langs):

        fulllang = xbmc.convertLanguage(item['preferredlanguage'], xbmc.ENGLISH_NAME)
        if fulllang == "Persian": fulllang = "Farsi/Persian"
        MainQueryString = self.filename;

        if item['mansearch']:
            QueryString = item['mansearchstr'];
        else:
            if len(item['tvshow']) > 0:
                QueryString = ("%s S%.2dE%.2d" % (item['tvshow'],int(item['season']),int(item['episode']),)).replace(" ","+")
            else:
                if str(item['year']) == "":
                   QueryStringTemp = xbmc.getCleanMovieTitle(item['title'])
                   QueryString = QueryStringTemp[0] + " " + QueryStringTemp[1]
                else:
                   QueryString = (item['title'] + " " + item['year']).replace(" ","+")
            if len(QueryString) < 6:
                QueryString = MainQueryString

        #xbmc.executebuiltin("Notification(Title," + QueryString + ")")

        addon = xbmcaddon.Addon();

        if len(QueryString) < 6:
            xbmc.executebuiltin("Notification(" + addon.getLocalizedString(32003) + "," + addon.getLocalizedString(32002) + ")")
            return

        url = "http://www.subtitool.com/api/?query=" + QueryString + "&Lang=" + langs
        subs = urllib.urlopen(url).read()
        DOMTree = minidom.parseString(subs)
        if DOMTree.getElementsByTagName('Subtitle').length == 0:
           try:
            url = "http://www.subtitool.com/api/?query=" + QueryString + "&Lang=" + langs + "&OR=1"
            subs = urllib.urlopen(url).read()
            DOMTree = minidom.parseString(subs)
           except Exception, e:
                log("Subtitool","Not Found OR")

           try:
            url = "http://www.subtitool.com/api/?query=" + QueryString + "&Lang=" + langs
            subs = urllib.urlopen(url).read()
            DOMTree = minidom.parseString(subs)
           except Exception, e:
                log("Subtitool","Not Found")

        return DOMTree

    def download(self, dllink, language="EN"):

        try:
            response = urllib.urlopen(dllink)
        except urllib2.URLError, e:
            sys.stderr.write(e.message)
            return False

        try:
            srtdata = response.read()
            with open(self.filename, "w") as file:
             file.write(srtdata)

            return self.filename

        except Exception, e:
            return False

        return False


def log(module, msg):
  xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG )
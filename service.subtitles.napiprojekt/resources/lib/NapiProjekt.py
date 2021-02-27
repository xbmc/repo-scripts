# *-* coding: utf-8 *-*

import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, base64, io, sys
from urllib import request, parse
import xbmc
import xbmcaddon
import xbmcgui

import base64
import traceback
from xml.dom import minidom
import requests

__addon__ = xbmcaddon.Addon()
__scriptname__ = __addon__.getAddonInfo('name')

class NapiProjektHelper:
    def __init__(self, filename, md5hash):
        self.info = {}
        self.filename = filename
        self.url = "http://napiprojekt.pl/api/api-napiprojekt3.php"
        self.md5hash = md5hash

    def log(self, msg=None, ex=None):
        if ex:
            msg = traceback.format_exc()
            
        level = xbmc.LOGDEBUG

        xbmc.log((u"### [%s] - %s" % (__scriptname__, msg)), level=level)

    def notify(self, msg):
        xbmcgui.Dialog().notification(__scriptname__, msg, time=2000, sound=False)
        # xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__, msg)))

    def search(self, item, t):
        subtitle_list = []

        for language in item["3let_language"]:
            language = "pl" if language == "pol" else language
            params = {
                "l": language.upper(),
                "f": self.md5hash,
                "t": t,
                "v": "other",
                "kolejka": "false",
                "nick": "",
                "pass": "",
                "napios": "Linux"
            }

            self.log(params)

            url = "http://napiprojekt.pl/unit_napisy/dl.php?" + urllib.parse.urlencode(params)
            subs = urllib.request.urlopen(url).read()

            if subs[0:3] != b'NPc':
                subtitle_list.append({"language": language, "is_preferred": language == item["preferredlanguage"]})

        return sorted(subtitle_list, key=lambda x: (x['is_preferred']), reverse=True)

    def download(self, language="PL"):
        values = {
            "mode": "1",
            # "client":"NapiTux",
            "client": "NapiProjektPython",
            "client_ver": "0.1",
            "downloaded_subtitles_id": self.md5hash,
            "downloaded_subtitles_txt": "1",
            "downloaded_subtitles_lang": language
        }

        self.log(values)

        try:
            # data = parse.urlencode(values).encode()
            response = requests.post(self.url, data=values).text

            self.log(response)
            DOMTree = minidom.parseString(response)

            cNodes = DOMTree.childNodes
            if cNodes[0].getElementsByTagName("status"):
                text = base64.b64decode(
                    cNodes[0].getElementsByTagName("subtitles")[0].getElementsByTagName("content")[0].childNodes[
                        0].data)
                filename2 = self.filename + ".txt"
        
                open(filename2, "wb").write(text)
                return filename2

        except Exception as e:
            self.notify(xbmcaddon.Addon().getLocalizedString(32002))

            self.log(ex=e)
            pass

        return None

    def getMoreInfo(self):
        values = {
            "mode": "32770",
            # "client":"NapiTux",
            "client": "NapiProjektPython",
            "client_ver": "0.1",
            "downloaded_cover_id": self.md5hash,
            "VideoFileInfoID": self.md5hash
        }

        data = urllib.parse.urlencode(values)
        # req = urllib2.Request(self.url, data)
        try:
            # response = urllib2.urlopen(req)
            response = urllib.request.urlopen(self.url, data)
        except urllib.error.URLError as e:
            sys.stderr.write(e.message)
            return False

        try:
            DOMTree = minidom.parseString(response.read())
            cNodes = DOMTree.childNodes[0].getElementsByTagName("movie")

            if (cNodes[0].getElementsByTagName("status") != []):
                self.info["title"] = cNodes[0].getElementsByTagName("title")[0].childNodes[0].data
                self.info["year"] = cNodes[0].getElementsByTagName("year")[0].childNodes[0].data
                self.info["country"] = \
                    cNodes[0].getElementsByTagName("country")[0].getElementsByTagName("pl")[0].childNodes[0].data
                if (cNodes[0].getElementsByTagName("genre")[0].getElementsByTagName("pl")[0].childNodes != []):
                    self.info["genre"] = \
                        cNodes[0].getElementsByTagName("genre")[0].getElementsByTagName("pl")[0].childNodes[0].data
                else:
                    self.info["genre"] = "Niepodany!"

                self.info["filmweb"] = \
                    cNodes[0].getElementsByTagName("direct_links")[0].getElementsByTagName("filmweb_pl")[0].childNodes[
                        0].data
                self.info["cover"] = io.StringIO(
                    base64.b64decode(cNodes[0].getElementsByTagName("cover")[0].childNodes[0].data))

                cNodes = DOMTree.childNodes[0].getElementsByTagName("file_info")

                self.info["size"] = cNodes[0].getElementsByTagName("rozmiar_pliku_z_jednostka")[0].childNodes[0].data
                self.info["duration"] = cNodes[0].getElementsByTagName("czas_trwania_sformatowany")[0].childNodes[
                    0].data
                self.info["resolution"] = cNodes[0].getElementsByTagName("rozdz_X")[0].childNodes[0].data + "x" + \
                                          cNodes[0].getElementsByTagName("rozdz_Y")[0].childNodes[0].data
        except Exception as e:
            sys.stderr.write(e.message)
            return False

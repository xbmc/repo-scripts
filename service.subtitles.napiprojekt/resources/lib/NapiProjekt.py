# *-* coding: utf-8 *-*

from os import path
import base64
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.dom import minidom
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__temp__ = xbmcvfs.translatePath(path.join(__profile__, 'temp', ''))


def log(msg):
    xbmc.log((u"### [%s] - %s" % (__scriptname__, msg)), level=xbmc.LOGDEBUG)

def notify(msg_id):
    xbmcgui.Dialog().notification(__scriptname__, __language__(msg_id))

class NapiProjektHelper:
    def __init__(self, md5hash):
        self.info = {}
        self.url = "http://napiprojekt.pl/api/api-napiprojekt3.php"
        self.md5hash = md5hash

    def search(self, item, file_token):
        subtitle_list = []

        for language in item["3let_language"]:
            params = {
                "l": xbmc.convertLanguage(language, xbmc.ISO_639_1).upper(),
                "f": self.md5hash,
                "t": file_token,
                "v": "other",
                "kolejka": "false",
                "nick": "",
                "pass": "",
                "napios": "Linux"
            }

            url = "http://napiprojekt.pl/unit_napisy/dl.php?" + urlencode(params)
            log("Requesting: %s" % url)

            subs = urlopen(url).read()

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

        subtitle_list = []

        try:
            data = urlencode(values).encode("utf-8")
            response = urlopen(self.url, data)

            DOMTree = minidom.parseString(response.read())
            cNodes = DOMTree.childNodes
            if (cNodes[0].getElementsByTagName("status") != []):
                content = base64.b64decode(
                    cNodes[0].getElementsByTagName("subtitles")[0].getElementsByTagName("content")[0].childNodes[
                        0].data)
                filename = self.md5hash + ".srt"
                filepath = path.join(__temp__, filename)

                with xbmcvfs.File(filepath, 'w') as vFile:
                    vFile.write(content)

                subtitle_list.append(filepath)

        except Exception as e:
            notify(32001)
            log("Exception %s" % e)

        return subtitle_list

# *-* coding: utf-8 *-*

import urllib, urllib2, base64, StringIO, sys
from xml.dom import minidom


class NapiProjektHelper:
    def __init__(self, filename, md5hash):
        self.info = {}
        self.filename = filename
        self.url = "http://napiprojekt.pl/api/api-napiprojekt3.php"
        self.md5hash = md5hash

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

            url = "http://napiprojekt.pl/unit_napisy/dl.php?" + urllib.urlencode(params)
            subs = urllib.urlopen(url).read()

            if subs[0:3] != 'NPc':
                subtitle_list.append({"language": language})

        return subtitle_list

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

        data = urllib.urlencode(values)
        # req = urllib2.Request(self.url, data)
        try:
            # response = urllib2.urlopen(req)
            response = urllib.urlopen(self.url, data)
        except urllib2.URLError, e:
            sys.stderr.write(e.message)
            return False

        try:
            DOMTree = minidom.parseString(response.read())

            cNodes = DOMTree.childNodes
            if (cNodes[0].getElementsByTagName("status") != []):
                self.text = base64.b64decode(
                    cNodes[0].getElementsByTagName("subtitles")[0].getElementsByTagName("content")[0].childNodes[
                        0].data)
                filename = self.filename[:self.filename.rfind(".")] + ".txt"
                open(filename, "w").write(self.text)
                return filename

        except Exception, e:
            return False

        return False

    def getMoreInfo(self):
        values = {
            "mode": "32770",
            # "client":"NapiTux",
            "client": "NapiProjektPython",
            "client_ver": "0.1",
            "downloaded_cover_id": self.md5hash,
            "VideoFileInfoID": self.md5hash
        }

        data = urllib.urlencode(values)
        # req = urllib2.Request(self.url, data)
        try:
            # response = urllib2.urlopen(req)
            response = urllib.urlopen(self.url, data)
        except urllib2.URLError, e:
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
                self.info["cover"] = StringIO.StringIO(
                    base64.b64decode(cNodes[0].getElementsByTagName("cover")[0].childNodes[0].data))

                cNodes = DOMTree.childNodes[0].getElementsByTagName("file_info")

                self.info["size"] = cNodes[0].getElementsByTagName("rozmiar_pliku_z_jednostka")[0].childNodes[0].data
                self.info["duration"] = cNodes[0].getElementsByTagName("czas_trwania_sformatowany")[0].childNodes[
                    0].data
                self.info["resolution"] = cNodes[0].getElementsByTagName("rozdz_X")[0].childNodes[0].data + "x" + \
                                          cNodes[0].getElementsByTagName("rozdz_Y")[0].childNodes[0].data
        except Exception, e:
            sys.stderr.write(e.message)
            return False

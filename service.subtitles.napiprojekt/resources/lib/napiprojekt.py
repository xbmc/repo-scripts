# *-* coding: utf-8 *-*

from os import path
import base64
import re
import time
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
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

API_URL = "https://napiprojekt.pl/api/api-napiprojekt3.php"
DOWNLOAD_URL = "https://napiprojekt.pl/unit_napisy/dl.php"
REQUEST_TIMEOUT = 15
API_MIN_INTERVAL = 2.0
RATE_LIMIT_FALLBACK = 10.0
__rate_limit_file__ = path.join(__profile__, "next_api_request.txt")

SRT_TIMECODE_RE = re.compile(
    r"(?m)^\s*\d+\s*\r?\n"
    r"\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*"
    r"\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*$"
)
MICRODVD_RE = re.compile(
    r"(?m)^\s*(?:\[\d+\]\[\d+\]|\{\d+\}\{\d+\})"
)


def log(msg):
    # Official Kodi repository rules require add-ons to use LOGDEBUG.
    xbmc.log((u"### [%s] - %s" % (__scriptname__, msg)), level=xbmc.LOGDEBUG)

def notify(msg_id):
    xbmcgui.Dialog().notification(__scriptname__, __language__(msg_id))

def subtitle_extension(content):
    """Detect the subtitle format returned by NapiProjekt from its content."""
    if SRT_TIMECODE_RE.search(content):
        return ".srt"
    if MICRODVD_RE.search(content):
        return ".sub"
    # Kodi handles unknown text subtitle formats more reliably as .sub than
    # under a false .srt extension.
    return ".sub"

class NapiProjektHelper:
    def __init__(self, md5hash):
        self.info = {}
        self.url = API_URL
        self.md5hash = md5hash
        self.last_error = None

    @staticmethod
    def _language_code(language):
        """Return the two-letter, upper-case code expected by NapiProjekt."""
        converted = xbmc.convertLanguage(language, xbmc.ISO_639_1)
        return (converted or language[:2]).upper()

    @staticmethod
    def _read_next_request_time():
        try:
            if not xbmcvfs.exists(__rate_limit_file__):
                return 0.0
            with xbmcvfs.File(__rate_limit_file__, "r") as state_file:
                return float(state_file.read().strip() or 0)
        except (OSError, TypeError, ValueError):
            return 0.0

    @staticmethod
    def _write_next_request_time(timestamp):
        try:
            if not xbmcvfs.exists(__profile__):
                xbmcvfs.mkdirs(__profile__)
            with xbmcvfs.File(__rate_limit_file__, "w") as state_file:
                state_file.write(str(timestamp))
        except OSError as exc:
            # A read-only profile must not make subtitle retrieval impossible.
            log("Could not save API rate-limit state: %s" % exc)

    @classmethod
    def _throttle(cls):
        wait_seconds = cls._read_next_request_time() - time.time()
        if wait_seconds > 0:
            log("Waiting %.1f seconds before the next API request" % wait_seconds)
            xbmc.sleep(int(wait_seconds * 1000) + 1)

        # Reserve the next slot before opening the connection. This also
        # limits a download launched by a separate Kodi plugin invocation.
        cls._write_next_request_time(time.time() + API_MIN_INTERVAL)

    @classmethod
    def _request(cls, url, data=None):
        cls._throttle()
        request = Request(url, data=data, headers={
            "User-Agent": "Kodi NapiProjekt subtitle addon/%s" % __version__,
            "Accept": "*/*",
        })
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code == 429:
                try:
                    retry_after = float(
                        exc.headers.get("Retry-After", RATE_LIMIT_FALLBACK)
                        if exc.headers else RATE_LIMIT_FALLBACK
                    )
                except (AttributeError, TypeError, ValueError):
                    retry_after = RATE_LIMIT_FALLBACK
                retry_after = max(retry_after, RATE_LIMIT_FALLBACK)
                cls._write_next_request_time(time.time() + retry_after)
                log("NapiProjekt rate limit active for %.0f seconds" % retry_after)
            raise

    def search(self, item, file_token):
        subtitle_list = []
        saw_not_found = False

        # NapiProjekt is a Polish subtitle service and rate-limits consecutive
        # requests aggressively. Query it exactly once for Polish subtitles,
        # independently of Kodi's preferred/configured language list.
        for language in ("pol",):
            params = {
                "l": self._language_code(language),
                "f": self.md5hash,
                "t": file_token,
                "v": "other"
            }

            url = DOWNLOAD_URL + "?" + urlencode(params)
            log("Checking subtitles for language %s" % params["l"])

            try:
                subs = self._request(url)
                # NPc0 is the service's "subtitles not found" response.
                if subs.startswith(b'NPc0'):
                    saw_not_found = True
                    log("No subtitles for language %s" % params["l"])
                elif subs and not subs.lstrip().startswith((b'<', b'<!DOCTYPE')):
                    subtitle_list.append({
                        "language": language,
                        "is_preferred": True
                    })
                else:
                    self.last_error = self.last_error or "invalid_response"
                    log("Invalid search response for language %s" % params["l"])
            except HTTPError as exc:
                # One unavailable language must not abort the whole Kodi search.
                log("Search request failed for %s: %s" % (params["l"], exc))
                if exc.code == 429:
                    self.last_error = "rate_limited"
                elif self.last_error != "rate_limited":
                    self.last_error = "network_error"
            except (URLError, TimeoutError, OSError) as exc:
                log("Search request failed for %s: %s" % (params["l"], exc))
                if self.last_error != "rate_limited":
                    self.last_error = "network_error"

        if not subtitle_list and not self.last_error and saw_not_found:
            self.last_error = "no_subtitles"

        return sorted(subtitle_list, key=lambda x: (x['is_preferred']), reverse=True)

    def download(self, language="PL"):
        values = {
            "mode": "1",
            "client": "NapiProjektPython",
            "downloaded_subtitles_id": self.md5hash,
            # Without this flag the XML API embeds a password-protected 7-Zip
            # archive. With it, content contains decoded subtitle text.
            "downloaded_subtitles_txt": "1"
        }

        subtitle_list = []

        try:
            data = urlencode(values).encode("utf-8")
            response = self._request(self.url, data)
            document = minidom.parseString(response)
            statuses = document.getElementsByTagName("status")
            contents = document.getElementsByTagName("content")

            if statuses and statuses[0].firstChild and statuses[0].firstChild.data == "success" and contents:
                content = base64.b64decode(contents[0].firstChild.data)

                if content.startswith(b"7z\xbc\xaf\x27\x1c"):
                    raise ValueError("NapiProjekt returned a 7-Zip archive instead of subtitle text")

                # NapiProjekt returns the original stored format: commonly
                # SubRip or MicroDVD. Detect it after decoding instead of
                # assigning a fixed, potentially incorrect extension.
                try:
                    content = content.decode("utf-8-sig")
                except UnicodeDecodeError:
                    content = content.decode("cp1250")

                extension = subtitle_extension(content)
                filename = self.md5hash + extension
                filepath = path.join(__temp__, filename)
                log("Detected subtitle format: %s" % extension[1:].upper())

                with xbmcvfs.File(filepath, 'w') as vFile:
                    vFile.write(content)

                subtitle_list.append(filepath)
            else:
                notify(32002)
                log("NapiProjekt returned no subtitles for %s" % self.md5hash)

        except HTTPError as e:
            notify(32005 if e.code == 429 else 32006)
            log("Download HTTP error: %s" % e)
        except (URLError, TimeoutError, OSError) as e:
            notify(32006)
            log("Download network error: %s" % e)
        except Exception as e:
            notify(32007)
            log("Invalid download response: %s" % e)

        return subtitle_list

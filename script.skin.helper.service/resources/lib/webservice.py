#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Helper service and scripts for Kodi skins
    webservice.py
    Simple webservice to directly retrieve metadata from artwork module
'''

import SimpleHTTPServer
import BaseHTTPServer
import httplib
import threading
from utils import log_msg, log_exception, json
import xbmc
import xbmcvfs
import urlparse
import urllib
from metadatautils import extend_dict

# port is hardcoded as there is no way in Kodi to pass a INFO-label inside a panel,
# otherwise the portnumber could be passed to the skin through a skin setting or window prop
PORT = 52307


class WebService(threading.Thread):
    '''Main webservice class which holds the SimpleHTTPServer instance'''
    event = None
    exit = False

    def __init__(self, *args, **kwargs):
        self.event = threading.Event()
        threading.Thread.__init__(self, *args)
        self.metadatautils = kwargs.get("metadatautils")

    def stop(self):
        '''called when the thread needs to stop'''
        try:
            log_msg("WebService - stop called", 0)
            conn = httplib.HTTPConnection("127.0.0.1:%d" % PORT)
            conn.request("QUIT", "/")
            conn.getresponse()
            self.exit = True
            self.event.set()
        except Exception as exc:
            log_exception(__name__, exc)

    def run(self):
        '''called to start our webservice'''
        log_msg("WebService - start helper webservice on port %s" % PORT, xbmc.LOGNOTICE)
        try:
            server = StoppableHttpServer(('127.0.0.1', PORT), StoppableHttpRequestHandler)
            server.metadatautils = self.metadatautils
            server.serve_forever()
        except Exception as exc:
            if "10053" not in exc: # ignore host diconnected errors
                log_exception(__name__, exc)


class Request(object):
    '''attributes from urlsplit that this class also sets'''
    uri_attrs = ('scheme', 'netloc', 'path', 'query', 'fragment')

    def __init__(self, uri, headers, rfile=None):
        self.uri = uri
        self.headers = headers
        parsed = urlparse.urlsplit(uri)
        for i, attr in enumerate(self.uri_attrs):
            setattr(self, attr, parsed[i])
        try:
            body_len = int(self.headers.get('Content-length', 0))
        except ValueError:
            body_len = 0
        if body_len and rfile:
            self.body = rfile.read(body_len)
        else:
            self.body = None


class StoppableHttpRequestHandler (SimpleHTTPServer.SimpleHTTPRequestHandler):
    '''http request handler with QUIT stopping the server'''
    raw_requestline = ""

    def __init__(self, request, client_address, server):
        try:
            SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
        except Exception:
            pass

    def do_QUIT(self):
        '''send 200 OK response, and set server.stop to True'''
        self.send_response(200)
        self.end_headers()
        self.server.stop = True

    def log_message(self, logformat, *args):
        ''' log message to kodi log'''
        log_msg("Webservice --> [%s] %s\n" % (self.log_date_time_string(), logformat % args))

    def parse_request(self):
        '''hack to accept non url encoded strings to pass listitem details from Kodi to webservice
        strip the passed arguments apart, urlencode them and pass them back as new requestline properly formatted'''
        if "GET /" in self.raw_requestline or "HEAD /" in self.raw_requestline:
            if self.raw_requestline.startswith("HEAD"):
                command = "HEAD /"
            else:
                command = "GET /"
            action = self.raw_requestline.split("&")[0].replace(command, "")
            temp_requestline = self.raw_requestline.replace(command, "")
            temp_requestline = temp_requestline.replace(" HTTP/1.1", "").replace("\r\n", "").replace(action, "")
            old_params = temp_requestline.split("&")
            new_params = {"action": action}
            for param in old_params:
                if param and len(param.split("=")) > 1:
                    key = param.split("=")[0]
                    value = param.split("=")[1]
                    new_params[key] = value
            paramstring = urllib.urlencode(new_params)
            self.raw_requestline = "%s%s&%s HTTP/1.1" % (command, action, paramstring)
        retval = SimpleHTTPServer.SimpleHTTPRequestHandler.parse_request(self)
        self.request = Request(self.path, self.headers, self.rfile)
        return retval

    def do_HEAD(self):
        '''called on HEAD requests'''
        self.handle_request(True)
        return

    def get_params(self):
        '''get the params'''
        params = {}
        for key, value in urlparse.parse_qs(self.path).iteritems():
            if value:
                value = value[0]
                if "%" in value:
                    value = urllib.unquote(value)
                params[key] = value.decode("utf-8")
        return params

    def handle_request(self, headers_only=False):
        '''send headers and reponse'''
        image = ""
        try:
            artwork = {}
            params = self.get_params()
            action = params.get("action", "")
            title = params.get("title", "")
            preferred_types = params.get("type")
            if preferred_types:
                preferred_types = preferred_types.split(",")
            else:
                preferred_types = []
            fallback = params.get("fallback", "")
            is_json_request = params.get("json", "") == "true"
            if fallback and not xbmcvfs.exists(fallback):
                fallback = "special://skin/media/" + fallback
                if not xbmcvfs.exists(fallback):
                    fallback = ""
                    log_msg(
                        "Webservice --> Non existent fallback image detected - "
                        "please use a full path to the fallback image!",
                        xbmc.LOGWARNING)

            log_msg("webservice called with params: %s" % params)

            # search image on google
            if action == "getthumb":
                image = self.server.metadatautils.google.search_image(title)

            # get pvr image
            elif "pvrthumb" in action:
                channel = params.get("channel", "")
                genre = params.get("genre", "")
                artwork = self.server.metadatautils.get_pvr_artwork(title, channel, genre)
                if action == "getallpvrthumb":
                    is_json_request = True

            # get video artwork and metadata
            elif action == "getartwork":
                if not preferred_types:
                    is_json_request = True
                year = params.get("year", "")
                media_type = params.get("mediatype", "")
                imdb_id = params.get("imdbid", "")
                if not imdb_id:
                    artwork = self.server.metadatautils.get_tmdb_details("", "", title, year, media_type)
                    if artwork:
                        imdb_id = artwork.get("imdbnumber")
                        if not media_type:
                            media_type = artwork.get("media_type")
                if imdb_id:
                    artwork = extend_dict(
                        artwork, self.server.metadatautils.get_extended_artwork(
                            imdb_id, "", "", media_type))

            # music art
            elif action == "getmusicart":
                artist = params.get("artist", "")
                album = params.get("album", "")
                track = params.get("track", "")
                artwork = self.server.metadatautils.get_music_artwork(artist, album, track)

            # genre images
            elif "genreimages" in action and preferred_types:
                arttype = preferred_types[0].split(".")[0]
                mediatype = "tvshows" if "tvshow" in action else "movies"
                randomize = "true" if "random" in action else "false"
                lib_path = u"plugin://script.skin.helper.service/?action=genrebackground"\
                    "&genre=%s&arttype=%s&mediatype=%s&random=%s" % (title, arttype, mediatype, randomize)
                for count, item in enumerate(self.server.metadatautils.kodidb.files(lib_path, limits=(0, 5))):
                    artwork["%s.%s" % (arttype, count)] = item["file"]

            # image from variable
            elif "getvarimage" in action:
                title = title.replace("{", "[").replace("}", "]")
                image = xbmc.getInfoLabel(title)
                if not xbmcvfs.exists(image):
                    if "resource.images" in image:
                        log_msg(
                            "Texture packed resource addons are not supported by the webservice! - %s" %
                            image, xbmc.LOGWARNING)
                    image = ""

            if not is_json_request:
                if artwork and artwork.get("art"):
                    artwork = artwork["art"]
                if preferred_types:
                    for pref_type in preferred_types:
                        if not image:
                            image = artwork.get(pref_type, "")
                elif not image and artwork.get("landscape"):
                    image = artwork["landscape"]
                elif not image and artwork.get("fanart"):
                    image = artwork["fanart"]
                elif not image and artwork.get("poster"):
                    image = artwork["poster"]
                elif not image and artwork.get("thumb"):
                    image = artwork["thumb"]
                # set fallback image if nothing else worked
                if not image or not xbmcvfs.exists(image):
                    image = fallback

            log_msg("webservice image: %s - fallback: %s - artwork: %s - title: %s" %
                    (image, fallback, artwork, title))

            if is_json_request and artwork:
                # send json reponse
                artwork = json.dumps(artwork)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Content-Length', len(artwork))
                self.end_headers()
                if not headers_only:
                    self.wfile.write(artwork)
            elif image:
                # send single image
                self.send_response(200)
                ext = image.split(".")[-1]
                self.send_header('Content-type', 'image/%s' % ext)
                modified = xbmcvfs.Stat(image).st_mtime()
                self.send_header('Last-Modified', "%s" % modified)
                image = xbmcvfs.File(image)
                size = image.size()
                self.send_header('Content-Length', str(size))
                self.end_headers()
                if not headers_only:
                    log_msg("sending image for request %s" % (self.path))
                    self.wfile.write(image.readBytes())
                image.close()
            else:
                self.send_error(404, 'No image was found')

        except Exception as exc:
            log_exception(__name__, exc)
            self.send_error(500, 'Exception occurred: %s' % exc)
        return

    def do_GET(self):
        '''called on GET requests'''
        self.handle_request()
        return


class StoppableHttpServer (BaseHTTPServer.HTTPServer):
    """http server that reacts to self.stop flag"""

    def serve_forever(self):
        """Handle one request at a time until stopped."""
        self.stop = False
        while not self.stop:
            self.handle_request()


def stop_server(port):
    """send QUIT request to http server running on localhost:<port>"""
    conn = httplib.HTTPConnection("localhost:%d" % port)
    conn.request("QUIT", "/")
    conn.getresponse()

#!/usr/bin/python
# -*- coding: utf-8 -*-

import SimpleHTTPServer, BaseHTTPServer, httplib
import threading
import thread
from Utils import *
from ArtworkUtils import *

#port is hardcoded as there is no way in Kodi to pass a INFO-label inside a panel, 
#otherwise the portnumber could be passed to the skin though a skin setting or window prop
port = 52307

class WebService(threading.Thread):
    event = None
    exit = False
    
    def __init__(self, *args):
        logMsg("WebService - start helper webservice on port " + str(port),0)
        self.event =  threading.Event()
        threading.Thread.__init__(self, *args)
    
    def stop(self):
        try:
            logMsg("WebService - stop called",0)
            conn = httplib.HTTPConnection("127.0.0.1:%d" % port)
            conn.request("QUIT", "/")
            conn.getresponse()
            self.exit = True
            self.event.set()
        except Exception as e: logMsg("WebServer exception occurred " + str(e))

    def run(self):
        try:
            server = StoppableHttpServer(('127.0.0.1', port), StoppableHttpRequestHandler)
            server.serve_forever()
        except Exception as e: logMsg("WebServer exception occurred " + str(e))
            


class Request(object):
    # attributes from urlsplit that this class also sets
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
    #http request handler with QUIT stopping the server
    
    def __init__(self, request, client_address, server):
        try:
            SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
        except Exception as e: logMsg("WebServer error in request --> " + str(e))
    
    def do_QUIT (self):
        #send 200 OK response, and set server.stop to True
        self.send_response(200)
        self.end_headers()
        self.server.stop = True
    
    def log_message(self, format, *args):
        logMsg("Webservice --> %s - - [%s] %s\n" %(self.address_string(),self.log_date_time_string(),format%args))
    
    def parse_request(self):
        #hack to accept non url encoded strings to pass listitem details from Kodi to webservice
        #strip the passed arguments apart, urlencode them and pass them back as new requestline properly formatted
        if "GET /" in self.raw_requestline or "HEAD /" in self.raw_requestline:
            if self.raw_requestline.startswith("HEAD"): command = "HEAD /"
            else: command = "GET /"
            action = self.raw_requestline.split("&")[0].replace(command,"")
            temp_requestline = self.raw_requestline.replace(command,"").replace(" HTTP/1.1","").replace("\r\n","").replace(action,"")
            parameters = temp_requestline.split("&")
            paramstring = "&action=%s" %action
            for param in parameters:
                if param and len(param.split("=")) > 1:  paramstring += "&%s=%s" %(param.split("=")[0], single_urlencode(param.split("=")[1]))
            self.raw_requestline = "%s%s%s HTTP/1.1" %(command,action,paramstring)
        retval = SimpleHTTPServer.SimpleHTTPRequestHandler.parse_request(self)
        self.request = Request(self.path, self.headers, self.rfile)
        return retval
    
    def do_HEAD(self):
        image, multi = self.send_headers()
        if image: image.close()
        return
    
    def send_headers(self):
        image = None
        images = None
        preferred_type = None
        params = urlparse.parse_qs(self.path)
        action = params.get("action","")[0]
        title = params.get("title","")
        if title: title = title[0].decode("utf-8")
        fallback = params.get("fallback","")
        if fallback: 
            fallback = fallback[0].decode("utf-8")
            if fallback.startswith("Default"): fallback = "special://skin/media/" + fallback

        if action == "getthumb":
            image = searchGoogleImage(title)
        
        elif action == "getvarimage":
            title = title.replace("{","[").replace("}","]")
            image_tmp = xbmc.getInfoLabel(title)
            if xbmcvfs.exists(image_tmp):
                if image_tmp.startswith("resource://"):
                    #texture packed resource images are failing: http://trac.kodi.tv/ticket/16366
                    logMsg("WebService ERROR --> resource images are currently not supported due to a bug in Kodi" ,0)
                else:
                    image = image_tmp
        
        elif action == "getpvrthumb":
            channel = params.get("channel","")
            preferred_type = params.get("type","")
            if channel: channel = channel[0].decode("utf-8")
            if preferred_type: preferred_type = preferred_type[0]
            if xbmc.getCondVisibility("Window.IsActive(MyPVRRecordings.xml)"): type = "recordings"
            else: type = "channels"
            artwork = getPVRThumbs(title, channel, type)
            if preferred_type:
                preferred_types = preferred_type.split(",")
                for preftype in preferred_types:
                    if artwork.get(preftype):
                        image = artwork.get(preftype)
                        break
            else:
                if artwork.get("thumb"): image = artwork.get("thumb")
                if artwork.get("fanart"): image = artwork.get("fanart")
                if artwork.get("landscape"): image = artwork.get("landscape")

        elif action == "getallpvrthumb":
            channel = params.get("channel","")
            if channel: channel = channel[0].decode("utf-8")
            images = getPVRThumbs(title, channel, "recordings")
            # Ensure no unicode in images...
            for key, value in images.iteritems():
                images[key] = unicode(value).encode('utf-8')
            images = urllib.urlencode(images)
        
        elif action == "getmusicart":
            dbid = params.get("dbid","")
            if dbid: dbid = dbid[0]
            preferred_type = params.get("type","")
            if preferred_type: preferred_type = preferred_type[0]
            artist = params.get("artist","")
            if artist: artist = artist[0]
            album = params.get("album","")
            if album: album = album[0]
            track = params.get("track","")
            if track: track = track[0]
            contenttype = params.get("contenttype","")
            if contenttype: contenttype = contenttype[0]
            if dbid and contenttype:
                artwork = getMusicArtworkByDbId(dbid, contenttype)
            else:
                artwork = getMusicArtworkByName(artist, track, album)
            if preferred_type:
                preferred_types = preferred_type.split(",")
                for preftype in preferred_types:
                    if artwork.get(preftype):
                        image = artwork.get(preftype)
                        break
            else:
                if artwork.get("thumb"): image = artwork.get("thumb")
                if artwork.get("fanart"): image = artwork.get("fanart")
        
        #set fallback image if nothing else worked
        if not image and fallback: image = fallback
        
        if images:
            self.send_response(200)
            self.send_header('Content-type','text/plaintext')
            self.send_header('Content-Length',len(images))
            self.end_headers()
            return images, True
        elif image:
            self.send_response(200)
            if ".jpg" in image: self.send_header('Content-type','image/jpeg')
            else: self.send_header('Content-type','image/png')
            logMsg("found image for request %s  --> %s" %(try_encode(self.path),try_encode(image)))
            st = xbmcvfs.Stat(image)
            modified = st.st_mtime()
            self.send_header('Last-Modified',"%s" %modified)
            image = xbmcvfs.File(image)
            size = image.size()
            self.send_header('Content-Length',str(size))
            self.end_headers() 
        else:
            self.send_error(404)
        return image, None

    def do_GET(self):
        image, multi = self.send_headers()
        if image and not multi:
            #send the image to the client
            logMsg("WebService -- sending image for --> " + try_encode(self.path))
            self.wfile.write(image.readBytes())
            image.close()
        elif image:
            #send multiple images to the client (plaintext)
            logMsg("WebService -- sending multiple images for --> " + try_encode(self.path))
            self.wfile.write(image)
        return

class StoppableHttpServer (BaseHTTPServer.HTTPServer):
    """http server that reacts to self.stop flag"""

    def serve_forever (self):
        """Handle one request at a time until stopped."""
        self.stop = False
        while not self.stop:
            self.handle_request()


def stop_server (port):
    """send QUIT request to http server running on localhost:<port>"""
    conn = httplib.HTTPConnection("localhost:%d" % port)
    conn.request("QUIT", "/")
    conn.getresponse()
   
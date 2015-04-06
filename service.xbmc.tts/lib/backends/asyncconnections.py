import socket, urllib2, httplib, select, time

from lib import util

STOP_REQUESTED = False
STOPPABLE = False
DEBUG = False

class AbortRequestedException(Exception): pass
class StopRequestedException(Exception): pass

if not hasattr(httplib.HTTPResponse, 'fileno'):
    class ModHTTPResponse(httplib.HTTPResponse):
        def fileno(self):
            return self.fp.fileno()
    httplib.HTTPResponse = ModHTTPResponse

def StopConnection():
    global STOP_REQUESTED
    if not STOPPABLE:
        STOP_REQUESTED = False
        return
    util.LOG('User requsted stop of connection')
    STOP_REQUESTED = True
    
def setStoppable(val):
    global STOPPABLE
    STOPPABLE = val
    
def resetStopRequest():
    global STOP_REQUESTED
    STOP_REQUESTED = False
    
class _AsyncHTTPResponse(httplib.HTTPResponse):
    _prog_callback = None
    def _read_status(self):
        ## Do non-blocking checks for server response until something arrives.
        setStoppable(True)
        try:
            while True:
                sel = select.select([self.fp.fileno()], [], [], 0)
                if len(sel[0]) > 0:
                    break
                ## <--- Right here, check to see whether thread has requested to stop
                ##      Also check to see whether timeout has elapsed
                if util.abortRequested():
                    if DEBUG: util.LOG(' -- XBMC requested abort during wait for server response: raising exception -- ')
                    raise AbortRequestedException('httplib.HTTPResponse._read_status')
                elif STOP_REQUESTED:
                    if DEBUG: util.LOG('Stop requested during wait for server response: raising exception')
                    resetStopRequest()
                    raise StopRequestedException('httplib.HTTPResponse._read_status')
                
                if self._prog_callback:
                    if not self._prog_callback(-1):
                        resetStopRequest()
                        raise StopRequestedException('httplib.HTTPResponse._read_status')
                    
                time.sleep(0.1)
            return httplib.HTTPResponse._read_status(self)
        finally:
            setStoppable(False)
            resetStopRequest()

AsyncHTTPResponse = _AsyncHTTPResponse

class Connection(httplib.HTTPConnection):
    response_class = AsyncHTTPResponse

class _Handler(urllib2.HTTPHandler):
    def http_open(self, req):
        return self.do_open(Connection, req)

Handler = _Handler

#def createHandlerWithCallback(callback):
#    if getSetting('disable_async_connections',False):
#        return urllib2.HTTPHandler
#    
#    class rc(AsyncHTTPResponse):
#        _prog_callback = callback
#        
#    class conn(httplib.HTTPConnection):
#        response_class = rc
#        
#    class handler(urllib2.HTTPHandler):
#        def http_open(self, req):
#            return self.do_open(conn, req)
#    
#    return handler

def checkStop():
    if util.abortRequested():
        if DEBUG: util.LOG(' -- XBMC requested abort during wait for connection to server: raising exception -- ')
        raise AbortRequestedException('socket[asyncconnections].create_connection')
    elif STOP_REQUESTED:
        if DEBUG: util.LOG('Stop requested during wait for connection to server: raising exception')
        resetStopRequest()
        raise StopRequestedException('socket[asyncconnections].create_connection')
        
def waitConnect(sock,timeout):
    start = time.time()
    while time.time() - start < timeout:
        sel = select.select([], [sock], [], 0)
        if len(sel[1]) > 0:
            break
        checkStop()
        time.sleep(0.1)
    sock.setblocking(True)
    return sock
    
def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    setStoppable(True)
    try:
        return _create_connection(address, timeout=timeout, source_address=source_address)
    finally:
        setStoppable(False)
        resetStopRequest()
        
def _create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    host, port = address
    err = None
    for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        checkStop()
        af, socktype, proto, canonname, sa = res  # @UnusedVariable
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            if port == 443: #SSL
                sock.connect(sa)
            else:
                sock.setblocking(False)
                err = sock.connect_ex(sa)
                waitConnect(sock,timeout)
            return sock

        except socket.error as _:
            err = _
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
    else:
        raise socket.error("getaddrinfo returns an empty list")
        
OLD_socket_create_connection = socket.create_connection

def setEnabled(enable=True):
    global OLD_socket_create_connection, AsyncHTTPResponse, Handler
    if enable:
        if DEBUG: util.LOG('Asynchronous connections: Enabled')
        socket.create_connection = create_connection
        AsyncHTTPResponse = _AsyncHTTPResponse
        Handler = _Handler
    else:
        if DEBUG: util.LOG('Asynchronous connections: Disabled')
        AsyncHTTPResponse = httplib.HTTPResponse
        Handler = urllib2.HTTPHandler
        if OLD_socket_create_connection: socket.create_connection = OLD_socket_create_connection
        
    
# h = Handler()
# o = urllib2.build_opener(h)
# f = o.open(url)
# print f.read()

import socket, urllib2, httplib, select, time, xbmc
from lib.util import AbortRequestedException, StopRequestedException, getSetting

def LOG(msg): print msg

STOP_REQUESTED = False
STOPPABLE = False

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
	LOG('User requsted stop of connection')
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
				##	  Also check to see whether timeout has elapsed
				if xbmc.abortRequested:
					LOG(' -- XBMC requested abort during wait for server response: raising exception -- ')
					raise AbortRequestedException('httplib.HTTPResponse._read_status')
				elif STOP_REQUESTED:
					LOG('Stop requested during wait for server response: raising exception')
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
if getSetting('disable_async_connections',False):
	LOG('Asynchronous connections: Disabled')
	AsyncHTTPResponse = httplib.HTTPResponse

class Connection(httplib.HTTPConnection):
	response_class = AsyncHTTPResponse

class Handler(urllib2.HTTPHandler):
	def http_open(self, req):
		return self.do_open(Connection, req)

def createHandlerWithCallback(callback):
	if getSetting('disable_async_connections',False):
		return urllib2.HTTPHandler
	
	class rc(AsyncHTTPResponse):
		_prog_callback = callback
		
	class conn(httplib.HTTPConnection):
		response_class = rc
		
	class handler(urllib2.HTTPHandler):
		def http_open(self, req):
			return self.do_open(conn, req)
	
	return handler

def create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
					  source_address=None):
	"""Connect to *address* and return the socket object.

	Convenience function.  Connect to *address* (a 2-tuple ``(host,
	port)``) and return the socket object.  Passing the optional
	*timeout* parameter will set the timeout on the socket instance
	before attempting to connect.  If no *timeout* is supplied, the
	global default timeout setting returned by :func:`getdefaulttimeout`
	is used.  If *source_address* is set it must be a tuple of (host, port)
	for the socket to bind as a source address before making the connection.
	An host of '' or port 0 tells the OS to use the default.
	"""

	host, port = address
	err = None
	setStoppable(True)
	try:
		for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
			if xbmc.abortRequested:
				LOG(' -- XBMC requested abort during wait for connection to server: raising exception -- ')
				raise AbortRequestedException('socket[asyncconnections].create_connection')
			elif STOP_REQUESTED:
				LOG('Stop requested during wait for connection to server: raising exception')
				resetStopRequest()
				raise StopRequestedException('socket[asyncconnections].create_connection')
			af, socktype, proto, canonname, sa = res  # @UnusedVariable
			sock = None
			try:
				sock = socket.socket(af, socktype, proto)
				if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
					sock.settimeout(timeout)
				sock.setblocking(False)
				if source_address:
					sock.bind(source_address)
				err = sock.connect_ex(sa)
				#print os.strerror(err) #Operation now in progress
				start = time.time()
				while time.time() - start < timeout:
					sel = select.select([], [sock], [], 0)
					if len(sel[1]) > 0:
						break
					if xbmc.abortRequested:
						LOG(' -- XBMC requested abort during wait for connection to server: raising exception -- ')
						raise AbortRequestedException('socket[asyncconnections].create_connection')
					elif STOP_REQUESTED:
						LOG('Stop requested during wait for connection to server: raising exception')
						resetStopRequest()
						raise StopRequestedException('socket[asyncconnections].create_connection')
					#err = sock.connect_ex(sa)
					#print time.time() #Operation already in progress
					time.sleep(0.1)
				#print os.strerror(sock.connect_ex(sa)) #Success
				sock.setblocking(True)
				return sock
	
			except socket.error as _:
				err = _
				if sock is not None:
					sock.close()
	
		if err is not None:
			raise err
		else:
			raise socket.error("getaddrinfo returns an empty list")
	finally:
		setStoppable(False)
		resetStopRequest()
		
if not getSetting('disable_async_connections',False):
	socket.create_connection = create_connection

# h = Handler()
# o = urllib2.build_opener(h)
# f = o.open(url)
# print f.read()

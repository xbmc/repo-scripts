import urllib, simplejson

class JsonRPCError(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
        
class ConnectionError(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
        
class UserPassError(Exception): pass
        
class Namespace:
	def __init__(self,name,url):
		self.name = name
		self.url = url
		self.__handler_cache = {}
		
	def __getattr__(self, method):
		if method in self.__handler_cache:
			return self.__handler_cache[method]
		
		def handler(**kwargs):
			postdata = '{"jsonrpc": "2.0","id":"1","method":"%s.%s"' % (self.name,method)
			if kwargs:
				postdata += ',"params": {'
				append = ''
				for k in kwargs:
					if append: append += ','
					append += '"%s":"%s"' % (str(k),str(kwargs[k]))
				postdata += append + '}'
			postdata += '}'
			#print postdata
			try:
				fobj = urllib.urlopen(self.url,postdata)
			except IOError,e:
				if e.args[0] == 'http error':
					 if e.args[1] == 401: raise UserPassError()
				raise ConnectionError(e.errno,'Connection error: ' + str(e.errno))
			
			try:
				json = simplejson.loads(fobj.read())
			except:
				fobj.close()
				
			if 'error' in json: raise JsonRPCError(json['error']['code'],json['error']['message'])
			
			return json['result']
				

		handler.method = method
		self.__handler_cache[method] = handler
		return handler
		
class jsonrpcAPI:
	def __init__(self,url='http://127.0.0.1:8080/jsonrpc',user=None,password=None):
		if password: url = url.replace('http://','http://%s:%s@' % (user,password))
		#print "URL: " + url
		self.url = url
		self.__namespace_cache = {}
		
	def __getattr__(self, namespace):
		if namespace in self.__namespace_cache:
			return self.__namespace_cache[namespace]
				
		nsobj = Namespace(namespace,self.url)
		self.__namespace_cache[namespace] = nsobj
		return nsobj
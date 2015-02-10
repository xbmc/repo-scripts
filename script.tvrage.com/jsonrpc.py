# -*- coding: utf-8 -*-
import requests, simplejson

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='urllib2')

try:
	import xbmc #@UnresolvedImport
except:
	#we're not in XBMC so we only get http
	pass

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

class baseNamespace:
	def createParams(self,method,args,kwargs):
		postdata = '{"jsonrpc": "2.0","id":"1","method":"%s.%s"' % (self.name,method)
		if kwargs:
			postdata += ',"params": {'
			append = ''
			for k in kwargs:
				if append: append += ','
				val = kwargs[k]
				append += '"%s":%s' % (str(k),simplejson.dumps(val))
			postdata += append + '}'
		elif args:
			postdata += ',"params":'
			if len(args) == 1: args = args[0]
			postdata += simplejson.dumps(args)
		postdata += '}'
		return postdata

class httpNamespace(baseNamespace):
	def __init__(self,name,api):
		self.__handler_cache = {}
		self.api = api
		self.name = name
		
	def __getattr__(self, method):
		if method in self.__handler_cache:
			return self.__handler_cache[method]

		def handler(*args,**kwargs):
			postdata = self.createParams(method,args,kwargs)
			
			try:
				req = requests.post(self.api.url,auth=(self.api.user,self.api.password),data=postdata)
			except Exception,e:
				raise ConnectionError(0,'Connection error: {0}'.format(e))
			
			json = req.json()
			if 'error' in json: raise JsonRPCError(json['error']['code'],json['error']['message'])
			
			return json['result']
				

		handler.method = method
		self.__handler_cache[method] = handler
		return handler
		
class execNamespace(baseNamespace):
	def __init__(self,name,api):
		self.__handler_cache = {}
		self.api = api
		self.name = name
		
	def __getattr__(self, method):
		if method in self.__handler_cache:
			return self.__handler_cache[method]
		
		def handler(*args,**kwargs):
			postdata = self.createParams(method,args,kwargs)
			
			jsonstring = xbmc.executeJSONRPC(postdata)
			json = simplejson.loads(jsonstring)
				
			if 'error' in json: raise JsonRPCError(json['error']['code'],json['error']['message'])

			return json['result']
				

		handler.method = method
		self.__handler_cache[method] = handler
		return handler

class jsonrpcAPI:
	def __init__(self,mode='exec',url='http://127.0.0.1:8080',user=None,password=None):
		self.__namespace = None
		self.user = None
		self.password = None
		self.base = url
		if mode == 'http':
			self.url = url + '/jsonrpc'
			self.__namespace = httpNamespace
			self.user = user
			self.password = password
		else:
			self.__namespace = execNamespace
		self.__namespace_cache = {}
		
	def __getattr__(self, namespace):
		if namespace in self.__namespace_cache:
			return self.__namespace_cache[namespace]
				
		self__namespace = self.__namespace #to prevent recursion
		nsobj = self__namespace(namespace,self)
		
		self.__namespace_cache[namespace] = nsobj
		return nsobj
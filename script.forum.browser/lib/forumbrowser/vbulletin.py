import urllib2, urllib, json, re, hashlib

def LOG(message):
	print message
	
DEBUG = False

class VBCFail:
	def __init__(self,result=None):
		self.result = result and result.get('response') or {}
		self.message = self.result.get('errormessage','') or ''
		
	def __nonzero__(self):
		return False
	
class VBulletinClient():
	def __init__(self,url):
		self.url = url
		if not self.url.endswith('/'): self.url += '/'
		self.cache = {}
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
		self.clientArgs = {	'clientname':'ForumBrowser',
							'clientversion':'0.9',
							'platformname':'xbmc',
							'platformversion':'11',
							'uniqueid':'123456789',
							}
		
		self.apikey = '250000'
		self.apiaccesstoken = None
		self.secret = None
		self.apiclientid = None
		self.initialized = False
		
	def __getattr__(self, method):
		if method.startswith('_'): return object.__getattr__(self,method)
		if method in self.cache:
			return self.cache[method]
				
		def handler(**args):
			try:
				return self._callMethod(method,**args)
			except:
				LOG('Failed: VBulletinClient.%s()' % method)
				raise
	
		handler.method = method
		
		self.cache[method] = handler
		return handler
	
	def _callMethod(self,method,**args):
		url = self.url + 'api.php?'
		#url = '&'.join((url,urllib.urlencode(args)))
		args.update({'api_m':method})
		if method != 'api_init': args.update({'api_s':self.apiaccesstoken,'api_sig':self._createSig(args),'api_c':self.apiclientid,'api_v':'3'})
		encArgs = urllib.urlencode(args)
		obj = self.opener.open(url,encArgs)
		if DEBUG: LOG('Response Headers: ' + str(obj.info()))
		encoding = obj.info().get('content-type').split('charset=')[-1]
		if '/' in encoding: encoding = 'utf8'
		data = unicode(obj.read(),encoding)
		pyobj = None
		try:
			pyobj = json.loads(data)
		except:
			pass
		if not pyobj: pyobj = json.loads(re.sub(r'\\u[\d\w]+','?',data),strict=False)
		if DEBUG: LOG('JSON: ' + str(pyobj))
		if not pyobj.get('response'):
			return pyobj
		else:
			return VBCFail(pyobj)
		
	def _createSig(self,args):
		sigargs = {}
		sigkeys = []
		for k,v in args.items():
			if not k.startswith('api_') or k == 'api_m':
				sigkeys.append(k)
				sigargs[k] = v
		sigkeys.sort()
		siglist = []
		for k in sigkeys:
			siglist.append(k + '=' + sigargs[k])
		sigstr = '&'.join(siglist)
		sigmd5 = hashlib.md5(sigstr + self.apiaccesstoken + self.apiclientid + self.secret + self.apikey).hexdigest()
		return sigmd5
		
				
			
	
	def _api_init(self):
		result = self._callMethod('api_init',**self.clientArgs)
		if result:
			self.apiaccesstoken = result.get('apiaccesstoken')
			self.secret = result.get('secret')
			self.apiclientid = result.get('apiclientid')
			self.initialized = True
		return result
	
	
	
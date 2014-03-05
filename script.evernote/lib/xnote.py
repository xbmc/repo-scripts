# -*- coding: utf-8 -*-
import xbmcaddon, xbmc, xbmcgui #@UnresolvedImport
import sys, os, re, traceback, glob, time, threading, httplib
from webviewer import htmltoxbmc #@UnresolvedImport
import maps
import httplib2  # @UnusedImport

	
#Evernote Imports
import hashlib, binascii, getpass
from xml.sax.saxutils import escape
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors

__author__ = 'ruuk'
__url__ = 'http://code.google.com/p/evernote-xbmc/'
__date__ = '1-21-2013'
__version__ = '0.3.1'
__addon__ = xbmcaddon.Addon(id='script.evernote')
__lang__ = __addon__.getLocalizedString


ACTION_MOVE_LEFT      = 1
ACTION_MOVE_RIGHT     = 2
ACTION_MOVE_UP        = 3
ACTION_MOVE_DOWN      = 4
ACTION_PAGE_UP        = 5
ACTION_PAGE_DOWN      = 6
ACTION_SELECT_ITEM    = 7
ACTION_HIGHLIGHT_ITEM = 8
ACTION_PARENT_DIR_OLD = 9
ACTION_PARENT_DIR     = 92
ACTION_PREVIOUS_MENU  = 10
ACTION_SHOW_INFO      = 11
ACTION_PAUSE          = 12
ACTION_STOP           = 13
ACTION_NEXT_ITEM      = 14
ACTION_PREV_ITEM      = 15
ACTION_SHOW_GUI       = 18
ACTION_PLAYER_PLAY    = 79
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_CONTEXT_MENU   = 117

#Actually it's show codec info but I'm using in a threaded callback
ACTION_RUN_IN_MAIN = 27

THEME = 'Default'

import locale
loc = locale.getdefaultlocale()
print loc
ENCODING = loc[1] or 'utf-8'

def ENCODE(string,encoding=ENCODING):
	try: string = str(string)
	except: pass
	try: string = string.decode('utf-8')
	except: pass
	return string.encode(encoding,'replace')

def LOG(message):
	message = ENCODE(message)
	xbmc.log('X-NOTE: %s' % message)
	
def ERROR(message):
	LOG(message)
	traceback.print_exc()
	err = str(sys.exc_info()[1])
	return err

LOG('Version: ' + __version__)

class EvernoteSessionError(Exception):
	def __init__(self,func,meth,e):
		errorText = Errors.EDAMErrorCode._VALUES_TO_NAMES[e.errorCode]
		Exception.__init__(self, errorText)
		self.error = e
		self.code = e.errorCode
		self.function = func
		self.method = meth
		self.parameter = hasattr(e,'parameter') and e.parameter or '?'
		self.message = errorText
			
class EvernoteSession():
	def __init__(self):
		self.consumerKey = "ruuk25-1051"
		self.consumerSecret = "5a5ca4c9cecf455b"
		self.evernoteHost = "www.evernote.com"
		
		self.userStoreUri = "https://" + self.evernoteHost + "/edam/user"
		self.noteStoreUriBase = "https://" + self.evernoteHost + "/edam/note/"
		
		self.request_token_url = 'https://' + self.evernoteHost + '/oauth'
		self.authorize_url = 'https://' + self.evernoteHost + '/OAuth.action'
		self.callback_url = 'http://2ndmind.com'
		
		self.userStoreHttpClient = THttpClient.THttpClient(self.userStoreUri)
		self.userStoreProtocol = TBinaryProtocol.TBinaryProtocol(self.userStoreHttpClient)
		self.userStore = UserStore.Client(self.userStoreProtocol)
		self.user = None
		self.username = None
		self.password = None
		self.noteStores = {}
		self.tokens = {}
		self._tempToken = None
		self.authToken = None
		
	def authenticate(self):
		LOG('Authenticating')
		import urlparse, urllib
		oauth = self.getOAuth()
		client = self.getOAuthClient(oauth)
		resp, content = client.request(self.request_token_url + '?oauth_callback='+ urllib.quote(self.callback_url), "POST")
		#LOG(resp['status'])
		if resp['status'] != '200':
			LOG(repr(content))
			raise Exception("Invalid response %s." % resp['status'])
		
		request_token = dict(urlparse.parse_qsl(content))
		
		#print "Request Token:"
		#print "    - oauth_token        = %s" % request_token['oauth_token']
		#print "    - oauth_token_secret = %s" % request_token['oauth_token_secret']
		auth_url = "%s?oauth_token=%s" % (self.authorize_url, request_token['oauth_token'])
		token_url = self.webwiewer(auth_url)
		#LOG('AUTH RESPONSE URL: ' + str(token_url))
		if not token_url: return None
		self._tempToken = self.authPart2(oauth,token_url,request_token)
		return self._tempToken
		
	def getOAuth(self):
		import ssl
		def _ssl_wrap_socket(sock, key_file, cert_file,
							 disable_validation, ca_certs):
			if disable_validation:
				cert_reqs = ssl.CERT_NONE
			else:
				cert_reqs = ssl.CERT_REQUIRED
			return ssl.wrap_socket(sock, keyfile=key_file, certfile=cert_file,
								   cert_reqs=cert_reqs, ca_certs=ca_certs, ssl_version=ssl.PROTOCOL_TLSv1)
		httplib2._ssl_wrap_socket = _ssl_wrap_socket
			
		import oauth2
		return oauth2
	
	def getOAuthClient(self,oauth,token=None):
		consumer = oauth.Consumer(self.consumerKey, self.consumerSecret)
		if token:
			client = oauth.Client(consumer, token)
		else:
			client = oauth.Client(consumer)
		return client
		
	def authPart2(self,oauth, url,request_token):
		import urlparse
		request_token2 = dict(urlparse.parse_qsl(url))
		oauth_verifier = request_token2.get('oauth_verifier', '')
		
		try:
			token = oauth.Token(
				request_token['oauth_token'],
				request_token['oauth_token_secret'])
			token.set_verifier(oauth_verifier)
	
			client = self.getOAuthClient(oauth,token)
	
			resp, content = client.request(self.request_token_url, 'POST')
			access_token = dict(urlparse.parse_qsl(content))
			auth_token = access_token['oauth_token']
		except KeyError:
			return None
		
		return auth_token
		
	def webwiewer(self,url):
		from webviewer import webviewer #@UnresolvedImport
		autoforms = [	{'name':'login_form'},{'name':'oauth_authorize_form'}]
		autoclose = {	'url':'.*&oauth_verifier=.*',
						'heading':__lang__(32505),
						'message':__lang__(32506)}

		
		print '-----------------------------------------------START'
		url,html = webviewer.getWebResult(url,autoForms=autoforms,autoClose=autoclose,dialog=True,clearCookies=True) #@UnusedVariable
		print '-----------------------------------------------END'
		return url
		
	def setUserToken(self,username,token):
		self.username = username
		self.authToken = token
		
	def startSession(self,new=False):
		self.defaultNotebook = None
		self.notebooks = []
		import ssl
		try:
			if not self.checkVersion(): return None
		except ssl.SSLError:
			self.fixSSL()
			if not self.checkVersion(): return None
		# Authenticate the user
		if not self.authToken or new:
			token = self.authenticate()
			if token: self.authToken = token
		if not self.authToken: return None
		
		self.user = self.userStore.getUser(self.authToken)
		
		LOG("Authentication was successful for %s" % self.user.username)
		#LOG("Authentication token = %s" % self.authToken)
		
		#noteStoreUri =  self.noteStoreUriBase + self.user.shardId
		noteStoreUri = self.userStore.getNoteStoreUrl(self.authToken)
		noteStoreHttpClient = THttpClient.THttpClient(noteStoreUri)
		noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
		self.noteStore = NoteStore.Client(noteStoreProtocol)
		
		return self.user

	def fixSSL(self):
		LOG('SSL Failed, attempting workaround')
		import socket, ssl
		class HTTPSConnection(httplib.HTTPConnection):
				"This class allows communication via SSL."
		
				default_port = httplib.HTTPS_PORT
		
				def __init__(self, host, port=None, key_file=None, cert_file=None,
							 strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
							 source_address=None):
					httplib.HTTPConnection.__init__(self, host, port, strict, timeout,
											source_address)
					self.key_file = key_file
					self.cert_file = cert_file
		
				def connect(self):
					"Connect to a host on a given (SSL) port."
		
					sock = socket.create_connection((self.host, self.port),
													self.timeout, self.source_address)
					if self._tunnel_host:
						self.sock = sock
						self._tunnel()
					self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,ssl_version=ssl.PROTOCOL_TLSv1)
		httplib.HTTPSConnection = HTTPSConnection
		
		class HTTPS(httplib.HTTP):
			_connection_class = HTTPSConnection
		
			def __init__(self, host='', port=None, key_file=None, cert_file=None,
							 strict=None):
					# provide a default host, pass the X509 cert info
		
					# urf. compensate for bad input.
					if port == 0:
						port = None
					self._setup(self._connection_class(host, port, key_file,
													   cert_file, strict))
		
					# we never actually use these for anything, but we keep them
					# here for compatibility with post-1.5.2 CVS.
					self.key_file = key_file
					self.cert_file = cert_file
		httplib.HTTPS = HTTPS

	def checkVersion(self):
		versionOK = self.userStore.checkVersion("Python EDAMTest",
										   UserStoreConstants.EDAM_VERSION_MAJOR,
										   UserStoreConstants.EDAM_VERSION_MINOR)
		
		LOG("EDAM protocol version up to date? - %s " % str(versionOK))
		return versionOK
		
	def getNotebooks(self,ignoreCache=False,linked=False):
		if linked:
			notebooks = self.authCallWrapper(self.noteStore.listLinkedNotebooks,'getNotebooks()','noteStore.listLinkedNotebooks')
			LOG("Found %s linked notebooks:" % len(notebooks))
		else:
			if self.notebooks and not ignoreCache: return self.notebooks
			notebooks = self.authCallWrapper(self.noteStore.listNotebooks,'getNotebooks()','noteStore.listNotebooks')
			self.notebooks = notebooks
			LOG("Found %s notebooks:" % len(notebooks))
			for notebook in notebooks:
				LOG("  * %s" % notebook.name)
				if notebook.defaultNotebook:
					self.defaultNotebook = notebook
		return notebooks

	def getNotebookCounts(self):
		ncc = self.authCallWrapper(self.noteStore.findNoteCounts,'getNotebookCounts()','noteStore.findNoteCounts',NoteStore.NoteFilter(),False)
		return ncc
		
	def getNotebookByGuid(self,guid):
		notebooks = self.getNotebooks()
		for nb in notebooks:
			if nb.guid == guid: return nb
		return None
	
	def getNotebookByName(self,notebook_name):
		notebooks = self.getNotebooks()
		for nb in notebooks:
			if nb.name == notebook_name: return nb
		return None
	
	def publishNotebook(self,notebook,publish=True,desc='',uri=None):
		if type(notebook) == type(''):
			notebook = self.getNotebookByGuid(notebook)
		if notebook.published == publish: return
		notebook.published = publish
		if publish: 
			pub = Types.Publishing()
			if not uri: uri = re.sub('\W','',notebook.name)
			pub.uri = uri
			pub.publicDescription = desc
			notebook.publishing = pub
		self.authCallWrapper(self.noteStore.updateNotebook,'publishNotebook()','noteStore.updateNotebook', notebook)
	
	def addNoteStore(self,guid,notestore,token=None):
		self.noteStores[guid] = notestore
		if token: self.tokens[guid] = token
		
	def getNoteStore(self,guid):
		if guid in self.noteStores:
			LOG('Using other noteStore')
			self.setTempToken(guid)
			return self.noteStores[guid]
		return self.noteStore
	
	def setTempToken(self,guid):
		if guid in self.tokens:
			LOG('Using other token')
			self._tempToken = self.tokens[guid]
		else:
			self._tempToken = None
	
	def getNoteByGuid(self,guid,nbguid=None):
		noteStore = self.getNoteStore(nbguid)
		note = self.authCallWrapper(noteStore.getNote,'getNoteByGuid()','noteStore.getNote', guid, True, False, False, False)
		return note
	
	def getNoteList(self,guid=None,search=None):
		noteStore = self.getNoteStore(guid)
		if guid and not type(guid) == type(''): guid = guid.guid
		nf = NoteStore.NoteFilter()
		if guid:
			if guid != 'all': nf.notebookGuid = guid
			LOG('Getting notes for notebook - guid: %s' % guid)
		else:
			nf.words = search
			LOG('Getting notes for search: %s' % search)
	
		notes = self.authCallWrapper(noteStore.findNotes,'getNoteList()','noteStore.findNotes',nf,0,999)
		return notes
		
	def getLinkedNoteList(self,guid,shardid,sharekey,notestoreurl,username,publicUri):
		info = self.userStore.getPublicUserInfo(username)
		noteStoreUri = info.noteStoreUrl #self.noteStoreUriBase + info.shardId
		noteStoreHttpClient = THttpClient.THttpClient(noteStoreUri)
		noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
		noteStore = NoteStore.Client(noteStoreProtocol)
		token = None
		if sharekey:
			res = noteStore.authenticateToSharedNotebook(sharekey, self.authToken)
			token = res.authenticationToken
			notebook = noteStore.getSharedNotebookByAuth(token)
			guid = notebook.notebookGuid
		else:
			notebook = noteStore.getPublicNotebook(info.userId, publicUri)
			guid = notebook.guid
			
		self.addNoteStore(guid, noteStore, token)
		
		return self.getNoteList(guid), guid
		
	def prepareText(self,text):
		return re.sub('[\n\r]+','<br />',escape(text))
		
	def deleteNote(self,guid):
		if not type(guid) == type(''): guid = guid.guid
		self.authCallWrapper(self.noteStore.deleteNote,'deleteNote()','noteStore.deleteNote', guid)
		LOG("Successfully deleted note with guid: %s" % (guid))
		
	def createNote(self,text='',image_files=[],notebook=None,title='',html='',lat=None,lon=None):
		note = Types.Note()
		if not title:
			if text:
				title = text.splitlines()[0][:30]
		if not title:
			if image_files: title = os.path.basename(image_files[0])
		if not title: title = 'UNTITLED'
		if type(notebook) == type(''):
			notebook = self.getNotebookByGuid(notebook)
			
		if notebook and not notebook.defaultNotebook:
			LOG("Creating a new note (%s) in notebook: %s" % (title,notebook.name))
			note.notebookGuid = notebook.guid
		else:
			LOG("Creating a new note (%s) in default notebook: %s" % (title,self.defaultNotebook.name))
			#notebook = self.defaultNotebook
		title = ENCODE(title,'utf-8')
		note.title = title
		if lat:
			note.attributes = Types.NoteAttributes()
			note.attributes.latitude = lat
			note.attributes.longitude = lon
		note.content = '<?xml version="1.0" encoding="UTF-8"?>'
		note.content += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
		note.content += '<en-note>%s%s<br/>' % (ENCODE(self.prepareText(text),'utf-8'),ENCODE(html,'utf-8'))
		
		if image_files:
			resources = []
			for ifile in image_files:
				root,ext = os.path.splitext(ifile) #@UnusedVariable
				if not ext: continue
				if ext == '.jpg': ext = '.jpeg'
				ext = ext[1:]
				image = open(ifile, 'rb').read()
				md5 = hashlib.md5()
				md5.update(image)
				mhash = md5.digest()
				hashHex = binascii.hexlify(mhash)
			
				data = Types.Data()
				data.size = len(image)
				data.bodyHash = mhash
				data.body = image
			
				resource = Types.Resource()
				resource.mime = 'image/' + ext
				resource.data = data
				resources.append(resource)
				note.content += '<en-media type="image/png" hash="' + hashHex + '"/>'
				
			note.resources = resources
			
		note.content += '</en-note>'
		createdNote = self.authCallWrapper(	self.noteStore.createNote,
											'createNote()',
											'noteStore.createNote',
											note)
		
		LOG("Successfully created a new note with GUID: %s" % createdNote.guid)
		return createdNote
	
	def moveNote(self,guid,nbguid):
		note = self.authCallWrapper(self.noteStore.getNote,'moveNote()','noteStore.getNote',guid,False,False,False,False)
		
		note.notebookGuid = nbguid
		
		self.authCallWrapper(self.noteStore.updateNote,'moveNote()','noteStore.updateNote', note)

		return note
						
	def deleteNotebook(self,guid=None,notebook=None):
		if not guid: guid = notebook.guid
		self.authCallWrapper(self.noteStore.expungeNotebook,'deleteNotebook()','noteStore.expungeNotebook', guid)
		
		LOG("Successfully deleted notebook with guid: %s" % (guid))
		
	def createNotebook(self,name,default=False):
		notebook = Types.Notebook()
		notebook.name = name
		createdNotebook = self.authCallWrapper(self.noteStore.createNotebook,'createNotebook()','noteStore.createNotebook', notebook)
		
		LOG("Successfully created a new notebook with GUID: %s" % createdNotebook.guid)
		return createdNotebook
		
	def addNotebookToStack(self,notebook,stack=''):
		if not stack:
			LOG('addNotebookToStack() - No Stack')
			return
		if type(notebook) == type(''):
			notebook = self.getNotebookByGuid(notebook)
		notebook.stack = stack
		return self.authCallWrapper(self.noteStore.updateNotebook,'addNotebookToStack()','noteStore.updateNotebook', notebook)
		
	def getResourceData(self,guid,nbguid=None):
		notestore = self.getNoteStore(nbguid)
		return self.authCallWrapper(notestore.getResourceData,'getResourceData()','noteStore.getResourceData', guid)
		
	def authCallWrapper(self,function,func_name,meth_name,*args,**kwargs):
		if self._tempToken:
			token = self._tempToken
			self._tempToken = None
		else:
			token = self.authToken
			
		try:
			return function(token,*args,**kwargs)
		except Errors.EDAMUserException as e:
			if e.errorCode != Errors.EDAMErrorCode.AUTH_EXPIRED:
				raise EvernoteSessionError(func_name,meth_name,e)
		except Errors.EDAMSystemException as e:
			raise EvernoteSessionError(func_name,meth_name,e)
		
		#If we get here, auth was expired. Restart session and try again
		LOG('API: Auth Expired - Restarting Session')
		self.startSession()
		LOG('API: Retrying Original Call...')
		try:
			return function(token,*args,**kwargs)
		except Errors.EDAMUserException as e:
			raise EvernoteSessionError(func_name,meth_name,e)
		except Errors.EDAMSystemException as e:
			raise EvernoteSessionError(func_name,meth_name,e)

def doKeyboard(prompt,default='',hidden=False):
	keyboard = xbmc.Keyboard(default,prompt)
	keyboard.setHiddenInput(hidden)
	keyboard.doModal()
	if not keyboard.isConfirmed(): return None
	return keyboard.getText()

def abbreviateURL(url):
	pre_len = 45
	base = '/' + os.path.basename(url)
	pre_len -= len(base)
	pre = os.path.dirname(url)[:-1][:pre_len] + '...'
	return pre + base
	
def getSetting(sett,default=None):
	return __addon__.getSetting(sett) or default

def getXBMCUser():
		return xbmc.getInfoLabel('System.ProfileName')
	
def getOSUser():
	try:
		return getpass.getuser()
	except:
		return ''
	
def getUserKey(user):
	return getXBMCUser() + getOSUser() + user

def preSavePassword(password):
	keyfile = getSetting('crypto_key_file', '')
	if keyfile: keyfile = ':' + binascii.hexlify(keyfile)
	if getSetting('crypto_type') == '0':
		return 'a' + password + keyfile
	elif getSetting('crypto_type') == '1':
		return 'd' + password + keyfile
	else:
		return 'b' + password + keyfile
	
def getPasswordCryptoMethod():
	s_idx = getSetting('crypto_type','2')
	if s_idx == '0':
		return 'aes'
	elif s_idx == '1':
		return 'des'
	else:
		return 'both'
	
def parsePassword(password):
	type_c = password[0]
	password = password[1:]
	password_keyfile = password.split(':',1)
	password = password_keyfile[0]
	keyfile = None
	if len(password_keyfile) == 2:
		keyfile = binascii.unhexlify(password_keyfile[1])
	if type_c.lower() == 'a':
		type_c = 'aes'
	elif type_c.lower() == 'd':
		type_c = 'des'
	else:
		type_c = 'both'
	return type_c,keyfile,password
	
def getUserList():
	userlist = __addon__.getSetting('user_list').split('@,@')
	if not userlist: return []
	if not userlist[0]: return []
	return userlist
	
class XNoteSession():
	def __init__(self,window=None,new=False):
		self.window = window
		self._pdialog = None
		self.currentNoteFilter = None
		self.updatingNote = None
		self.clipboard = None
		self.esession = None
		if new:
			self.start(new=True)
			return
		try:
			import SSClipboard #@UnresolvedImport
			self.clipboard = SSClipboard.Clipboard()
			LOG('Clipboard Enabled')
		except:
			LOG('Clipboard Disabled: Failed to import SSClipboard')
		
		self.CACHE_PATH = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')),'cache')
		maps_path = os.path.join(self.CACHE_PATH,'maps')
		if not os.path.exists(maps_path): os.makedirs(maps_path)
		
		self.maps = maps.Maps(maps_path)
		self.htmlconverter = htmltoxbmc.HTMLConverter()
		
		if not self.start():
			if not self.chooseUser():
				self.window.close()
				return
			if not self.start():
				self.window.close()
				return
		if new: return
		self.showNotebooks()
	
	def start(self,new=False):
		try:
			self.esession = EvernoteSession()
			if not self.startSession(new=new,just_close=new):
				return False
		except EvernoteSessionError as e:
			self.error(e,message=__lang__(32041))
			return False
		except:
			self.error(message=__lang__(32041))
			return False
		
		return True
			
	def startSession(self,user=None,new=False,just_close=False):
		if new:
			user = None
			token = None
		else:
			user,token = self.getUserToken(user)
			self.esession.setUserToken(user, token)
		if not user and not new:
			return False
		if not token: new = True
		#if not user: return False
		try:
			self.esession.startSession(new=new)
		except Errors.EDAMUserException, e:
			if e.errorCode == Errors.EDAMErrorCode.BAD_DATA_FORMAT:
				if e.parameter == 'authenticationToken':
					return self.changeUser()
		if not self.updateToken(new): return False
		if new and not just_close:
			self.clearNotes()
			self.showNotebooks()
			self.window.initFocus()
		return True
		
	def updateToken(self,new):
		if not self.esession.user: return False
		user = self.esession.user.username
		token = self.esession.authToken
		if (not user) or (not token): return False
		__addon__.setSetting('last_user',user)
		__addon__.setSetting('token_%s' % user,token)
		if new: self.addUser(user, token)
		return True
	
	def error(self,error=None,message='',extra=''):
		if error:
			if isinstance(error,EvernoteSessionError):
				ERROR('ES API Error - %s:%s - Param: %s - %s' % (error.function,error.method,error.parameter,error.message))
				err = 'ES API: %s' % error.message
			else:
				err = error
		else:
			err = ERROR(message)
		self.showError(message,err,extra)
	
	def showError(self,l1,l2='',l3=''):
		xbmcgui.Dialog().ok(__lang__(32040),l1,l2,l3)
		
	def cleanCache(self):
		root = self.CACHE_PATH
		expiration = 2592000
		day = 86400
		now = time.time()
		for folder in glob.glob(root):
			LOG('Cleaning Cache: %s' % folder)
			for image in glob.glob(folder + '/*'):
				show = os.path.basename(image)
				# retrieves the stats for the current jpeg image file
				# the tuple element at index 8 is the last-modified-date
				stats = os.stat(image)
				lastAccessDate = stats[7]
				days_left = int(((lastAccessDate + expiration) - now) / day)
				if days_left < 0:
					LOG('File %s last accessed: %s - %s days past limit.' % (show, time.strftime("%m/%d/%y", time.localtime(lastAccessDate)),abs(days_left)))
				else:
					LOG('File %s last accessed: %s - %s days left.' % (show, time.strftime("%m/%d/%y", time.localtime(lastAccessDate)),days_left))
				# check if image-last-accessed-date is outdated
				if now - lastAccessDate > expiration:
					try:
						LOG('Removing: %s' % show)
						os.remove(image)
					except OSError:
						LOG('Could not remove: %s' % show)
						
	def getFocusedItem(self,list_id):
		lc = self.window.getControl(list_id)
		return lc.getSelectedItem()
	
	def startProgress(self,caption=__lang__(32030),text=''):
		self._pdialog = xbmcgui.DialogProgress()
		self._pdialog.create(caption)
		self._pdialog.update(0,text)
		
	def updateProgress(self,pct=0,line1='',line2='',line3='',total=0):
		if total: pct = int((pct*100.0)/total)
		self._pdialog.update(pct,line1,line2,line3)
		
	def endProgress(self):
		if not self._pdialog: return
		self._pdialog.close()
		self._pdialog = None
		
	def notebookSelected(self):
		item = self.getFocusedItem(120)
		if item.getProperty('stack') == 'stack' and not item.getProperty('linked'):
			stack = item.getLabel()
			self.showNotes(search='stack:"%s"' % stack)
			self.setNotebookTitleDisplay(stack)
			return
		elif not item.getProperty('stack') == 'stack' and item.getProperty('linked'):
			name = item.getLabel()
			guid = item.getProperty('guid')
			shardId = item.getProperty('shardid')
			shareKey = item.getProperty('sharekey') or None
			notestoreurl = item.getProperty('notestoreurl')
			username = item.getProperty('username')
			publicUri = item.getProperty('publicuri')
			self.showNotes(guid,shardid=shardId,sharekey=shareKey,notestoreurl=notestoreurl,username=username,publicuri=publicUri)
			self.setNotebookTitleDisplay(name)
			return
		guid = item.getProperty('guid')
		self.setNotebookTitleDisplay(item.getProperty('name'))
		LOG('Showing notes for notebook with guid: ' + guid)
		self.showNotes(guid)
		
	def setNotebookTitleDisplay(self,name=''):
		self.window.getControl(130).setLabel(__lang__(3021) + '   [COLOR FF888888]' + name + '[/COLOR]')
		
	def noteSelected(self):
		item = self.getFocusedItem(125)
		guid = item.getProperty('guid')
		nbguid = item.getProperty('nbguid')
		note = self.esession.getNoteByGuid(guid,nbguid)
		self.viewNote(note)
	
	def getUserToken(self,user=None,force=False):
		if not user:
			if __addon__.getSetting('choose_user') == 'true':
				user = self.chooseUser()
		if not user:
			user = __addon__.getSetting('last_user')
		if not user:
			user = self.chooseUser(0)
		if not user: return None,None
		token = __addon__.getSetting('token_%s' % user)
		if not token:
			if not self.addUser(user,token): return None,None
		__addon__.setSetting('last_user',user)
		__addon__.setSetting('token_%s' % user,token)
		return user,token
		
	def getUserList(self):
		return getUserList()
	
	def addUser(self,user,token):
		userlist = self.getUserList()
		if user in userlist: return True
		if not self.usersCount(): userlist = []
		userlist.append(user)
		__addon__.setSetting('user_list','@,@'.join(userlist))
		return True
		
	def removeUser(self):
		user = self.chooseUser(just_users=True)
		if not user: return
		userlist = __addon__.getSetting('user_list').split('@,@')
		idx = userlist.index(user)
		if idx < 0: return
		userlist.pop(idx)
		__addon__.setSetting('user_list','@,@'.join(userlist))
		__addon__.setSetting('login_pass_%s' % user,'')
		last_user = __addon__.getSetting('last_user')
		if last_user == user: __addon__.setSetting('last_user','')
	
	def chooseUser(self,index=None,just_users=False):
		#if not self.usersCount(): return None
		users = self.getUserList()
		add = remove = -2
		if not just_users:
			add = len(users)
			users.append(__lang__(32014))
			if self.getUserList():
				remove = len(users)
				users.append(__lang__(32111))
		
		if index != None:
			if not self.getUserList(): return None
			return users[index]
		idx = xbmcgui.Dialog().select(__lang__(32019),users)
		if idx < 0:
			if not self.usersCount():
				self.window.close()
			return None
		elif idx == add:
			#self.getUserToken(force=True)
			return self.startSession(new=True)
		elif idx == remove:
			self.removeUser()
			if not self.usersCount():
				self.chooseUser() #This is a loop
				return None
		else:
			return users[idx]
	
	def changeUser(self,user=None):
		if not user: user = self.chooseUser()
		if not user: return
		if not self.startSession(user): return False
		__addon__.setSetting('last_user',user)
		self.clearNotes()
		self.showNotebooks()
		self.window.initFocus()
		return True
		
	def usersCount(self):
		ulist = self.getUserList()
		return len(ulist)
			
	def doContextMenu(self):
		options = [__lang__(32011),__lang__(32012),__lang__(32013),__lang__(32016),__lang__(32014),__lang__(32015)]
		optionIDs = ['xbmclog','screenshot','write','notebook','adduser','changeuser']

		options.append('')
		optionIDs.append('')
		focus = self.window.getFocusId()
		if focus == 125 or focus == 131:
			options.append(__lang__(32026))
			optionIDs.append('movenote')
			options.append(__lang__(32017))
			optionIDs.append('deletenote')
			item = self.getFocusedItem(125)
			if item.getProperty('haslocation') == 'yes':
				options.append(__lang__(32037))
				optionIDs.append('showmap')
		elif focus == 120:
			#Disabled until we get permissions for the api key
			item = self.getFocusedItem(120)
			linked = item.getProperty('linked')
			if not linked:
				options.append(__lang__(32018))
				optionIDs.append('deletenotebook')
			if item.getProperty('published') == 'notpublished':
				if not linked: options.append(__lang__(32035))
			else:
				if item.getProperty('publicuri') or item.getProperty('published'):
					optionIDs.append('viewurl')
					options.append(__lang__(32112))
				if not linked: options.append(__lang__(32036))
			if not linked:
				optionIDs.append('publishnotebook')
				options.append(__lang__(32038))
				optionIDs.append('addtostack')
			
		idx = xbmcgui.Dialog().select(__lang__(32010),options)
		if idx < 0:
			return
		else:
			option = optionIDs[idx]
		try:
			err_msg = __lang__(32046)
			if option == 'xbmclog':
				self.createXBMCLogNote()
			elif option == 'screenshot':
				self.createScreenshotNote()
			elif option == 'write':
				self.createWriteNote()
			elif option == 'notebook':
				err_msg = __lang__(32049)
				self.createNotebook()
			elif option == 'adduser':
				err_msg = __lang__(32047)
				self.startSession(new=True)
			elif option == 'changeuser':
				err_msg = __lang__(32048)
				self.changeUser()
			elif option == 'movenote':
				err_msg = __lang__(32053)
				self.moveNote()
			elif option == 'deletenote':
				err_msg = __lang__(32051)
				self.deleteNote()
			elif option == 'deletenotebook':
				err_msg = __lang__(32052)
				self.deleteNotebook()
			elif option == 'publishnotebook':
				err_msg = __lang__(32056)
				self.toggleNotebookPublished()
			elif option == 'viewurl':
				err_msg = __lang__(32059)
				self.viewPublishedNotebookURL()
			elif option == 'showmap':
				err_msg = __lang__(32057)
				self.showMap()
			elif option == 'addtostack':
				err_msg = __lang__(32058)
				self.addNotebookToStack()
		except EvernoteSessionError as e:
			self.error(e,message=err_msg)
		except:
			self.error(message=err_msg)
	
	def showMap(self):
		item = self.getFocusedItem(125)
		guid = item.getProperty('guid')
		nbguid = item.getProperty('nbguid')
		note = self.esession.getNoteByGuid(guid,nbguid)
		lat = note.attributes.latitude
		lon = note.attributes.longitude
		self.maps.doMap({'lat':lat,'lon':lon})#,{'lat':lat,'lon':lon,'zoom':'19'})
		
		
	def getXBMCLog(self):
		log_file = xbmc.translatePath('special://temp/xbmc.log')
		if not os.path.exists(log_file): log_file = xbmc.translatePath('special://home/xbmc.log')
		if not os.path.exists(log_file): xbmcgui.Dialog().ok('Error',"Could not find log file.")
		lf = open(log_file,'r')
		data = lf.read()
		lf.close()
		return data
	
	def createXBMCLogNote(self):
		nb = None
		if __addon__.getSetting('choose_notebook') == 'true':
			nb = self.chooseNotebook()
			if nb == None: return
		note = self.esession.createNote(self.getXBMCLog(),title=__lang__(32063),notebook=nb)
		self.updateNotebookCounts()
		self.showNotes()
		self.notify(__lang__(32101) % note.title)
		
	def createScreenshotNote(self):
		nb = None
		if __addon__.getSetting('choose_notebook') == 'true':
			nb = self.chooseNotebook()
			if nb == None: return
		fname = xbmcgui.Dialog().browse(1, __lang__(32022), 'files','.png|.jpg|.gif',True,False,xbmc.translatePath('special://screenshots/'))
		if not fname: return
		note = self.esession.createNote(title=__lang__(32060) % os.path.basename(fname),image_files=[fname],notebook=nb)
		self.updateNotebookCounts()
		self.showNotes()
		self.notify(__lang__(32102) % note.title)
	
	def createWriteNote(self):
		nb = None
		if __addon__.getSetting('choose_notebook') == 'true':
			nb = self.chooseNotebook()
			if nb == None: return
		title = doKeyboard(__lang__(32020))
		if title == None: return
		text = doKeyboard(__lang__(32021))
		if text == None: return
		if not text: return
		note = self.esession.createNote(text,title=title,notebook=nb)
		self.updateNotebookCounts()
		self.showNotes()
		self.notify(__lang__(32103) % note.title)
	
	def createNotebook(self):
		title = doKeyboard(__lang__(32023))
		if not title: return
		if self.esession.notebooks:
			for n in self.esession.notebooks:
				if n.name == title:
					self.showError(__lang__(32050))
					return
		nb = self.esession.createNotebook(title)
		self.showNotebooks(force=True)
		self.notify(__lang__(32104) % nb.name)
		
	def getStackList(self):
		stacks = []
		for nb in self.esession.getNotebooks():
			if nb.stack and not nb.stack in stacks: stacks.append(nb.stack)
		return stacks
	
	def addNotebookToStack(self):
		item = self.getFocusedItem(120)
		guid = item.getProperty('guid')
		nb = self.esession.getNotebookByGuid(guid)
		if not nb:
			LOG('addNotebookToStack() - No notebook')
			return
		stacks = self.getStackList()
		stacks.append(__lang__(32071))
		idx = xbmcgui.Dialog().select(__lang__(32072),stacks)
		if idx < 0:
			return
		elif idx == len(stacks) - 1:
			stack = doKeyboard(__lang__(32070))
		else:
			stack = stacks[idx]
		if not stack: return
		
		self.esession.addNotebookToStack(nb, stack)
		self.showNotebooks(force=True)
		self.notify(__lang__(32110) % (nb.name,stack))
		
	def deleteNote(self):
		item = self.getFocusedItem(125)
		guid = item.getProperty('guid')
		title = item.getLabel()
		if xbmcgui.Dialog().yesno(__lang__(32024), __lang__(32025), title):
			self.esession.deleteNote(guid)
			self.updateNotebookCounts()
			self.showNotes()
			self.notify(__lang__(32105) % title)
			
	def cleanURI(self,uri):
		return re.sub('[^\w_-]','',uri).lower()
		
	def viewPublishedNotebookURL(self):
		item = self.getFocusedItem(120)
		guid = item.getProperty('guid')
		notebook = self.esession.getNotebookByGuid(guid)
		if hasattr(notebook, 'publishing') and notebook.publishing:
			url = 'http://' + self.esession.evernoteHost + '/pub/' + self.esession.user.username + '/' + str(notebook.publishing.uri)
		elif item.getProperty('publicuri'):
			url = 'http://' + self.esession.evernoteHost + '/pub/' + str(item.getProperty('username')) + '/' + str(item.getProperty('publicuri'))
		else:
			return
		
		cf= lambda s,p: [ s[i:i+p] for i in range(0,len(s),p) ]
		parts = cf(url,50)[:2]
		if not self.clipboard:
			xbmcgui.Dialog().ok('URL',*parts)
			return
		parts.append('Save to clipboard?')
		yes = xbmcgui.Dialog().yesno('URL',*parts)
		if yes:
			share = self.clipboard.getShare('script.evernote','link')
			share.page = url
			self.clipboard.setClipboard(share)
				
		
	def toggleNotebookPublished(self):
		item = self.getFocusedItem(120)
		guid = item.getProperty('guid')
		published = item.getProperty('published')
		name = item.getProperty('name')
		if published == 'published':
			self.esession.publishNotebook(guid,False)
		else:
			uri=self.cleanURI(name)
			desc=''
			nb = self.esession.getNotebookByGuid(guid)
			if nb.publishing:
				uri = nb.publishing.uri or uri
				desc = nb.publishing.publicDescription or desc
			url = 'http://' + self.esession.evernoteHost + '/pub/' + self.esession.user.username + '/'
			uri = doKeyboard(__lang__(32064) + url,uri)
			if uri == None: return
			uri = self.cleanURI(uri)
			desc = doKeyboard(__lang__(32065),desc)
			if desc == None: return
			if not xbmcgui.Dialog().yesno('Confirm',abbreviateURL(url + uri), '"%s"' % desc,__lang__(32068)): return
			try:
				self.esession.publishNotebook(guid,True,desc,uri)
			except EvernoteSessionError as e:
				if e.parameter == 'Publishing.uri':
					if e.message == 'DATA_CONFLICT':
						self.showError(__lang__(32066))
					elif e.message == 'BAD_DATA_FORMAT' or e.message == 'DATA_REQUIRED':
						self.showError(__lang__(32067))
					else:
						raise
					return
				else:
					raise
			
		self.showNotebooks(force=True)
		if published == 'published':
			self.notify(__lang__(32109) % name)
		else:
			self.notify(__lang__(32108) % name)
		
	def deleteNotebook(self):
		item = self.getFocusedItem(120)
		guid = item.getProperty('guid')
		name = item.getProperty('name')
		if xbmcgui.Dialog().yesno(__lang__(32024), __lang__(32025), name):
			self.esession.deleteNotebook(guid)
			self.showNotebooks(True)
			self.notify(__lang__(32106) % name)
			#TODO: Perhaps clear the note list, when this is working we can check to see if we can still access the notes
		
	def moveNote(self):
		item = self.getFocusedItem(125)
		guid = item.getProperty('guid')
		title = item.getLabel()

		nbguid = self.chooseNotebook()
		if not nbguid: return
		
		self.esession.moveNote(guid, nbguid)
		self.updateNotebookCounts()
		self.showNotes()
		self.notify(__lang__(32107) % title)
		
	def chooseNotebook(self):
		nblist = []
		guids = []
		
		for nb in self.esession.getNotebooks():
			nblist.append(nb.name)
			guids.append(nb.guid)
			
		idx = xbmcgui.Dialog().select(__lang__(32027),nblist)
		if idx < 0:
			return None
		
		return guids[idx]
		
	def showNotebooks(self,force=False):
		self.startProgress(text=__lang__(32031))
		try:
			notebooks = self.esession.getNotebooks(ignoreCache=force)
			stacks = {'@@-main-@@':[]}
			for nb in notebooks:
				stack = nb.stack
				if stack:
					if stack in stacks:
						stacks[stack].append(nb)
					else:
						stacks[stack] = [nb]
				else:
					stacks['@@-main-@@'].append(nb)
			ncc = self.esession.getNotebookCounts()
			stack_names = stacks.keys()
			midx = stack_names.index('@@-main-@@')
			stack_names = stack_names[midx:] + stack_names[:midx]
			items = []
			item = xbmcgui.ListItem(label=__lang__(32069))
			all_item = item
			item.setProperty('guid','all')
			item.setProperty('published','notpublished')
			item.setProperty('name',__lang__(32069))
			items.append(item)
			total = 0
			for stack in stack_names:
				if stack == '@@-main-@@':
					stacked = ''
				else:
					stacked = 'stacked'
					item = xbmcgui.ListItem(label=stack)
					item.setProperty('stack','stack')
					items.append(item)
				for nb in stacks[stack]:
					count = ncc.notebookCounts and ncc.notebookCounts.get(nb.guid) or 0
					ct_disp = ''
					if count:
						total += count
						ct_disp = ' (%s)' % count
					item = xbmcgui.ListItem()
					item.setThumbnailImage('')
					item.setLabel(nb.name + ct_disp)
					item.setProperty('stack',stacked)
					item.setProperty('guid',nb.guid)
					item.setProperty('name',nb.name)
					pub = nb.published and 'published' or 'notpublished'
					item.setProperty('published',pub)
					items.append(item)
			items = self.showLinkedNotebooks(items)
			all_item.setLabel(__lang__(32069) + ' (%s)' % total)
			wlist = self.window.getControl(120)
			wlist.reset()
			wlist.addItems(items)
		except EvernoteSessionError as e:
			self.error(e,message=__lang__(32043))
		except:
			self.error(message=__lang__(32043))
		finally:
			self.endProgress()
		
	def showLinkedNotebooks(self,items):
		item = xbmcgui.ListItem(label=__lang__(32113))
		item.setProperty('stack','stack')
		item.setProperty('linked','linked')
		items.append(item)
		notebooks = self.esession.getNotebooks(linked=True)
		for nb in notebooks:
			item = xbmcgui.ListItem()
			item.setThumbnailImage('')
			item.setLabel(nb.shareName+' ('+nb.username+')')
			item.setProperty('stack','stacked')
			item.setProperty('guid',nb.guid)
			item.setProperty('name',nb.shareName)
			item.setProperty('username',nb.username)
			#print nb.__dict__
			item.setProperty('shardid',nb.shardId)
			item.setProperty('notestoreurl',nb.noteStoreUrl)
			if nb.uri: item.setProperty('publicuri',nb.uri)
			pub = nb.uri and 'published' or 'notpublished'
			item.setProperty('published',pub)
			if nb.shareKey: item.setProperty('sharekey',nb.shareKey)
			item.setProperty('linked','linked')
			items.append(item)
		return items
	
	def updateNotebookCounts(self):
		ncc = self.esession.getNotebookCounts()
		wlist = self.window.getControl(120)
		for idx in range(0,wlist.size()):
			item = wlist.getListItem(idx)
			guid = item.getProperty('guid')
			name = item.getProperty('name')
			count = ncc.notebookCounts.get(guid)
			ct_disp = ''
			if count: ct_disp = ' (%s)' % count
			item.setLabel(name + ct_disp)
		
	def clearNotes(self):
		self.setNotebookTitleDisplay()
		self.window.getControl(125).reset()
		self.currentNoteFilter = None
		
	def showNotes(self,nbguid=None,search=None,shardid=None,sharekey=None,notestoreurl=None,username=None,publicuri=None):
		if not nbguid and not search and self.currentNoteFilter:
			nbguid,search = self.currentNoteFilter
		if not nbguid and not search: return
		self.currentNoteFilter = (nbguid,search)
		
		self.startProgress(text=__lang__(32032))
		try:
			if shardid:
				noteList, nbguid = self.esession.getLinkedNoteList(nbguid, shardid, sharekey, notestoreurl,username,publicuri)
			else:
				noteList = self.esession.getNoteList(nbguid,search)
			items = []
			ct=0
			tot= len(noteList.notes)
			for note in noteList.notes: 
				path = ''
				self.updateProgress(ct,__lang__(32032),note.title,'',total=tot)
				if note.resources:
					#print 'test'
					#print note.resources
					for res in note.resources:
						#print res.mime
						if 'image/' in res.mime:
							self.updateProgress(ct,__lang__(32032),note.title,res.attributes.fileName or '',total=tot)
							ext = '.' + res.mime.split('/',1)[1]
							filename = note.guid + ext
							path = self.isCached(filename)
							if not path:
								data = self.esession.getResourceData(res.guid,nbguid)
								path = self.cacheImage(filename,data)
				item = xbmcgui.ListItem()
				item.setThumbnailImage(path)
				item.setLabel(note.title)
				item.setProperty('guid',note.guid)
				item.setProperty('nbguid',nbguid)
				item.setProperty('content','')
				if note.attributes.latitude: item.setProperty('haslocation','yes')
				items.append(item)
				ct+=1
			items.reverse()
			wlist = self.window.getControl(125)
			wlist.reset()
			wlist.addItems(items)
		except EvernoteSessionError as e:
			self.error(e,message=__lang__(32044))
		except:
			self.error(message=__lang__(32044))
		finally:
			self.endProgress()
		
	def cacheImage(self,filename,data):
		path = os.path.join(self.CACHE_PATH,filename)
		ifile = open(path,'wb')
		ifile.write(data)
		ifile.close()
		return path
		
	def isCached(self,filename):
		path = os.path.join(self.CACHE_PATH,filename)
		if os.path.exists(path):
			st = os.stat(path)
			mtime = st[8] #modification time
			#modify the file timestamp
			try:
				os.utime(path,(int(time.time()),mtime))
			except:
				pass
			return path
		return ''
	
	def viewNote(self,note):
		self.startProgress(text=__lang__(32033))
		try:
			contents = self.prepareContentForWebviewer(note.content)
			noteFile = os.path.join(self.CACHE_PATH,'notecontents.html')
			nf = open(noteFile,'w')
			nf.write(contents)
			nf.close()
			if note.resources:
				ct=0
				tot=len(note.resources)
				self.updateProgress(0,__lang__(32034))
				for res in note.resources:
					if 'image' in res.mime:
						self.updateProgress(ct,__lang__(32034),res.attributes.fileName or '',total=tot)
						#ext = '.' + res.mime.split('/',1)[1]
						filename = binascii.hexlify(res.data.bodyHash)
						path = self.isCached(filename)
						if not path:
							data = self.esession.getResourceData(res.guid,note.notebookGuid)
							path = self.cacheImage(filename,data)
					ct+=1		
			url = 'file://%s' % noteFile
		except EvernoteSessionError as e:
			self.error(e,message=__lang__(32045))
		except:
			self.error(message=__lang__(32045))
		finally:
			self.endProgress()
			
		from webviewer import webviewer #@UnresolvedImport
		url,html = webviewer.getWebResult(url) #@UnusedVariable
		
	def prepareContentForWebviewer(self,contents):
		contents = re.sub('<!DOCTYPE.*?>','',contents)
		contents = re.sub(r'<en-media[^>]*type="image/[^>]*hash="([^"]+)"[^>]*/?>(?:</en-media>)?',r'<img src="%s/\1" />' % self.CACHE_PATH,contents)
		contents = re.sub(r'<en-media[^>]*hash="([^"]+)"[^>]*type="image/[^>]*/?>(?:</en-media>)?',r'<img src="%s/\1" />' % self.CACHE_PATH,contents)
		return contents.replace('<en-note>','<body>').replace('</en-note>','</body>')
	
	def notify(self,message,header='X-NOTE'):
		mtime=2000
		image=''
		xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % (header,message,mtime,image))
		
	def findNoteItem(self,guid):
		wlist = self.window.getControl(125)
		for idx in range(0,wlist.size()):
			item = wlist.getListItem(idx)
			iguid = item.getProperty('guid')
			if iguid == guid: return item
		return None
	
	def noteChanged(self):
		item = self.getFocusedItem(125)
		content = item.getProperty('content')
		if content:
			#LOG('Note Changed - Cached Content')
			return
#		else:
#			LOG('Note Changed')
		t = self.window.getThread(self.getNote,finishedCallback=self.updateNote,wait=True)
		t.setArgs(callback=t.progressCallback,donecallback=t.finishedCallback)
		t.start()
		
	def getNote(self,callback=None,donecallback=None):
		item = self.getFocusedItem(125)
		if not item: return
		guid = item.getProperty('guid')
		nbguid = item.getProperty('nbguid')
		if self.updatingNote == guid: return
		self.updatingNote = guid
		time.sleep(0.5)
		if self.updatingNote and not self.updatingNote == guid:
			#LOG('getNote() interrupted by another call')
			return
		self.updatingNote = None
		#LOG('Updating Note: %s' % guid)
		note = None
		try:
			note = self.esession.getNoteByGuid(guid,nbguid)
		except httplib.ResponseNotReady:
			LOG('getNote() - Failed: ResponseNotReady - Retrying...')
		except AttributeError:
			LOG('getNote() - Failed: HTTP Error - Retrying...')
		if not note:
			time.sleep(0.5)
			try:
				note = self.esession.getNoteByGuid(guid,nbguid)
			except httplib.ResponseNotReady:
				LOG('getNote() - Failed: ResponseNotReady - Giving Up')
				return
			except AttributeError:
				LOG('getNote() - Failed: HTTP Error - Giving Up')
				return
		donecallback(note)
	
	def updateNote(self,note):
		item = self.getFocusedItem(125)
		guid = item.getProperty('guid')
		if not note.guid == guid:
			#LOG('updateNote(): Wrong Note - finding correct item...')
			item = self.findNoteItem(note.guid)
			if not item:
				LOG('updateNote(): item not found - abort')
				return
		#LOG('Updated Changed Note: %s' % guid)
		content = self.prepareContentForWebviewer(note.content)
		content, title = self.htmlconverter.htmlToDisplay(content) #@UnusedVariable
		item.setProperty('content',content or " ")
		
######################################################################################
# Base Window Classes
######################################################################################
class StoppableThread(threading.Thread):
	def __init__(self,group=None, target=None, name=None, args=(), kwargs={}):
		self._stop = threading.Event()
		threading.Thread.__init__(self,group=group, target=target, name=name, args=args, kwargs=kwargs)
		
	def stop(self):
		self._stop.set()
		
	def stopped(self):
		return self._stop.isSet()
		
class StoppableCallbackThread(StoppableThread):
	def __init__(self,target=None, name=None):
		self._target = target
		self._stop = threading.Event()
		self._finishedHelper = None
		self._finishedCallback = None
		self._progressHelper = None
		self._progressCallback = None
		self.wait = None
		StoppableThread.__init__(self,name=name)
		
	def setArgs(self,*args,**kwargs):
		self.args = args
		self.kwargs = kwargs
		
	def run(self):
		if self.wait:
			self.wait.join(0.5)
			time.sleep(0.5)
		self._target(*self.args,**self.kwargs)
		
	def setFinishedCallback(self,helper,callback):
		self._finishedHelper = helper
		self._finishedCallback = callback
	
	def setProgressCallback(self,helper,callback):
		self._progressHelper = helper
		self._progressCallback = callback
		
	def stop(self):
		self._stop.set()
		
	def stopped(self):
		return self._stop.isSet()
		
	def progressCallback(self,*args,**kwargs):
		if self.stopped(): return False
		if self._progressCallback: self._progressHelper(self._progressCallback,*args,**kwargs)
		return True
		
	def finishedCallback(self,*args,**kwargs):
		if self.stopped(): return False
		if self._finishedCallback: self._finishedHelper(self._finishedCallback,*args,**kwargs)
		return True

class ThreadWindow:
	def __init__(self):
		self._currentThread = None
		self._stopControl = None
		self._startCommand = None
		self._progressCommand = None
		self._endCommand = None
		self._isMain = False
		self._resetFunction()
			
	def setAsMain(self):
		self._isMain = True
		
	def setStopControl(self,control):
		self._stopControl = control
		control.setVisible(False)
		
	def setProgressCommands(self,start=None,progress=None,end=None):
		self._startCommand = start
		self._progressCommand = progress
		self._endCommand = end
		
	def onAction(self,action):
		if action == ACTION_RUN_IN_MAIN:
			if self._function:
				self._function(*self._functionArgs,**self._functionKwargs)
				self._resetFunction()
				return True
		elif action == ACTION_PREVIOUS_MENU:
			if self._currentThread and self._currentThread.isAlive():
				self._currentThread.stop()
				if self._endCommand: self._endCommand()
				if self._stopControl: self._stopControl.setVisible(False)
			if self._isMain and len(threading.enumerate()) > 1:
				d = xbmcgui.DialogProgress()
				d.create(__lang__(32220),__lang__(32221))
				d.update(0)
				self.stopThreads()
				if d.iscanceled():
					d.close()
					return True
				d.close()
			return False
		return False
	
	def stopThreads(self):
		for t in threading.enumerate():
			if isinstance(t,StoppableThread): t.stop()
		for t in threading.enumerate():
			if t != threading.currentThread(): t.join()
			
	def _resetFunction(self):
		self._function = None
		self._functionArgs = []
		self._functionKwargs = {}
		
	def runInMain(self,function,*args,**kwargs):
		self._function = function
		self._functionArgs = args
		self._functionKwargs = kwargs
		xbmc.executebuiltin('Action(codecinfo)')
		
	def endInMain(self,function,*args,**kwargs):
		if self._endCommand: self._endCommand()
		if self._stopControl: self._stopControl.setVisible(False)
		self.runInMain(function,*args,**kwargs)
		
	def getThread(self,function,finishedCallback=None,progressCallback=None,wait=False):
		if self._currentThread and not wait: self._currentThread.stop()
		if not progressCallback: progressCallback = self._progressCommand
		t = StoppableCallbackThread(target=function)
		t.setFinishedCallback(self.endInMain,finishedCallback)
		t.setProgressCallback(self.runInMain,progressCallback)
		if wait: t.wait = self._currentThread
		self._currentThread = t
		if self._stopControl: self._stopControl.setVisible(True)
		if self._startCommand: self._startCommand()
		return t
		
	def stopThread(self):
		if self._stopControl: self._stopControl.setVisible(False)
		if self._currentThread:
			self._currentThread.stop()
			self._currentThread = None
			if self._endCommand: self._endCommand()
			
class BaseWindow(xbmcgui.WindowXML,ThreadWindow):
	def __init__( self, *args, **kwargs):
		xbmcgui.WindowXML.__init__( self)
		ThreadWindow.__init__(self)
		
	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onAction(self,action):
		if action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		if ThreadWindow.onAction(self,action): return True
		if action == ACTION_PREVIOUS_MENU:
			try:
				self.onClose()
			except:
				ERROR('BaseWindow - doClose() Error')
				
			self.close()
			return True
		else:
			return False
		
	def onClose(self):
		pass
		
class MainWindow(BaseWindow):
	def __init__( self, *args, **kwargs):
		self.session = None
		BaseWindow.__init__( self, *args, **kwargs )
		self.lastFocus = 0
		self.lastItem = -1
		
	def onInit(self):
		if not self.session:
			self.session = XNoteSession(self)
			self.initFocus()
		
	def initFocus(self):
		self.setFocusId(120)
		
	def onClick( self, controlID ):
		if controlID == 120:
			self.session.notebookSelected()
		if controlID == 125 or controlID == 131:
			self.session.noteSelected()
			
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.session.doContextMenu()
		if BaseWindow.onAction(self, action): return
		focus = self.getFocusId()
		if self.lastFocus != focus:
			if focus == 125:
				self.session.noteChanged()
				
	def onClose(self):
		if not self.session: return
		self.session.cleanCache()

def registerAsShareTarget():
	try:
		import ShareSocial #@UnresolvedImport
	except:
		LOG('Could not import ShareSocial')
		return
	
	target = ShareSocial.getShareTarget()
	target.addonID = 'script.evernote'
	target.name = 'Evernote'
	target.importPath = 'lib/script_evernote_share'
	target.iconPath = os.path.join(__addon__.getAddonInfo('path'),'evernote.png')
	target.shareTypes = ['image','imagefile','video','text','html']
	ShareSocial.registerShareTarget(target)
	LOG('Registered as share target with ShareSocial')
		
def openWindow(window_name,session=None,**kwargs):
	windowFile = 'script-evernote-%s.xml' % window_name
	w = MainWindow(windowFile , xbmc.translatePath(__addon__.getAddonInfo('path')), THEME,session=session)
	w.doModal()			
	del w
	
if __name__ == '__main__':
	if len(sys.argv) > 1:
		if sys.argv[1] == 'crypto_help':
			xbmcgui.Dialog().ok('Crypto Help','Passwords are encrypted using user data as the key.','Optional: include a keyfile whose contents must not','change and must be readable by XBMC.')
		elif sys.argv[1] == 'auth':
			session = XNoteSession(new=True)
			if session.esession.authToken: xbmcgui.Dialog().ok(__lang__(32505),__lang__(32506))
	else:
		registerAsShareTarget()
		openWindow('main')

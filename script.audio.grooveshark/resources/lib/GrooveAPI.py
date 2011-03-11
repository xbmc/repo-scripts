import urllib, urllib2, unicodedata, re, os, traceback, sys, pickle, socket, string, time, random, sha, md5
from operator import itemgetter, attrgetter

#sys.path.append('/home/solver/.xbmc/addons/script.module.simplejson/lib')
import simplejson as json

import traceback
from gw import Request as Request
from gw import JsonRPC as gwAPI

CLIENT_NAME = "gslite" #htmlshark #jsqueue
CLIENT_VERSION = "20101012.37" #"20100831.25"

RANDOM_CHARS = "1234567890abcdef"
VALIDITY_SESSION = 172800 #2 days
VALIDITY_TOKEN = 1000 # ca. 16 min.

class LoginTokensExceededError(Exception):
	def __init__(self):
		self.value = 'You have created to many tokens. Only 12 are allowed'
	def __str__(self):
		return repr(self.value)
		
class LoginUnknownError(Exception):
	def __init__(self):
		self.value = 'Unable to get a new session ID. Wait a few minutes and try again'
	def __str__(self):
		return repr(self.value)

class SessionIDTryAgainError(Exception):
	def __init__(self):
		self.value = 'Unable to get a new session ID. Wait a few minutes and try again'
	def __str__(self):
		return repr(self.value)

class AuthRequest(Request):
	def __init__(self, api, parameters, method, type="default", clientVersion=None):
		if clientVersion != None:
			if float(clientVersion) < float(CLIENT_VERSION):
				clientVersion = CLIENT_VERSION
		if clientVersion == None:
			clientVersion = CLIENT_VERSION
		postData = {
			"header": {
				"client": CLIENT_NAME,
				"clientRevision": clientVersion,
				"uuid": api._uuid,
				"session": api._session},
				"country": {"IPR":"1021", "ID":"223", "CC1":"0", "CC2":"0", "CC3":"0", "CC4":"2147483648"},
				"privacy": 1,
			"parameters": parameters,
			"method": method}
			
		headers = {
			"Content-Type": "application/json",
			"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.12) Gecko/20101026 Firefox/3.6.12 (.NET CLR 3.5.30729)",			
			"Referer": "http://listen.grooveshark.com/main.swf?cowbell=fe87233106a6cef919a1294fb2c3c05f"
			}
		url = 'https://cowbell.grooveshark.com/more.php?' + method
		postData["header"]["token"] = api._generateToken(method)
		postData = json.dumps(postData)
		self._request = urllib2.Request(url, postData, headers)
		

class GrooveAPI(gwAPI):
	def __init__(self, cwd = None, enableDebug = False, clientUuid = None, clientVersion = None):
#		import simplejson
#		self.simplejson = simplejson
		sys.path.append(os.path.join(cwd,'uuid'))
		import uuid
		self.clientVersion = clientVersion
		#timeout = 40
		#socket.setdefaulttimeout(timeout) # Disabled for now. A bug in SSL in python 2.4 on windows makes the connection throw a read error
		self.enableDebug = enableDebug
		self.loggedIn = 0
		self.radioEnabled = 0
		self.userId = 0
		self.seedArtists = []
		self.frowns = []
		self.songIDsAlreadySeen = []
		self.recentArtists = []
		self.rootDir = cwd
		self.dataDir = 'addon_data'
		self.confDir = cwd
		#self.startSession()
		self._isAuthenticated = False
		self._authenticatedUserId = -1
		self._authenticatedUser = ''
		self._username = ''
		self._password = ''

	def authenticate(self):
		if self._isAuthenticated == True:
			if self._authenticatedUser == self._username:
				self.debug('Already logged in')
				return True
			else:
				self.generateInstance()
		if (self._username != '') and (self._password != ''):
			parameters = {
				"username": self._username,
				"password": self._password,
				"savePassword": 0,
				}
			response = AuthRequest(self, parameters, "authenticateUser").send()
			try:
				res = response['result']
				if res['userID'] > 0: 
					self._authenticatedUserId= res['userID']
					self._authenticatedUser = self._username
					self._isAuthenticated = True
				else:
					self.debug('Failed to log in (else)')
					self._isAuthenticated = False
					self._authenticatedUserId = -1
					self._authenticatedUser = ''
					print response
			except:
				self.debug('Failed to log in (exception)')
				print response
				self._isAuthenticated = False
				self._authenticatedUserId = -1
				self._authenticatedUser = ''
		else:
			self._isAuthenticated = False
			self._authenticatedUserId = -1
			self._authenticatedUser = ''
		
		self.saveInstance()
		return self._isAuthenticated

	def getUserId(self):
		return self._authenticatedUserId

	def isLoggedIn(self):
		return self._isAuthenticated

	def _generateToken(self, method):
		#Overload _generateToken()
		if (time.time() - self._lastTokenTime) >= VALIDITY_TOKEN:
			self.debug('_generateToken(): Token has expired')
			self._token = self._getToken()
			self._lastTokenTime = time.time()
			self.saveInstance()

		randomChars = ""
		while 6 > len(randomChars):
			randomChars = randomChars + random.choice(RANDOM_CHARS)

		token = sha.new(method + ":" + self._token + ":quitStealinMahShit:" + randomChars).hexdigest()
				#:quitBasinYoBidnessPlanOnBuildingALargeUserbaseViaCopyrightInfringment:

		if (time.time() - self._lastSessionTime) >= VALIDITY_SESSION:
			self.debug('_generateToken(): Session has expired')
			self.generateInstance()

		return randomChars + token

	def startSession(self, username = '', password = ''):
		#Overload startSession()
		self._username = username
		self._password = password
		self.debug('Starting session')
		s = self.loadInstance()
		self.debug('Saved instance: ' + str(s))
		try:
			self._session, self._lastSessionTime, self._token, self._lastTokenTime, self._uuid, self._authenticatedUser, self._isAuthenticated, self._authenticatedUserId = s
			if self._authenticatedUser != self._username:
				self.generateInstance()
			if (time.time() - self._lastSessionTime) >= VALIDITY_SESSION:
				self.debug('_startSession(): Session has expired')
				self.generateInstance()
		except:
			self.generateInstance()
			traceback.print_exc()

	def generateInstance(self):
		self.debug('Generating new instance')
		self._uuid = self._generateUUID()
		self._session = self._parseHomePage()
		self._token = self._getToken()
		self._lastTokenTime = time.time()
		self._lastSessionTime = time.time()
		self._isAuthenticated = False
		self._authenticatedUserId = -1
		self._authenticatedUser = ''
		self.saveInstance()

	def __del__(self):
		try:
			if self.loggedIn == 1:
				self.logout()
		except:
			pass

	def _enableDebug(self, v):
		if v == True:
			self.enableDebug == True
		if v == False:
			self.enableDebug == False
			
	def debug(self, msg):
		if self.enableDebug == True:
			print 'GrooveAPI: ' + str(msg)
			
	def setRemoveDuplicates(self, enable):
		if enable == True or enable == 'true' or enable == 'True':
			self.removeDuplicates = True
		else:
			self.removeDuplicates = False

	def loadInstance(self):
		path = os.path.join(self.confDir, 'instance.txt')
		try:
			f = open(path, 'rb')
			res = pickle.load(f)
			f.close()
		except:
			res = None
			pass	
		return res

	def saveInstance(self):
		print 'Saving instance'
		try:
			var = (self._session, self._lastSessionTime, self._token, self._lastTokenTime, self._uuid, self._authenticatedUser, self._isAuthenticated, self._authenticatedUserId)
			print 'Saving: ' + str(var)
			path = os.path.join(self.confDir, 'instance.txt')
			self.savePickle(path, var)
		except:
			print 'Exception in saveSession: ' + str(sys.exc_info()[0])		
			traceback.print_exc()

	def saveSettings(self):
		try:
			dir = os.path.join(self.rootDir, 'data')
			# Create the 'data' directory if it doesn't exist.
			if not os.path.exists(dir):
				os.mkdir(dir)
			path = os.path.join(dir, 'settings.txt')
			self.savePickle(path, self.settings)
		except:
			print 'Exception in saveSettings()'

	def loadPickle(self, path):
		try:
			f = open(path, 'rb')
			res = pickle.load(f)
			f.close()
		except:
			res = None
			pass				
		return res

	def savePickle(self, path, var):
		try:
			f = open(path, 'wb')
			pickle.dump(var, f, protocol=pickle.HIGHEST_PROTOCOL)
			f.close()
		except IOError, e:
			print 'There was an error while saving the settings pickle (%s)' % e
			pass
		except:
			print "An unknown error occured during save settings\n"
			pass

	def getStreamURL(self, songID):
		parameters = {
			"songID": songID,
			"prefetch": False,
			"mobile": False, 
			"country": {"IPR":"1021","ID":"223", "CC1":"0", "CC2":"0", "CC3":"0", "CC4":"2147483648"}
			}
		response = Request(self, parameters,"getStreamKeyFromSongIDEx").send()
		try:
			streamKey = response["result"]["streamKey"]
			streamServer = response["result"]["ip"]
			streamServerID = response["result"]["streamServerID"]
			postData = {"streamKey": streamKey}
			postData = urllib.urlencode(postData)
			url = "http://" + streamServer + "/stream.php?" + str(postData)
			return url
		except:
			traceback.print_exc()
			return ''
		
	def loggedInStatus(self):
		return self.loggedIn

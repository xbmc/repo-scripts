# -*- coding: utf-8 -*-
import requests
	
import xbmc, xbmcgui, xbmcaddon
import time, re, os, json

ADDON_ID = 'script.module.oauth.helper'

T = xbmcaddon.Addon(ADDON_ID).getLocalizedString

TOKEN_PATH = os.path.join(xbmc.translatePath(xbmcaddon.Addon(ADDON_ID).getAddonInfo('profile')),'tokens')
if not os.path.exists(TOKEN_PATH): os.makedirs(TOKEN_PATH)

URL = 'https://main-ruuk.rhcloud.com/auth/{0}'
USER_URL = 'auth.2ndmind.com'
REFERRER = 'https://main-ruuk.rhcloud.com/'
WAIT_SECONDS = 300
POLL_INTERVAL_SECONDS = 5

def LOG(msg):
	xbmc.log('{0}: {1}'.format(ADDON_ID,msg))

class GetTokenFail:
	def __init__(self,ftype,show_options=False):
		self.failType = ftype
		self.showOptions = show_options

	def __nonzero__(self):
		return False

def getToken(source,from_file=False):
	if from_file:
		return loadTokenFromFile()
		
	token = True
	while token:
		if token == True: token = _getToken(source)
		if token or token == None:
			return token
		if not token.showOptions:
			return None
		token = showFailOptions()

def showFailOptions():
	idx = xbmcgui.Dialog().select(T(32001),[T(32002),T(32003),T(32004)])
	if idx < 0 or idx == 2:
		return None
		
	if idx == 1:
		return loadTokenFromFile()
	else:
		return True

def loadTokenFromFile():	
	fpath = xbmcgui.Dialog().browseSingle(1,T(32005),'files')
	if not fpath: return None
	try:
		import xbmcvfs
		f = xbmcvfs.File(fpath)
		token = f.read().strip()
		if re.search('[\n\r\t]',token):
			xbmcgui.Dialog().ok(T(32006).upper(),'',T(32007))
			return None
	except:
		import traceback
		xbmc.log(traceback.format_exc())
		return None
	finally:
		f.close()
	xbmcgui.Dialog().ok(T(32008),'',T(32009))
	return token

def _getToken(source):
	session = requests.Session()
	session.headers.update({'referer': REFERRER})
	req = session.post(URL.format('getlookup'),data={'source':source})
	start = time.time()
	data = req.json()
	lookup = data['lookup']
	lookup_disp = lookup[0:4] + '-' + lookup[-4:]
	md5 = data['md5']
	prog = xbmcgui.DialogProgress()
	prog.create(
		T(32010),
		'{0} {1}'.format(T(32011),USER_URL),'{0} {1}'.format(T(32012),lookup_disp),T(32013)
	)
	prog.update(
		0,
		'{0} {1}'.format(T(32011),USER_URL),'{0} {1}'.format(T(32012),lookup_disp),T(32013)
	)
	secsLeft = 0
	try:
		while not prog.iscanceled() and not xbmc.abortRequested:
			req = session.post(URL.format('gettoken'),data={'lookup':lookup,'md5':md5})
			try:
				data = req.json()
				status = data.get('status') or 'error'
				xbmc.sleep(5000)
			except:
				if time.time() - start >= WAIT_SECONDS - 5:
					status = 'timeout'
				else:
					status = 'error'
				import traceback
				xbmc.log(traceback.format_exc())
			if status == 'error':
				prog.close()
				yesno = xbmcgui.Dialog().yesno(T(32006).upper(),T(32014),'',T(32015),T(32016),T(32001))
				return GetTokenFail('ERROR',yesno)
			elif status == 'waiting':
				secsLeft = data.get('secsLeft')
			elif status == 'timeout':
				prog.close()
				yesno = xbmcgui.Dialog().ok(T(32017),T(32018),'',T(32015),T(32016),T(32001))
				return GetTokenFail('TIMEOUT',yesno)
			elif status == 'ready':
				prog.close()
				xbmcgui.Dialog().ok(T(32008),'',T(32019))
				return data.get('token')

			for x in range(0,POLL_INTERVAL_SECONDS): #Update display every second, but only poll every POLL_INTERVAL_SECONDS
				if prog.iscanceled(): return
				pct, leftDisp, start = timeLeft(start,WAIT_SECONDS,secsLeft=secsLeft)
				if pct == None: break
				secsLeft = None
				prog.update(
					pct,
					'{0} {1}'.format(T(32011),USER_URL),'{0} {1}'.format(T(32012),lookup_disp),T(32013) + leftDisp
				)
				xbmc.sleep(1000)
			
	finally:
		prog.close()

def timeLeft(start,total,secsLeft=None):
	leftDisp = ''
	
	now = time.time()
	if secsLeft:
		left = secsLeft
		sofar = total - left
		start = now - sofar
	else:
		sofar = now - start
		left = total - sofar
		
	if left < 0 :
		return None, None, start
		
	pct = int((sofar/float(total))*100)
	mins = int(left/60)
	secs = int(left%60)
	mins = mins and ' {0} {1}'.format(mins,T(32020)) or ''
	secs = secs and ' {0} {1}'.format(secs,T(32021)) or ''
	if mins or secs: leftDisp = mins + secs + ' {0}'.format(T(32022))
	return pct, leftDisp, start

class AddonTokens(object):
	def __init__(self,addon_id=None):
		self.addonID = addon_id or xbmcaddon.Addon().getAddonInfo('id')
		self.usersFile = os.path.join(TOKEN_PATH,self.addonID)
		self.currentID = None
		self.loadUsers()
		
	def loadUsers(self):
		self.users = {}
		if os.path.exists(self.usersFile):
			try:
				with open(self.usersFile,'r') as f:
					self.users = json.load(f)
					return
			except ValueError:
				pass

	def saveUsers(self):
		jsonString = json.dumps(self.users)
		with open(self.usersFile,'w') as f:
			f.write(jsonString)

	def setUsers(self,users):
		self.users = users
		self.saveUsers()

	def setUser(self,ID):
		if self.currentID == ID: return
		self.currentID = ID

	def renameUser(self,ID,new):
		if not ID in self.users: return
		self.users[ID]['name'] = new
		self.saveUsers()

	def deleteUser(self,ID):
		if not ID in self.users: return
		del(self.users[ID])
		self.saveUsers()

	def setSetting(self,key,val):
		if not self.currentID in self.users: self.users[self.currentID] = {}
		self.users[self.currentID][key] = val
		self.saveUsers()

	def getSetting(self,key,default=None):
		if not self.currentID in self.users: return default
		if not key in self.users[self.currentID]: return default
		return self.users[self.currentID][key]
	
	def hasToken(self,ID):
		return bool(ID in self.users and self.users[ID].get('access_token'))

	@property
	def token(self):
		return self.getSetting('access_token','')
		
	@property
	def refreshToken(self):
		return self.getSetting('refresh_token','')
	
	@property
	def tokenExpiration(self):
		return int(float(self.getSetting('token_expiration','0')))

	@property
	def userName(self):
		return self.getSetting('name','')

class GoogleOAuthorizer(object):
	auth1URL = 'https://accounts.google.com/o/oauth2/device/code'
	auth2URL = 'https://accounts.google.com/o/oauth2/token'
	grantType = 'http://oauth.net/grant_type/device/1.0'
	verificationURL = 'http://www.google.com/device'

	def __init__(self,addon_id=None,client_id=None,client_secret=None,auth_scope=None):
		assert addon_id != None, 'addon_id cannot be None'
		assert client_id != None, 'client_id cannot be None'
		assert client_secret != None, 'client_secret cannot be None'
		assert auth_scope != None, 'auth_scope cannot be None'
		
		self.addonID = addon_id
		self.clientID = client_id
		self.clientS = client_secret
		self.authScope = auth_scope
		self.authPollInterval = 5
		self.deviceCode = ''
		self.session = requests.Session()
		self.tokenHandler = AddonTokens()

	def _setSetting(self,key,value):
		self.tokenHandler.setSetting(key,value)

	def _getSetting(self,key,default=None):
		return self.tokenHandler.getSetting(key,default)

	def setUser(self,userID):
		self.tokenHandler.setUser(userID)
	
	def userName(self):
		return self.tokenHandler.userName

	def setUserName(self,name):
		self._setSetting('name',name)

	def renameUser(self,ID,new):
		self.tokenHandler.renameUser(ID,new)
		
	def deleteUser(self,ID):
		self.tokenHandler.deleteUser(ID)

	def setUsers(self,users):
		self.tokenHandler.setUsers(users)

	def users(self):
		ret = []
		for k,v in self.tokenHandler.users.items():
			ret.append((k,v['name']))
		return ret

	def getToken(self):
		if self.tokenHandler.tokenExpiration <= int(time.time()):
			return self.updateToken()
		return self.tokenHandler.token

	def errorReAuthorize(self):
		LOG('Re-authorizing due to error or missing refresh token...')
		noAuth = xbmcgui.Dialog().yesno(T(32006),T(32023),T(32024),nolabel=T(32025),yeslabel=T(32026))
		if noAuth: return None
		self.authorize()
		return self.tokenHandler.token

	def updateToken(self):
		if not self.tokenHandler.refreshToken:
			LOG('Refresh token missing')
			return self.errorReAuthorize()

		LOG('REFRESHING TOKEN')
		data = {	
					'client_id':self.clientID,
					'client_secret':self.clientS,
					'refresh_token':self.tokenHandler.refreshToken,
					'grant_type':'refresh_token'
		}

		json = self.session.post(self.auth2URL,data=data).json()
		if 'access_token' in json:
			self.saveData(json)
		else:
			LOG('Failed to update token')
			return self.errorReAuthorize()

		return self.tokenHandler.token
	
	def authorized(self):
		return bool(self.tokenHandler.token)
		
	def authorize(self):
		userCode = self.getDeviceUserCode()
		if not userCode: return
		d = xbmcgui.DialogProgress()
		d.create(T(32010),'{0} {1}'.format(T(32011),self.verificationURL),'{0} {1}'.format(T(32012),userCode),T(32013))
		try:
			ct=0
			while not d.iscanceled() and not xbmc.abortRequested:
				d.update(ct,'{0} {1}'.format(T(32011),self.verificationURL),'{0} {1}'.format(T(32012),userCode),T(32013))
				json = self.pollAuthServer()
				if 'access_token' in json: break
				for x in range(0,self.authPollInterval):
					if d.iscanceled(): return
					xbmc.sleep(1000)
				ct+=1
			if d.iscanceled(): return
		finally:
			d.close()
			
		xbmcgui.Dialog().ok(T(32008),'',T(32019))
		return self.saveData(json)
		
	def saveData(self,json):
		self._setSetting('access_token',json.get('access_token',''))
		refreshToken = json.get('refresh_token')
		if refreshToken: self._setSetting('refresh_token',refreshToken)
		self._setSetting('token_expiration',json.get('expires_in',3600) + int(time.time()))

	def pollAuthServer(self):
		json = self.session.post(
			self.auth2URL, 
			data={
					'client_id':self.clientID,
					'client_secret':self.clientS,
					'code':self.deviceCode,
					'grant_type':self.grantType
			}
		).json()
		if 'error' in json:
			if json['error'] == 'slow_down':
				self.authPollInterval += 1
		return json
		
	def getDeviceUserCode(self):
		json = self.session.post(self.auth1URL,data={'client_id':self.clientID,'scope':self.authScope}).json()
		self.authPollInterval = json.get('interval',5)
		self.authExpires = json.get('expires_in',1800) + int(time.time())
		self.deviceCode = json.get('device_code','')
		self.verificationURL = json.get('verification_url',self.verificationURL)
		if 'error' in json:
			LOG('ERROR - getDeviceUserCode(): ' + json.get('error_description',''))
		return json.get('user_code','')


import sys, binascii, getpass, xbmc #@UnresolvedImport
import easypassword

__addon__ = sys.modules["__main__"].__addon__
ERROR = sys.modules["__main__"].ERROR

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

def savePassword(key,user,password):
	method = getPasswordCryptoMethod()
	__addon__.setSetting(key,preSavePassword(easypassword.encryptPassword(getUserKey(user),password,method=method,keyfile=getSetting('crypto_key_file'))))

def getPassword(key,user):
	if not user: return ''
	try:
		password = getSetting(key)
		method, keyfile, password = parsePassword(password)
		password = easypassword.decryptPassword(getUserKey(user),password,method=method,keyfile=keyfile)
	except:
		ERROR('passmanager.getPassword()')
		return ''
	return password


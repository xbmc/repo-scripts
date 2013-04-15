import aes, pyDes, binascii, hashlib

def encryptPassword(key,password,method='aes',keyfile=None):
	if keyfile: key = getKeyFromFile(keyfile,key)
	if not key: return None
	if method.lower() == 'des':
		password = encryptDes(key,password)
	elif method.lower() == 'aes':
		password =  aes.encryptData(hashlib.md5(key).digest(),password)
	else:
		password = encryptDes(key,password)
		password = aes.encryptData(hashlib.md5(key).digest(),password)
		
	return binascii.hexlify(password)

def decryptPassword(key,password,method='aes',keyfile=None):
	if keyfile: key = getKeyFromFile(keyfile,key)
	if not key: return None
	password = binascii.unhexlify(password)
	if method.lower() == 'des':
		return decryptDes(key,password)
	elif method.lower() == 'aes':
		return aes.decryptData(hashlib.md5(key).digest(),password)
	else:
		password = aes.decryptData(hashlib.md5(key).digest(),password)
		return decryptDes(key,password)
	
def encryptDes(key,password):
	des = pyDes.triple_des(hashlib.md5(key).digest())
	return des.encrypt(password,padmode=pyDes.PAD_PKCS5)
	
def decryptDes(key,password):
	des = pyDes.triple_des(hashlib.md5(key).digest())
	return des.decrypt(password,padmode=pyDes.PAD_PKCS5)

def getKeyFromFile(filename,pre=''):
	try:
		kf = open(filename,'r')
		key = kf.read(1024)
		kf.close()
		return pre + key
	except:
		return pre
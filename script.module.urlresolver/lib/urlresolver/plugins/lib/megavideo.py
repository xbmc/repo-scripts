''' Python Megavideo Parser
    Copyright (C) 2011  Alessio Glorioso 

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>. '''
 
import urllib2,re
__version__ = "1.0.0"

try:
	if bin(0): pass
except NameError, ne:
	def bin(x):
		'''
		bin(number) -> string

		Stringifies an int or long in base 2.
		'''
		if x < 0: return '-' + bin(-x)
		out = []
		if x == 0: out.append('0')
		while x > 0:
			out.append('01'[x & 1])
			x >>= 1
			pass
		try: return '0b' + ''.join(reversed(out))
		except NameError, ne2: out.reverse()
		return '0b' + ''.join(out)

class Megavideo:
	URL = "http://www.megavideo.com/xml/videolink.php"

	def __init__(self,reference):
		l = len(reference)
		if(l > 8):
			reference = reference[l-8 : l]
	
		xml_url = self.URL+"?v="+str(reference)		
		self.XML_FILE = urllib2.urlopen(xml_url).read()

	def getLink(self):
		try:	self.decrypted
		except:	self.decrypted = Megavideo_Decrypt(self.XML_FILE)
		return "http://www" + str(self.getServer()) + ".megavideo.com/files/" + str(self.decrypted.getDecrypted()) + "/"

	def getFLV(self):
		try:	self.decrypted
		except:	self.decrypted = Megavideo_Decrypt(self.XML_FILE)
		return	"http://www" + str(self.getServer()) + ".megavideo.com/files/" + str(self.decrypted.getDecrypted()) + "/index.flv"

	def is_valid(self):
		error = re.findall('errortext="(.+?)"',self.XML_FILE,re.I)

		if len(error)>0:
			print "ERROR: " + str(error)
			return False
		else:
			return True

	def getServer(self):
		self.server = re.findall('s="([0-9]+)"',self.XML_FILE,re.I)[0]
		return self.server

	def getTitle(self):
		self.title = re.findall('title="(.+?)"',self.XML_FILE,re.I)[0].replace("+"," ")
		return self.title

	def getRuntime(self):
		self.runtime = re.findall('runtimehms="(.+?)"',self.XML_FILE,re.I)[0].replace("+"," ")
		return self.runtime

	def getAllInfo(self):
		self.info = {}

		try: 	self.title
		except:	self.info["Title"] = self.getTitle()
		else:	self.info["Title"] = self.title

		try: 	self.server
		except:	self.info["Server"] = self.getServer()
		else:	self.info["Server"] = self.server

		try: 	self.runtime
		except:	self.info["Runtime"] = self.getRuntime()
		else:	self.info["Runtime"] = self.runtime	

		return self.info

class Megavideo_Decrypt:
	def __init__(self,XML_FILE):
		self.XML_FILE = XML_FILE
		self.setKeys()

		tobin = self.hex2bin(self.un)
		keys = []
		index = 0

		while (index < 384):
			self.k1 = ((int(self.k1) * 11) + 77213) % 81371
			self.k2 = ((int(self.k2) * 17) + 92717) % 192811
			keys.append((int(self.k1) + int(self.k2)) % 128)
			index += 1

		index = 256

		while (index >= 0):
			val1 = keys[index]
			mod  = index%128
			val2 = tobin[val1]
			tobin[val1] = tobin[mod]
			tobin[mod] = val2
			index -= 1

		index = 0
		while(index<128):
			tobin[index] = int(tobin[index]) ^ int(keys[index+256]) & 1
			index += 1

		self.decrypted = self.bin2hex(tobin)

	def setKeys(self):
		self.k1 = re.findall('k1="([0-9]+)"',self.XML_FILE,re.I)[0].replace("+"," ")
		self.k2 = re.findall('k2="([0-9]+)"',self.XML_FILE,re.I)[0].replace("+"," ")
		self.un = re.findall('un="(.+?)"',self.XML_FILE,re.I)[0].replace("+"," ")

	def getDecrypted(self):
		return self.decrypted

	def hex2bin(self,val):
		bin_array = []
		string =  bin(int(val, 16))[2:].zfill(128)
		for value in string:
			bin_array.append(value)
		return bin_array

	def bin2hex(self,val):
		string = str("")
		for char in val:
			string+=str(char)
		return "%x" % int(string, 2)

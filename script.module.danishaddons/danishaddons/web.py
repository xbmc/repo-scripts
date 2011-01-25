import os
import re
import time
import urllib2
from htmlentitydefs import name2codepoint

def downloadUrl(url):
	"""Downloads the url and returns its contents.

	Keyword arguments:
	url -- the url to download, can either be a string or a urllib2.Request object

	"""
	u = urllib2.urlopen(url)
	content = u.read()
	u.close()

	return content
	
def downloadAndCacheUrl(url, cacheFile, cacheMinutes):
	"""Downloads the url and returns its content, which will be cache for the specificed period of time.

	Keyword arguments:
	url -- the url to download, can either be a string or a urllib2.Request object
	cacheFile -- the full path and filename where the cached content will be store
	cacheMinutes -- the contents will be retrieve from the cache if it's age is less than specified minutes

	"""
	try:
		cachedOn = os.path.getmtime(cacheFile)
	except:
		cachedOn = 0

	if(time.time() - cacheMinutes * 60 >= cachedOn):
		# Cache expired or miss
		content = downloadUrl(url)
	
		f = open(cacheFile, 'w')
		f.write(content)
		f.close()

	else:
		f = open(cacheFile)
		content = f.read()
		f.close()

	return content


def decodeHtmlEntities(string):
	"""Decodes the HTML entities found in the string and returns the modified string.

	Both decimal (&#000;) and hexadecimal (&x00;) are supported as well as HTML entities,
	such as &aelig;

	Keyword arguments:
	string -- the string with HTML entities

	"""
	def substituteEntity(match):
		ent = match.group(3)
		if match.group(1) == "#":
			# decoding by number
			if match.group(2) == '':
				# number is in decimal
				return unichr(int(ent))
		elif match.group(2) == 'x':
			# number is in hex
			return unichr(int('0x'+ent, 16))
		else:
			# they were using a name
			cp = name2codepoint.get(ent)
			if cp:
				return unichr(cp)
			else:
				return match.group()
    
	entity_re = re.compile(r'&(#?)(x?)(\w+);')
	return entity_re.subn(substituteEntity, string)[0]



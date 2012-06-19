import urllib2
import json

server_base_address = "http://50.57.179.9"

def post(address, d):
	h = {
		"Content-Type": "application/json",

		# Some extra headers for fun
		"Accept": "*/*",   # curl does this
		"User-Agent": "xbmc-gsoc2012-statistics", # otherwise it uses "Python-urllib/..."
	}

	req = urllib2.Request(address, headers = h, data = d)

	f = urllib2.urlopen(req, timeout = 10)

def uploadMedia(media, data):
	post(server_base_address + "/" + media, json.dumps(data))

def serverActive():
	try:
		ret = urllib2.urlopen(server_base_address + "/active", timeout = 10)
		if ret == None:
			return False
		else:
			return json.load(ret)
	except:
		return False

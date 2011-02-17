import sys

sys.path.append('/home/solver/.xbmc/addons/script.module.simplejson/lib')

import simplejson

def dumps(var):
	return simplejson.dumps(var)

def loads(var):
	return simplejson.loads(var)

import sys
_log = sys.modules["__main__"].xbmcutil.plugin.log

if sys.version_info >=  (2, 7):
	_log("Importing Built in Json Library", 0)
	from json import *
else:
	_log("Importing Older Simplejson Library", 0)
	from simplejson import *
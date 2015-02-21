import sys
if sys.version_info >=  (2, 7):	from json import *
else: 
	try: from simplejson import *
	except: from json import *
import sys

if sys.version_info >=  (2, 7):
	print "Importing Built in Json Library"
	from json import *
else:
	print "Importing Older Simplejson Library"
	from simplejson import *
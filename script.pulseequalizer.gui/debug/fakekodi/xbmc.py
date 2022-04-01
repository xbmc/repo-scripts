
LOGINFO='INFO:'
LOGERROR='ERROR:'
LOGDEBUG='DEBUG:'

#LOGDEBUG = 0
#LOGERROR = 3
#LOGFATAL = 4
#LOGINFO = 1
#LOGNONE = 5
#LOGWARNING = 2

def log(text, level = LOGINFO):
	print (level,text)

def translatePath(path):
	return path

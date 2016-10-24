import time

LOGDEBUG = 0
abortRequested = False

def log(message, level):
	print(message)

def sleep(msec):
	time.sleep(msec / 1000.0)
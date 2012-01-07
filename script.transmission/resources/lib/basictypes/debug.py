"""Logging facilities for basictypes

If the logging package (from Python 2.3) is available,
we use it for our logging needs, otherwise we use a
simplistic locally-defined class for logging.
"""
import traceback, cStringIO
def getException(error):
	"""Get formatted exception"""
	exception = str(error)
	file = cStringIO.StringIO()
	try:
		traceback.print_exc( limit=10, file = file )
		exception = file.getvalue()
	finally:
		file.close()
	return exception

try:
	import logging
	Log = logging.getLogger
	logging.basicConfig()
	WARN = logging.WARN
	ERROR = logging.ERROR
	INFO = logging.INFO
	DEBUG = logging.DEBUG
	logging.Logger.getException = staticmethod( getException )
	logging.Logger.err = logging.Logger.error
except ImportError:
	# does not have the logging package installed
	import sys
	DEBUG = 10
	INFO = 20
	WARN = 30
	ERROR = 40
	class Log( object ):
		"""Stand-in logging facility"""
		level = WARN
		def __init__( self, name ):
			self.name = name
		def debug(self, message, *arguments):
			if self.level <= DEBUG:
				sys.stderr.write( 'DEBUG:%s:%s\n'%(self.name, message%arguments))
		def warn( self, message, *arguments ):
			if self.level <= WARN:
				sys.stderr.write( 'WARN:%s:%s\n'%(self.name, message%arguments))
		def error( self, message, *arguments ):
			if self.level <= ERROR:
				sys.stderr.write( 'ERR :%s:%s\n'%(self.name, message%arguments))
		def info( self, message, *arguments ):
			if self.level <= INFO:
				sys.stderr.write( 'INFO:%s:%s\n'%(self.name, message%arguments))
		def setLevel( self, level ):
			self.level = level
		getException = staticmethod( getException )
		


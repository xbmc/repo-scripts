#v.0.1.4

try:
    import xbmc
    LOGTYPE = 'xbmc'
except:
    import logging, logging.handlers
    LOGTYPE = 'file'

#this class creates an object used to log stuff to the xbmc log file
class Logger():
    def __init__(self, preamble='', logfile='logfile.log', logdebug='true'):
        self.LOGPREAMBLE = preamble
        self.LOGDEBUG = logdebug
        if LOGTYPE == 'file':
            self.logger = logging.getLogger( '_logger' )
            self.logger.setLevel( logging.DEBUG )
            lr = logging.handlers.RotatingFileHandler( logfile, maxBytes=100000, backupCount=5 )
            lr.setLevel( logging.DEBUG )
            lr.setFormatter( logging.Formatter( "%(asctime)-15s %(levelname)-8s %(message)s" ) )
            self.logger.addHandler( lr )


    def log( self, loglines, loglevel='' ):
        if LOGTYPE == 'xbmc' and not loglevel:
            loglevel = xbmc.LOGDEBUG
        elif LOGTYPE == 'file':
            if loglevel == 'info':
                loglevel = self.logger.info
            elif loglevel == 'warning':
                loglevel = self.logger.warning
            elif loglevel == 'error':
                loglevel = self.logger.error
            elif loglevel == 'critical':
                loglevel = self.logger.critical
            else:
                loglevel = self.logger.debug
            
        for line in loglines:
            try:
                if type(line).__name__=='unicode':
                    line = line.encode('utf-8')
                str_line = line.__str__()
            except Exception, e:
                str_line = ''
                self._output( 'error parsing logline', loglevel )
                self._output( e, loglevel )
            if str_line:
                self._output( str_line, loglevel )


    def _output( self, line, loglevel ):
        if LOGTYPE == 'file':
            self._output_file( line, loglevel )
        else:
            self._output_xbmc( line, loglevel )

                
    def _output_file( self, line, loglevel ):
        if not (self.LOGDEBUG.lower() == 'false' and loglevel == self.logger.debug):
            try:
                loglevel( "%s %s" % (self.LOGPREAMBLE, line.__str__()) )
            except Exception, e:
                self.logger.debug( "%s unable to output logline" % self.LOGPREAMBLE )
                self.logger.debug( "%s %s" % (self.LOGPREAMBLE, e.__str__()) )


    def _output_xbmc( self, line, loglevel ):
        if not (self.LOGDEBUG.lower() == 'false' and (loglevel == xbmc.LOGINFO or loglevel == xbmc.LOGDEBUG)):
            try:
                xbmc.log( "%s %s" % (self.LOGPREAMBLE, line.__str__()), loglevel)
            except Exception, e:
                xbmc.log( "%s unable to output logline" % self.LOGPREAMBLE, loglevel)
                xbmc.log ("%s %s" % (self.LOGPREAMBLE, e.__str__()), loglevel)
#v.0.1.0

import xbmc

#this class creates an object used to log stuff to the xbmc log file
class Logger():
    def __init__(self, preamble=''):
        self.logpreamble = preamble


    def _output( self, line, loglevel ):
        try:
            xbmc.log("%s %s" % (self.logpreamble, line.__str__()), loglevel)
        except Exception, e:
            xbmc.log("%s unable to output logline" % self.logpreamble, loglevel)
            xbmc.log("%s %s" % (self.logpreamble, e.__str__()), loglevel)
            

    def log( self, loglines, loglevel=xbmc.LOGDEBUG ):
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
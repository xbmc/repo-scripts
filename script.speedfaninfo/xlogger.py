import xbmcaddon, xbmc

### get addon info and set globals
__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__author__       = __addon__.getAddonInfo('author')
__version__      = __addon__.getAddonInfo('version')
__addonpath__    = __addon__.getAddonInfo('path')
__addondir__     = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__icon__         = __addon__.getAddonInfo('icon')
__localize__     = __addon__.getLocalizedString
__log_preamble__ = ''

#this class creates an object used to log stuff to the xbmc log file
class Logger():
    def __init__(self): pass
        # and define it as self

    def setPreamble(self, preamble):
        #sets the preamble for the log line so you can find it in the XBMC log
        global __log_preamble__
        __log_preamble__ = preamble

    def parseListorTuple(self, items, count):
        #parse a list or tuple into a string
        #this function will recurse if it detects lists of lists of lists, etc.
        #define a whole bunch of possible delimiters for recursion purposes
        delims = [',', ':', '/', ';', '~', '!', '@', '#', '$', '%', '^', '&', '*']
        line = ''
        for item in items:
            itemclass = item.__class__.__name__
            if(itemclass == 'list' or itemclass == 'tuple'):
                grouping = self.parseListorTuple(item, count+1)
            else:
                grouping = item
            if(len(line) == 0):
                line = grouping
            else:
                line = line + delims[count] + ' ' + grouping
        return line
        
    def log(self, *args):
        #send an arbitrary group of data to log
        #the last argument must be the logtype of the data (i.e. standard or verbose)
        #convert
        #l_args = list(args)
        #the type (i.e. standard or verbose) of the log item is in the last item of the tuple
        type = args[-1]
        #if advanced logging is disabled, only non-detailed items are logged
        verbose = False
        standard = False
        if(__addon__.getSetting('advanced_log') == 'true' and type == 'verbose'):
            verbose = True
        elif(type =='standard'):
            standard = True
        #now we need to iterate through all the other args and log them
        for arg in args[:-1]:
            argclass = arg.__class__.__name__
            if(argclass == 'str' or argclass == 'unicode'):
                line = arg
            elif(argclass == 'list' or argclass == 'tuple'):
                #loop through the items and put them into comma separated list
                line = self.parseListorTuple(arg, 0)
            else:
                line = 'no appropriate action found for class ' + argclass
            if verbose:
                xbmc.log(__log_preamble__ + ' ' + line)
            elif standard:
                xbmc.log(__log_preamble__ + ' ' + line)


inst = Logger()
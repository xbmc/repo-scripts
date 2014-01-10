import xbmc, unicodedata

__log_preamble__ = ''

#this class creates an object used to log stuff to the xbmc log file
class Logger():
    def __init__(self, preamble=''):
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
        #the log_level is in the last item of the args
        log_level = args[-1]
        #now we need to iterate through all the other args and log them
        for arg in args[:-1]:
            argclass = arg.__class__.__name__
            if(argclass == 'str' or argclass == 'unicode'):
                line = arg
            elif(argclass == 'list' or argclass == 'tuple'):
                #loop through the items and put them into comma separated list
                line = self.parseListorTuple(arg, 0)
            else:
                line = arg
                #line = 'no appropriate action found for class ' + argclass
            if type(line).__name__=='unicode':
                line = line.encode('utf-8')
            xbmc.log("%s %s" % (__log_preamble__, line.__str__()), log_level)

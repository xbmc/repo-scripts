# v.0.1.0

import ntpath, xbmcvfs


def checkDir(path):
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)

def pathLeaf(path):
    path, filename = ntpath.split(path)
    return {"path":path, "filename":filename}

def writeFile( data, filename ):
    log_lines = []
    if type(data).__name__=='unicode':
        data = data.encode('utf-8')
    try:
        thefile = open( filename, 'wb' )
        thefile.write( data )
        thefile.close()
    except IOError, e:
        log_lines.append( 'unable to write data to ' + filename )
        log_lines.append( e )
        return False, log_lines
    except Exception, e:
        log_lines.append( 'unknown error while writing data to ' + filename )
        log_lines.append( e )
        return False, log_lines
    log_lines.append( 'successfuly wrote data to ' + filename )
    return True, log_lines

def readFile( filename ):
    log_lines = []
    if xbmcvfs.exists( filename):
        try:
            the_file = open (filename, 'r')
            data = the_file.read()
            the_file.close()
        except IOError:
            log_lines.append( 'unable to read data from ' + filename )
            return log_lines, ''
        except Exception, e:
            log_lines.append( 'unknown error while reading data from ' + filename )
            log_lines.append( e )
            return log_lines, ''
        return log_lines, data
    else:
        log_lines.append( '%s does not exist' % filename )
        return log_lines, ''

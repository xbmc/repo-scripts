# v.0.3.3

try:
    import xbmcvfs
    isXBMC = True
except:
    import os
    isXBMC= False

if isXBMC:
    _mkdirs = xbmcvfs.mkdirs
    _exists = xbmcvfs.exists
    _delete = xbmcvfs.delete
    _file = xbmcvfs.File
else:
    _mkdirs = os.makedirs
    _exists = os.path.exists
    _delete = os.remove


def checkPath( path, create=True ):
    log_lines = []
    log_lines.append( 'checking for %s' % path )
    if not _exists( path ):
        if create:
            log_lines.append( '%s does not exist, creating it' % path )
            _mkdirs( path )
        else:
            log_lines.append( '%s does not exist' % path )
        return False, log_lines
    else:
        log_lines.append( '%s exists' % path )
        return True, log_lines

def deleteFile( filename ):
    log_lines = []
    if _exists( filename ):
        try:
            _delete( filename )
            log_lines.append( 'deleting file %s' % filename )
        except IOError:
            log_lines.append( 'unable to delete %s' % filename )
            return False, log_lines
        except Exception, e:
            log_lines.append( 'unknown error while attempting to delete %s' % filename )
            log_lines.append( e )
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append( '%s does not exist' % filename )
        return False, log_lines


def readFile( filename ):
    log_lines = []
    if _exists( filename ):
        try:
            thefile = xbmcvfs.File( filename, 'r' )
        except:
            thefile = open( filename, 'r' )
        try:
            data = thefile.read()
            thefile.close()
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

def writeFile( data, filename ):
    log_lines = []
    if type(data).__name__=='unicode':
        data = data.encode('utf-8')
    try:
        thefile = xbmcvfs.File( filename, 'wb' )
    except:
        thefile = open( filename, 'wb' )
    try:
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
# v.0.3.6

import subprocess, time
try:
    import xbmcvfs
    isXBMC = True
except:
    import os
    isXBMC= False

if isXBMC:
    _mkdirs = xbmcvfs.mkdirs
    _rmdir  = xbmcvfs.rmdir
    _exists = xbmcvfs.exists
    _delete = xbmcvfs.delete
    _rename = xbmcvfs.rename
    _file = xbmcvfs.File
else:
    _mkdirs = os.makedirs
    _rmdir  = os.rmdir
    _exists = os.path.exists
    _delete = os.remove
    _rename = os.rename


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


def deleteFolder( foldername ):
    log_lines = []
    if _exists( foldername ):
        try:
            _rmdir( foldername )
            log_lines.append( 'deleting folder %s' % foldername )
        except IOError:
            log_lines.append( 'unable to delete %s' % foldername )
            return False, log_lines
        except Exception, e:
            log_lines.append( 'unknown error while attempting to delete %s' % foldername )
            log_lines.append( e )
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append( '%s does not exist' % foldername )
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


def renameFile ( filename, newfilename ):
    log_lines = []
    if _exists( filename ):
        try:
            _rename( filename, newfilename )
            log_lines.append( 'renaming %s to %s' % (filename, newfilename) )
        except IOError:
            log_lines.append( 'unable to rename %s' % filename )
            return False, log_lines
        except Exception, e:
            log_lines.append( 'unknown error while attempting to rename %s' % filename )
            log_lines.append( e )
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append( '%s does not exist' % filename )
        return False, log_lines


def popenWithTimeout( command, timeout ):
    log_lines = []
    try:
        p = subprocess.Popen( command, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
    except OSError:
        log_lines.append( 'error finding external script, terminating' )
        return False, log_lines
    except Exception, e:
        log_lines.append( 'unknown error while attempting to run %s' % command )
        log_lines.append( e )
        return False, log_lines
    for t in xrange( timeout * 4 ):
        time.sleep( 0.25 )
        if p.poll() is not None:
            return p.communicate(), ''
    p.kill()
    log_lines.append( 'script took too long to run, terminating' )
    return False, log_lines


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
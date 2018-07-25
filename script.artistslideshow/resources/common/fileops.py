# v.0.4.4

import shutil, time
try:
    import subprocess
    hasSubprocess = True
except:
    import os
    hasSubprocess = False
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
    _copy   = xbmcvfs.copy
else:
    _mkdirs = os.makedirs
    _rmdir  = os.rmdir
    _exists = os.path.exists
    _delete = os.remove
    _copy   = shutil.copyfile


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


def copyFile( src, dst ):
    log_lines = []
    if _exists( src ):
        try:
            log_lines.append( 'copying file %s to %s' % (src, dst) )
            _copy( src, dst )
        except IOError:
            log_lines.append( 'unable to copy %s to %s' % (src, dst) )
            return False, log_lines
        except Exception as e:
            log_lines.append( 'unknown error while attempting to copy %s to %s' % (src, dst) )
            log_lines.append( e )
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append( '%s does not exist' % src )
        return False, log_lines


def deleteFile( src ):
    return deleteFolder( src, type='file')


def deleteFolder( src, type='folder' ):
    log_lines = []
    if _exists( src ):
        if type == 'folder':
            _action = _rmdir
        else:
            _action = _delete
        try:
            log_lines.append( 'deleting %s %s' % (type, src) )
            _action( src )
        except IOError:
            log_lines.append( 'unable to delete %s' % src )
            return False, log_lines
        except Exception as e:
            log_lines.append( 'unknown error while attempting to delete %s' % src )
            log_lines.append( e )
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append( '%s does not exist' % src )
        return False, log_lines


def moveFile( src, dst ):
    log_lines = []
    cp_loglines = []
    dl_loglines = []
    success = False
    if _exists( src ):
        cp_success, cp_loglines = copyFile( src, dst )
        if cp_success:
            dl_success, dl_loglines = deleteFile( src )
            if dl_success:
                success = True
    else:
        log_lines.append( '%s does not exist' % src)
        success = False
    return success, log_lines + cp_loglines + dl_loglines


def popenWithTimeout( command, timeout ):
    log_lines = []
    log_lines.append( 'running command ' + command)
    if hasSubprocess:
        try:
            p = subprocess.Popen( command, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        except OSError:
            log_lines.append( 'error finding external script, terminating' )
            return False, log_lines
        except Exception as e:
            log_lines.append( 'unknown error while attempting to run %s' % command )
            log_lines.append( e )
            return False, log_lines
        for t in xrange( timeout * 4 ):
            time.sleep( 0.25 )
            if p.poll() is not None:
                return p.communicate(), log_lines
        p.kill()
        log_lines.append( 'script took too long to run, terminating' )
        return False, log_lines
    else:
        log_lines.append( 'running command with os.system' )
        os.system( command )
        return True, log_lines


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
        except Exception as e:
            log_lines.append( 'unknown error while reading data from ' + filename )
            log_lines.append( e )
            return log_lines, ''
        return log_lines, data
    else:
        log_lines.append( '%s does not exist' % filename )
        return log_lines, ''


def renameFile ( src, dst ):
    return moveFile( src, dst )


def writeFile( data, filename, wtype='wb' ):
    log_lines = []
    if type(data).__name__=='unicode':
        data = data.encode('utf-8')
    try:
        thefile = xbmcvfs.File( filename, wtype )
    except:
        thefile = open( filename, wtype )
    try:
        thefile.write( data )
        thefile.close()
    except IOError as e:
        log_lines.append( 'unable to write data to ' + filename )
        log_lines.append( e )
        return False, log_lines
    except Exception as e:
        log_lines.append( 'unknown error while writing data to ' + filename )
        log_lines.append( e )
        return False, log_lines
    log_lines.append( 'successfuly wrote data to ' + filename )
    return True, log_lines
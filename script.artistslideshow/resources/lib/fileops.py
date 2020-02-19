# v.0.7.0

import os, re
try:
    _range = range
except NameError:
    _range = xrange
try:
    from kodi_six import xbmcvfs
    isXBMC = True
except ImportError:
    isXBMC= False

if isXBMC:
    _mkdirs = xbmcvfs.mkdirs
    _rmdir  = xbmcvfs.rmdir
    _exists = xbmcvfs.exists
    _delete = xbmcvfs.delete
    _copy   = xbmcvfs.copy
    _open   = xbmcvfs.File
else:
    import shutil
    _mkdirs = os.makedirs
    _rmdir  = os.rmdir
    _exists = os.path.exists
    _delete = os.remove
    _copy   = shutil.copyfile
    _open   = open


def checkPath( thepath, createdir=True ):
    log_lines = []
    log_lines.append( 'checking for %s' % thepath )
    if not _exists( thepath ):
        if createdir:
            log_lines.append( '%s does not exist, creating it' % thepath )
            _mkdirs( thepath )
        else:
            log_lines.append( '%s does not exist' % thepath )
        return False, log_lines
    else:
        log_lines.append( '%s exists' % thepath )
        return True, log_lines


def copyFile( thesource, thedest ):
    log_lines = []
    if _exists( thesource ):
        try:
            log_lines.append( 'copying file %s to %s' % (thesource, thedest) )
            _copy( thesource, thedest )
        except IOError:
            log_lines.append( 'unable to copy %s to %s' % (thesource, thedest) )
            return False, log_lines
        except Exception as e:
            log_lines.append( 'unknown error while attempting to copy %s to %s' % (thesource, thedest) )
            log_lines.append( e )
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append( '%s does not exist' % thesource )
        return False, log_lines


def deleteFile( thesource ):
    return deleteFolder( thesource, thetype='file')


def deleteFolder( thesource, thetype='folder' ):
    log_lines = []
    if _exists( thesource ):
        if thetype == 'folder':
            #in Mac OSX the .DS_Store file, if present, will block a folder from being deleted, so delete the file
            try:
                _delete( os.path.join( thesource, '.DS_Store' ) )
            except IOError:
                log_lines.append( 'unable to delete .DS_Store file' )
            except Exception as e:
                log_lines.append( 'unknown error while attempting to delete .DS_Store file' )
                log_lines.append( e )
            _action = _rmdir
        else:
            _action = _delete
        try:
            log_lines.append( 'deleting %s %s' % (thetype, thesource) )
            if isXBMC:
                if not _action( thesource ):
                    raise IOError( 'unable to delete item' )
            else:
                _action( thesource )
        except IOError:
            log_lines.append( 'unable to delete %s' % thesource )
            return False, log_lines
        except Exception as e:
            log_lines.append( 'unknown error while attempting to delete %s' % thesource )
            log_lines.append( e )
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append( '%s does not exist' % thesource )
        return False, log_lines


def moveFile( thesource, thedest ):
    log_lines = []
    cp_loglines = []
    dl_loglines = []
    success = False
    if _exists( thesource ):
        cp_success, cp_loglines = copyFile( thesource, thedest )
        if cp_success:
            dl_success, dl_loglines = deleteFile( thesource )
            if dl_success:
                success = True
    else:
        log_lines.append( '%s does not exist' % thesource)
        success = False
    return success, log_lines + cp_loglines + dl_loglines


def atoi( text ):
    return int(text) if text.isdigit() else text


def naturalKeys( text ):
    '''
    alist.sort( key=naturalKeys ) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    '''
    return [ atoi( c ) for c in re.split( r'(\d+)', text ) ]


def readFile( filename ):
    log_lines = []
    if _exists( filename ):
        thefile = _open( filename, 'r' )
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


def renameFile ( thesource, thedest ):
    return moveFile( thesource, thedest )


def writeFile( data, filename, wtype='wb' ):
    log_lines = []
    if type(data).__name__=='unicode':
        data = data.encode('utf-8')
    thefile = _open( filename, wtype )
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
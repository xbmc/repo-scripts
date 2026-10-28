# v.0.12.4

import os
import re
import sys
try:
    import xbmcvfs
    isXBMC = True
except ImportError:
    isXBMC = False

if isXBMC:
    _mkdirs = xbmcvfs.mkdirs
    _rmdir = xbmcvfs.rmdir
    _exists = xbmcvfs.exists
    _delete = xbmcvfs.delete
    _copy = xbmcvfs.copy
    _open = xbmcvfs.File
    _rename = xbmcvfs.rename
else:
    import shutil
    _mkdirs = os.makedirs
    _rmdir = os.rmdir
    _exists = os.path.exists
    _delete = os.remove
    _copy = shutil.copyfile
    _open = open
    _rename = os.rename


def checkPath(thepath, createdir=True):
    log_lines = []
    log_lines.append('checking for %s' % thepath)
    if not _exists(thepath):
        if createdir:
            log_lines.append('%s does not exist, creating it' % thepath)
            _mkdirs(thepath)
        else:
            log_lines.append('%s does not exist' % thepath)
        return False, log_lines
    else:
        log_lines.append('%s exists' % thepath)
        return True, log_lines


def copyFile(thesource, thedest):
    log_lines = []
    if _exists(thesource):
        log_lines.append('copying file %s to %s' % (thesource, thedest))
        try:
            _copy(thesource, thedest)
        except IOError:
            log_lines.append('unable to copy %s to %s' % (thesource, thedest))
            return False, log_lines
        except Exception as e:
            log_lines.append(
                'unknown error while attempting to copy %s to %s' % (thesource, thedest))
            log_lines.append(e)
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append('%s does not exist' % thesource)
        return False, log_lines


def deleteFile(thesource):
    return deleteFolder(thesource, thetype='file')


def deleteFolder(thesource, thetype='folder'):
    log_lines = []
    if _exists(thesource):
        if thetype == 'folder':
            # in Mac OSX the .DS_Store file, if present, will block a folder from being deleted, so delete the file
            try:
                _delete(os.path.join(thesource, '.DS_Store'))
            except IOError:
                log_lines.append('unable to delete .DS_Store file')
            except Exception as e:
                log_lines.append(
                    'unknown error while attempting to delete .DS_Store file')
                log_lines.append(e)
            _action = _rmdir
        else:
            _action = _delete
        log_lines.append('deleting %s %s' % (thetype, thesource))
        try:
            if isXBMC:
                if not _action(thesource):
                    raise IOError('unable to delete item')
            else:
                _action(thesource)
        except IOError:
            log_lines.append('unable to delete %s' % thesource)
            return False, log_lines
        except Exception as e:
            log_lines.append(
                'unknown error while attempting to delete %s' % thesource)
            log_lines.append(e)
            return False, log_lines
        return True, log_lines
    else:
        log_lines.append('%s does not exist' % thesource)
        return False, log_lines


def listDirectory(thesource, thefilter='all'):
    log_lines = []
    log_lines.append('getting contents of folder %s' % thesource)
    if isXBMC:
        try:
            dirs, files = xbmcvfs.listdir(thesource)
        except OSError:
            log_lines.append('OSError getting directory list')
            return [], log_lines
        except Exception as e:
            log_lines.append('unexpected error getting directory list')
            log_lines.append(e)
            return [], log_lines
        if thefilter == 'files':
            log_lines.append('returning files from %s' % thesource)
            log_lines.append(files)
            return files, log_lines
        elif thefilter == 'folders':
            log_lines.append('returning folders from %s' % thesource)
            log_lines.append(dirs)
            return dirs, log_lines
        else:
            log_lines.append('returning files and folders from %s' % thesource)
            log_lines.append(files + dirs)
            return files + dirs, log_lines
    else:
        try:
            contents = os.listdir(thesource)
        except OSError:
            log_lines.append('OSError getting directory list')
            return [], log_lines
        except Exception as e:
            log_lines.append('unexpected error getting directory list')
            log_lines.append(e)
            return [], log_lines
        log_lines.append('returning files and folders from %s' % thesource)
        return contents, log_lines


def moveFile(thesource, thedest):
    log_lines = []
    cp_loglines = []
    dl_loglines = []
    success = False
    if _exists(thesource):
        cp_success, cp_loglines = copyFile(thesource, thedest)
        if cp_success:
            dl_success, dl_loglines = deleteFile(thesource)
            if dl_success:
                success = True
    else:
        log_lines.append('%s does not exist' % thesource)
        success = False
    return success, log_lines + cp_loglines + dl_loglines


def _atoi(text):
    return int(text) if text.isdigit() else text


def naturalKeys(thelist):
    # from http://nedbatchelder.com/blog/200712/human_sorting.html
    return [_atoi(c) for c in re.split(r'(\d+)', thelist)]


def osPathFromString(spath, sep='/'):
    pathlist = spath.split(sep)
    if spath.startswith(sep):
        pathlist.insert(0, os.sep)
        pathlist[2] = pathlist[2] + os.sep
    return os.path.join(*pathlist)


def readFile(filename):
    log_lines = []
    if _exists(filename):
        try:
            if sys.version_info >= (3, 0):
                with _open(filename, 'r') as thefile:
                    thedata = thefile.read()
            else:
                thefile = _open(filename, 'r')
                thedata = thefile.read()
                thefile.close()
        except IOError:
            log_lines.append('unable to read data from ' + filename)
            return log_lines, ''
        except Exception as e:
            log_lines.append(
                'unknown error while reading data from ' + filename)
            log_lines.append(e)
            return log_lines, ''
        return log_lines, thedata
    else:
        log_lines.append('%s does not exist' % filename)
        return log_lines, ''


def renameFile(thesource, thedest):
    log_lines = []
    log_lines.append('renaming file %s to %s' % (thesource, thedest))
    try:
        _rename(thesource, thedest)
    except IOError:
        log_lines.append('unable to rename %s to %s' % (thesource, thedest))
        return False, log_lines
    except Exception as e:
        log_lines.append(
            'unknown error while attempting to rename %s to %s' % (thesource, thedest))
        log_lines.append(e)
        return False, log_lines
    return True, log_lines


def _remove_trailing_dot(thename, endreplace=''):
    if thename[-1] == '.' and len(thename) > 1 and endreplace != '.':
        return _remove_trailing_dot(thename[:-1] + endreplace)
    else:
        return thename


def setSafeName(thename, illegalchars='<>:"/\|?*', illegalreplace='_', endreplace=''):
    loglines = []
    if not thename:
        loglines.append('name is empty, returning it')
        return thename, loglines
    s_name = ''
    loglines.append('started with %s' % thename)
    loglines.append('the illegal characters are %s and the replacement is %s' % (
        illegalchars, illegalreplace))
    for c in list(_remove_trailing_dot(thename, endreplace=endreplace)):
        if c in illegalchars:
            s_name = s_name + illegalreplace
        else:
            s_name = s_name + c
    loglines.append('finished with %s' % s_name)
    return s_name, loglines


def writeFile(data, filename, wtype='wb'):
    log_lines = []
    if type(data).__name__ == 'unicode':
        data = data.encode('utf-8')
    try:
        if sys.version_info >= (3, 0):
            with _open(filename, wtype) as thefile:
                thefile.write(data)
        else:
            thefile = _open(filename, wtype)
            thefile.write(data)
            thefile.close()
    except IOError as e:
        log_lines.append('unable to write data to ' + filename)
        log_lines.append(e)
        return False, log_lines
    except Exception as e:
        log_lines.append('unknown error while writing data to ' + filename)
        log_lines.append(e)
        return False, log_lines
    log_lines.append('successfuly wrote data to ' + filename)
    return True, log_lines

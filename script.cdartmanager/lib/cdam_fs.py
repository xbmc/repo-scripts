# -*- coding: utf-8 -*-
# system imports
import os

import xbmc
import xbmcvfs

import cdam
import cdam_utils as cu
from cdam_utils import log


# sanitize filename
def sanitize(fn):
    return fn.replace("\\\\", "\\")


# get target path for artist related artwork
def get_artist_path(artist_name, fn=None):
    cfg = cdam.Settings()
    result = os.path.join(cfg.path_music_path(), cu.change_characters(cu.smart_unicode(artist_name)))
    if fn:
        result = os.path.join(result, fn)
    return sanitize(result)


# get backup folder for album
def cdart_get_backup_filename(artist, album, disc_num=1):
    cfg = cdam.Settings()
    fn_format = cfg.folder()
    backup_folder = cfg.path_backup_path()
    if not backup_folder:
        cfg.open()
        backup_folder = cfg.path_backup_path()
    if fn_format == 0:
        destination = os.path.join(backup_folder, cu.change_characters(artist))
        fn = os.path.join(destination, cu.change_characters(album))
    else:
        destination = backup_folder
        fn = os.path.join(destination, cu.change_characters((artist + " - " + album).lower()))
    if disc_num > 1:
        fn += "_disc_" + str(disc_num)
    fn += ".png"
    log("backup filename: %s" % fn, xbmc.LOGDEBUG)
    return fn


def cdart_single_restore(target, artist, album, disc_num=1):
    log("Restore: %s - %s" % (artist, album), xbmc.LOGNOTICE)
    log(" target: %s" % target, xbmc.LOGNOTICE)
    source = cdart_get_backup_filename(artist, album, disc_num)
    if disc_num > 1 and not xbmcvfs.exists(source):
        log(" DISC %s source (%s) not found, searching upwards" % (disc_num, source), xbmc.LOGDEBUG)
        source = cdart_get_backup_filename(artist, album)
    log(" source: %s" % source, xbmc.LOGNOTICE)
    if xbmcvfs.exists(source):
        try:
            if not xbmcvfs.exists(os.path.dirname(target)):
                xbmcvfs.mkdirs(os.path.dirname(target))
                log(" target path created", xbmc.LOGDEBUG)
            xbmcvfs.copy(source, target)
            log("Restore succesful.", xbmc.LOGNOTICE)
            return True
        except Exception as e:
            log("copying error, check path and file permissions", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
    else:
        log("No Backup found, skipped.", xbmc.LOGNOTICE)
    return False


# backup a cdart file
def cdart_single_backup(source, artist, album, disc_num=1):
    log("Backup: %s - %s" % (artist, album), xbmc.LOGNOTICE)
    log(" source: %s" % source, xbmc.LOGNOTICE)
    if xbmcvfs.exists(source):
        target = cdart_get_backup_filename(artist, album, disc_num)
        log(" target: %s" % target, xbmc.LOGNOTICE)
        if xbmcvfs.exists(target):
            log(" target exists, skipping", xbmc.LOGNOTICE)
        else:
            try:
                if not xbmcvfs.exists(os.path.dirname(target)):
                    xbmcvfs.mkdirs(os.path.dirname(target))
                    log(" target path created", xbmc.LOGDEBUG)
                xbmcvfs.copy(source, target)
                log("Backup succesful.", xbmc.LOGNOTICE)
                return True
            except Exception as e:
                log("copying error, check path and file permissions", xbmc.LOGNOTICE)
                log(e.message, xbmc.LOGWARNING)
    else:
        log("Backup source does not exist, skipped.", xbmc.LOGNOTICE)
    return False


def cdart_single_delete(fn):
    log("Deleting: %s" % fn, xbmc.LOGNOTICE)
    if xbmcvfs.exists(fn):
        try:
            xbmcvfs.delete(fn)
            return True
        except Exception as e:
            log("Error in script occured", xbmc.LOGNOTICE)
            log(e.message, xbmc.LOGWARNING)
            log("Deleteing error, check path and file permissions", xbmc.LOGNOTICE)
            return False
    else:
        log("Error: cdART file does not exist..  Please check...", xbmc.LOGNOTICE)
    return True

# coding=iso-8859-2
debug_pretext = "[Feliratok.hu] "


def debuglog(msg):
    import xbmc
    msg = msg.encode('ascii', 'replace')
    xbmc.log( debug_pretext + msg, level=xbmc.LOGDEBUG )     

def errorlog(msg):
    import xbmc
    msg = msg.encode('ascii', 'replace')
    xbmc.log( debug_pretext + msg, level=xbmc.LOGERROR )     

def unpack_archive(archive_file, dst_dir):
    import xbmc
    xbmc.executebuiltin("XBMC.Extract(" + archive_file + "," + dst_dir +")")

def clean_title(filename):
    import xbmc                                 
    return xbmc.getCleanMovieTitle( filename ) 

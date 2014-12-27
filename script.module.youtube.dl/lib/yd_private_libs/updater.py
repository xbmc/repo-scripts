# -*- coding: utf-8 -*-
import sys
import util

LATEST_URL = 'https://yt-dl.org/latest/youtube-dl.tar.gz'
VERSION_URL = 'https://yt-dl.org/latest/version'

def set_youtube_dl_importPath():
    return
    #if not util.getSetting('use_update_version',True): return
    import os
    import xbmc
    profile = xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8')
    youtube_dl_path = os.path.join(profile,'youtube-dl')
    if not os.path.exists(youtube_dl_path): return
    sys.path.insert(0,youtube_dl_path)

def saveVersion(version):
    import util
    util.setSetting('core_version',version)

def updateCore(force=False):
    if not force: return
    import xbmc
    import os, urllib, urllib2
    import tarfile

    util.LOG('Checking for new youtube_dl core version...')

    currentVersion = util.getSetting('core_version')
    try:
        newVersion = urllib2.urlopen(VERSION_URL).read().strip()
        if currentVersion == newVersion:
            util.LOG('Core version up to date')
            return False
    except:
        util.ERROR()
        return False

    util.LOG('Updating youtube_dl core to new version: {0}'.format(newVersion))

    profile = xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8')
    archivePath = os.path.join(profile,'youtube_dl.tar.gz')
    extractedPath = os.path.join(profile,'youtube-dl')

    try:
        if os.path.exists(extractedPath):
            import shutil
            shutil.rmtree(extractedPath, ignore_errors=True)
            util.LOG('Old version removed')

        urllib.urlretrieve(LATEST_URL,filename=archivePath)
        with tarfile.open(archivePath,mode='r:gz') as tf:
            members = [m for m in tf.getmembers() if m.name.startswith('youtube-dl/youtube_dl')] #get just the files from the youtube_dl source directory
            tf.extractall(path=profile,members=members)
    except:
        util.ERROR('Core update FAILED')

    util.LOG('Core update complete')
    return True
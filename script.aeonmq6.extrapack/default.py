import os, sys, urllib, urllib2, zipfile, shutil
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from StringIO import StringIO
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__language__     = __addon__.getLocalizedString


def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        # init vars
        self._set_vars()
        # check how we were started
        self.mode = self._parse_argv()
        # continue if a valid arg was passed to the script
        if self.mode:
            # create needed directories
            completed = self._make_dirs()
            # abort if we couldn't create the directories
            if completed and self.mode == 'update':
                xbmcgui.Dialog().notification(__addonname__, xbmc.getLocalizedString(24092), xbmcgui.NOTIFICATION_INFO, 5000)
                # check for updates
                update = self._update_check()
                # update available
                if update == 1:
                    log('update availale')
                    success = self._partial_update()
                    if success:
                        xbmcgui.Dialog().notification(__addonname__, xbmc.getLocalizedString(20177), xbmcgui.NOTIFICATION_INFO, 5000)
                    else:
                        xbmcgui.Dialog().notification(__addonname__, xbmc.getLocalizedString(113), xbmcgui.NOTIFICATION_INFO, 5000)
                # no update available
                elif update == 0:
                    log('no update availale')
                    xbmcgui.Dialog().notification(__addonname__, xbmc.getLocalizedString(20177), xbmcgui.NOTIFICATION_INFO, 5000)
                # error checking for updates, do a full install
                elif update == 2:
                    log('error, trying full install instead')
                    self.mode = 'install'
                # first run, do a full install
                elif update == 4:
                    log('do full install')
                    self.mode = 'install'
            # full install
            if completed and self.mode == 'install':
                xbmcgui.Dialog().notification(__addonname__, xbmc.getLocalizedString(13413), xbmcgui.NOTIFICATION_INFO, 5000)
                # recreate the tempdir, just in case there are some stray files in there
                shutil.rmtree(self.tempdir)
                xbmcvfs.mkdirs(self.tempdir)
                # get github directory revisions
                dirrevs = self._get_dirrevs()
                # save dirrevs to file
                if dirrevs:
                    self._save_data(self.revdirs, str(dirrevs))
                # do a full install
                success = self._full_install()
                if success:
                    xbmcgui.Dialog().notification(__addonname__, xbmc.getLocalizedString(20177), xbmcgui.NOTIFICATION_INFO, 5000)
                else:
                    xbmcgui.Dialog().notification(__addonname__, xbmc.getLocalizedString(114), xbmcgui.NOTIFICATION_INFO, 5000)

    def _set_vars(self):
        # backup directory
        self.backupdir = xbmc.translatePath('special://profile/addon_data/%s/backup/' % __addonid__).decode("utf-8")
        # temp directory
        self.tempdir = xbmc.translatePath('special://profile/addon_data/%s/updates/' % __addonid__).decode("utf-8")
        # installation directory
        self.targetdir = xbmc.translatePath('special://profile/addon_data/skin.aeonmq6.extrapack/')
        # github base api url
        self.githubapi = 'https://api.github.com/%s'
        # repo api call
        self.repo = 'repos/AeonMQ/skin.aeonmq6.extrapack/branches?callback=rev'
        # directories api call
        self.repodirs = 'repos/AeonMQ/skin.aeonmq6.extrapack/contents?callback=dir'
        # files api call
        self.repofiles = 'repos/AeonMQ/skin.aeonmq6.extrapack/git/trees/%s?recursive=1'
        # file download url
        self.repofiledl = 'https://raw.githubusercontent.com/AeonMQ/skin.aeonmq6.extrapack/master/%s/%s'
        # zipfile download url
        self.repozip = 'https://codeload.github.com/AeonMQ/skin.aeonmq6.extrapack/legacy.zip/master'
        # repo revision file
        self.revrepo = xbmc.translatePath(os.path.join(self.tempdir, 'repo-revision.txt')).decode("utf-8")
        # directory revision file
        self.revdirs = xbmc.translatePath(os.path.join(self.tempdir, 'file-revisions.txt')).decode("utf-8")

    def _parse_argv(self):
        log('script params: %s' % sys.argv)
        if len(sys.argv) == 2:
            argv = sys.argv[1]
        else:
            return False
        if argv:
            if argv == 'mode=default':
                params = 'update'
            elif argv == 'mode=forcerefresh':
                params = 'install'
            else:
                params = False
        return params

    def _make_dirs(self):
        log('creating directories')
        try:
            if not xbmcvfs.exists(self.backupdir):
                xbmcvfs.mkdirs(self.backupdir)
            if not xbmcvfs.exists(self.tempdir):
                xbmcvfs.mkdirs(self.tempdir)
            if not xbmcvfs.exists(self.targetdir):
                xbmcvfs.mkdirs(self.targetdir)
            return True
        except:
            log('failed to create directories')
            return False

    def _create_backup(self, item):
        log('creating backup')
        # remove old backup
        try:
            shutil.rmtree(xbmc.translatePath(os.path.join(self.backupdir, item)).decode("utf-8"))
        except:
            pass # if this is the first time we make a backup, the backup folder will not exist
        # copy current install to backup folder
        try:
            xbmcvfs.rename(xbmc.translatePath(os.path.join(self.targetdir, item)).decode("utf-8"), xbmc.translatePath(os.path.join(self.backupdir, item)).decode("utf-8"))
        except:
            pass # if a new remote folder was added, it will not exist locally the targetdir

    def _full_install(self):
        log('downloading zipfile')
        tmpfile = xbmc.translatePath(os.path.join(self.tempdir, 'temp.zip')).decode("utf-8")
        # download the entire repo as a zipfile
        data = self._download_file(self.repozip, tmpfile)
        if not data:
            log('zipfile download failed')
            return False
        log('extracting zipfile')
        # extract the zipfile and copy the contents to the install directory
        try:
            zipdata = zipfile.ZipFile(tmpfile)
            folder = zipdata.namelist()[0]
            revision = folder.split('-')[2].rstrip('/')
            zipdata.extractall(self.tempdir)
            zipdata.close()
            shutil.rmtree(self.targetdir)
            path = os.path.join(self.tempdir, folder)
            shutil.move(path, self.targetdir)
        except:
            log('failed to extract zipfile')
            return False
        # save the repo revision to file
        self._save_data(self.revrepo, revision)
        # remove the zipfile
        xbmcvfs.delete(tmpfile)
        return True

    def _get_file(self, url):
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            data = response.read()
            response.close()
        except:
            log('error response from github')
            return False
        return data

    def _show_progress(self, blocks_read, block_size, total_size):
        # connection opened but no data received yet
        if not blocks_read:
            return
        # github does not always return the filesize of the zipfile
        if total_size < 0: 
            self.count += 1
            if self.count > 10000:
                self.count = 0
            percent = int(self.count / 100)
        # filsize is known
        else:
            percent = int(((float(blocks_read) * float(block_size)) / float(total_size)) * 100)
        self.dialog.update(percent, __addonname__, xbmc.getLocalizedString(13413))
        return

    def _download_file(self, url, path):
        self.dialog = xbmcgui.DialogProgressBG()
        self.dialog.create(__addonname__, xbmc.getLocalizedString(13413))
        self.count = 0
        try:
            urllib.urlretrieve(url, path, reporthook=self._show_progress)
            self.dialog.close()
            return True
        except:
            self.dialog.close()
            log('file download error')
            return False

    def _update_check(self):
        log('checking for updates')
        # check the cached repo revision
        local_rev = self._read_data(self.revrepo)
        if not local_rev:
            return 4
        # get the current repo revision
        url = self.githubapi % self.repo
        data = self._get_file(url)
        if data:
            json_data = unicode(data[8:-1])
            json_response = simplejson.loads(json_data)
            if json_response.has_key('data'):
                remote_rev = json_response['data'][0]['commit']['sha'][:7]
                # update available
                if local_rev != remote_rev:
                    # save the new repo revision to file
                    self._save_data(self.revrepo, remote_rev)
                    return 1
                return 0
        return 2

    def _get_dirrevs(self):
        url = self.githubapi % (self.repodirs)
        # get the individual folder revisions from github
        data = self._get_file(url)
        json_data = unicode(data[8:-1])
        json_response = simplejson.loads(json_data)
        if json_response.has_key('data'):
            dirs = []
            for item in json_response['data']:
                name = item['path']
                rev = item['sha']
                dirs.append([name, rev])
            return dirs
        return False

    def _partial_update(self):
        updated_dirs = []
        updated_files = []
        # read the cached dirrevs from file
        local_dirs = eval(self._read_data(self.revdirs))
        # get the current dirrevs from github
        remote_dirs = self._get_dirrevs()
        # abort in case of an error
        if not remote_dirs:
            return False
        # save the current dirrevs to file
        self._save_data(self.revdirs, str(remote_dirs))
        for item in remote_dirs:
            # check if there are any newer dirrevs
            if item not in local_dirs:
                dirname = item[0]
                dirsha = item[1]
                xbmcvfs.mkdirs(xbmc.translatePath(os.path.join(self.tempdir, dirname)).decode("utf-8"))
                updated_dirs.append(item[0])
                url = self.githubapi % (self.repofiles % dirsha)
                # get a list of files inside the updated directory
                data = self._get_file(url)
                if data:
                    json_data = unicode(data)
                    json_response = simplejson.loads(json_data)
                    if json_response.has_key('tree'):
                        # create a list of files to be downloaded
                        for fileentry in json_response['tree']:
                            if fileentry.has_key('size'):
                                name = fileentry['path']
                                url = self.repofiledl % (dirname, name)
                                updated_files.append([name, url, dirname])
        # github api limit allows only 60 calls an hour
        if len(updated_files) > 50:
            # too many files have been updated, do a full install instead
            success = self._full_install()
            return success
        # download the images
        for image in updated_files:
            data = self._download_file(image[1].replace(' ','%20'), xbmc.translatePath(os.path.join(self.tempdir, image[2], image[0])).decode("utf-8"))
            if not data:
                log('file download failed')
        for item in updated_dirs:
            # create a backup of the old folders that will updated
            self._create_backup(item)
            # move the updated folder to the install directory
            xbmcvfs.rename(xbmc.translatePath(os.path.join(self.tempdir, item)).decode("utf-8"), xbmc.translatePath(os.path.join(self.targetdir, item)).decode("utf-8"))
        # check if any folders have been removed on github
        for item in local_dirs:
            localname = item[0]
            match = False
            for item in remote_dirs:
                remotename = item[0]
                if localname == remotename:
                    match = True
                    break
            #remote folder was removed, move the local one to backup
            if not match:
                xbmcvfs.rename(xbmc.translatePath(os.path.join(self.targetdir, localname)).decode("utf-8"), xbmc.translatePath(os.path.join(self.backupdir, localname)).decode("utf-8"))
        return True

    def _read_data(self, path):
        try:
            filename = open(path, 'r')
            data = filename.read()
            filename.close()
            return data
        except:
            return False

    def _save_data(self, path, data):
        filename = open(path, 'wb')
        filename.write(data)
        filename.close()

if (__name__ == "__main__"):
    log('script version %s started' % __addonversion__)
    Main()
log('script stopped')

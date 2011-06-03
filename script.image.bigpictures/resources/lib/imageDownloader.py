import urllib
import os
import sys
import re
import xbmc
import xbmcgui
import xbmcaddon

Addon = sys.modules['__main__'].Addon
#enable localization
getLS = Addon.getLocalizedString

scriptName = sys.modules['__main__'].__scriptname__


class Download:

    def __init__(self, photos, downloadPath):
        self.len = str(len(photos))
        self.pDialog = xbmcgui.DialogProgress()
        self.pDialog.create('')
        downloadPath = xbmc.translatePath(downloadPath)

        for i, photo in enumerate(photos):
            self.url = photo['pic']
            self.index = str(i + 1)
            # unicode causes problems here, convert to standard str
            self.filename = '_'.join([str(i),
                                      str(self.url.split('/')[-1])])
            # download folder should be named like the album
            foldername = re.sub('[^\w\s-]', '', str(photo['title']))
            self.fullDownloadPath = os.path.join(downloadPath,
                                                 foldername,
                                                 self.filename)
            print '[SCRIPT][%s] %s --> %s' % (scriptName,
                                              self.url,
                                              self.fullDownloadPath)

            if self.checkPath(downloadPath, foldername, self.filename):
                try:
                    dl = urllib.urlretrieve(self.url,
                                            self.fullDownloadPath,
                                            reporthook=self.showdlProgress)
                    print '[SCRIPT][%s] Download Success!' % scriptName
                except IOError, e:
                    print e
                    self.pDialog.close()
                    dialog = xbmcgui.Dialog()
                    dialog.ok('Error',
                              '%s %s %s\n%s' % (self.index,
                                                getLS(32025),
                                                self.len,
                                                self.url),
                              e.__str__())
                    break
                if self.pDialog.iscanceled():
                    self.pDialog.close()
                    break
        # close the progress dialog
        self.pDialog.close()

    def showdlProgress(self, count, blockSize, totalSize):
        percent = int(count * blockSize * 100 / totalSize)
        enum = '%s %s %s' % (self.index, getLS(32025), self.len)
        fromPath = '%s %s' % (getLS(32023), self.url)
        toPath = '%s %s' % (getLS(32024), self.fullDownloadPath)
        self.pDialog.update(percent, enum, fromPath, toPath)

    def checkPath(self, path, folder, filename):
        if os.path.isdir(path):
            if os.path.isdir(os.path.join(path,
                                          folder)):
                if os.path.isfile(os.path.join(path,
                                               folder,
                                               filename)):
                    if not os.path.getsize(os.path.join(path,
                                                        folder,
                                                        filename)) > 0:
                        return True  # overwrite empty files, #skip others.
                else:
                    return True
            else:
                os.mkdir(os.path.join(path, folder))
                # check again after creating directory
                self.checkPath(path, folder, filename)

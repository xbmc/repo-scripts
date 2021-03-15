from __future__ import unicode_literals
import zipfile
import os.path
import sys
import xbmcvfs
import xbmcgui
from dropbox import dropbox
from . import utils as utils
from dropbox.files import WriteMode, CommitInfo, UploadSessionCursor
from . authorizers import DropboxAuthorizer


class Vfs:
    root_path = None

    def __init__(self, rootString):
        self.set_root(rootString)

    def clean_path(self, path):
        # fix slashes
        path = path.replace("\\", "/")

        # check if trailing slash is included
        if(path[-1:] != '/'):
            path = path + '/'

        return path

    def set_root(self, rootString):
        old_root = self.root_path
        self.root_path = self.clean_path(rootString)

        # return the old root
        return old_root

    def listdir(self, directory):
        return {}

    def mkdir(self, directory):
        return True

    def put(self, source, dest):
        return True

    def rmdir(self, directory):
        return True

    def rmfile(self, aFile):
        return True

    def exists(self, aFile):
        return True

    def rename(self, aFile, newName):
        return True

    def cleanup(self):
        return True

    def fileSize(self, filename):
        return 0  # result should be in KB


class XBMCFileSystem(Vfs):

    def listdir(self, directory):
        return xbmcvfs.listdir(directory)

    def mkdir(self, directory):
        return xbmcvfs.mkdir(xbmcvfs.translatePath(directory))

    def put(self, source, dest):
        return xbmcvfs.copy(xbmcvfs.translatePath(source), xbmcvfs.translatePath(dest))

    def rmdir(self, directory):
        return xbmcvfs.rmdir(directory, force=True)  # use force=True to make sure it works recursively

    def rmfile(self, aFile):
        return xbmcvfs.delete(aFile)

    def rename(self, aFile, newName):
        return xbmcvfs.rename(aFile, newName)

    def exists(self, aFile):
        return xbmcvfs.exists(aFile)

    def fileSize(self, filename):
        with xbmcvfs.File(filename) as f:
            result = f.size() / 1024  # bytes to kilobytes

        return result


class ZipFileSystem(Vfs):
    zip = None

    def __init__(self, rootString, mode):
        self.root_path = ""
        self.zip = zipfile.ZipFile(rootString, mode=mode, compression=zipfile.ZIP_DEFLATED, allowZip64=True)

    def listdir(self, directory):
        return [[], []]

    def mkdir(self, directory):
        # self.zip.write(directory[len(self.root_path):])
        return False

    def put(self, source, dest):

        aFile = xbmcvfs.File(xbmcvfs.translatePath(source), 'r')

        self.zip.writestr(dest, aFile.readBytes())

        return True

    def rmdir(self, directory):
        return False

    def exists(self, aFile):
        return False

    def cleanup(self):
        self.zip.close()

    def extract(self, aFile, path):
        # extract zip file to path
        self.zip.extract(aFile, path)

    def listFiles(self):
        return self.zip.infolist()


class DropboxFileSystem(Vfs):
    MAX_CHUNK = 50 * 1000 * 1000  # dropbox uses 150, reduced to 50 for small mem systems
    client = None
    APP_KEY = ''
    APP_SECRET = ''

    def __init__(self, rootString):
        self.set_root(rootString)

        authorizer = DropboxAuthorizer()

        if(authorizer.isAuthorized()):
            self.client = authorizer.getClient()
        else:
            # tell the user to go back and run the authorizer
            xbmcgui.Dialog().ok(utils.getString(30010), utils.getString(30105))
            sys.exit()

    def listdir(self, directory):
        directory = self._fix_slashes(directory)

        if(self.client is not None and self.exists(directory)):
            files = []
            dirs = []
            metadata = self.client.files_list_folder(directory)

            for aFile in metadata.entries:
                if(isinstance(aFile, dropbox.files.FolderMetadata)):
                    dirs.append(aFile.name)
                else:
                    files.append(aFile.name)

            return [dirs, files]
        else:
            return [[], []]

    def mkdir(self, directory):
        directory = self._fix_slashes(directory)
        if(self.client is not None):
            # sort of odd but always return true, folder create is implicit with file upload
            return True
        else:
            return False

    def rmdir(self, directory):
        directory = self._fix_slashes(directory)
        if(self.client is not None and self.exists(directory)):
            # dropbox is stupid and will refuse to do this sometimes, need to delete recursively
            dirs, files = self.listdir(directory)

            for aDir in dirs:
                self.rmdir(aDir)

            # finally remove the root directory
            self.client.files_delete(directory)

            return True
        else:
            return False

    def rmfile(self, aFile):
        aFile = self._fix_slashes(aFile)

        if(self.client is not None and self.exists(aFile)):
            self.client.files_delete(aFile)
            return True
        else:
            return False

    def exists(self, aFile):
        aFile = self._fix_slashes(aFile)

        if(self.client is not None):
            # can't list root metadata
            if(aFile == ''):
                return True

            try:
                self.client.files_get_metadata(aFile)
                # if we make it here the file does exist
                return True
            except:
                return False
        else:
            return False

    def put(self, source, dest, retry=True):
        dest = self._fix_slashes(dest)

        if(self.client is not None):
            # open the file and get its size
            f = open(source, 'rb')
            f_size = os.path.getsize(source)

            try:
                if(f_size < self.MAX_CHUNK):
                    # use the regular upload
                    self.client.files_upload(f.read(), dest, mode=WriteMode('overwrite'))
                else:
                    # start the upload session
                    upload_session = self.client.files_upload_session_start(f.read(self.MAX_CHUNK))
                    upload_cursor = UploadSessionCursor(upload_session.session_id, f.tell())

                    while(f.tell() < f_size):
                        # check if we should finish the upload
                        if((f_size - f.tell()) <= self.MAX_CHUNK):
                            # upload and close
                            self.client.files_upload_session_finish(f.read(self.MAX_CHUNK), upload_cursor, CommitInfo(dest, mode=WriteMode('overwrite')))
                        else:
                            # upload a part and store the offset
                            self.client.files_upload_session_append_v2(f.read(self.MAX_CHUNK), upload_cursor)
                            upload_cursor.offset = f.tell()

                # if no errors we're good!
                return True
            except Exception as anError:
                utils.log(str(anError))

                # if we have an exception retry
                if(retry):
                    return self.put(source, dest, False)
                else:
                    # tried once already, just quit
                    return False
        else:
            return False

    def fileSize(self, filename):
        result = 0
        aFile = self._fix_slashes(filename)

        if(self.client is not None):
            metadata = self.client.files_get_metadata(aFile)
            result = metadata.size / 1024  # bytes to KB

        return result

    def get_file(self, source, dest):
        if(self.client is not None):
            # write the file locally
            self.client.files_download_to_file(dest, source)
            return True
        else:
            return False

    def _fix_slashes(self, filename):
        result = filename.replace('\\', '/')

        # root needs to be a blank string
        if(result == '/'):
            result = ""

        # if dir ends in slash, remove it
        if(result[-1:] == "/"):
            result = result[:-1]

        return result

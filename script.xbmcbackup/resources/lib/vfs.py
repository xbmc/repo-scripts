import utils as utils
import tinyurl as tinyurl
import xbmc
import xbmcvfs
import xbmcgui
import zipfile
import zlib
import os
import os.path
import sys
import dropbox
from dropbox.files import WriteMode,CommitInfo,UploadSessionCursor
from pydrive.drive import GoogleDrive
from authorizers import DropboxAuthorizer,GoogleDriveAuthorizer

class Vfs:
    root_path = None

    def __init__(self,rootString):
        self.set_root(rootString)
        
    def set_root(self,rootString):
        old_root = self.root_path
        self.root_path = rootString
        
        #fix slashes
        self.root_path = self.root_path.replace("\\","/")
        
        #check if trailing slash is included
        if(self.root_path[-1:] != "/"):
            self.root_path = self.root_path + "/"

        #return the old root
        return old_root
        
    def listdir(self,directory):
        return {}

    def mkdir(self,directory):
        return True

    def put(self,source,dest):
        return True

    def rmdir(self,directory):
        return True

    def rmfile(self,aFile):
        return True

    def exists(self,aFile):
        return True
    
    def rename(self,aFile,newName):
        return True
    
    def cleanup(self):
        return True
        
class XBMCFileSystem(Vfs):

    def listdir(self,directory):
        return xbmcvfs.listdir(directory)

    def mkdir(self,directory):
        return xbmcvfs.mkdir(xbmc.translatePath(directory))

    def put(self,source,dest):
        return xbmcvfs.copy(xbmc.translatePath(source),xbmc.translatePath(dest))
        
    def rmdir(self,directory):
        return xbmcvfs.rmdir(directory,True)

    def rmfile(self,aFile):
        return xbmcvfs.delete(aFile)

    def rename(self,aFile,newName):
        return xbmcvfs.rename(aFile, newName)

    def exists(self,aFile):
        return xbmcvfs.exists(aFile)

class ZipFileSystem(Vfs):
    zip = None
    
    def __init__(self,rootString,mode):
        self.root_path = ""
        self.zip = zipfile.ZipFile(rootString,mode=mode,compression=zipfile.ZIP_DEFLATED,allowZip64=True)
        
    def listdir(self,directory):
        return [[],[]]
    
    def mkdir(self,directory):
        #self.zip.write(directory[len(self.root_path):])
        return False
    
    def put(self,source,dest):
        
        aFile = xbmcvfs.File(xbmc.translatePath(source),'r')
        
        self.zip.writestr(utils.encode(dest),aFile.read())
        
        return True
    
    def rmdir(self,directory):
        return False
    
    def exists(self,aFile):
        return False
    
    def cleanup(self):
        self.zip.close()
        
    def extract(self,aFile,path):
        #extract zip file to path
        self.zip.extract(aFile,path)
    
    def listFiles(self):
        return self.zip.infolist()

class DropboxFileSystem(Vfs):
    MAX_CHUNK = 50 * 1000 * 1000 #dropbox uses 150, reduced to 50 for small mem systems
    client = None
    APP_KEY = ''
    APP_SECRET = ''
    
    def __init__(self,rootString):
        self.set_root(rootString)

        authorizer = DropboxAuthorizer()

        if(authorizer.isAuthorized()):
            self.client = authorizer.getClient()
        else:
            #tell the user to go back and run the authorizer
            xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30105))
            sys.exit()

    def listdir(self,directory):
        directory = self._fix_slashes(directory)
        
        if(self.client != None and self.exists(directory)):
            files = []
            dirs = []
            metadata = self.client.files_list_folder(directory)

            for aFile in metadata.entries:
                if(isinstance(aFile,dropbox.files.FolderMetadata)):
                    dirs.append(utils.encode(aFile.name))
                else:
                    files.append(utils.encode(aFile.name))

            return [dirs,files]
        else:
            return [[],[]]
            

    def mkdir(self,directory):
        directory = self._fix_slashes(directory)
        if(self.client != None):
            #sort of odd but always return true, folder create is implicit with file upload
            return True
        else:
            return False

    def rmdir(self,directory):
        directory = self._fix_slashes(directory)
        if(self.client != None and self.exists(directory)):
            #dropbox is stupid and will refuse to do this sometimes, need to delete recursively
            dirs,files = self.listdir(directory)
            
            for aDir in dirs:
                self.rmdir(aDir)

            #finally remove the root directory
            self.client.files_delete(directory)
            
            return True
        else:
            return False

    def rmfile(self,aFile):
        aFile = self._fix_slashes(aFile)
        
        if(self.client != None and self.exists(aFile)):
            self.client.files_delete(aFile)
            return True
        else:
            return False

    def exists(self,aFile):
        aFile = self._fix_slashes(aFile)
        
        if(self.client != None):
            #can't list root metadata
            if(aFile == ''):
                return True
            
            try:
                meta_data = self.client.files_get_metadata(aFile)
                #if we make it here the file does exist
                return True
            except:
                return False
        else:
            return False

    def put(self,source,dest,retry=True):
        dest = self._fix_slashes(dest)
        
        if(self.client != None):
            #open the file and get its size
            f = open(source,'rb')
            f_size = os.path.getsize(source)
            
            try:
                if(f_size < self.MAX_CHUNK):
                    #use the regular upload
                    response = self.client.files_upload(f.read(),dest,mode=WriteMode('overwrite'))
                else:
                    #start the upload session
                    upload_session = self.client.files_upload_session_start(f.read(self.MAX_CHUNK))
                    upload_cursor = UploadSessionCursor(upload_session.session_id,f.tell())
                    
                    while(f.tell() < f_size):
                        #check if we should finish the upload
                        if((f_size - f.tell()) <= self.MAX_CHUNK):
                            #upload and close
                            self.client.files_upload_session_finish(f.read(self.MAX_CHUNK),upload_cursor,CommitInfo(dest,mode=WriteMode('overwrite')))
                        else:
                            #upload a part and store the offset
                            self.client.files_upload_session_append_v2(f.read(self.MAX_CHUNK),upload_cursor)
                            upload_cursor.offset = f.tell()
                    
                 #if no errors we're good!   
                return True
            except Exception as anError:
                utils.log(str(anError))
                
                #if we have an exception retry
                if(retry):
                    return self.put(source,dest,False)
                else:
                    #tried once already, just quit
                    return False
        else:
            return False

    def get_file(self,source,dest):
        if(self.client != None):
            #write the file locally
            f = self.client.files_download_to_file(dest,source)
            return True
        else:
            return False

    def _fix_slashes(self,filename):
        result = filename.replace('\\','/')

        #root needs to be a blank string
        if(result == '/'):
            result = ""

        #if dir ends in slash, remove it
        if(result[-1:] == "/"):
            result = result[:-1]

        return result
            

class GoogleDriveFilesystem(Vfs):
    drive = None
    history = {}
    FOLDER_TYPE = 'application/vnd.google-apps.folder'
    
    def __init__(self,rootString):
        self.set_root(rootString)

        authorizer = GoogleDriveAuthorizer()

        if(authorizer.isAuthorized()):
            self.drive = authorizer.getClient()
        else:
            #tell the user to go back and run the authorizer
            xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30105))
            sys.exit()

        #make sure we have the folder we need
        xbmc_folder = self._getGoogleFile(self.root_path)
        if(xbmc_folder == None):
            self.mkdir(self.root_path)
            
    def listdir(self,directory):
        files = []
        dirs = []
    
        if(not directory.startswith('/')):
            directory = '/' + directory
        
        #get the id of this folder
        parentFolder = self._getGoogleFile(directory)
    
        #need to do this after
        if(not directory.endswith('/')):
                directory = directory + '/'
    
        if(parentFolder != None):
        
            fileList = self.drive.ListFile({'q':"'" + parentFolder['id'] + "' in parents and trashed = false"}).GetList()
       
            for aFile in fileList:
                if(aFile['mimeType'] == self.FOLDER_TYPE):
                    dirs.append(utils.encode(aFile['title']))
                else:
                    files.append(utils.encode(aFile['title']))
                
    
        return [dirs,files]    

    def mkdir(self,directory):
        result = True
        
        if(not directory.startswith('/')):
            directory = '/' + directory
        
        if(directory.endswith('/')):
            directory = directory[:-1]
        
        #split the string by the directory separator
        pathList = os.path.split(directory)
        
        if(pathList[0] == '/'):
            
            #we're at the root, just make the folder
            newFolder = self.drive.CreateFile({'title': pathList[1], 'parent':'root','mimeType':self.FOLDER_TYPE})
            newFolder.Upload()
        else:
            #get the id of the parent folder
            parentFolder = self._getGoogleFile(pathList[0])
        
            if(parentFolder != None):
                newFolder = self.drive.CreateFile({'title': pathList[1],"parents":[{'kind':'drive#fileLink','id':parentFolder['id']}],'mimeType':self.FOLDER_TYPE})
                newFolder.Upload()
            else:
                result = False
        
        return result

    def put(self,source,dest):
        result = True
        
        #make the name separate from the path
        if(not dest.startswith('/')):
            dest = '/' + dest
    
        pathList = os.path.split(dest)
    
        #get the parent location
        parentFolder = self._getGoogleFile(pathList[0])
    
        if(parentFolder != None):
            #create a new file in this folder
            newFile = self.drive.CreateFile({"title":pathList[1],"parents":[{'kind':'drive#fileLink','id':parentFolder['id']}]})
            newFile.SetContentFile(source)
            newFile.Upload()
        else:
            result = False
            
        return result

    def get_file(self,source, dest):
        result = True
        
        #get the id of this file
        file = self._getGoogleFile(source)
    
        if(file != None):
            file.GetContentFile(dest)
        else:
            result = False
            
        return result
    
    def rmdir(self,directory):
        result = True
        
        #check that the folder exists
        folder = self._getGoogleFile(directory)
    
        if(folder != None):
            #delete the folder
            folder.Delete()
        else:
            result = False
            
        return result

    def rmfile(self,aFile):
        #really just the same as the remove directory function
        return self.rmdir(aFile)

    def exists(self,aFile):
        #attempt to get this file
        foundFile = self._getGoogleFile(aFile)
        
        if(foundFile != None):
            return True
        else:
            return False
    
    def rename(self,aFile,newName):
        return True
    
    def _getGoogleFile(self,file):
        result = None
       
        #file must start with / and not end with one (even directory)
        if(not file.startswith('/')):
            file = '/' + file
        
        if(file.endswith('/')):
            file = file[:-1]
    
        if(self.history.has_key(file)):
            
            result = self.history[file]
        else:
            pathList = os.path.split(file)
        
            #end of recurision, we got the root
            if(pathList[0] == '/'):
                #get the id of this file (if it exists)
                file_list = self.drive.ListFile({'q':"title='" + pathList[1] + "' and 'root' in parents and trashed=false"}).GetList()
        
                if(len(file_list) > 0):
                    result = file_list[0]
                    self.history[pathList[1]] = result
            else:
                #recurse down the tree
                current_file = pathList[1]
    
                parentId = self._getGoogleFile(pathList[0])
            
                if(parentId != None):
                    self.history[pathList[0]] = parentId
                    
                    #attempt to get the id of this file, with this parent
                    file_list = file_list = self.drive.ListFile({'q':"title='" + current_file + "' and '" + parentId['id'] + "' in parents and trashed=false"}).GetList()
                
                    if(len(file_list) > 0):
                        result = file_list[0]
                        self.history[file] = result
                        

        return result


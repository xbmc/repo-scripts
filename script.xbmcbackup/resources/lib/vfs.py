import utils as utils
import xbmc
import xbmcvfs
import xbmcgui
import zipfile
import zlib
import os
from dropbox import client, rest, session
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

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
    client = None
    APP_KEY = ''
    APP_SECRET = ''
    
    def __init__(self,rootString):
        self.set_root(rootString)
        
        self.APP_KEY = utils.getSetting('dropbox_key')
        self.APP_SECRET = utils.getSetting('dropbox_secret')

        self.setup()

    def setup(self):
        if(self.APP_KEY == '' or self.APP_SECRET == ''):
            xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30058),utils.getString(30059))
            return
        
        user_token_key,user_token_secret = self.getToken()
        
        sess = session.DropboxSession(self.APP_KEY,self.APP_SECRET,"app_folder")
        utils.log("token:" + user_token_key + ":" + user_token_secret)
        if(user_token_key == '' and user_token_secret == ''):
            token = sess.obtain_request_token()
            url = sess.build_authorize_url(token)

            #print url in log
            utils.log("Authorize URL: " + url)
            xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30056),utils.getString(30057))  
            
            #if user authorized this will work
            user_token = sess.obtain_access_token(token)
            self.setToken(user_token.key,user_token.secret)
            
        else:
            sess.set_token(user_token_key,user_token_secret)
        
        self.client = client.DropboxClient(sess)

        try:
            utils.log(str(self.client.account_info()))
        except:
            #this didn't work, delete the token file
            self.deleteToken()

    def listdir(self,directory):
        if(self.client != None and self.exists(directory)):
            files = []
            dirs = []
            metadata = self.client.metadata(directory)

            for aFile in metadata['contents']:
                if(aFile['is_dir']):
                    dirs.append(utils.encode(aFile['path'][len(directory):]))
                else:
                    files.append(utils.encode(aFile['path'][len(directory):]))

            return [dirs,files]
        else:
            return [[],[]]
            

    def mkdir(self,directory):
        directory = self._fix_slashes(directory)
        if(self.client != None):
            if(not self.exists(directory)):
                self.client.file_create_folder(directory)
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
            self.client.file_delete(directory)
            
            return True
        else:
            return False

    def rmfile(self,aFile):
        aFile = self._fix_slashes(aFile)
        
        if(self.client != None and self.exists(aFile)):
            self.client.file_delete(aFile)
            return True
        else:
            return False

    def exists(self,aFile):
        aFile = self._fix_slashes(aFile)
        if(self.client != None):
            try:
                meta_data = self.client.metadata(aFile)
                #if we make it here the file does exist
                return True
            except:
                return False
        else:
            return False

    def put(self,source,dest,retry=True):
        dest = self._fix_slashes(dest)
        
        if(self.client != None):
            f = open(source,'rb')
            try:
                response = self.client.put_file(dest,f,True)
                return True
            except:
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
            out = open(dest,'wb')
            f = self.client.get_file(source).read()
            out.write(f)
            out.close()
            return True
        else:
            return False

    def _fix_slashes(self,filename):
        return filename.replace('\\','/')
    
    def setToken(self,key,secret):
        #write the token files
        token_file = open(xbmc.translatePath(utils.data_dir() + "tokens.txt"),'w')
        token_file.write("%s|%s" % (key,secret))
        token_file.close()

    def getToken(self):
        #get tokens, if they exist
        if(xbmcvfs.exists(xbmc.translatePath(utils.data_dir() + "tokens.txt"))):
            token_file = open(xbmc.translatePath(utils.data_dir() + "tokens.txt"))
            key,secret = token_file.read().split('|')
            token_file.close()

            return [key,secret]
        else:
            return ["",""]

    def deleteToken(self):
        if(xbmcvfs.exists(xbmc.translatePath(utils.data_dir() + "tokens.txt"))):
            xbmcvfs.delete(xbmc.translatePath(utils.data_dir() + "tokens.txt"))
            

class GoogleDriveFilesystem(Vfs):
    drive = None
    history = {}
    CLIENT_ID = ''
    CLIENT_SECRET = ''
    FOLDER_TYPE = 'application/vnd.google-apps.folder'
    
    def __init__(self,rootString):
        self.set_root(rootString)
        
        self.CLIENT_ID = utils.getSetting('google_drive_id')
        self.CLIENT_SECRET = utils.getSetting('google_drive_secret')

        self.setup()
    
    def setup(self):
        #create authorization helper and load default settings
        gauth = GoogleAuth(xbmc.validatePath(xbmc.translatePath(utils.addon_dir() + '/resources/lib/pydrive/settings.yaml')))
        gauth.LoadClientConfigSettings()
        
        #check if this user is already authorized
        if(not xbmcvfs.exists(xbmc.translatePath(utils.data_dir() + "google_drive.dat"))):
            settings = {"client_id":self.CLIENT_ID,'client_secret':self.CLIENT_SECRET}
    
            drive_url = gauth.GetAuthUrl(settings)
    
            utils.log("Google Drive Authorize URL: " + drive_url)

            code = xbmcgui.Dialog().input('Google Drive Validation Code','Input the Validation code after authorizing this app')

            gauth.Auth(code)
            gauth.SaveCredentialsFile(xbmc.validatePath(xbmc.translatePath(utils.data_dir() + 'google_drive.dat')))
        else:
            gauth.LoadCredentialsFile(xbmc.validatePath(xbmc.translatePath(utils.data_dir() + 'google_drive.dat')))
    
        #create the drive object
        self.drive = GoogleDrive(gauth)
        
        #make sure we have the folder we need
        xbmc_folder = self._getGoogleFile(self.root_path)
        print xbmc_folder
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


import utils as utils
import xbmc
import xbmcvfs
import xbmcgui
import sys
from dropbox import client, rest, session

APP_KEY = utils.getSetting('dropbox_key')
APP_SECRET = utils.getSetting('dropbox_secret')

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

    def getFile(self,source):
        return True
    
    def rmdir(self,directory):
        return True

    def exists(self,aFile):
        return True
        
class XBMCFileSystem(Vfs):

    def listdir(self,directory):
        return xbmcvfs.listdir(directory)

    def mkdir(self,directory):
        return xbmcvfs.mkdir(directory)

    def put(self,source,dest):
        return xbmcvfs.copy(source,dest)
        
    def rmdir(self,directory):
        return xbmcvfs.rmdir(directory,True)

    def exists(self,aFile):
        return xbmcvfs.exists(aFile)

class DropboxFileSystem(Vfs):
    client = None
    
    def __init__(self,rootString):
        self.set_root(rootString)
        self.setup()

    def setup(self):
        if(APP_KEY == '' or APP_SECRET == ''):
            xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30058),utils.getString(30059))
            return
        
        user_token_key,user_token_secret = self.getToken()
        
        sess = session.DropboxSession(APP_KEY,APP_SECRET,"app_folder")

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
                    dirs.append(aFile['path'][len(directory):])
                else:
                    files.append(aFile['path'][len(directory):])

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
            self.client.file_delete(directory)
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

    def put(self,source,dest):
        dest = self._fix_slashes(dest)
        
        if(self.client != None):
            f = open(source,'rb')
            try:
                response = self.client.put_file(dest,f,True)
                return True
            except:
                #if we have an exception retry
                retry = True
                return self.put(source,dest)
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
            



            

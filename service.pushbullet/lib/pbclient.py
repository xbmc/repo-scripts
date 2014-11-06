import json
import platform
import requests

STREAM_BASE_URL = 'wss://stream.pushbullet.com/websocket/{0}'

DEBUG = False
def LOG(msg): pass

class PushbulletException(Exception):
    def __init__(self,error):
        self.type = error.get('type')
        self.message = error.get('message')
        Exception.__init__(self)

class Device:
    settings = {}

    def __init__(self,ID,name=None,data=None):
        self.ID = ID
        self.name = name
        self.type = 'stream'
        self.model = 'Kodi'
        self.manufacturer = platform.system()
        self.data = data
        self.mostRecent = 0
        self._bulletHoles = {}
        self.init()

    def __eq__(self,other):
        if not isinstance(other, Device): return False
        return self.ID == other.ID

    def __ne__(self,other):
        return not self.__eq__(other)
                                
    def init(self):
        pass
    
    def isValid(self):
        return bool(self.ID)

    def getSetting(self,sid):
        default = self.settings.get(sid)
        value = self.data.get(sid)
        try:
            return type(default)(value)
        except:
            pass
        return default    

    def setSetting(self,sid,value):
        self.data[sid] = value

    def getShot(self,bullet):
        ID = bullet.get('iden')
        modified = bullet.get('modified')
        if modified > self.mostRecent: self.mostRecent = modified
        if self._bulletHoles.get(ID) >= modified: return
        self._bulletHoles[ID] = modified
        bType = bullet.get('type')
        if bType == 'link':
            return self.link(bullet)
        elif bType == 'note':
            return self.note(bullet)
        elif bType == 'file':
            return self.file(bullet)
        elif bType == 'address':
            return self.address(bullet)
        elif bType == 'list':
            return self.list(bullet)
        else:
            return self.unhandled(bullet)
        
    def link(self,data):
        self.unhandled(data)

    def note(self,data):
        self.unhandled(data)
    
    def file(self,data):
        self.unhandled(data)
        
    def address(self,data):
        self.unhandled(data)
        
    def list(self,data):
        self.unhandled(data)

    def unhandled(self,data):
        if DEBUG: LOG('NOT_IMPL: {0}'.format(data))

class Client:
    baseURL = 'https://api.pushbullet.com/v2/{0}'
    
    def __init__(self,token):
        self.token = token

    def pushes(self,modified_after=0):
        params = {'modified_after':modified_after and '{0:10f}'.format(modified_after) or '0'}
        req = requests.get(self.baseURL.format('pushes'),auth=(self.token,''),params=params)
        try:
            data = req.json()
        except:
            if DEBUG:
                print repr(req.text)
            else:
                LOG('JSON decode error')
            
        return data.get('pushes')

    def modifyPush(self,data):
        requests.post(self.baseURL.format('pushes/{0}'.format(data.get('iden'))),auth=(self.token,''),data=json.dumps(data),headers={'Content-type': 'application/json', 'Accept': 'text/plain'})

    def dismissPush(self,ID):
        if isinstance(ID,dict): ID = ID.get('iden')
        requests.post(self.baseURL.format('pushes/{0}'.format(ID)),auth=(self.token,''),data={'dismissed':'true'})
        
    def deletePush(self,ID):
        if isinstance(ID,dict): ID = ID.get('iden')
        requests.delete(self.baseURL.format('pushes/{0}'.format(ID)),auth=(self.token,''))
        
    def getDevicesList(self):
        req = requests.get(self.baseURL.format('devices'),auth=(self.token,''))
        data = req.json()
        if 'error' in data:
            LOG(data['error'])
            raise PushbulletException(data['error'])
        return data.get('devices')

    def addDevice(self,device):
        if device.ID: return
        req = requests.post(    self.baseURL.format('devices'),
                                auth=(self.token,''),
                                data={'nickname':device.name,'type':device.type,'model':device.model,'manufacturer':device.manufacturer}
        )
        data = req.json()
        if 'error' in data:
            LOG(data['error'])
            raise PushbulletException(data['error'])
        device.ID = data.get('iden')
        return True

    def updateDevice(self,device,**kwargs):
        assert device.ID != None, 'Invalid Device'
        req = requests.post(self.baseURL.format('devices/{0}'.format(device.ID)),auth=(self.token,''),data=kwargs)
        data = req.json()
        if 'error' in data:
            LOG(data['error'])
            raise PushbulletException(data['error'])
        device.name = data.get('nickname',device.name)
        return True

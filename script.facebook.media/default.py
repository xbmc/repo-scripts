#Facebook Media

import os,urllib,urllib2,time
import sys, traceback, threading

from xml.sax.saxutils import unescape as xml_unescape
import threadpool

import xbmc, xbmcaddon, xbmcgui #@UnresolvedImport

#import traceback
import facebook

from facebook import GraphAPIError, GraphWrapAuthError

__author__ = 'Rick Phillips (ruuk)'
__addon__ = xbmcaddon.Addon(id='script.facebook.media')
__version__ = __addon__.getAddonInfo('version')
__lang__ = __addon__.getLocalizedString

THEME = 'Default'
CURRENT_SKIN = 'skin.confluence'

ACTION_MOVE_LEFT      = 1
ACTION_MOVE_RIGHT     = 2
ACTION_MOVE_UP        = 3
ACTION_MOVE_DOWN      = 4
ACTION_PAGE_UP        = 5
ACTION_PAGE_DOWN      = 6
ACTION_SELECT_ITEM    = 7
ACTION_HIGHLIGHT_ITEM = 8
ACTION_PARENT_DIR_OLD = 9
ACTION_PARENT_DIR     = 92
ACTION_PREVIOUS_MENU  = 10
ACTION_SHOW_INFO      = 11
ACTION_PAUSE          = 12
ACTION_STOP           = 13
ACTION_NEXT_ITEM      = 14
ACTION_PREV_ITEM      = 15
ACTION_SHOW_GUI       = 18
ACTION_PLAYER_PLAY    = 79
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_CONTEXT_MENU   = 117

import locale
loc = locale.getdefaultlocale()
print loc
ENCODING = loc[1] or 'utf-8'

def ENCODE(string):
    try:
        return string.encode('utf-8','replace')
    except:
        LOG('ENCODE() - Failed to encode to UTF-8')

    try:
        return string.encode('latin','replace')
    except:
        LOG('ENCODE() - Failed to encode to latin')

    try:
        return string.decode(ENCODING,'replace').encode('utf-8','replace')
    except:
        LOG('ENCODE() - Failed to encode to UTF-8 (alt-method) - using repr()')
        ret = repr(string)
        if ret.startswith('u'): ret = ret[1:]
        return ret[1:-1]

def DONOTHING(text):
    return text

def LOG(message):
    print 'FACEBOOK MEDIA: %s' % ENCODE(str(message))

LOG('Version: ' + __version__)

def ERROR(message):
    LOG(message)
    traceback.print_exc()
    return str(sys.exc_info()[1])

##############################################################################################
## Password handling
##############################################################################################
#import passwordStorage  # @UnresolvedImport
#
#def getPassword(user_pass_key,username=''):
#    if username:
#        ask_msg = ' [B]Facebook[/B] password for %s: ' % username
#        password = passwordStorage.retrieve(user_pass_key,ask_msg=ask_msg)
#    else:
#        password = passwordStorage.retrieve(user_pass_key,ask_on_fail=False)
#    if password: savePassword(user_pass_key,password)
#    return password or ''
#
#def savePassword(user_pass_key,password):
#    passwordStorage.store(user_pass_key,password,only_if_unlocked=True)
#    if __addon__.getSetting(user_pass_key): __addon__.setSetting(user_pass_key,'') #Just to make sure the password is not lingering here
#    return passwordStorage.encrypted

#############################################################################################

class FacebookUser:
    def __init__(self,uid):
        self.id = uid
        self.email = __addon__.getSetting('login_email_%s' % uid)
        self._password = None
        self.token = __addon__.getSetting('token_%s' % uid)
        self.pic = __addon__.getSetting('profile_pic_%s' % uid)
        self.username = __addon__.getSetting('username_%s' % uid)

    def resetPassword(self):
        self._password = None

    def password(self):
#        if self._password: return self._password
#        self._password = getPassword('login_pass_%s' % self.id,username=self.username)
#        return self._password
        return None

    def updateToken(self,token):
        self.token = token
        __addon__.setSetting('token_%s' % self.id,str(token))

    def changePassword(self):
        password = doKeyboard(__lang__(30048),hidden=True)
        if not password or password == self._password: return
        self._password = password
        #savePassword('login_pass_{0}'.format(self.id), password)

class WindowState:
    def __init__(self):
        self.items = None
        self.listIndex = 0
        self.settings = {}

class BaseWindow(xbmcgui.WindowXML):
    def __init__( self, *args, **kwargs):
        self.oldWindow = None
        xbmcgui.WindowXML.__init__( self )

    def doClose(self):
        self.session.window = self.oldWindow
        self.close()

    def onInit(self):
        self.setSessionWindow()

    def onFocus( self, controlId ):
        self.controlId = controlId

    def setSessionWindow(self):
        self.oldWindow = self.session.window
        self.session.window = self

    def onAction(self,action):
        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            self.doClose()
            return True
        else:
            return False

class MainWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.session = None
        BaseWindow.__init__( self, *args, **kwargs )

    def onInit(self):
        if self.session:
            self.session.window = self
        else:
            try:
                self.session = FacebookSession(self)
                if not self.session.start():
                    self.doClose()
                    return
                #self.getControl(120).selectItem(2)
            except:
                ERROR('Unhandled Error')
                self.close()


    def onClick( self, controlID ):
        if controlID == 120:
            self.session.menuItemSelected(select=True)
        elif controlID == 125:
            self.session.optionMenuItemSelected()
        elif controlID == 128:
            self.session.photovideoMenuSelected()

    def onAction(self,action):
        if self.getFocusId() == 119:
            self.setFocusId(120)
            if action.getId() == ACTION_MOVE_DOWN:
                self.session.menuItemDeSelected()
            elif action.getId() == ACTION_PREVIOUS_MENU:
                self.session.menuItemDeSelected(prev_menu=True)
        if self.getFocusId() == 118:
            self.setFocusId(120)
        elif self.getFocusId() == 120:
            #print action.getId()
            if self.session.progressVisible: return
            if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PARENT_DIR_OLD:
                self.session.menuItemDeSelected(prev_menu=True)
            elif action.getId() == ACTION_PREVIOUS_MENU:
                self.session.menuItemDeSelected(prev_menu=True)
            elif action.getId() == ACTION_MOVE_UP:
                self.session.menuItemSelected()
            else:
                self.session.doNextPrev()

        elif self.getFocusId() == 125:
            if action.getId() == ACTION_PREVIOUS_MENU:
                self.doClose()
        elif self.getFocusId() == 128:
            if  action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU or action.getId() == ACTION_PARENT_DIR_OLD:
                self.setFocusId(120)
        elif self.getFocusId() == 138:
            if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU or action.getId() == ACTION_MOVE_LEFT or action.getId() == ACTION_MOVE_RIGHT  or action.getId() == ACTION_PARENT_DIR_OLD:
                self.setFocusId(128)
        elif self.getFocusId() == 160:
            if action.getId() == ACTION_PREVIOUS_MENU:
                self.session.cancelProgress()

class AuthWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.session = kwargs.get('session')
        self.email = kwargs.get('email')
        self.password = kwargs.get('password')
        self.initialized = False
        self.returnValue = None
        BaseWindow.__init__( self, *args, **kwargs )

    def onInit(self):
        BaseWindow.onInit(self)
        if self.initialized: return
        self.initialized = True
        token = self.session.addUser(self.email, self.password)
        self.returnValue = token

    def onFocus( self, controlId ):
        self.controlId = controlId

    def onClick( self, controlID ):
        pass

    def onAction(self,action):
        BaseWindow.onAction(self, action)

class StoppableThread(threading.Thread):
    def __init__(self,group=None, target=None, name=None, args=(), kwargs={}):
        self._stop = threading.Event()
        threading.Thread.__init__(self,group=group, target=target, name=name, args=args, kwargs=kwargs)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class SlideshowTagsWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.session = kwargs.get('session')
        self.photos = kwargs.get('photos',[''])
        self.current_index = kwargs.get('index',0)
        self.doSlideshow = kwargs.get('slideshow',False)
        self.slideshowThread = None
        self.closed = False
        self.slideInterval = self.session.getSetting('slideshow_interval', 5)
        BaseWindow.__init__( self, *args, **kwargs )

    def onInit(self):
        self.getControl(160).setVisible(False)
        BaseWindow.onInit(self)
        self.session.window = self
        self.showPhoto()
        if not self.doSlideshow:
            self.getControl(150).setAnimations([('conditional','effect=fade start=100 end=0 time=400 delay=2000 condition=Control.IsVisible(150)')])
            self.setFocusId(150)
        if self.doSlideshow: self.startSlideshow()

    def onFocus( self, controlId ):
        self.controlId = controlId

    def onClick( self, controlID ):
        pass

    def onAction(self,action):
        BaseWindow.onAction(self, action)
        if action.getId() == ACTION_MOVE_LEFT:
            self.prevPhoto()
        elif action.getId() == ACTION_MOVE_RIGHT:
            self.nextPhoto()
        elif action.getId() == ACTION_PLAYER_PLAY:
            if self.slideshowThread:
                self.stopSlideshow()
            else:
                self.startSlideshow()
        elif action.getId() == ACTION_STOP:
            self.stopSlideshow()
        elif action.getId() == ACTION_CONTEXT_MENU:
            self.session.showPhotoDialog(self.currentPhoto().source(''))
        else:
            self.resetSlideshow()
            self.getControl(150).setAnimations([('conditional','effect=fade start=100 end=0 time=400 delay=2000 condition=Control.IsVisible(150)')])
            self.setFocusId(150)

    def doClose(self):
        self.closed = True
        self.stopSlideshow()
        BaseWindow.doClose(self)

    def startSlideshow(self):
        if self.slideshowThread: return
        LOG('Starting Slideshow')
        self.showNotification(__lang__(30054))
        self.slideshowThread = threading.Timer(self.slideInterval, self.triggerNextFromThread)
        self.slideshowThread.start()

    def stopSlideshow(self):
        if self.slideshowThread:
            LOG('Stopping Slideshow')
            self.showNotification(__lang__(30055))
            self.slideshowThread.cancel()
            self.slideshowThread = None

    def triggerNextFromThread(self):
        xbmc.executebuiltin('Action(Right)')

    def currentPhoto(self):
        return self.photos[self.current_index]

    def resetSlideshow(self):
        if self.slideshowThread:
            if self.closed: return #Probabaly not necessary, but just in case...
            if self.slideshowThread: self.slideshowThread.cancel()
            self.slideshowThread = threading.Timer(self.slideInterval, self.triggerNextFromThread)
            self.slideshowThread.start()
            return True
        else:
            return False

    def nextPhoto(self):
        self.resetSlideshow()
        self.current_index += 1
        if self.current_index >= len(self.photos):
            self.current_index = 0
        self.showPhoto()

    def prevPhoto(self):
        self.resetSlideshow()
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = len(self.photos) - 1
        self.showPhoto()

    def scale(self,w, h, x, y, maximum=True):
        nw = y * w / h
        nh = x * h / w
        if maximum ^ (nw >= x):
                return nw or 1, y
        return x, nh or 1

    def showPhoto(self):
        photo = self.currentPhoto()
        width = int(photo.width(0))
        height = int(photo.height(0))
        if not width or not height: return
        tags = photo.tags()
        source = photo.source('')

        window_w = self.getWidth()
        window_h = self.getHeight()

        image_win_w, image_win_h = self.scale(width,height,window_w,window_h)

        w_aspect = window_w/float(window_h)
        aspect = width/float(height)
        x=0
        y=0
        #LOG('SlideshowTags Window Width: %s - Height: %s' % (window_w,window_h))
        if aspect < w_aspect:
            wmod = int((1280*image_win_w)/window_w)
            hmod = 720
            x = int((1280*((window_w - image_win_w)/2))/window_w)
        else:
            wmod = 1280
            hmod = int((720*image_win_h)/window_h)
            y = int((720*((window_h - image_win_h)/2))/window_h)

        box_len = 200
        box_off = box_len/2
        #LOG('SlideshowTags Image Location X: %s - Y: %s' % (x,y))
        self.getControl(150).setPosition(x,y)
        image = self.getControl(101)
        #image.setWidth(wmod)
        #image.setHeight(hmod)
        #image.setPosition(x,y)
        image.setImage(source)

        base_gcid = 400
        base_lcid = 500
        base_lgcid = 200
        tag_count = 0
        if tags: tag_count = len(tags)
        for idx in range(0,20):
            group = self.getControl(base_gcid + idx)
            label = self.getControl(base_lcid + idx)
            labelgroup = self.getControl(base_lgcid + idx)
            if idx < tag_count:
                tag = tags[idx]
                tag_name = tag.name('')
                tag_x = int(wmod * (float(tag.x(0))/100)) - box_off
                tag_y = int(hmod * (float(tag.y(0))/100)) - box_off
                if tag_y + 245 > 720:
                    labelgroup.setPosition(-50,-45)
                else:
                    labelgroup.setPosition(-50,205)
                group.setPosition(tag_x,tag_y)
                label.setLabel(tag_name)
                group.setEnabled(True)
            else:
                group.setPosition(-300,-300)
                label.setLabel('')
                group.setEnabled(False)

    def showNotification(self,notice):
        self.getControl(161).setLabel(notice)
        self.getControl(160).setAnimations([('conditional','effect=fade start=100 end=0 time=400 delay=2000 condition=Control.IsVisible(160)')])
        self.getControl(160).setVisible(True)
        self.getControl(160).setAnimations([('conditional','effect=fade start=100 end=0 time=400 delay=2000 condition=Control.IsVisible(160)')])

class ListItemProxy:
    def __init__(self):
        self.label = ''
        self.label2 = ''
        self.icon = ''
        self.thumb = ''
        self.path = ''
        self.properties = {}
        self.infos = {}

    def getLabel(self): return self.label
    def getLabel2(self): return self.label2
    def isSelected(self): return False
    def select(self,selected): pass
    def setIconImage(self,icon): self.icon = icon
    def setInfo(self,itype, infoLabels): self.infos[itype] = infoLabels
    def setLabel(self,label): self.label = label
    def setLabel2(self,label2): self.label2 = label2
    def setPath(self,path): self.path = path
    def setProperty(self,key, value): self.properties[key] = value
    def setThumbnailImage(self,thumb): self.thumb = thumb

    def asListItem(self):
        item = xbmcgui.ListItem()
        item.setLabel(self.label)
        item.setLabel2(self.label2)
        item.setIconImage(self.icon)
        item.setThumbnailImage(self.thumb)
        item.setPath(self.path)
        for k,v in self.properties.items():
            item.setProperty(k,v)
        return item


class FacebookSession:
    def __init__(self,window=None):
        self.window = window
        self.graph = None
        self._permissions = None
        self.states = []
        self.current_state = None
        self.paging = []
        self.cancel_progress = False
        self.progressVisible = False
        self.progAutoCt = 0
        self.progAutoTotal = 0
        self.progAutoMessage = ''
        self.lastItemNumber = 0
        self.CACHE_PATH = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')),'cache')
        if not os.path.exists(self.CACHE_PATH): os.makedirs(self.CACHE_PATH)
        self.newUserCache = None
        self.currentUser = None
        self.setFriend()

        self.imageURLCache = {}
        self.loadImageURLCache()

        self.stateSettings = (    'current_friend_name',
                                'current_user_pic',
                                'current_user_name',
                                'last_item_name',
                                'current_nav_path')

        self.setSetting('current_user_pic','facebook-media-icon-generic-user.png')
        self.setSetting('current_friend_name','')
        self.setSetting('progress','')
        self.setSetting('last_item_name',__lang__(30009))
        self.setSetting('current_nav_path','')

        self.endProgress()

    def start(self,noApp=False):
        user = self.getCurrentUser()
        if not user:
            if not self.openAddUserWindow(): return False
            user = self.getCurrentUser()

        self.graph = newGraph(  user.email,
                                user.password(),
                                user.id,
                                user.token,
                                self.newTokenCallback,
                                self.credentialsCallback
        )

        #print user.username
        #print user.email
        if noApp: return
        self.loadOptions()
        self.CATEGORIES()
        self.setCurrentState()
        self.setUserDisplay()
        return True

    def credentialsCallback(self):
        reAuth = xbmcgui.Dialog().yesno('Choose','Login Expired!','Re-authorize or enter email/pass ','to allow auto-fetching a new token?','Enter E/P','Re-auth')
        if reAuth:
            token = openWindow('auth',session=self)
            return {'token':token}
        email = doKeyboard(__lang__(30047),default='')
        if not email:
            return
        password = doKeyboard(__lang__(30048),default='',hidden=True)
        if not password:
            return
        return {'email':email,'password':password}

    def newTokenCallback(self,token):
        self.token = token
        if self.currentUser: self.currentUser.updateToken(token)

    def loadOptions(self):
        items = []
        for user in self.getUsers():
            item = xbmcgui.ListItem()
            item.setLabel(user.username)
            item.setThumbnailImage(user.pic)
            item.setProperty('uid',user.id)
            items.append(item)
        options = [ ('add_user','facebook-media-icon-adduser.png',__lang__(30038),'data'),
                    ('remove_user','facebook-media-icon-removeuser.png',__lang__(30039),'data')
#                    ('reauth_user','facebook-media-icon-reauth-user.png',__lang__(30040),'data'),
#                    ('extauth_user','facebook-media-icon-reauth-user.png','Extend Authorization','data')
        ]
        for action,icon,label,data in options:
            item = xbmcgui.ListItem()
            item.setThumbnailImage(icon)
            item.setLabel(label)
            item.setProperty('action',action)
            item.setProperty('data',data)
            items.append(item)
        olist = self.window.getControl(125)
        olist.reset()
        olist.addItems(items)

    def openAddUserWindow(self,email='',password=''):
        openWindow('auth',session=self,email=email,password=password)
        return self.getSetting('has_user') == 'true'

    def saveState(self):
        state = self.createCurrentState()
        self.states.append(state)

    def getListItems(self,alist):
        items = []
        for x in range(0,alist.size()):
            items.append(alist.getListItem(x))
        return items

    def createCurrentState(self,items=None):
        ilist = self.window.getControl(120)
        state = WindowState()
        if not items:
            items = self.getListItems(ilist)
            state.listIndex = ilist.getSelectedPosition()
        storageList = xbmcgui.ControlList(-100,-100,80,80)
        storageList.addItems(items)
        state.items = storageList
        for sett in self.stateSettings: state.settings[sett] = self.getSetting(sett)
        return state

    def setCurrentState(self,items=None):
        self.current_state = self.createCurrentState(items)

    def popState(self,clear=False):
        if not self.states: return False
        state = self.states.pop()
        if not clear: self.restoreState(state)
        del state.items
        del state
        return True

    def restoreState(self,state,onload=False):
        if not state:
            LOG('restoreState() - No State')
            return
        for sett in self.stateSettings: self.clearSetting(sett)
        for sett in self.stateSettings: self.setSetting(sett,state.settings.get(sett,''))
        ilist = self.window.getControl(120)
        self.fillList(self.getListItems(state.items))
        ilist.selectItem(state.listIndex)
        self.current_state = state
        self.setFriend(restore=True)

    def reInitState(self,state=None):
        if not state: state = self.current_state
        self.restoreState(state)
        self.setPathDisplay()

    def getRealURL(self,url):
        return url

        if not url: return url
        for ct in range(1,4):
            try:
                req = urllib2.urlopen(url)
                break
            except:
                LOG('getRealURL(): ATTEMPT #%s FAILED' % ct)
        else:
            return url
        return req.geturl()

    def setListFocus(self,nextprev,conn_obj):
        ilist = self.window.getControl(120)
        if nextprev == 'prev':
            if conn_obj.next: self.jumpToListEnd(ilist,-1)
            else: self.jumpToListEnd(ilist)
        else:
            if conn_obj.previous: ilist.selectItem(1)

    def jumpToListEnd(self,ilist,offset=0):
        idx = len(self.getListItems(ilist)) - 1
        idx += offset
        if idx < 0: idx = 0
        ilist.selectItem(idx)

    def getPagingItem(self,nextprev,url,itype,current_url='',uid=''):
        item = xbmcgui.ListItem()
        item.setThumbnailImage('facebook-media-icon-%s.png' % nextprev)
        item.setProperty('hidetube','true')
        item.setProperty('category','paging')
        item.setProperty('uid',uid)
        item.setProperty('paging',DONOTHING(url))
        item.setProperty('ispagingitem','yes')
        item.setProperty('nextprev',nextprev)
        item.setProperty('media_type',itype)
        if nextprev == 'next': item.setProperty('from_url',current_url)
        item.setProperty('previous',self.getSetting('last_item_name'))
        return item

    def fillList(self,items):
        ilist = self.window.getControl(120)
        ilist.reset()
        ilist.addItems(items)

        #Fix for unpredictable Boxee wraplist behavior
#        if len(items) < 6:
#            newitems = []
#            for y in items: newitems.append(y)
#            mult = 6/len(items)
#            if mult < 2: mult = 2
#            for x in range(1,mult): #@UnusedVariable
#                for y in items: newitems.append(y)
#            ilist.addItems(newitems)
#        else:
#            ilist.addItems(items)

    def permission(self,perm):
        if not self._permissions:
            self._permissions = {}
            for p in self.graph.getObject('me').connections.permissions():
                self._permissions[p.permission()] = p.status() == 'granted' and True or False
            LOG('Permissons: {0}'.format( ', '.join([p for p in self._permissions.keys() if self._permissions[p]])))
        return self._permissions.get(perm,False)

    def refreshCATEGORIES(self):
        self.setSetting('last_item_name',__lang__(30009))
        self.CATEGORIES()

    def CATEGORIES(self,item=None):
        LOG("CATEGORIES - STARTED")
        window = self.window
        uid = 'me'
        friend_thumb = None
        if item:
            self.saveState()
            uid = item.getProperty('fid')
            friend_thumb = item.getProperty('friend_thumb')

        items = []

        if uid == 'me':
            cids = ('albums','videos','friends','photosofme','videosofme')
            cats = (__lang__(30001),__lang__(30002),__lang__(30003),__lang__(30004),__lang__(30005))
        else:
            cids = ('albums','videos','photosofme','videosofme')
            cats = (__lang__(30001),__lang__(30002),__lang__(30006),__lang__(30007))

        for cat,cid in zip(cats,cids):
            item = xbmcgui.ListItem()
            #item.setContentType("")
            item.setLabel(cat)
            item.setProperty('category',cid)
            item.setProperty('uid',uid)
            item.setThumbnailImage('facebook-media-icon-%s.png' % cid)
            if friend_thumb: item.setProperty('friend_thumb',friend_thumb)
            else: item.setProperty('friend_thumb','facebook-media-icon-%s.png' % cid)
            item.setProperty('background','')
            item.setProperty('previous',self.getSetting('last_item_name') or 'ERROR')
            items.append(item)

        self.fillList(items)
        window.setFocusId(120)
        self.setCurrentState(items)
        self.setSetting('last_item_name',__lang__(30008))
        LOG("CATEGORIES - STOPPED")

    def updateImageCache(self,ID):
        tn = "https://graph.facebook.com/"+ID+"/picture?access_token=" + self.graph.access_token
        tn_url = self.getRealURL(tn).replace('https://','http://')
        self.imageURLCache[ID] = tn_url
        return tn_url

    def sharePhoto(self,url):
        LOG('Sharing Photo')
        try:
            import ShareSocial #@UnresolvedImport
        except:
            return

        share = ShareSocial.getShare('script.facebook.media','image')
        share.content = url
        share.name = 'Facebook Media'
        share.title = 'Facebook Media Photo'
        share.share()

    def showPhotoDialog(self,url):
        options = []
        optionIDs = []
        try:
            import ShareSocial #@UnresolvedImport
            if ShareSocial.shareTargetAvailable('image','script.facebook.media'):
                options.append(__lang__(30056))
                optionIDs.append('share')
        except:
            pass
        if not options:
            options.append(__lang__(30058))
            optionIDs.append('NOOPTIONS')
        idx = xbmcgui.Dialog().select(__lang__(30057),options)
        if idx < 0:
            return
        else:
            option = optionIDs[idx]
        if option == 'share':
            self.sharePhoto(url)

    def ALBUMS(self,item):
        LOG('ALBUMS - STARTED')
        uid = item.getProperty('uid')
        paging = item.getProperty('paging')
        nextprev = item.getProperty('nextprev')
        fromUrl = item.getProperty('from_url')

        if not paging: self.saveState()

        self.startProgress(__lang__(30016))

        items = []
        try:
            self.graph.withProgress(self.updateProgress,0.5,100,__lang__(30010))
            if paging:
                if fromUrl:
                    self.paging.append(fromUrl)
                else:
                    if self.paging: paging = self.paging.pop()
                albums = self.graph.urlRequest(paging)
            else:
                self.paging = []
                albums = self.graph.getObject(uid).connections.albums()

            cids = []
            for a in albums:
                cid = a.cover_photo()
                if cid:
                    cids.append(cid)
            cover_objects = {}
            if cids: cover_objects = self.graph.getObjects(cids)

            if albums.previous:
                item = self.getPagingItem('prev', albums.previous, 'albums',uid=uid)
                items.append(item)

            updates = []
            for a in albums:
                cover = None
                acp = a.cover_photo()
                if acp: cover = cover_objects.get(acp)
                if cover:
                    tn_url = cover.picture('')
                    self.imageURLCache[a.id] = tn_url
                else:
                    if not a.id in self.imageURLCache:
                        updates.append(a.id)
            if updates:
                self.startProgress(auto_ct_start=len(updates),auto_total=len(updates)*2,auto_message=__lang__(30011))
                self.doThreadedOperations(self.updateImageCache, updates, self.updateProgress)

#            total = len(albums) or 1
#            ct = 0
#            offset = 50
#            modifier = 50.0 / total
            for a in albums:
#                ct += 1
                cover = None
                acp = a.cover_photo()
                if acp: cover = cover_objects.get(acp)
                if cover:
                    tn_url = cover.picture('')
                    src_url = cover.source('')
                else:
                    tn_url = self.imageURLCache[a.id]
                    src_url = tn_url.replace('_a.','_n.')
#                if not self.updateProgress(int(ct*modifier)+offset,100,'ALBUM %s OF %s' % (ct,total)):
#                    return

                #aname = a.get('name','').encode('ISO-8859-1','replace')
                aname = DONOTHING(a.name(''))

                item = xbmcgui.ListItem()
                item.setLabel(aname)
                item.setThumbnailImage(tn_url)
                item.setProperty('image0',src_url)
                item.setProperty('album',a.id)
                item.setProperty('uid',uid)
                item.setProperty('category','photos')
                item.setProperty('previous',self.getSetting('last_item_name') or 'ERROR')
                items.append(item)

            if albums.next:
                item = self.getPagingItem('next', albums.next, 'albums', paging,uid=uid)
                items.append(item)

            self.saveImageURLCache()

            if items:
                self.fillList(items)
                self.setListFocus(nextprev, albums)
                self.setCurrentState(items)
        finally:
            self.endProgress()

        if not items: self.noItems(__lang__(30028))

        LOG('ALBUMS - STOPPED')

    def FRIENDS(self,uid='me'):
        if not self.permission('user_friends'):
            if not self.extendAuthorization(ask=True,permission='user_friends'):
                return

        LOG('FRIENDS - STARTED')
        self.saveState()

        self.startProgress(__lang__(30017))
        self.graph.withProgress(self.updateProgress,0.5,100,__lang__(30010))

        items = []
        try:
            friends = self.graph.getObject(uid).connections.friends(fields="picture,name")
            srt = []
            show = {}
            for f in friends:
                name = f.name('')
                s = name.rsplit(' ',1)[-1] + name.rsplit(' ',1)[0]
                srt.append(s)
                show[s] = f
                srt.sort()
            total = len(srt) or 1
            ct=0
            offset = 50
            modifier = 50.0 / total
            for s in srt:
                fid = show[s].id
                tn_url = show[s].picture('').get('url','').replace('_q.','_n.')
                ct+=1
                self.updateProgress(int(ct*modifier)+offset, 100, __lang__(30012) % (ct,total))

                #if fid in self.imageURLCache:
                #    tn_url = self.imageURLCache[fid]
                #else:
                #    tn = "https://graph.facebook.com/"+fid+"/picture?type=large&access_token=" + self.graph.access_token
                #    tn_url = self.getRealURL(tn)
                #    self.imageURLCache[fid] = tn_url
                name = show[s].name('')
                item = xbmcgui.ListItem()
                item.setLabel(DONOTHING(name))
                item.setThumbnailImage(DONOTHING(tn_url))
                item.setProperty('friend_thumb',DONOTHING(tn_url))
                item.setProperty('uid',uid)
                item.setProperty('fid',DONOTHING(fid))
                item.setProperty('category','friend')
                item.setProperty('previous',self.getSetting('last_item_name'))
                items.append(item)

            self.saveImageURLCache()
            self.endProgress()
        except GraphAPIError,e:
            self.endProgress()
            if not '#604' in str(e): raise
            LOG("CAN'T ACCESS USER'S FRIENDS")
        except:
            self.endProgress()
            raise

        if items:
            self.fillList(items)
            self.setCurrentState(items)
        else:
            self.noItems(__lang__(30029))

        LOG("FRIENDS - STOPPED")

    def PHOTOS(self,item):
        LOG("PHOTOS - STARTED")
        aid = item.getProperty('album')
        uid = item.getProperty('uid')
        paging = item.getProperty('paging')
        nextprev = item.getProperty('nextprev')
        fromUrl = item.getProperty('from_url')
        if item.getProperty('category') == 'photosofme': aid = uid

        if not paging: self.saveState()

        self.startProgress(__lang__(30018))
        self.graph.withProgress(self.updateProgress,0.5,100,__lang__(30010))

        items = []
        try:
            if paging:
                if fromUrl:
                    self.paging.append(fromUrl)
                else:
                    if self.paging: paging = self.paging.pop()
                photos = self.graph.urlRequest(paging)
            else:
                self.paging = []
                photos = self.graph.getObject(aid).connections.photos(limit=self.getSetting('photo_limit',100))

            tot = len(photos) or 1

            ct=0
            offset = 50
            modifier = 50.0/tot

            if uid == 'me': uid = self.currentUser.id

            if photos.previous:
                items.append(self.getPagingItem('prev', photos.previous, 'photos', paging,uid=uid))

            for p in photos:
                tn = p.picture('') + '?fix=' + str(time.time()) #why does this work? I have no idea. Why did I try it. I have no idea :)
                #tn = re.sub('/hphotos-\w+-\w+/\w+\.\w+/','/hphotos-ak-snc1/hs255.snc1/',tn) # this seems to get better results then using the random server
                item = xbmcgui.ListItem()
                item.setLabel(DONOTHING(self.removeCRLF(p.name(p.id))))
                source = DONOTHING(p.source())
                caption = self.makeCaption(p, uid)
                item.setPath(source)
                item.setProperty('source',source)
                item.setProperty('category','photovideo')
                item.setProperty('media_type','image')
                item.setProperty('hidetube','true')
                item.setLabel('')
                item.setProperty('image0',source)
                item.setThumbnailImage(DONOTHING(tn))
                item.setProperty('uid',uid)
                item.setProperty('id',DONOTHING(p.id))
                item.setProperty('caption',caption)
                if p.hasProperty('comments'): item.setProperty('comments','true')
                if p.hasProperty('tags'): item.setProperty('tags','true')
                item.setProperty('data',p.toJSON())
                item.setProperty('previous',self.getSetting('last_item_name'))
                items.append(item)
                ct += 1
                self.updateProgress(int(ct*modifier)+offset,100,message=__lang__(30013) % (ct,tot))

            if photos.next:
                items.append(self.getPagingItem('next', photos.next, 'photos', paging,uid=uid))
            if items:
                self.fillList(items)
                self.setListFocus(nextprev, photos)
                self.setCurrentState(items)
        except:
            err = ERROR("ERROR GETTING PHOTOS")
            xbmcgui.Dialog().ok(__lang__(30034),err)
        finally:
            self.endProgress()

        if not items: self.noItems(__lang__(30026),paging)

        LOG("PHOTOS - STOPPED")

    def VIDEOS(self,item):
        LOG("VIDEOS - STARTED")

        uploaded = False
        uid = item.getProperty('uid')
        paging = item.getProperty('paging')
        nextprev = item.getProperty('nextprev')
        fromUrl = item.getProperty('from_url')
        if item.getProperty('category') != 'videosofme': uploaded = True

        if not paging: self.saveState()

        self.startProgress(__lang__(30019))
        self.graph.withProgress(self.updateProgress,0.5,100,__lang__(30010))

        items = []
        try:
            if paging:
                if fromUrl:
                    self.paging.append(fromUrl)
                else:
                    if self.paging: paging = self.paging.pop()
                videos = self.graph.urlRequest(paging)
            else:
                self.paging = []
                if uploaded: videos = self.graph.getObject(uid).connections.videos__uploaded()
                else: videos = self.graph.getObject(uid).connections.videos()
            if videos.previous:
                item = self.getPagingItem('prev', videos.previous, 'videos',uid=uid)
                items.append(item)

            if uid == 'me': uid = self.currentUser.id

            total = len(videos) or 1
            ct=0
            offset = 50
            modifier = 50.0/total
            for v in videos:
                item = xbmcgui.ListItem()
                item.setProperty('ispagingitem','no')
                tn = v.picture('') + '?fix=' + str(time.time()) #why does this work? I have no idea. Why did I try it. I have no idea :)
                #tn = re.sub('/hphotos-\w+-\w+/\w+\.\w+/','/hphotos-ak-snc1/hs255.snc1/',tn)
                caption = self.makeCaption(v, uid)
                item.setPath(v.source(''))
                item.setProperty('source',v.source(''))
                item.setProperty('uid',uid)
                item.setProperty('id',DONOTHING(v.id))
                item.setProperty('category','photovideo')
                item.setProperty('media_type','video')
                item.setProperty('hidetube','true')
                item.setThumbnailImage(DONOTHING(tn))
                item.setProperty('image0',DONOTHING(tn))
                item.setProperty('caption',caption)
                if v.hasProperty('comments'): item.setProperty('comments','true')
                if v.hasProperty('tags'): item.setProperty('tags','true')
                item.setProperty('data',v.toJSON())
                item.setProperty('previous',self.getSetting('last_item_name'))
                items.append(item)
                ct+=1
                self.updateProgress(int(ct*modifier)+offset,100, __lang__(30014) % (ct,total))

            if videos.next:
                item = self.getPagingItem('next', videos.next, 'videos', paging,uid=uid)
                items.append(item)

            if items:
                self.fillList(items)
                self.setListFocus(nextprev, videos)
                self.setCurrentState(items)
        except:
            err = ERROR("ERROR GETTING VIDEOS")
            xbmcgui.Dialog().ok(__lang__(30034),err)
        finally:
            self.endProgress()

        if not items: self.noItems(__lang__(30027),paging)

        LOG("VIDEOS - STOPPED")

    def convertJSONText(self,text):
        return xml_unescape(urllib.unquote(text),{"&apos;": "'", "&quot;": '"'})

    def makeCaption(self,obj,uid):
        name = u''
        f_id = obj.from_({}).get('id','')
        if f_id != uid:
            name = obj.from_({}).get('name','') or u''
            if name: name = u'[COLOR FF55FF55]'+__lang__(30022) % name +u'[/COLOR][CR]'
        title = obj.name('')
        if title: title = u'[COLOR yellow]%s[/COLOR][CR]' % title
        caption = name + title + obj.description('')
        if not caption: return ''
        caption += '[CR] '
        return DONOTHING(self.convertJSONText(caption))

    def noItems(self,itype='items',paging=None):
        if not paging: self.popState(clear=True)
        message = __lang__(30023) % itype
        if paging: message = __lang__(30024) % itype
        xbmcgui.Dialog().ok(__lang__(30025), message)

    def saveImageURLCache(self):
        out = ''
        for k in self.imageURLCache:
            out += '%s=%s\n' % (k,self.imageURLCache[k])

        cache_file = os.path.join(self.CACHE_PATH,'imagecache')

        f = open(cache_file,"w")
        f.write(out)
        f.close()

    def loadImageURLCache(self):
        cache_file = os.path.join(self.CACHE_PATH,'facebook-media','imagecache')
        if not os.path.exists(cache_file): return

        f = open(cache_file,"r")
        data = f.read()
        f.close()

        for line in data.splitlines():
            k,v = line.split('=',1)
            self.imageURLCache[k] = v

#    def mediaNextPrev(self,np):
#        LOG("PHOTOS - %s" % np.upper())
#        item = self.window.getControl(120).getItem(0)
#        url = item.getProperty(np)
#        print "%s URL: %s" % (np.upper(),url)
#        if url:
#            if self.itemType(item) == 'image':
#                self.PHOTOS(url, isPaging=True)
#            else:
#                self.VIDEOS(url, isPaging=True)
#            if np == 'prev':
#                list = self.window.getControl(120)
#                idx = len(list.getItems()) - 1
#                if idx < 0: idx = 0
#                self.window.getControl(120).setFocusedItem(idx)

    def menuItemSelected(self,select=False):
        state_len = len(self.states)
        try:
            item = self.getFocusedItem(120)
            name = item.getLabel()

            cat = item.getProperty('category')
            uid = item.getProperty('uid') or 'me'

            if cat == 'friend':
                self.CATEGORIES(item)
                self.setFriend(name)
                self.setSetting('last_item_name',name)
                self.setPathDisplay()
                return
            else:
                if uid == 'me': self.setFriend()

            if cat == 'albums':
                self.ALBUMS(item)
            elif cat == 'photos':
                self.PHOTOS(item)
            elif cat == 'friends':
                self.FRIENDS(uid)
            elif cat == 'videos':
                self.VIDEOS(item)
            elif cat == 'photosofme':
                self.PHOTOS(item)
            elif cat == 'videosofme':
                self.VIDEOS(item)
            elif cat == 'photovideo':
                if not select:
                    if self.showPhotoMenu():
                        return
                self.setCurrentState()
                self.setFriend('')
                self.showMedia(item)
                self.setPathDisplay()
                return
            elif cat == 'paging':
                self.doNextPrev()
                return
            self.setSetting('last_item_name',name)
            self.setPathDisplay()
        except GraphWrapAuthError,e:
            if len(self.states) > state_len: self.popState()
            if e.type == 'RENEW_TOKEN_FAILURE':
                response = xbmcgui.Dialog().yesno(__lang__(30030), __lang__(30031),'','', __lang__(30032), __lang__(30033))
                if response:
                    self.openAddUserWindow(self.currentUser.email, self.currentUser.password())
            else:
                message = ERROR('UNHANDLED ERROR')
                xbmcgui.Dialog().ok(__lang__(30034),message)
        except:
            if len(self.states) > state_len: self.popState()
            message = ERROR('UNHANDLED ERROR')
            xbmcgui.Dialog().ok(__lang__(30034),message)

    def menuItemDeSelected(self,prev_menu=False):
        if not self.popState():
            if prev_menu:
                self.closeWindow()
                return
            else:
                self.window.setFocusId(125)
        self.setPathDisplay()

    def optionMenuItemSelected(self):
        LOG("OPTION ITEM SELECTED")
        item = self.getFocusedItem(125)
        self.window.setFocusId(120)
        uid = item.getProperty('uid')
        if uid:
            self.setCurrentUser(uid)
            self.refreshCATEGORIES()
        else:
            action = item.getProperty('action')
            if action == 'add_user':
                self.openAddUserWindow()
                self.loadOptions()
            elif action == 'remove_user':
                self.removeUserMenu()
            elif action == 'reauth_user':
                self.openAddUserWindow(self.currentUser.email, self.currentUser.password())
                self.currentUser.resetPassword()
            elif action == 'extauth_user':
                self.extendAuthorization()
            elif action == 'change_user_password':
                self.currentUser.changePassword()
                self.graph.setLogin(self.currentUser.email,self.currentUser.password())

    def extendAuthorization(self,ask=False,permission=None):
        if ask:
            yes = xbmcgui.Dialog().yesno('Extended Authorization','This action requires extended Facebook permissions','','Would you like to extend authorization?')
            if not yes: return False
        token = self.getAuthExtended(graph=self.graph)
        self.newTokenCallback(token)
        self._permissions = None
        if permission:
            return self.permission(permission)
        return True

    def photovideoMenuSelected(self):
        item = self.getFocusedItem(128)
        name = item.getProperty('name')
        itemNumber = int(item.getProperty('item_number'))
        if name == 'slideshow':
            self.window.setFocusId(120)
            self.setFriend()
            self.showImages(None,True)
        elif name == 'comments':
            self.doCommentDialog(itemNumber,item)
        elif name == 'likes':
            self.doLike(itemNumber,item)

    def doNextPrev(self):
        ilist = self.window.getControl(120)
        item = ilist.getSelectedItem()
        if not item: return
        if not item.getProperty('paging'): return
        LOG('PAGING: %s' % item.getProperty('nextprev'))
        self.setSetting('last_item_name',item.getProperty('previous'))
        if item.getProperty('media_type') == 'photos':         self.PHOTOS(item)
        elif item.getProperty('media_type') == 'videos':     self.VIDEOS(item)
        elif item.getProperty('media_type') == 'albums':     self.ALBUMS(item)

    def openSlideshowTagsWindow(self,photos,index,slideshow=False):
        openWindow('slideshow',session=self,photos=photos,index=index,slideshow=slideshow)

    def doCommentDialog(self,itemNumber,comment_item):
        if not self.permission('publish_actions'):
            if not self.extendAuthorization(ask=True,permission='publish_actions'): return
        comment = doKeyboard("Enter Comment",'',False)
        if not comment: return
        item = self.window.getControl(120).getListItem(int(itemNumber))
        pv_obj = self.graph.fromJSON(item.getProperty('data'))
        pv_obj.comment(comment)
        pv_obj = self.updateMediaItem(item,pv_obj)
        if comment_item:
            comments = pv_obj.comments()
            if comments:
                comments_string = ''
                for c in comments:
                    name = c.from_({}).get('name','')
                    comments_string += '[COLOR yellow]%s:[/COLOR][CR]%s[CR][CR]' % (name,c.message(''))
                comment_item.setProperty('data',comments_string)

    def doLike(self,itemNumber,like_item=None):
        if not self.permission('publish_actions'):
            if not self.extendAuthorization(ask=True,permission='publish_actions'): return
        item = self.window.getControl(120).getListItem(int(itemNumber))
        pv_obj = self.graph.fromJSON(item.getProperty('data'))
        pv_obj.like()
        pv_obj = self.updateMediaItem(item,pv_obj)
        if like_item:
            likes = pv_obj.connections.likes()
            if likes:
                likes_string = ''
                for l in likes:
                    likes_string += '[COLOR yellow]%s[/COLOR][CR]' % l.name('')
                like_item.setLabel(__lang__(30043) % len(likes))
                like_item.setProperty('data',likes_string)

    def updateMediaItem(self,item,pv_obj=None):
        if not pv_obj: pv_obj = self.graph.fromJSON(item.getProperty('data'))
        item.setProperty('data',pv_obj.updateData().toJSON())
        if pv_obj.hasProperty('comments'): item.setProperty('comments','true')
        if pv_obj.hasProperty('tags'): item.setProperty('tags','true')
        return pv_obj
        #items = self.window.getControl(120).getItems()
        #idx=0
        #for i in items:
        #    if i.getProperty('id') == item.getProperty('id'):
        #        break
        #    idx+=1
        #else:
        #    return
        #items[idx] = item
        #self.window.getControl(120).setItems(items)

    def showPhotoMenu(self):
        self.setCurrentState()
        items = []
        itemNumber = self.window.getControl(120).getSelectedPosition()
        item = self.getFocusedItem(120)
        pv_obj = self.graph.fromJSON(item.getProperty('data'))

        comments_string = ''
        comments = pv_obj.comments()
        if comments:
            for c in comments:
                name = c.from_({}).get('name','')
                comments_string += '[COLOR yellow]%s:[/COLOR][CR]%s[CR][CR]' % (name,c.message(''))

        likes_string = ''
        likes = pv_obj.connections.likes()
        if likes:
            for l in likes:
                likes_string += '[COLOR yellow]%s[/COLOR][CR]' % l.name('')

        items.append(self.createPhotoMenuItem('comments', __lang__(30041), __lang__(30042), comments_string, itemNumber))
        items.append(self.createPhotoMenuItem('likes', __lang__(30043) % len(likes), __lang__(30044), likes_string, itemNumber))

        if self.itemType(item) == 'image':
            items.append(self.createPhotoMenuItem('slideshow', __lang__(30045), __lang__(30046), '', itemNumber))
        self.window.getControl(128).reset()
        self.window.getControl(128).addItems(items)
        self.window.setFocusId(128)
        return True

    def createPhotoMenuItem(self,name,label,sublabel,data,itemNumber):
        item = xbmcgui.ListItem()
        item.setLabel(label)
        item.setProperty('sublabel',sublabel)
        item.setProperty('name',name)
        item.setProperty('item_number',str(itemNumber))
        item.setProperty('data',DONOTHING(data))
        return item


    def removeUserMenu(self):
        uids = self.getUserList()
        options = []
        for uid in uids: options.append(self.getSetting('username_%s' % uid))

        idx = xbmcgui.Dialog().select(__lang__(30037),options)
        if idx < 0:
            return
        else:
            uid = uids[idx]
            self.removeUser(uid)

    def removeUser(self,uid):
        self.removeUserFromList(uid)
        self.clearSetting('login_email_%s' % uid)
#        savePassword('login_pass_%s' % uid,'')
        self.clearSetting('token_%s' % uid)
        self.clearSetting('profile_pic_%s' % uid)
        self.clearSetting('username_%s' % uid)
        self.setSetting('current_user','')
        self.currentUser = None
        self.getCurrentUser()
        self.loadOptions()

    def setPathDisplay(self):
        path = []
        for state in self.states:
            path.append(state.settings.get('last_item_name') or '')
        path.append(self.getSetting('last_item_name') or '')
        path = ' : '.join(path[1:])
        self.window.getControl(195).setLabel(path)
        LOG('PATH - %s' % path)

    def setFriend(self,name='',restore=False):
        if restore:
            name = self.getSetting('current_friend_name')
        else:
            self.setSetting('current_friend_name',name)
        #if name:
        #    self.window.getControl(181).setLabel('Friend: ' + name)
        #else:
        #    self.window.getControl(181).setLabel('')

    def setUserDisplay(self):
        self.window.getControl(140).setImage(self.getSetting('current_user_pic',''))
        self.window.getControl(141).setLabel(self.getSetting('current_user_name','ERROR'))

    def startProgress(self,message='',auto_ct_start=0,auto_total=0,auto_message=''):
        self.progressVisible = True
        self.cancel_progress = False
        if not auto_ct_start:
            self.window.getControl(153).setWidth(1)
            self.window.getControl(152).setLabel(message)
        #self.window.getControl(150).setVisible(True)
        self.window.setFocusId(160)
        self.progAutoCt = auto_ct_start
        self.progAutoTotal = auto_total
        self.progAutoMessage = auto_message
        if auto_ct_start: self.updateProgress(auto_ct_start, auto_total, auto_message)

    def updateProgress(self,ct=0,total=0,message=''):
        if self.progAutoTotal:
            total = self.progAutoTotal
            self.progAutoCt+=1
            ct = self.progAutoCt
            message=self.progAutoMessage.replace('@CT',str(ct)).replace('@TOT',str(total))
        if not self.progressVisible: return True
        if self.cancel_progress: return False
        try:
            if ct < 0 or ct > total:
                LOG('PROGRESS OUT OF BOUNDS')
                return True
            width = int((ct / float(total)) * 500)
            window = self.window
            window.getControl(153).setWidth(width)
            window.getControl(152).setLabel(message)
        except:
            return False
        return True

    def endProgress(self):
        self.window.setFocusId(120)
        self.window.getControl(152).setLabel('')
        self.progressVisible = False
        #self.window.getControl(150).setVisible(False)

    def cancelProgress(self):
        LOG('PROGRESS CANCEL ATTEMPT')
        self.cancel_progress = True

    def showImagesOld(self,items):
        target_path = os.path.join(self.CACHE_PATH,'slideshow')
        if not os.path.exists(target_path): os.makedirs(target_path)
        self.clearDirFiles(target_path)
        urls = []
        for i in items:
            url = i.getProperty('source')
            if url: urls.append(url)
        self.downloadImagesThreaded(urls,target_path)
        xbmc.executebuiltin('SlideShow(%s)' % target_path)
        return

    def downloadImages(self,urls,target_path):
        total=len(urls)
        self.startProgress()
        try:
            ct=0
            for url in urls:
                self.updateProgress(ct, total, __lang__(30015) % (str(ct + 1),str(total)))
                target_file = os.path.join(target_path,str(ct) + str(time.time()) + '.jpg')
                self.getFile(url, target_file)
                ct+=1
        except:
            ERROR("downloadImages()")
            self.endProgress()

    def downloadImagesThreaded(self,urls,target_path):
        total=len(urls)
        self.startProgress(__lang__(30020),auto_total=total,auto_message=__lang__(30021))
        try:
            ct=0
            args = []
            for url in urls:
                target_file = os.path.join(target_path,str(ct) + str(time.time()) + '.jpg')
                args.append(([url,target_file],{}))
                ct+=1
            self.doThreadedOperations(self.getFile, args, self.updateProgress)
            self.endProgress()
        except:
            ERROR("downloadImagesThreaded()")
            self.endProgress()

    def doThreadedOperations(self,function,args,callback=None):
        pool = threadpool.ThreadPool(3,poll_timeout=0)
        requests = threadpool.makeRequests(function, args, callback)
        [pool.putRequest(req) for req in requests]
        pool.wait()
        pool.dismissWorkers(3, True)

    def clearDirFiles(self,filepath):
        if not os.path.exists(filepath): return
        for f in os.listdir(filepath):
            f = os.path.join(filepath,f)
            if os.path.isfile(f): os.remove(f)

    def showImages(self,item=None,slideshow=False):
        if not item: item = self.getFocusedItem(120)
        items = self.getListItems(self.window.getControl(120))
        ct=0
        idx = 0
        photos = []
        for it in items:
            if it.getProperty('id') == item.getProperty('id'): idx = ct
            photo = self.graph.fromJSON(it.getProperty('data'))
            if photo:
                photos.append(photo)
                ct+=1
        self.openSlideshowTagsWindow(photos,idx,slideshow)

    def showVideo(self,item):
        xbmc.executebuiltin('PlayMedia(%s)' % item.getProperty('source'))

    def showMedia(self,item):
        LOG('SHOWING MEDIA')
        if self.itemType(item) == 'image':
            self.showImages(item)
        else:
            self.showVideo(item)

    def itemType(self,item):
        return item.getProperty('media_type') or 'other'

    def getFocusedItem(self,list_id):
        lc = self.window.getControl(list_id)
        return lc.getSelectedItem()

    def removeCRLF(self,text):
        return " ".join(text.split())

    def makeAscii(self,name):
        return name.encode('ascii','replace')

    def getFile(self,url,target_file):
        if not url: return
        try:
            request = urllib2.urlopen(url)
            target_file = self.fixExtension(request.info().get('content-type',''),target_file)
        except:
            ERROR('ERROR: urlopen() in getFile() - URL: %s' % ENCODE(url))
            return ''
        f = open(target_file,"wb")
        f.write(request.read())
        f.close()
        return target_file

    def fixExtension(self,content_type,fn):
        if not 'image' in content_type: return
        ext = content_type.split('/',1)[-1]
        if not ext in 'jpeg,png,gif,bmp': return
        if ext == 'jpeg': ext = 'jpg'
        fn = os.path.splitext(fn)[0] + '.' + ext
        return fn

    def closeWindow(self):
        self.window.doClose()

    def addUser(self,email=None,password=None):
        try:
            LOG("ADD USER PART 1")
            self.window.getControl(101).setVisible(False)
#            lastEmail = self.getSetting('last_email', '')
#            lastPass = ''
#            if not email:
#                email = doKeyboard(__lang__(30047),default=lastEmail)
#            if not email:
#                self.closeWindow()
#                return
#            self.setSetting('last_email', email)
#            if lastEmail == email: lastPass = getPassword('last_password')
#            savePassword('last_password', '')
#            if not password:
#                password = doKeyboard(__lang__(30048),default=lastPass,hidden=True)
#            if not password:
#                self.closeWindow()
#                return
#            savePassword('last_password', password)
#            self.newUserCache = (email,password)
            self.window.getControl(102).setVisible(False)
            self.window.getControl(111).setVisible(False)
            token = self.getAuth()
            if token == None:
                self.closeWindow()
                self.newUserCache = None
                return
        except:
            message = ERROR('ERROR')
            xbmcgui.Dialog().ok(__lang__(30035),message)
            self.closeWindow()
            self.newUserCache = None
            return

        if not token:
            LOG('addUser(): Failed to get authorization token')
            xbmcgui.Dialog().ok(__lang__(30035),__lang__(30060))
            self.closeWindow()
            self.newUserCache = None
            return

        LOG("ADD USER PART 2")
        self.window.getControl(112).setVisible(False)
        self.window.getControl(121).setVisible(False)
        #email,password = self.newUserCache
        self.newUserCache = None
        graph = newGraph(email, password,token=token)
        #graph.getNewToken()
        self.window.getControl(122).setVisible(False)
        self.window.getControl(131).setVisible(False)
        #retry = False
        try:
            user = graph.getObject('me',fields='id,name,picture')
        #except facebook.GraphWrapAuthError,e:
        #    if e.type == 'RENEW_TOKEN_FAILURE':
        #        retry = True
        except:
            message = ERROR('ERROR')
            xbmcgui.Dialog().ok(__lang__(30035),message)
            self.closeWindow()
            self.newUserCache = None
            return token
#        if retry:
#            token = self.getAuth2(email,password)
#            try:
#                user = graph.getObject('me',fields='id,name,picture')
#            except:
#                message = ERROR('ERROR')
#                xbmcgui.Dialog().ok(__lang__(30035),message)
#                self.closeWindow()
#                self.newUserCache = None
#                return

        uid = user.id
        username = user.name()
        if not self.addUserToList(uid):
            LOG("USER ALREADY ADDED")
        #self.setSetting('login_email_%s' % uid,email)
        #self.setSetting('login_pass_%s' % uid,password)
        #enc = savePassword('login_pass_%s' % uid, password)
        self.setSetting('username_%s' % uid,username)
        self.setSetting('token_%s' % uid,graph.access_token)
        if self.graph:
            self.graph.access_token = graph.access_token
        else:
            self.graph = graph
        #if self.token: self.setSetting('token_%s' % uid,self.token)
        self.setSetting('profile_pic_%s' % uid,user.picture('').get('url','').replace('_q.','_n.'))
        #self.getProfilePic(uid,force=True)
        self.window.getControl(132).setVisible(False)
        xbmcgui.Dialog().ok(__lang__(30036),DONOTHING(username))
        self.closeWindow()
        self.setSetting('has_user','true')
        #self.setCurrentUser(uid)
        #if enc: xbmcgui.Dialog().ok(__lang__(30063),__lang__(30062))
        return token

    def getUserList(self):
        ustring = self.getSetting('user_list')
        if not ustring: return []
        return ustring.split(',')

    def getUsers(self):
        ulist = []
        for uid in self.getUserList():
            ulist.append(FacebookUser(uid))
        return ulist

    def addUserToList(self,uid):
        ulist = self.getUserList()
        if uid in ulist: return False
        ulist.append(uid)
        self.setSetting('user_list',','.join(ulist))
        return True

    def removeUserFromList(self,uid):
        ulist = self.getUserList()
        if not uid in ulist: return
        new = []
        for u in ulist:
            if u != uid: new.append(u)
        self.setSetting('user_list',','.join(new))

    def setCurrentUser(self,uid):
        self.currentUser = FacebookUser(uid)
        self._permissions = None
        self.setSetting('current_user', uid)
        u = self.currentUser
        self.setSetting('current_user_name', u.username)
        self.updateUserPic()
        if self.graph: self.graph.setLogin(u.email,u.password(),u.id,u.token)
        self.setUserDisplay()

    def getCurrentUser(self):
        if self.currentUser: return self.currentUser
        uid = self.getSetting('current_user')
        if not uid:
            ulist = self.getUserList()
            if ulist:
                uid = ulist[0]
                if uid: self.setCurrentUser(uid)
        if not uid: return None
        self.currentUser = FacebookUser(uid)
        self.setSetting('current_user_name', self.currentUser.username)
        self.updateUserPic()
        return self.currentUser

    def updateUserPic(self):
        self.setSetting('current_user_pic',self.currentUser.pic)
#        self.setSetting('current_user_pic','')
#        outfile = os.path.join(self.CACHE_PATH,'current_user_pic')
#        self.setSetting('current_user_pic',self.getFile(self.currentUser.pic,outfile))

    def clearSetting(self,key):
        __addon__.setSetting(key,'')

    def setSetting(self,key,value):
        __addon__.setSetting(key,value and ENCODE(value) or '')

    def getSetting(self,key,default=None):
        setting = __addon__.getSetting(key)
        if not setting: return default
        if type(default) == type(0):
            return int(float(setting))
        elif isinstance(default,bool):
            return setting == 'true'
        return setting

    def getAuth(self,graph=None):
        import OAuthHelper

        token = OAuthHelper.getToken('script.facebook.media')
        if graph: graph.access_token = token
        return token

    def getAuthExtended(self,graph=None):
        import OAuthHelper

        token = OAuthHelper.getToken('script.facebook.media_extended')
        if graph: graph.access_token = token
        return token

    def getAuthOld(self,email='',password='',graph=None,no_auto=False):
        #xbmcgui.Dialog().ok('Authorize','Goto xbmc.2ndmind.net/fb','Authorize the addon, and write down the pin.','Click OK when done')
        xbmcgui.Dialog().ok('Authorize','Goto xbmc.2ndmind.net/fb','and authorize the addon.','Click OK when done')
        return '123456789'
        pin = '-'
        while (len(pin) != 4 and len(pin) != 12) or not pin.isdigit():
            if pin != '-':
                xbmcgui.Dialog().ok('Bad PIN','PIN must be 4 or 12 digits')
            else:
                pin = ''
            pin = doKeyboard('Enter the 4 or 12 digit pin',pin)
            if pin == None: return
            pin = pin.replace('-','')

        token = urllib2.urlopen('http://xbmc.2ndmind.net/fb/gettoken.php?pin=' + pin).read()
        if not token:
            dbg = urllib2.urlopen('http://xbmc.2ndmind.net/fb/getdebug.php?pin=' + pin).read()
            LOG('Failed to get token. Site debug info:')
            LOG(dbg)
        #print 'tkn: ' + token
        return token

def doKeyboard(prompt,default='',hidden=False):
    keyboard = xbmc.Keyboard(default,prompt)
    keyboard.setHiddenInput(hidden)
    keyboard.doModal()
    if not keyboard.isConfirmed(): return None
    return keyboard.getText()

def createWindowFile(skin_name):
    if not skin_name: raise Exception
    try:
        from elementtree import ElementTree as etree
    except:
        import xml.etree.ElementTree as etree

    path = os.path.join(SKIN_PATH,'720p','Font.xml')
    if not os.path.exists(path): path = os.path.join(SKIN_PATH,'1080i','Font.xml')
    if not os.path.exists(path): return

    fonts_xml = open(path).read()
    fonts_dom = etree.fromstring(fonts_xml)
    curr_fonts = {    'font10_title':12,
                    'font12_title':16,
                    'font13_title':20,
                    'font24_title':24}

    new_fonts = {}

    for fn in curr_fonts:
        csize = curr_fonts[fn]
        cmpr = 0
        smallest_size = 200
        smallest_name = ''
        for sett in fonts_dom.findall('fontset'):
            for font in sett.findall('font'):
                name = font.find('name').text
                size = int(font.find('size').text)
                if size <= csize and size >= cmpr:
                    cmpr = size
                    new_fonts[fn] = name
                elif fn == name:
                    new_fonts[fn] = name
                    break
                    break
                else:
                    if size < smallest_size:
                        smallest_size = size
                        smallest_name = name
            if not fn in new_fonts:
                new_fonts[fn] = smallest_name

    win_def_file = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('path')),'resources','skins',THEME,'720p','facebook-media-main-skin.confluence.xml')
    f = open(win_def_file,'r')
    win_def_xml = f.read()
    f.close()
    for fn in new_fonts:
        win_def_xml = win_def_xml.replace(fn,new_fonts[fn])
    win_new_file = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('path')),'resources','skins',THEME,'720p','facebook-media-main-%s.xml' % skin_name)
    f = open(win_new_file,'w')
    f.write(win_def_xml)
    f.close()

def openWindow(window_name,session=None,**kwargs):
    returnValue = None
    windowFile = 'facebook-media-%s.xml' % window_name
    if window_name == 'main':
        windowFile = 'facebook-media-main-%s.xml' % CURRENT_SKIN
        windowFilePath = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('path')),'resources','skins',THEME,'720p',windowFile)
        if not os.path.exists(windowFilePath):
            try:
                createWindowFile(CURRENT_SKIN)
            except:
                ERROR('ERROR GENERATING WINDOW FILE FOR SKIN: %s' % CURRENT_SKIN)
                windowFile = 'facebook-media-main-skin.confluence.xml'
        w = MainWindow(windowFile , xbmc.translatePath(__addon__.getAddonInfo('path')), THEME)
    elif window_name == 'auth':
        w = AuthWindow(windowFile , xbmc.translatePath(__addon__.getAddonInfo('path')), THEME,session=session,**kwargs)
        w.doModal()
        returnValue = w.returnValue
        del w
        return returnValue
    elif window_name == 'slideshow':
        w = SlideshowTagsWindow(windowFile , xbmc.translatePath(__addon__.getAddonInfo('path')), THEME,session=session,**kwargs)
    else:
        return #Won't happen :)
    w.doModal()
    del w
    return returnValue

def newGraph(email,password,uid=None,token=None,new_token_callback=None,credentials_callback=None):
    graph = facebook.GraphWrap(token,new_token_callback=new_token_callback,credentials_callback=credentials_callback,version=__version__)
    graph.setAppData('150505371652086')
    graph.setLogin(email,password,uid)
    return graph

def registerAsShareTarget():
    try:
        import ShareSocial #@UnresolvedImport
    except:
        LOG('Could not import ShareSocial')
        return

    target = ShareSocial.getShareTarget()
    target.addonID = 'script.facebook.media'
    target.name = 'Facebook'
    target.importPath = 'share'
    target.shareTypes = ['image','audio','video','imagefile','videofile','status']
    target.provideTypes = ['feed','imagestream']
    ShareSocial.registerShareTarget(target)
    LOG('Registered as share target with ShareSocial')

XBMC_VERSION = xbmc.getInfoLabel('System.BuildVersion')
SKIN_PATH = xbmc.translatePath('special://skin')
if SKIN_PATH.endswith(os.path.sep): SKIN_PATH = SKIN_PATH[:-1]
CURRENT_SKIN = os.path.basename(SKIN_PATH)
LOG('XBMC Version: %s' % XBMC_VERSION)
LOG('XBMC Skin: %s' % CURRENT_SKIN)

if __name__ == '__main__':
    registerAsShareTarget()
    openWindow('main')

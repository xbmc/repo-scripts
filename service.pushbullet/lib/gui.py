# -*- coding: utf-8 -*-
import xbmc, xbmcgui, time, urllib, os
import util
import pushhandler
import pbclient
import devices
import maps
import YDStreamExtractor as StreamExtractor

T = util.T

CACHE_PATH = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')),'cache')
if not os.path.exists(CACHE_PATH): os.makedirs(CACHE_PATH)

def getCachedData(ID):
    path = os.path.join(CACHE_PATH,ID)
    if os.path.exists(path):
        with open(path,'r') as f: return f.read()
    return None

def cacheData(ID,data):
    path = os.path.join(CACHE_PATH,ID)
    with open(path,'w') as f: f.write(data)

def deleteCachedData(ID):
    path = os.path.join(CACHE_PATH,ID)
    if os.path.exists(path): os.remove(path)

def cleanCache(used_ids):
    for ID in os.listdir(CACHE_PATH):
        if not ID in used_ids: deleteCachedData(ID)

def selectDevice(client,extra=T(32050)):
    deviceMap = {}
    try:
        for d in client.getDevicesList():
            if not d.get('active'): continue
            deviceMap[d['iden']] = d['nickname']
    except pbclient.PushbulletException, e:
        xbmcgui.Dialog().ok(T(32051).upper(), '{0}:'.format(T(32051)),'',e.message)
        return
    
    idx = xbmcgui.Dialog().select(T(32052),deviceMap.values() + [extra])
    if idx < 0: return
    if idx >= len(deviceMap.keys()): return ''
    return deviceMap.keys()[idx]

class BaseWindow(xbmcgui.WindowXML):
    def __init__(self,*args,**kwargs):
        self._closing = False
        self._winID = ''

    def onInit(self):
        self._winID = xbmcgui.getCurrentWindowId()
        
    def setProperty(self,key,value):
        if self._closing: return
        xbmcgui.Window(self._winID).setProperty(key,value)
        xbmcgui.WindowXMLDialog.setProperty(self,key,value)
        
    def doClose(self):
        self._closing = True
        self.close()

class PushbulletWindow(BaseWindow):
    def __init__(self,*args,**kwargs):
        self.client = pbclient.Client(util.getToken())
        self.lastSelected = None
        self.viewMode = 'SELF'
        self.initViewMode()
        self.pushes = []
        BaseWindow.__init__(self,*args,**kwargs)

    def initViewMode(self):
        setID = util.getSetting('selected_device')
        if setID:
            self.viewMode = setID
        else:
            defModeIdx = util.getSetting('default_view_mode',0)
            viewMode = ['SELF','ALL','LAST'][defModeIdx]

            if viewMode == 'LAST':
                last = util.getSetting('last_view_mode')
                self.viewMode = last or 'SELF'
            else:
                self.viewMode = viewMode

    def onInit(self):
        BaseWindow.onInit(self)
        self.setProperty('loading','1')
        self._winID = xbmcgui.getCurrentWindowId()
        self.pushList = self.getControl(101)
        token = util.getSetting('pb_access_token')
        if not token: return
        
        loadVideoThumbs = util.getSetting('load_video_thumbs',False)
        kodiDevice = devices.getDefaultKodiDevice(util.getSetting('pb_client_iden'),util.getSetting('pb_client_nickname'))
        if not kodiDevice: return
        self.pushes = []
        pushes = self.client.pushes()
        if not pushes: return
        items = []
        cacheIDs = []
        self.pushes = []

        for p in pushes: #Keep all IDs cached so that we don't cause a delay when changing view
            if p.get('active'):
                cacheIDs.append(p.get('iden'))

        if self.viewMode == 'SELF':
            self.pushes = [p for p in pushes if p.get('active') and p.get('target_device_iden') == kodiDevice.ID]
        elif self.viewMode == 'ALL':
            self.pushes = [p for p in pushes if p.get('active')]
        elif self.viewMode:
            self.pushes = [p for p in pushes if p.get('active') and p.get('target_device_iden') == self.viewMode]

        for push in self.pushes:
            iden = push.get('iden')

            title = push.get('title',push.get('name',push.get('file_name','')))
            bg = push.get('image_url','')
            info = push.get('url','')
            mediaIcon = ''
            media = ''

            if push.get('type') == 'address':
                bg = maps.Maps().getMap(urllib.quote(push.get('address','')),'None',marker=True,return_url_only=True)
            elif push.get('type') == 'link':
                url = push.get('url')
                if StreamExtractor.mightHaveVideo(url):
                    media = 'video'
                    if loadVideoThumbs:
                        bg = getCachedData(iden)
                        if not bg:
                            bg = StreamExtractor.getVideoInfo(url).thumbnail
                            cacheData(iden,bg)
                else:
                    media = pushhandler.getURLMediaType(url)
                if not title:
                    title = url.rsplit('/',1)[-1]
            elif push.get('type') == 'file':
                info = urllib.unquote(push.get('file_url',''))
                if push.get('file_type','').startswith('image/'):
                    media = 'image'
                elif push.get('file_type','').startswith('audio/'):
                    media = 'music'
                elif push.get('file_type','').startswith('video/'):
                    media = 'video'
            if media:
                mediaIcon = 'service-pushbullet-com-icon_{0}.png'.format(media)

            item = xbmcgui.ListItem(title,iconImage='service-pushbullet-com-{0}.png'.format(push.get('type','')))

            desc = push.get('body',push.get('address',''))
            if push.get('type') == 'list':
                li = []
                ct = 0
                for i in push.get('items',[]):
                    li.append(i.get('text',''))
                    ct+=1
                    if ct > 50: break
                desc = ', '.join(li)
            desc = '[CR]'.join(desc.splitlines()[:4])
            item.setProperty('description',desc)
            item.setProperty('info',info)
            item.setProperty('sender', push.get('sender_name',push.get('sender_email','')))
            item.setProperty('media_icon',mediaIcon)
            item.setProperty('background',bg)
            #item.setProperty('date',time.strftime('%m-%d-%Y %H:%M',time.localtime(push.get('created',0))))
            item.setProperty('date','{0} {1}'.format(util.durationToShortText(time.time() - push.get('created',0)),T(32053)))
            items.append(item)

        self.setProperty('loading','0')
        self.pushList.reset()
        self.pushList.addItems(items)

        if items: self.setFocusId(101)
        self.reSelect()
        cleanCache(cacheIDs)

    def onClick(self,controlID):
        if controlID == 101:
            push = self.getSelectedPush()
            if not push: return
            if not pushhandler.handlePush(push,from_gui=True):
                xbmcgui.Dialog().ok(T(32054),'{0}:'.format(T(32054)),'',T(32055))

    def onAction(self,action):
        try:
            if action.getId() == 11: #xbmcgui.ACTION_SHOW_INFO:
                self.onInit()
            elif action.getId() == 117: #xbmcgui.ACTION_CONTEXT_MENU:
                self.doMenu()
            push = self.getSelectedPush()
            if push: self.lastSelected = push.get('iden')
        except:
            import traceback
            xbmc.log(traceback.format_exc())
        finally:
            BaseWindow.onAction(self,action)
        
    def getSelectedPush(self):
        selected = self.pushList.getSelectedPosition()
        if selected < 0 or selected >= len(self.pushes): return
        return self.pushes[selected]

    def reSelect(self):
        if not self.lastSelected: return
        idx = next((i for i in range(len(self.pushes)) if self.pushes[i].get('iden') == self.lastSelected),-1)
        if idx < 0:
            self.lastSelected = None
        else:
            self.getControl(101).selectItem(idx)

    def doMenu(self):
        selected = self.pushList.getSelectedPosition()
        options = []
        if self.viewMode != 'ALL':
            options.append(('show_all',T(32056)))
        if self.viewMode != 'SELF':
            options.append(('show_self',T(32057)))
        options.append(('show_device',T(32058)))
        if selected >= 0:
            push = self.pushes[selected]
            if push.get('type') in ('file','link'):
                options.append(('download',T(32059)))
            options.append(('delete',T(32060)))
        idx = xbmcgui.Dialog().select(T(32061),[o[1] for o in options])
        if idx < 0: return
        choice = options[idx][0]
        
        if choice == 'download':
            import os
            d = util.Downloader()
            targetDir = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')),'temp')
            if not os.path.exists(targetDir): os.makedirs(targetDir)
            finalTargetDir = d.chooseDirectory()
            if not finalTargetDir: return
            
            url = push.get('url')
            if push.get('type') == 'link':
                vid = StreamExtractor.getVideoInfo(url)
                if vid:
                    return d.youtubeDLDownload(vid,targetDir,finalTargetDir)
            elif push.get('type') == 'file':
                url = push.get('file_url')

            fname, ftype = d.downloadURL(targetDir,url,fname=push.get('file_name'),final_target_dir=finalTargetDir)
            if fname:
                xbmcgui.Dialog().ok(T(32062),'{0}:'.format(T(32063)),'[CR]',fname)
            else:
                xbmcgui.Dialog().ok(T(32064),'[CR]',T(32064))

        elif choice == 'delete':
            #set last selected to the item above, or the item below if we are at the top
            closest = selected - 1
            if closest < 0:
                self.lastSelected = None
            else:
                self.lastSelected = self.pushes[closest].get('iden')

            self.client.deletePush(push)
            self.onInit()
        elif choice == 'show_all':
            self.viewMode = 'ALL'
            self.onInit()
        elif choice == 'show_self':
            self.viewMode = 'SELF'
            self.onInit()
        elif choice == 'show_device':
            deviceID = selectDevice(self.client)
            if not deviceID: return
            self.viewMode = deviceID
            self.onInit()
        util.setSetting('last_view_mode',self.viewMode)

class ImageViewWindow(BaseWindow):
    def __init__(self,*args,**kwargs):
        self.url = kwargs.get('url','')
        BaseWindow.__init__(self,*args,**kwargs)

    def onInit(self):
        BaseWindow.onInit(self)
        self.setProperty('image_url',self.url)

class NoteViewWindow(BaseWindow):
    def __init__(self,*args,**kwargs):
        self.text = kwargs.get('text','')
        BaseWindow.__init__(self,*args,**kwargs)

    def onInit(self):
        BaseWindow.onInit(self)
        self.getControl(100).setText(self.text)
        import xbmc
        xbmc.sleep(100) #Attempt to give scrollbar time to becomve visible so we can focus it
        if xbmc.getCondVisibility('Control.IsVisible(101)'): self.setFocusId(101) #Prevent log message by checking visibility first

class ListViewWindow(BaseWindow):
    def __init__(self,*args,**kwargs):
        self.data = kwargs.get('data','')
        self.client = pbclient.Client(util.getToken())
        BaseWindow.__init__(self,*args,**kwargs)

    def onInit(self):
        BaseWindow.onInit(self)
        self.listControl = self.getControl(101)
        items = []
        for i in self.data.get('items',[]):
            item = xbmcgui.ListItem(i.get('text'))
            item.setProperty('checked',i.get('checked') and '1' or '') 
            items.append(item)
        self.listControl.reset()
        self.listControl.addItems(items)
        if items: self.setFocusId(101)

    def refresh(self):
        idx = self.listControl.getSelectedPosition()
        for p in self.client.pushes():
            if p.get('iden') == self.data.get('iden'):
                self.data = p
                break

        self.onInit()
        if idx < 0 or idx >= self.listControl.size(): return
        self.listControl.selectItem(idx)

    def onAction(self,action):
        try:
            if action.getId() == 11: #xbmcgui.ACTION_SHOW_INFO:
                self.refresh()
        finally:
            BaseWindow.onAction(self,action)

    def onClick(self,controlID):
        if controlID == 101:
            idx = self.listControl.getSelectedPosition()
            if idx < 0: return
            item = self.listControl.getListItem(idx)
            checked = not self.data['items'][idx].get('checked')
            self.data['items'][idx]['checked'] = checked
            item.setProperty('checked',checked and '1' or '')
            self.client.modifyPush(self.data)

WINDOW_FONTS = {
    'default':{
        '@font10@':'font10', #Small
        '@font10T@':'font10', #Small Title
        '@font13@':'font13', #Normal
        '@font13T@':'font13' #Normal Title
    }
}

try:
    import json
except:
    import simplejson as json
    
SKIN_XML_PATH = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('path')),'resources','skins','Main','720p')

with open(os.path.join(SKIN_XML_PATH,'fonts.json'),'r') as j:
    WINDOW_FONTS.update(json.load(j))
        
def openWindow(winClass,winXML,**kwargs):
    winXMLPath = os.path.join(SKIN_XML_PATH,winXML)
    workingXMLPath = os.path.join(SKIN_XML_PATH,'service.pushbullet.com-working.xml')

    skinName = util.skinName()
    fonts = WINDOW_FONTS['default']
    if skinName in WINDOW_FONTS: fonts = WINDOW_FONTS[skinName]

    with open(winXMLPath,'r') as infile:
        with open(workingXMLPath,'w') as outfile:
            out = infile.read()
            for f,r in fonts.items():
                out = out.replace(f,r)
            outfile.write(out)
    w = winClass('service.pushbullet.com-working.xml',util.ADDON.getAddonInfo('path'),'Main','720p',**kwargs)
    w.doModal()
    del w
    os.remove(workingXMLPath)

def showImage(url):
    openWindow(ImageViewWindow,'service.pushbullet.com-image.xml',url=url)

def showNote(text):
    openWindow(NoteViewWindow,'service.pushbullet.com-note.xml',text=text)

def showList(data):
    openWindow(ListViewWindow,'service.pushbullet.com-list.xml',data=data)

def start():
    openWindow(PushbulletWindow,'service.pushbullet.com-pushes.xml')

        
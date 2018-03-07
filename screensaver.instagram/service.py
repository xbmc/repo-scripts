#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of Instagram ScreenSaver.
#
# Instagram ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Instagram ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Instagram ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

#inspired by https://github.com/huijay12/instagram-photo-crawler
import random, os, sys, json, time, datetime, requests
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'screensaver.instagram'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

# Globals
USERNAME       = (REAL_SETTINGS.getSetting('Username') or None)
PASSWORD       = (REAL_SETTINGS.getSetting('Password') or None)
ORIGIN_URL     = 'https://www.instagram.com'
LOGIN_URL      = ORIGIN_URL + '/accounts/login/ajax/'

def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
    
def ProgressDialogBG(percent=0, control=None, string1='', header=ADDON_NAME):
    if percent == 0 and not control:
        control = xbmcgui.DialogProgressBG()
        control.create(header, string1)
    elif percent == 100 and control: return control.close()
    elif control: control.update(percent, string1)
    return control
         
class Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        self.pendingChange = True

        
    def onSettingsChanged(self):
        log('onSettingsChanged')
        self.pendingChange = True

        
class service(object):
    def __init__(self):
        self.myMonitor = Monitor()
        self.startService()
            
    
    def startService(self):
        log('startService')
        while not self.myMonitor.abortRequested(): 
            if self.myMonitor.waitForAbort(2): break
            if self.myMonitor.pendingChange: self.updateJson()
            
            
    def updateJson(self):
        log('updateJson')
        self.myMonitor.pendingChange = False
        if USERNAME is None: return
        for target_id in self.getTargets(): self.loadImages(target_id)
        return
        

    def getTargets(self):
        log('getTargets')
        userList = []
        REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID) #reinitialize settings
        for i in range(1,11): userList.append((REAL_SETTINGS.getSetting('USER%d'%i)))
        return filter(None, userList)
        

    def loadImages(self, target_id):
        log('loadImages, target_id = ' + target_id)
        # now = datetime.datetime.now()
        # todo parse datetime rebuild outdated images
        filename = xbmc.translatePath(os.path.join(SETTINGS_LOC,'%s.json'%(target_id)))
        if xbmcvfs.exists(filename): return
        if self.updateImages(target_id, filename): self.myMonitor.waitForAbort(2)
        
        
    def updateImages(self, target_id, filename):
        count         = 0
        json_results  = []
        pics_url_list = []
        pics_url_date = datetime.datetime.now()
        instagram_parser = instagram(target_id)
        target_url = ORIGIN_URL + '/' + target_id +'/?__a=1'
        progressBG = ProgressDialogBG(0, string1=LANGUAGE(32305)%(target_id))
        req = instagram_parser.session.get(target_url)
        try: req.raise_for_status()
        except Exception as exc:
            log('problem occur: %s' % (exc))
            return

        data = req.json()
        not_last = True
        #Only 12 posts are received when directing to one's profile,
        #we have to get the end_cursor and redirect to get the next 12 posts,
        #keep redirecting until number of posts is less than 12
        while(not_last):
            try:
                count += .1
                ProgressDialogBG(int(count * 100 // 100), progressBG)
                pics_url_list.extend(instagram_parser.handle_12_posts(data, ORIGIN_URL, target_id))
                end_cursor = instagram_parser.get_end_cursor(data)
                target_url = instagram_parser.refresh_url(ORIGIN_URL, target_id, end_cursor)
                data = instagram_parser.session.get(target_url).json()
                if(len(data['user']['media']['nodes']) < 12): break
                self.myMonitor.waitForAbort(2)
            except Exception('Session Closed'): break

        # Last posts
        ProgressDialogBG(95, progressBG)
        pics_url_list.extend(instagram_parser.handle_12_posts(data, ORIGIN_URL, target_id))
        ProgressDialogBG(100, string1=LANGUAGE(32306)%(target_id))
        for idx, url in enumerate( pics_url_list): json_results.append({'idx': idx, 'image': url, 'updated':str(pics_url_date)})
        if len(json_results) == 0: return
        return self.writeJson(filename, json_results)
            
    
    def loadJson(self, filename):
        if not xbmcvfs.exists(filename): return [{'updated':''}]
        with open(filename) as data: return json.load(data)
     
     
    def writeJson(self, filename, items):
        log('writeJson')
        if xbmcvfs.exists(filename): 
            try: xbmcvfs.delete(filename)
            except: pass
        file = open(filename,'a')
        file.write(json.dumps(items))
        file.close()
        return True

        
class instagram(object):
    def __init__(self, target_id):
        log('instagram, target_id = %s'%target_id)
        #login id and get cookies
        self.session = requests.Session()
        self.session.headers = {'user-agent': 'Chrome/59.0.3071.115'}
        self.session.headers.update({'Referer': ORIGIN_URL})

        req = self.session.get(ORIGIN_URL)
        try: req.raise_for_status()
        except Exception as exc:
            log('problem occur: %s' % (exc))
            exit()
        
        if USERNAME is None or PASSWORD is None: return
        self.session.headers.update({'X-CSRFToken': req.cookies['csrftoken']})
        login_data = {'username': USERNAME, 'password': PASSWORD}
        login = self.session.post(LOGIN_URL, data=login_data, allow_redirects=True)
        try: login.raise_for_status()
        except Exception as exc:
            log('problem occur: %s' % (exc))
            exit()

        self.session.headers.update({'X-CSRFToken': login.cookies['csrftoken']})
        cookies = login.cookies
        login_text = json.loads(login.text)


    #Get url of pictures,
    #if the post has single picture, get url,
    #if the post has multiple pictures, get the url of the post,
    #request the url and get all urls of pictures
    #save all urls in pics_url_list
    def handle_12_posts(self, data, ORIGIN_URL, target_id):
        pics_url_list = []
        for i in data['user']['media']['nodes']:
            typename = str(i['__typename'])

            if typename == "GraphImage":
                pic_url = str(i['display_src'])
                pics_url_list.append(pic_url)

            if typename == "GraphSidecar":
                code = str(i['code'])
                post_url = ORIGIN_URL + '/p/' + code + '/?__a=1'

                response = self.session.get(post_url)
                try: response.raise_for_status()
                except Exception as exc:
                    log('problem occur: %s' % (exc))
                    exit()

                post_data = response.json()
                node_arr = post_data['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']
                for node in node_arr:
                    pic_url = node['node']['display_url']
                    pics_url_list.append(pic_url)
        return pics_url_list


    def get_end_cursor(self, data):
        return str(data['user']['media']['page_info']['end_cursor'])


    def refresh_url(self, ORIGIN_URL, target_id, end_cursor):
        return str(ORIGIN_URL + '/' + target_id + '/?__a=1&max_id=' + end_cursor)


if __name__ == '__main__': service()
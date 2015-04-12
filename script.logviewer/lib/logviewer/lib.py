# -*- coding: utf-8 -*-

import xbmc,xbmcaddon,xbmcgui,xbmcplugin,urllib,os,re,sys

class Logmodule:
    def loglocation(self,old=False):
        versionNumber = int(xbmc.getInfoLabel("System.BuildVersion" )[0:2])
        if versionNumber < 12:
            if xbmc.getCondVisibility('system.platform.osx'):
                if xbmc.getCondVisibility('system.platform.atv2'):
                    log_path = '/var/mobile/Library/Preferences'
                else:
                    log_path = os.path.join(os.path.expanduser('~'), 'Library/Logs')
            elif xbmc.getCondVisibility('system.platform.ios'):
                log_path = '/var/mobile/Library/Preferences'
            elif xbmc.getCondVisibility('system.platform.windows'):
                log_path = xbmc.translatePath('special://home')
            elif xbmc.getCondVisibility('system.platform.linux'):
                log_path = xbmc.translatePath('special://home/temp')
            else:
                log_path = xbmc.translatePath('special://logpath')
                
        else:
            log_path = xbmc.translatePath('special://logpath')

        if versionNumber < 14:
            filename='xbmc.log'
            filenameold='xbmc.old.log'
        else:
            filename='kodi.log'
            filenameold='kodi.old.log'

        if not os.path.exists(os.path.join(log_path, filename)):
            if os.path.exists(os.path.join(log_path, 'spmc.log')):
                filename='spmc.log'
                filenameold='spmc.old.log'
            else:
                return False
                
        if old==True:
            log_path = os.path.join(log_path, filenameold).decode('utf-8')
        else:
            log_path = os.path.join(log_path, filename).decode('utf-8')
        return log_path

    def getcontent(self,old=False,invert=False,line_number=0):
        content=openfile(self.loglocation(old)).replace(' ERROR: ',' [COLOR red]ERROR[/COLOR]: ').replace(' WARNING: ',' [COLOR gold]WARNING[/COLOR]: ')

        if invert==True:
            content='\n'.join(content.splitlines()[::-1])

        if line_number>0:
            try: content=content[0:int(line_number)]
            except: content='%s\n%s' % (translate(30003),content)

        return content

    def window(self,old=False,invert=False,line_number=0):
        try:
            xbmc.executebuiltin("ActivateWindow(10147)")
            window = xbmcgui.Window(10147)
            xbmc.sleep(100)
            window.getControl(1).setLabel(translate(30000))
            window.getControl(5).setText(self.getcontent(old,invert,line_number))
        except:
            pass

def openfile(path):
    try:
        fh = open(path, 'rb')
        contents=fh.read()
        fh.close()
        return contents
    except:
        print "%s: %s" % (translate(30004,path))
        return None

def translate(text):
      return xbmcaddon.Addon().getLocalizedString(text).encode('utf-8')

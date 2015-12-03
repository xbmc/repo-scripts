import json
from time import strftime
import time
import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.wemo import wemo

addon = xbmcaddon.Addon()
ip_address_list = {}

class Settings_Monitor(xbmc.Monitor):
    def __init__(self, player):
        self.player = player

    def onSettingsChanged(self):
        update_device_list()
        self.player.update_settings()

class Player_Monitor(xbmc.Player):
    def __init__(self):
        self.update_settings()
        self.movie_playing = None
        self.tv_show_playing = None

    def onPlayBackStarted(self):
        # turn switch off
        self.now_playing('1')
        if self.media_start_always_off == 'true':
            self.toggle_switch('1')
        elif self.start_stop_end_toggle == 'true':
            if self.movie_toggle == 'true' and self.movie_playing:
                self.toggle_switch('1')
            elif self.tv_toggle == 'true' and self.tv_show_playing:
                self.toggle_switch('1')
            elif self.unspecified_toggle == 'true':
                self.toggle_switch('1')

    def onPlayBackStopped(self):
        # turn switch on
        self.now_playing('0')
        if self.start_stop_end_toggle == 'true':
            if self.movie_toggle == 'true' and self.movie_playing:
                self.toggle_switch('0')
            elif self.tv_toggle == 'true' and self.tv_show_playing:
                self.toggle_switch('0')
            elif self.unspecified_toggle == 'true':
                self.toggle_switch('0')

    def onPlayBackEnded(self):
        # turn switch on
        self.now_playing('0')
        if self.start_stop_end_toggle == 'true':
            if self.movie_toggle == 'true' and self.movie_playing:
                self.toggle_switch('0')
            elif self.tv_toggle == 'true' and self.tv_show_playing:
                self.toggle_switch('0')
            elif self.unspecified_toggle == 'true':
                self.toggle_switch('0')

    def onPlayBackPaused(self):
        # turn switch on
        self.now_playing('1')
        if self.play_pause_toggle == 'true':
            if self.movie_toggle == 'true' and self.movie_playing:
                self.toggle_switch('0')
            elif self.tv_toggle == 'true' and self.tv_show_playing:
                self.toggle_switch('0')
            elif self.unspecified_toggle == 'true':
                self.toggle_switch('0')

    def onPlayBackResumed(self):
        # turn switch off
        self.now_playing('1')
        if self.media_start_always_off == 'true':
            self.toggle_switch('1')
        elif self.play_pause_toggle == 'true':
            if self.movie_toggle == 'true' and self.movie_playing:
                self.toggle_switch('1')
            elif self.tv_toggle == 'true' and self.tv_show_playing:
                self.toggle_switch('1')
            elif self.unspecified_toggle == 'true':
                self.toggle_switch('1')

    def toggle_switch(self, state):
        # send command to switch
        if self.toggle_time == 'true':
            if self.check_time():
                if state == '0':
                    on()
                else:
                    off()
            elif self.media_start_always_off == 'true' and state == '1':
                off()
        elif self.media_start_always_off == 'true' and state == '1':
            off()
        else:
            if state == '0':
                on()
            else:
                off()

    def check_time(self):
        # format time and compare
        current_time = strftime('%H%M', time.localtime())
        start_time = strftime('%H%M', time.strptime(addon.getSetting('start_time'), '%H%M'))
        end_time = strftime('%H%M', time.strptime(addon.getSetting('end_time'), '%H%M'))
        if start_time < end_time:
            if (start_time < current_time) and (current_time < end_time):
                return True
        elif start_time > end_time:
            if (current_time > start_time) or (current_time < end_time):
                return True
        else:
            return False

    def now_playing(self, event):
        # check media type when a video starts, pauses, or resumes
        if (self.movie_toggle == 'true' or self.tv_toggle == 'true') and event == '1':
            query = {'jsonrpc': '2.0', 'method': 'Player.GetItem', 'params': { 'properties': ['showtitle', 'season', 'episode', 'duration', 'streamdetails'], 'playerid': 1 }, 'id': 'VideoGetItem'}
            response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
            if response['result']['item']['type'] == 'movie':
                self.movie_playing = True
                self.tv_show_playing = False
                log(response, 'DEBUG')
            elif response['result']['item']['type'] == 'episode':
                self.movie_playing = False
                self.tv_show_playing = True
                log(response, 'DEBUG')
            else:
                self.movie_playing = False
                self.tv_show_playing = False
                log(response, 'DEBUG')

    def update_settings(self):
        # update variables
        self.start_stop_end_toggle = addon.getSetting('startStopEnd_toggle')
        self.play_pause_toggle = addon.getSetting('playPause_toggle')
        self.movie_toggle = addon.getSetting('movie_toggle')
        self.tv_toggle = addon.getSetting('tv_toggle')
        self.unspecified_toggle = addon.getSetting('unspecified_toggle')
        self.toggle_time = addon.getSetting('toggle_time')
        self.media_start_always_off = addon.getSetting('always_off_toggle')

def off():
    if addon.getSetting('multiple_devices') == 'true':
        for ip_address in ip_address_list.keys():
            try:
                ip_address_list[ip_address].off()
            except Exception, e:
                log(e, 'NOTIFICATION_ERROR')
                return None
    else:
        try:
            ip_address_list[addon.getSetting('ip_address')].off()
        except Exception, e:
            log(e, 'NOTIFICATION_ERROR')
            return None
    log('Switch: Off', 'NOTIFICATION_INFO')

def on():
    if addon.getSetting('multiple_devices') == 'true':
        for ip_address in ip_address_list.keys():
            try:
                ip_address_list[ip_address].on()
            except Exception, e:
                log(e, 'NOTIFICATION_ERROR')
                return None
    else:
        try:
            ip_address_list[addon.getSetting('ip_address')].on()
        except Exception, e:
            log(e, 'NOTIFICATION_ERROR')
            return None
    log('Switch: On', 'NOTIFICATION_INFO')

def toggle():
    if addon.getSetting('toggle_multiple') == 'true' and addon.getSetting('multiple_devices') == 'true':
        for ip_address in ip_address_list.keys():
            try:
                ip_address_list[ip_address].toggle()
            except Exception, e:
                log(e, 'NOTIFICATION_ERROR')
    else:
        try:
            ip_address_list[addon.getSetting('ip_address')].toggle()
        except:
            log(e, 'NOTIFICATION_ERROR')
    log('Switch: Toggled', 'NOTIFICATION_INFO')

def log(msg_text, msg_type):
    addon_name = addon.getAddonInfo('name')
    if addon.getSetting('debug') == 'true':
        xbmc.log('{0} - {1}'.format(addon_name, msg_text), level=xbmc.LOGDEBUG)
    if addon.getSetting('display_notification') == 'true':
        if msg_type == 'NOTIFICATION_INFO':
            xbmcgui.Dialog().notification(addon_name, '{0}'.format(msg_text), xbmcgui.NOTIFICATION_INFO, 500)
    if msg_type == 'NOTIFICATION_ERROR':
        xbmc.log('{0} - {1}'.format(addon_name, msg_text), level=xbmc.LOGDEBUG)
        xbmcgui.Dialog().notification(addon_name, '{0}'.format(msg_text), xbmcgui.NOTIFICATION_ERROR, 5000)

def update_device_list():
    for ip_address in addon.getSetting('ip_address_list').split(';'):
        if ip_address != '':
            try:
                ip_address_list.update({ip_address: wemo(ip_address)})
            except Exception, e:
                log(e, 'NOTIFICATION_ERROR')
    log('WeMo Device list: {0}'.format(ip_address_list.keys()), 'DEBUG')

def main():
    if addon.getSetting('ip_address') == '':
        log('Missing IP address', 'NOTIFICATION_ERROR')
        addon.openSettings()

    ip_address = addon.getSetting('ip_address')
    try:
        ip_address_list.update({ip_address: wemo(ip_address)})
    except Exception, e:
        log(e, 'NOTIFICATION_ERROR')

    if addon.getSetting('multiple_devices') == 'true':
        update_device_list()

    # delay startup if necessary to wait for network
    xbmc.sleep(int(addon.getSetting('start_delay'))*1000)

    # turn switch on when service starts
    if addon.getSetting('toggle_startup') == 'true':
        try:
            ip_address_list[ip_address].on()
        except Exception, e:
            log(e, 'NOTIFICATION_ERROR')

    player = Player_Monitor()
    settings = Settings_Monitor(player)
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        if monitor.waitForAbort(0.5):
            break
        # toggle switch
        if xbmc.getInfoLabel('skin.string(wemoToggle)') == '0':
            toggle()
            xbmc.executebuiltin('Skin.SetString(wemoToggle, 1)')

    # turn switch off when service ends
    if addon.getSetting('toggle_shutdown') == 'true':
        try:
            ip_address_list[ip_address].off()
        except Exception, e:
            log(e, 'NOTIFICATION_ERROR')

if __name__ == '__main__':
    main()

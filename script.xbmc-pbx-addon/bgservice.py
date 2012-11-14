#
#  XBMC PBX Addon
#      Fron-end (XBMC) side
#      This script will be running as a service in background
#
#
#  Copyright (C) 2012 hmronline@gmail.com 
#  http://xbmc-pbx-addon.googlecode.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

# Script constants
__addon__       = "XBMC PBX Addon"
__addon_id__    = "script.xbmc-pbx-addon"
__author__      = "hmronline"
__url__         = "http://code.google.com/p/xbmc-pbx-addon/"
__version__     = "1.0.10"

# Modules
import sys, os
import xbmc, xbmcaddon, xbmcgui, xbmcvfs
import re, traceback


xbmc.log("[%s]: Version %s\n" % (__addon__,__version__))

# Get environment OS
__os__          = os.environ.get( "OS", "win32" )
xbmc.log("[%s]: XBMC for %s\n" % (__addon__,__os__))

__language__    = xbmcaddon.Addon(__addon_id__).getLocalizedString
CWD             = xbmcaddon.Addon(__addon_id__).getAddonInfo('path')
RESOURCE_PATH   = os.path.join(CWD, "resources" )

sys.path.append(os.path.join(RESOURCE_PATH,'lib'))
from Asterisk.Manager import Manager
import Asterisk.Manager, Asterisk.Util



#############################################################################################################
def log(msg):
    try:
        xbmc.log("[%s]: %s\n" % (__addon__,str(msg)))
    except:
        pass

#############################################################################################################
class get_incoming_call(object):

    def __init__(self):
        log("__init__()")
        global asterisk_series
        self.asterisk_series = asterisk_series
        self.DEBUG = False
        self.xbmc_player_paused = False
        self.asterisk_now_playing = False
        self.ast_first_uniqid = 0
        self.ast_my_uniqid = 0
        self.got_newcall_actions = False
        self.events = Asterisk.Util.EventCollection()
        self.events.clear()
        self.events.subscribe('Newchannel',self.NewChannel)
        self.events.subscribe('Newcallerid',self.NewCallerID)       # Asterisk 1.4
        self.events.subscribe('NewCallerid',self.NewCallerID)       # Asterisk 1.6
        self.events.subscribe('Hangup',self.Hangup)

    #####################################################################################################
    def NewChannel(self,pbx,event):
        settings = xbmcaddon.Addon(__addon_id__)
        DEBUG = settings.getSetting("xbmc_debug")
        arr_chan_states = ['Down','Ring','Auto']
        asterisk_chan_state = settings.getSetting("asterisk_chan_state")
        if (asterisk_chan_state == "2"):
            if (self.asterisk_series == "1.4"):
                # Asterisk 1.4
                asterisk_chan_state = "0"
            else:
                # Asterisk 1.6+
                asterisk_chan_state = "1"
            settings.setSetting("asterisk_chan_state",asterisk_chan_state)
        asterisk_chan_state = str(arr_chan_states[int(asterisk_chan_state)])
        del settings
        self.DEBUG = False
        if (DEBUG == "true"):
            self.DEBUG = True
        if (self.DEBUG):
            log("> NewChannel()")
            log(">> UniqueID: " + event.Uniqueid)
        if (self.asterisk_series == "1.4"):
            # Asterisk 1.4
            event_state = str(event.State)
        else:
            # Asterisk 1.6+
            event_state = str(event.ChannelStateDesc)
        if (self.DEBUG): log(">> State: " + event_state)
        if (event_state == asterisk_chan_state and self.ast_my_uniqid == 0 and self.ast_first_uniqid == 0):
            self.ast_my_uniqid = event.Uniqueid
            if (self.DEBUG):
                log(">>> Will attach to this one:")
                log(">>> UniqueID: " + self.ast_my_uniqid)
                log(">>> State: " + asterisk_chan_state)
        if (self.ast_first_uniqid == 0):
            self.ast_first_uniqid = event.Uniqueid

    #####################################################################################################
    def NewCallerID(self,pbx,event):
        if (self.DEBUG):
            log("> NewCallerID()")
            log(">> UniqueID: " + event.Uniqueid)
        if (self.asterisk_series == "1.4"):
            # Asterisk 1.4
            self.event_callerid_num = str(event.CallerID)
        else:
            # Asterisk 1.6+
            self.event_callerid_num = str(event.CallerIDNum)
        if (event.CallerIDName != "" and self.event_callerid_num != ""):
            self.event_callerid = str(event.CallerIDName + " <" + self.event_callerid_num + ">")
        else:
            self.event_callerid = ""
        if (self.DEBUG): log(">> CallerID: " + self.event_callerid)
        if (event.Uniqueid == self.ast_my_uniqid and not self.got_newcall_actions):
            if (self.DEBUG):
                log(">>> Will fire actions for this one:")
                log(">>> UniqueID: " + self.ast_my_uniqid)
                log(">> CallerID: " + self.event_callerid)
            self.newcall_actions(event)

    #####################################################################################################
    def Hangup(self,pbx,event):
        if (self.DEBUG):
            log("> Hangup()")
            log(">> UniqueID: " + event.Uniqueid)
        if (event.Uniqueid == self.ast_first_uniqid):
            self.ast_first_uniqid = 0
        if (event.Uniqueid == self.ast_my_uniqid):
            self.ast_my_uniqid = 0
            self.hangup_actions(event)

    #####################################################################################################
    def hangup_actions(self,event):
        log("> hangup_actions()")
        if (self.DEBUG):
            log(">> UniqueID: " + event.Uniqueid)
        self.asterisk_now_playing = False
        xbmc_player = xbmc.Player(xbmc.PLAYER_CORE_AUTO)
        if (xbmc_player.isPlaying() == 1):
            # Resume media
            xbmc_remaining_time = xbmc_player.getTotalTime() - xbmc_player.getTime()
            xbmc.sleep(1000)
            xbmc_new_remaining_time = xbmc_player.getTotalTime() - xbmc_player.getTime()
            if (self.xbmc_player_paused and xbmc_remaining_time == xbmc_new_remaining_time):
                log(">> Resume media...")
                xbmc_player.pause()
                self.xbmc_player_paused = False
        del xbmc_player
        self.got_newcall_actions = False

    #####################################################################################################
    def newcall_actions(self,event):
        log("> newcall_actions()")
        self.got_newcall_actions = True
        asterisk_alert_info = str(pbx.Getvar(event.Channel,"ALERT_INFO",""))
        if (self.DEBUG):
            log(">> Channel: " + str(event.Channel))
            log(">> UniqueID: " + self.ast_my_uniqid)
            log(">> CallerID: " + self.event_callerid)
            log(">> ALERT_INFO: " + asterisk_alert_info)
        settings = xbmcaddon.Addon(__addon_id__)
        arr_timeout = [5,10,15,20,25,30]
        xbmc_oncall_notification_timeout = int(arr_timeout[int(settings.getSetting("xbmc_oncall_notification_timeout"))])
        cfg_asterisk_cid_alert_info = settings.getSetting("asterisk_cid_alert_info").strip(' \t\n\r')
        cfg_asterisk_redir_alert_info = settings.getSetting("asterisk_redir_alert_info").strip(' \t\n\r')
        asterisk_now_playing_context = settings.getSetting("asterisk_now_playing_context").strip(' \t\n\r') 
        xbmc_caller_picture_path = settings.getSetting("xbmc_caller_picture_path").strip(' \t\n\r')
        xbmc_img = xbmc.translatePath(os.path.join(RESOURCE_PATH,'media','xbmc-pbx-addon.png'))
        xbmc_oncall_pause_media = False
        if (settings.getSetting("xbmc_oncall_pause_media") == "true"):
            xbmc_oncall_pause_media = True
        asterisk_now_playing_enabled = False
        if (settings.getSetting("asterisk_now_playing_enabled") == "true"):
            asterisk_now_playing_enabled = True
        xbmc_oncall_notification = False
        if (settings.getSetting("xbmc_oncall_notification") == "true"):
            xbmc_oncall_notification = True
        xbmc_caller_picture_enabled = False
        if (settings.getSetting("xbmc_caller_picture_enabled") == "true"):
            xbmc_caller_picture_enabled = True        
        del settings
        xbmc_player = xbmc.Player(xbmc.PLAYER_CORE_AUTO)
        if (xbmc_player.isPlaying() == 1):
            log(">> XBMC is playing content...")
            if (xbmc_player.isPlayingAudio() == 1):
                info_tag = xbmc_player.getMusicInfoTag(object)
                if (self.DEBUG):
                    log(">> Music title: " + info_tag.getTitle())
                del info_tag
            if (xbmc_player.isPlayingVideo() == 1):
                xbmc_remaining_time = xbmc_player.getTotalTime() - xbmc_player.getTime()
                info_tag = xbmc_player.getVideoInfoTag(object)
                xbmc_video_title = info_tag.getTitle()
                xbmc_video_rating = info_tag.getRating()
                del info_tag
                if (self.DEBUG):
                    log(">> Video title: " + xbmc_video_title)
                    log(">> Rating: " + str(xbmc_video_rating))
                    log(">> Remaining time (minutes): " + str(round(xbmc_remaining_time/60)))
                # Pause Video
                if (xbmc_oncall_pause_media):
                    xbmc.sleep(1000)
                    if (asterisk_alert_info == cfg_asterisk_cid_alert_info or cfg_asterisk_cid_alert_info == ''):
                        xbmc_new_remaining_time = xbmc_player.getTotalTime() - xbmc_player.getTime()
                        if (not self.xbmc_player_paused and xbmc_remaining_time > xbmc_new_remaining_time):
                            log(">> Pausing player...")
                            xbmc_player.pause()
                            self.xbmc_player_paused = True
                # Redirect Incoming Call
                if (asterisk_now_playing_enabled):
                    try:
                        if ((asterisk_alert_info == cfg_asterisk_redir_alert_info or cfg_asterisk_redir_alert_info == '') and not self.asterisk_now_playing):
                            log(">> Redirecting call...")
                            pbx.Setvar(event.Channel,"xbmc_video_title",xbmc_video_title)
                            pbx.Setvar(event.Channel,"xbmc_remaining_time",round(xbmc_remaining_time/60))
                            pbx.Redirect(event.Channel,asterisk_now_playing_context)
                            self.asterisk_now_playing = True
                    except:
                        xbmc_notification = unicode(str(sys.exc_info()[1]))
                        log(">> Notification: " + xbmc_notification)
                        xbmc.executebuiltin("XBMC.Notification("+ __language__(30051) +","+ xbmc_notification +","+ str(15*1000) +","+ xbmc_img +")")
        del xbmc_player
        # Show Incoming Call Notification Popup
        if (xbmc_oncall_notification):
            if (asterisk_alert_info == cfg_asterisk_cid_alert_info or cfg_asterisk_cid_alert_info == ''):
                xbmc_notification = unicode(self.event_callerid)
                log(">> Notification: " + xbmc_notification)
                xbmc.executebuiltin("XBMC.Notification("+ __language__(30050) +","+ xbmc_notification +","+ str(xbmc_oncall_notification_timeout*1000) +","+ xbmc_img +")")
        # EXPERIMENTAL: Show Caller's Picture
        if (xbmc_caller_picture_enabled):
            xbmc_caller_picture = xbmc_caller_picture_path + self.event_callerid_num
            if (self.DEBUG): log(">> Caller's picture: " + xbmc_caller_picture)
            if (xbmcvfs.exists(xbmc_caller_picture)):
                log(">> Showing Caller's picture")
                popup = PopUpGUI("popup.xml",CWD,"Default")
                popup .show()
                popup.getControl(110).setImage(xbmc_caller_picture)
                xbmc.sleep(xbmc_oncall_notification_timeout*1000)
                popup .close()
                del popup

#############################################################################################################
class PopUpGUI(xbmcgui.WindowXML):
    def __init__(self,*args,**kwargs):
        xbmcgui.WindowXML.__init__(self)
        
    def onAction(self, action):
        self.close()
        


#################################################################################################################
# Starts here
#################################################################################################################

try:
    log("Running in background...")
    settings = xbmcaddon.Addon(__addon_id__)
    DEBUG = settings.getSetting("xbmc_debug")
    xbmc_bgservice = settings.getSetting("xbmc_bgservice")
    manager_host_port = settings.getSetting("asterisk_manager_host"),int(settings.getSetting("asterisk_manager_port"))
    manager_user = settings.getSetting("asterisk_manager_user")
    manager_pass = settings.getSetting("asterisk_manager_pass")
    vm = settings.getSetting("asterisk_vm_mailbox") +"@"+ settings.getSetting("asterisk_vm_context")
    arr_timeout = [5,10,15,20,25,30]
    xbmc_vm_notification_timeout = int(arr_timeout[int(settings.getSetting("xbmc_vm_notification_timeout"))])
    del settings
    if (xbmc_bgservice == "true"):
        log(">> Background service is disabled.")
    else:
        pbx = Manager(manager_host_port,manager_user,manager_pass)
        asterisk_version = str(pbx.Command("core show version")[1])
        asterisk_series = asterisk_version[9:12]
        log(">> Asterisk " + asterisk_series)
        if (DEBUG == "true"): log(">> " + asterisk_version)
        vm_count = str(pbx.MailboxCount(vm)[0])
        xbmc_notification = unicode(__language__(30053) + vm_count)
        xbmc_img = xbmc.translatePath(os.path.join(RESOURCE_PATH,'media','xbmc-pbx-addon.png'))
        log(">> Notification: " + xbmc_notification)
        xbmc.executebuiltin("XBMC.Notification("+ __language__(30052) +","+ xbmc_notification +","+ str(xbmc_vm_notification_timeout*1000) +","+ xbmc_img +")")
        grab = get_incoming_call()
        pbx.events += grab.events
        while (not xbmc.abortRequested):
            pbx.read()
except:
    xbmc_notification = unicode(str(sys.exc_info()[1]))
    xbmc_img = xbmc.translatePath(os.path.join(RESOURCE_PATH,'media','xbmc-pbx-addon.png'))
    log(">> EXIT Notification: " + xbmc_notification)
    xbmc.executebuiltin("XBMC.Notification("+ __language__(30051) +","+ xbmc_notification +","+ str(15*1000) +","+ xbmc_img +")")
try:
    del grab
    del pbx
except:
    pass


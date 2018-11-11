import xbmc
import resources.lib.utils as utils
from resources.lib.player import Player

class Monitor(xbmc.Monitor):

    def __init__(self, *args):
        self.logMsg("Starting UpNext Service", 0)
        self.logMsg("========  START %s  ========" % utils.addon_name(), 0)
        self.logMsg("KODI Version: %s" % xbmc.getInfoLabel("System.BuildVersion"), 0)
        self.logMsg("%s Version: %s" % (utils.addon_name(), utils.addon_version()), 0)
        self.player = Player()
        xbmc.Monitor.__init__(self)

    def logMsg(self, msg, lvl=1):
        class_name = self.__class__.__name__
        utils.logMsg("%s %s" % (utils.addon_name(), class_name), str(msg), int(lvl))

    def run(self):
        last_file = None

        while not self.abortRequested():
            # check every 1 sec
            if self.waitForAbort(1):
                # Abort was requested while waiting. We should exit
                break
            if self.player.isPlaying():

                try:
                    play_time = self.player.getTime()
                    total_time = self.player.getTotalTime()
                    current_file = self.player.getPlayingFile()
                    notification_time = self.player.notification_time()
                    up_next_disabled = utils.settings("disableNextUp") == "true"
                    if utils.window("PseudoTVRunning") != "True" and not up_next_disabled and total_time > 300:
                        if (total_time - play_time <= int(notification_time) and (
                                last_file is None or last_file != current_file)) and total_time != 0:
                            last_file = current_file
                            self.logMsg("Calling autoplayback totaltime - playtime is %s" % (total_time - play_time), 2)
                            self.player.autoPlayPlayback()
                            self.logMsg("Up Next style autoplay succeeded.", 2)

                except Exception as e:
                    self.logMsg("Exception in Playback Monitor Service: %s" % e)

        self.logMsg("======== STOP %s ========" % utils.addon_name(), 0)

    def onNotification(self, sender, method, data):

        if method.split('.')[1].lower() != 'upnext_data': # method looks like Other.upnext_data
            return

        data = utils.decode_data(data)
        data['id'] = "%s_play_action" % str(sender.replace(".SIGNAL",""))

        self.player.addon_data_received(data)

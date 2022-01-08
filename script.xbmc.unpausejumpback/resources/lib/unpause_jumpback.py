# -*- coding: utf-8 -*-

import xbmc
import time
from resources.lib.common import *

global player
global kodi_monitor


def run():

    global player
    global kodi_monitor

    footprints()

    # Set up our Kodi Monitor & Player...
    kodi_monitor = MyMonitor()
    player = MyPlayer()

    # Run until abort requested
    while not kodi_monitor.abortRequested():
        if kodi_monitor.waitForAbort(1):
            # Abort was requested while waiting. We should exit
            footprints(False)
            break


class MyPlayer(xbmc.Player):

    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        log('MyPlayer - init')

        self.jump_back_on_resume = 0
        self.jump_back_on_playback_started = 0
        self.paused_time = 0
        self.jump_back_secs_after_pause = 0
        self.jump_back_secs_after_fwd_x2 = 0
        self.jump_back_secs_after_fwd_x4 = 0
        self.jump_back_secs_after_fwd_x8 = 0
        self.jump_back_secs_after_fwd_x16 = 0
        self.jump_back_secs_after_fwd_x32 = 0
        self.jump_back_secs_after_rwd_x2 = 0
        self.jump_back_secs_after_rwd_x4 = 0
        self.jump_back_secs_after_rwd_x8 = 0
        self.jump_back_secs_after_rwd_x16 = 0
        self.jump_back_secs_after_rwd_x32 = 0
        self.jump_back_secs_after_resume = 0
        self.last_playback_speed = 0
        self.wait_for_jumpback = 0
        self.exclude_live_tv = True
        self.exclude_http = True
        self.excluded_path_1_enabled = None
        self.excluded_path_2_enabled = None
        self.excluded_path_3_enabled = None
        self.excluded_path_1 = None
        self.excluded_path_2 = None
        self.excluded_path_3 = None

        self.load_settings()

    def load_settings(self):
        """
        Load the addon's settings
        """

        self.jump_back_on_resume = get_setting_as_bool('jumpbackonresume')
        self.jump_back_on_playback_started = get_setting_as_bool('jumpbackonplaybackstarted')
        self.jump_back_secs_after_pause = int(float(get_setting("jumpbacksecs")))
        self.jump_back_secs_after_fwd_x2 = int(float(get_setting("jumpbacksecsfwdx2")))
        self.jump_back_secs_after_fwd_x4 = int(float(get_setting("jumpbacksecsfwdx4")))
        self.jump_back_secs_after_fwd_x8 = int(float(get_setting("jumpbacksecsfwdx8")))
        self.jump_back_secs_after_fwd_x16 = int(float(get_setting("jumpbacksecsfwdx16")))
        self.jump_back_secs_after_fwd_x32 = int(float(get_setting("jumpbacksecsfwdx32")))
        self.jump_back_secs_after_rwd_x2 = int(float(get_setting("jumpbacksecsrwdx2")))
        self.jump_back_secs_after_rwd_x4 = int(float(get_setting("jumpbacksecsrwdx4")))
        self.jump_back_secs_after_rwd_x8 = int(float(get_setting("jumpbacksecsrwdx8")))
        self.jump_back_secs_after_rwd_x16 = int(float(get_setting("jumpbacksecsrwdx16")))
        self.jump_back_secs_after_rwd_x32 = int(float(get_setting("jumpbacksecsrwdx32")))
        self.wait_for_jumpback = int(float(get_setting("waitforjumpback")))
        self.exclude_live_tv = get_setting_as_bool('ExcludeLiveTV')
        self.exclude_http = get_setting_as_bool('ExcludeHTTP')
        self.excluded_path_1_enabled = get_setting_as_bool('ExcludePathOption')
        self.excluded_path_2_enabled = get_setting_as_bool('ExcludePathOption2')
        self.excluded_path_3_enabled = get_setting_as_bool('ExcludePathOption3')
        self.excluded_path_1 = get_setting('ExcludePath')
        self.excluded_path_2 = get_setting('ExcludePath2')
        self.excluded_path_3 = get_setting('ExcludePath3')

        if self.jump_back_on_resume:
            log(f'Settings loaded, jump back set to: On Resume with a jump back of {self.jump_back_secs_after_pause} seconds')
        else:
            log(f'Settings loaded, jump back set to: On Pause with a jump back of {self.jump_back_secs_after_pause} seconds')

    def is_excluded(self, full_path):
        """
        Check exclusion settings for filename passed as argument

        @param full_path: path to check
        @return True or False
        """
        if not full_path:
            return True

        log(f"Checking exclusion for: '{full_path}'.")

        if (full_path.find("pvr://") > -1) and self.exclude_live_tv:
            log("Video is playing via Live TV, which is set as an excluded location.")
            return True

        if ((full_path.find("http://") > -1) or (full_path.find("https://") > -1)) and self.exclude_http:
            log("Video is playing via HTTP source, which is set as an excluded location.")
            return True

        if self.excluded_path_1 and self.excluded_path_1_enabled:
            if full_path.find(self.excluded_path_1) > -1:
                log(f"Video is playing from '{self.excluded_path_1}', which is set as excluded path 1.")
                return True

        if self.excluded_path_2 and self.excluded_path_2_enabled:
            if full_path.find(self.excluded_path_2) > -1:
                log(f"Video is playing from '{self.excluded_path_2}', which is set as excluded path 2.")
                return True

        if self.excluded_path_3 and self.excluded_path_3_enabled:
            if full_path.find(self.excluded_path_3) > -1:
                log(f"Video is playing from '{self.excluded_path_3}', which is set as excluded path 3.")
                return True

        log(f"Not excluded: '{full_path}'")
        return False

    # Default case, Jump Back on Resume
    # This means the pause position is where the user actually paused...which is usually the desired behaviour
    def onPlayBackResumed(self):

        log(f'onPlayBackResumed. {self.jump_back_on_resume}')

        if self.jump_back_on_resume:

            if self.paused_time > 0:
                log(f'Was paused for {int(time.time() - self.paused_time)} seconds.')

            # check for exclusion
            _filename = self.getPlayingFile()
            if self.is_excluded(_filename):
                log(f"Ignored because '{_filename}' is in exclusion settings.")
                return

            else:
                # handle jump back after pause
                if self.jump_back_secs_after_pause != 0 \
                        and self.isPlayingVideo() \
                        and self.getTime() > self.jump_back_secs_after_pause \
                        and self.paused_time > 0 \
                        and (time.time() - self.paused_time) > self.wait_for_jumpback:
                    resume_time = self.getTime() - self.jump_back_secs_after_pause
                    self.seekTime(resume_time)
                    log(f'Resumed, with {int(self.jump_back_secs_after_pause)}s jump back')

                self.paused_time = 0

        # If we're not jumping back on resume, then we should cancel the alarm set if they manually resume playback
        # before it goes off
        else:
            log('Cancelling alarm - playback either resumed or stopped by the user.')
            xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')

    # Alternatively, handle Jump Back on Pause
    # (for low power systems, so it happens in the background during the pause - helps prevents janky-ness)
    def onPlayBackPaused(self):

        # Record when the pause was done
        self.paused_time = time.time()
        log(f'onPlayBackPaused. Time: {self.paused_time}')

        _filename = self.getPlayingFile()
        if self.is_excluded(_filename):
            log(f'Playback paused - ignoring because [{_filename}] is in exclusion settings.')
            return

        # For low power systems, the addon can be set to do the jump back _during_ the pause period
        # Which prevents a janky experience on resume, but has the disadvantage that actual paused image
        # jumps back as well.
        if not self.jump_back_on_resume and self.isPlayingVideo() and 0 < self.jump_back_secs_after_pause < self.getTime():
            jump_back_point = self.getTime() - self.jump_back_secs_after_pause
            log(f'Playback paused - jumping back {self.jump_back_secs_after_pause}s to: {int(jump_back_point)} seconds')
            xbmc.executebuiltin(
                f'AlarmClock(JumpbackPaused, Seek(-{self.jump_back_secs_after_pause})), 0:{self.wait_for_jumpback}, silent)')

    def onAVStarted(self):

        # If the addon is set to do a jump back when playback is started from a resume point...
        if self.jump_back_on_playback_started:
            try:
                current_time = self.getTime()
            except RuntimeError as exc:
                log('No file is playing, stopping UnpauseJumpBack')
                xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')
                pass

            log(f'onAVStarted at {current_time}')

            # check for exclusion
            _filename = self.getPlayingFile()
            if self.is_excluded(_filename):
                log(f"Ignored because '{_filename}' is in exclusion settings.")
                return
            else:
                if current_time > 0 and 0 < self.jump_back_secs_after_pause < current_time:
                    resume_time = current_time - self.jump_back_secs_after_pause
                    log(f"Resuming playback from saved time: {int(current_time)} "
                        f"with jump back seconds: {self.jump_back_secs_after_pause}, "
                        f"thus resume time: {int(resume_time)}")
                    self.seekTime(resume_time)

    def onPlayBackSpeedChanged(self, speed):

        if speed == 1:  # normal playback speed reached
            direction = 1
            abs_last_speed = abs(self.last_playback_speed)
            # default value, just in case
            try:
                resume_time = self.getTime()
            except RuntimeError as exc:
                log('No file is playing, stopping UnpauseJumpBack')
                xbmc.executebuiltin('CancelAlarm(JumpbackPaused, true)')
                pass
                
            if self.last_playback_speed < 0:
                log('Resuming. Was rewound with speed X%d.' % (abs(self.last_playback_speed)))
            if self.last_playback_speed > 1:
                direction = -1
                log('Resuming. Was forwarded with speed X%d.' % (abs(self.last_playback_speed)))
            # handle jump after fwd/rwd (jump back after fwd, jump forward after rwd)
            if direction == -1:  # fwd
                if abs_last_speed == 2:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x2 * direction
                elif abs_last_speed == 4:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x4 * direction
                elif abs_last_speed == 8:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x8 * direction
                elif abs_last_speed == 16:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x16 * direction
                elif abs_last_speed == 32:
                    resume_time = self.getTime() + self.jump_back_secs_after_fwd_x32 * direction
            else:  # rwd
                if abs_last_speed == 2:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x2 * direction
                elif abs_last_speed == 4:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x4 * direction
                elif abs_last_speed == 8:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x8 * direction
                elif abs_last_speed == 16:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x16 * direction
                elif abs_last_speed == 32:
                    resume_time = self.getTime() + self.jump_back_secs_after_rwd_x32 * direction

            if abs_last_speed != 1:  # we really fwd'ed or rwd'ed
                self.seekTime(resume_time)  # do the jump

        self.last_playback_speed = speed


class MyMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        log('MyMonitor - init')

    def onSettingsChanged(self):
        global player
        player.load_settings()



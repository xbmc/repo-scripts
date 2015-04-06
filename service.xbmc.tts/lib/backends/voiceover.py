# -*- coding: utf-8 -*-
import base
import subprocess
import sys
from lib import util

class VoiceOverBackend(base.SimpleTTSBackendBase):
    provider = 'voiceover'
    displayName = 'VoiceOver'

    def init(self):
        self.setMode(base.SimpleTTSBackendBase.ENGINESPEAK)

    def runCommandAndSpeak(self,text):
        subprocess.call(['osascript', '-e', 'tell application "voiceover" to output "{0}"'.format(text.replace('"','').encode('utf-8'))])

    def stop(self):
        subprocess.call(['osascript', '-e', 'tell application "voiceover" to output ""'])

    @staticmethod
    def available():
        return sys.platform == 'darwin' and not util.isATV2()

#on isVoiceOverRunning()
#	set isRunning to false
#	tell application "System Events"
#		set isRunning to (name of processes) contains "VoiceOver"
#	end tell
#	return isRunning
#end isVoiceOverRunning
#
#on isVoiceOverRunningWithAppleScript()
#	if isVoiceOverRunning() then
#		set isRunningWithAppleScript to true
#
#		-- is AppleScript enabled on VoiceOver --
#		tell application "VoiceOver"
#			try
#				set x to bounds of vo cursor
#			on error
#				set isRunningWithAppleScript to false
#			end try
#		end tell
#		return isRunningWithAppleScript
#	end if
#	return false
#end isVoiceOverRunningWithAppleScript
import json
from time import sleep

import variables

import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon()

__music_action__			= int(__addon__.getSetting(variables.__setting_key_music_action_on_call__))
__music_volume__			= int(__addon__.getSetting(variables.__setting_key_music_volume__))
__unmute_music__			= __addon__.getSetting(variables.__setting_key_unmute_music__)
__play_music__				= __addon__.getSetting(variables.__setting_key_play_music__)
__reset_music_volume__		= __addon__.getSetting(variables.__setting_key_reset_music_volume__)

__video_action__			= int(__addon__.getSetting(variables.__setting_key_video_action_on_call__))
__video_volume__			= int(__addon__.getSetting(variables.__setting_key_video_volume__))
__unmute_video__			= __addon__.getSetting(variables.__setting_key_unmute_video__)
__play_video__				= __addon__.getSetting(variables.__setting_key_play_video__)
__reset_video_volume__		= __addon__.getSetting(variables.__setting_key_reset_video_volume__)

__player__ = xbmc.Player()

def load_settings():
	__addon__ = xbmcaddon.Addon()

	global __music_action__
	global __music_volume__
	global __unmute_music__
	global __play_music__
	global __reset_music_volume__

	global __video_action__
	global __video_volume__
	global __unmute_video__
	global __play_video__
	global __reset_video_volume__

	__music_action__			= int(__addon__.getSetting(variables.__setting_key_music_action_on_call__))
	__music_volume__			= int(__addon__.getSetting(variables.__setting_key_music_volume__))
	__unmute_music__			= __addon__.getSetting(variables.__setting_key_unmute_music__)
	__play_music__				= __addon__.getSetting(variables.__setting_key_play_music__)
	__reset_music_volume__		= __addon__.getSetting(variables.__setting_key_reset_music_volume__)

	__video_action__			= int(__addon__.getSetting(variables.__setting_key_video_action_on_call__))
	__video_volume__			= int(__addon__.getSetting(variables.__setting_key_video_volume__))
	__unmute_video__			= __addon__.getSetting(variables.__setting_key_unmute_video__)
	__play_video__				= __addon__.getSetting(variables.__setting_key_play_video__)
	__reset_video_volume__		= __addon__.getSetting(variables.__setting_key_reset_video_volume__)

def on_call_start(data):
	'''
	:param data: The data received by the android-app
	:return: the current volume-level of Kodi
	'''

	load_settings()

	current_volume_level = __get_current_volume_level()

	if __player__.isPlayingAudio():
		if __music_action__ == 1:
			xbmc.executebuiltin('Mute')

		if __music_action__ == 2:
			__player__.pause()

		if __music_action__ == 3:
			__fade_volume_to(__music_volume__)


	if __player__.isPlayingVideo():
		if __video_action__ == 1:
			xbmc.executebuiltin('Mute')

		if __video_action__ == 2:
			__player__.pause()

		if __video_action__ == 3:
			__fade_volume_to(__music_volume__)

	return current_volume_level

def on_call_end(data, resetVolumeTo):
	'''
	:param data: The data received by the android-app
	:param resetVolumeTo: volume-level to reset if activated in the settings
	'''

	load_settings()

	if __player__.isPlayingAudio():
		if __music_action__ == 1 and __unmute_music__:
			xbmc.executebuiltin('Mute')

		if __music_action__ == 2 and __play_music__:
			__player__.play()

		if __music_action__ == 3 and __reset_music_volume__:
			__fade_volume_to(resetVolumeTo)


	if __player__.isPlayingVideo():
		if __video_action__ == 1 and __unmute_video__:
			xbmc.executebuiltin('Mute')

		if __video_action__ == 2 and __play_video__:
			__player__.play()

		if __video_action__ == 3 and __reset_video_volume__:
			__fade_volume_to(resetVolumeTo)

def __get_current_volume_level():
	'''
	:return: Returns the current volume set in kodi
	'''
	return json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": ["volume"] }, "id": 1}'))['result']['volume']

def __fade_volume_to(volume_to):
	'''
	:param volume_to: the volume to set in kodi
	'''
	volume_from = __get_current_volume_level()

	if volume_to > volume_from:
		for vol in range(volume_from, volume_to, 3):
			xbmc.executebuiltin('XBMC.SetVolume(%d, showvolumebar)' % (vol))
			sleep(0.1)
	elif volume_to < volume_from:
		for vol in range(volume_from, volume_to, -3):
			xbmc.executebuiltin('XBMC.SetVolume(%d, showvolumebar)' % (vol))
			sleep(0.1)


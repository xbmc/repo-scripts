import os
import hashlib

import variables

import xbmc
import xbmcaddon

__addon__ 		= xbmcaddon.Addon()
__tmp_dir__		= os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8'), 'tmp')

def post_notification(id, app_name, title, text, big_text, info_text, ticker_text, sub_text, display_time, large_icon, app_icon, small_icon):
	'''
	:param id: ID of the notification
	:param app_name: Name of the app
	:param title: Title of the notification
	:param text: Text of the notification
	:param big_text: Big-Text of the notification
	:param info_text: Info-Text of the notification
	:param ticker_text: Ticker-Text of the notification
	:param sub_text: Sub-Text of the notification
	:param display_time: How long the notification should be displayed in ms
	:param large_icon: Large-Icon of the notification
	:param app_icon: App-Icon of the app which posted the notification
	:param small_icon: Small-Icon of the notification
	'''

	'''
	Create a tmp-dir to save the notification icons to if not already exist
	'''
	if not os.path.exists(__tmp_dir__):
		os.makedirs(__tmp_dir__)


	'''
	Define the notification-text to show
	'''
	notification_text = ''
	if big_text != '':
		notification_text = big_text
	elif text != '':
		notification_text = text
	elif ticker_text != '':
		notification_text = ticker_text

	if sub_text != '':
		notification_text += '\n' + sub_text

	notification_text = notification_text.replace('\n', ' ').replace('\r', ' ')

	'''
	Specify the target files and try to save the first
	image which is not empty in a specific order:
		1. large_icon
		2. app_icon
		3. small_icon
	'''
	large_icon_data = large_icon.get('data')
	app_icon_data = app_icon.get('data')
	small_icon_data = small_icon.get('data')

	large_icon_path = os.path.join(__tmp_dir__, hashlib.md5(large_icon_data).hexdigest())
	app_icon_path = os.path.join(__tmp_dir__, hashlib.md5(app_icon_data).hexdigest())
	small_icon_path = os.path.join(__tmp_dir__, hashlib.md5(small_icon_data).hexdigest())

	notification_icon = None
	if large_icon_data != '':
		with open(large_icon_path, 'w') as f:
			f.write(large_icon_data.decode('base64'))
		notification_icon = large_icon_path
	elif app_icon_data != '':
		with open(app_icon_path, 'w') as f:
			f.write(app_icon_data.decode('base64'))
		notification_icon = app_icon_path
	elif small_icon_data != '':
		with open(small_icon_path, 'w') as f:
			f.write(small_icon_data.decode('base64'))
		notification_icon = small_icon_path


	'''
	We remove all previously saved images (excluding the current one) BEFORE showing the notification so
	we can make sure Kodi does have the image to show.
	This way we make sure the image exists long enough for the notification to display it properly
	and also clean up all the old images.
	'''
	for file in os.listdir(__tmp_dir__):
		file_path = os.path.join(__tmp_dir__, file)
		if file_path != notification_icon:
			os.remove(file_path)

	'''
	Post the notification to the user
	'''
	xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (title, notification_text, display_time, notification_icon))
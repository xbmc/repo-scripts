import os
import site
import socket

import variables

import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon()

'''
We add our resources/lib directory to path-variable so we can import modules out of it
'''
site.addsitedir(os.path.join(xbmc.translatePath( __addon__.getAddonInfo('path')), 'resources', 'lib'))
import qrcode

'''
The QR-Code module used need the PIL (Python Image Library) to draw
the image. On some platforms (like android) PIL isn't available so
we check for the availability of this module and in case it is not
available we show a notification informing the user about it
'''
try:
	import PIL
	pil_available = True
except ImportError:
	pil_available = False


def show_qr_code(host, port, is_auth_enabled, username=None, password=None):
	'''
	:param host: hostname or ip
	:param port: port
	:param is_auth_enabled: if basic auth is enabled or not
	:param username: username
	:param password: password
	'''

	'''
	Define the temporary directory, file path und the string we want to display via a QR-Code
	'''
	tmp_dir	= os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8'), 'tmp')
	tmp_file = os.path.join(tmp_dir, 'qr-code.png')

	if not os.path.exists(tmp_dir):
		os.makedirs(tmp_dir)

	qr_string = host + ':' + port

	if is_auth_enabled:
		if username != '' and password != '':
			qr_string = username + ':' + password + '@' + qr_string

	'''
	Create the actual image and save it to our temp direcotry
	'''
	qr = qrcode.main.QRCode(box_size=40, border=2)
	qr.add_data(qr_string)
	qr.make(fit=True)
	img = qr.make_image()
	img.save(tmp_file)

	'''
	Show the QR-Code in Kodi
	'''
	xbmc.executeJSONRPC(
		'{"jsonrpc": "2.0", "method": "Player.Open", "params": { "item": {"file":"' + tmp_file + '"} }, "id": 1}')


if __name__ == '__main__':
	if pil_available:
		'''
		Get all the needed values from the Addon-Settings
		'''
		host = xbmc.getIPAddress()
		port = __addon__.getSetting(variables.__setting_key_port__)

		is_auth_enabled	 = __addon__.getSetting(variables.__setting_key_base_auth_enabled__)
		username = __addon__.getSetting(variables.__setting_key_username__)
		password = __addon__.getSetting(variables.__setting_key_password__)

		'''
		We get the hostname of the client and try to resolve it within
		the network.
		If this works we send the hostname, if not we use the IP-Address
		'''
		try:
			hostname = socket.gethostname()
			socket.gethostbyname(hostname)
			host = hostname
		except socket.gaierror:
			pass

		'''
		Show the QR-Code to the user
		'''
		show_qr_code(host, port, is_auth_enabled, username, password)
	else:
		'''
		The PIL module isn't available so we inform the user about it
		'''
		xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (__addon__.getLocalizedString(200), __addon__.getLocalizedString(201), 10000, os.path.join(xbmc.translatePath( __addon__.getAddonInfo('path')), 'icon.png')))

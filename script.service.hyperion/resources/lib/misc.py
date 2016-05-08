'''
    Kodi video capturer for Hyperion
	
	Copyright (c) 2013-2016 Hyperion Team

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in
	all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
	THE SOFTWARE.
'''
import xbmc
import xbmcaddon

def log(msg):
	'''Write a debug message to the Kodi log
	'''
	addon = xbmcaddon.Addon()
	xbmc.log("### [%s] - %s" % (addon.getAddonInfo('name'),msg,), level=xbmc.LOGDEBUG)

def notify(msg):
	'''Show a notification in Kodi
	'''
	addon = xbmcaddon.Addon()
	xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % \
		(addon.getAddonInfo('name'), msg, 1000, addon.getAddonInfo('icon')))
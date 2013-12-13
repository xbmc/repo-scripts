import xbmc, xbmcaddon

__addon__	= xbmcaddon.Addon()
__addonid__  = __addon__.getAddonInfo('id')

def log(txt):
	if isinstance (txt,str):
		txt = txt.decode("utf-8")
	message = u'%s - XBMC Start : %s' % (__addonid__, txt)
	xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGNOTICE)
	
def checkStartup():
	if __addon__.getSetting('onstart') == 'true':
		url = __addon__.getSetting('path')
		if __addon__.getSetting('xbmc_slideshow') == 'true' and url.startswith('plugin:'):
			log('STARTING')
			url = url.replace('/?','?')
			url += '&plugin_slideshow_ss=true'
			log('Slideshow URL: %s' % url)
			randomize = ''
			if __addon__.getSetting('randomize') == 'true': randomize = 'random'
			xbmc.executebuiltin('SlideShow(%s,%s)' % (url,randomize))
		else:
			log('STARTING')
			from pluginscreensaver import Screensaver
			Screensaver('plugin-slideshow-screensaver.xml', __addon__.getAddonInfo('path'), 'default').doModal()
			del Screensaver
			
	else:
		log('DISABLED')

log('Version: ' + __addon__.getAddonInfo('version'))
log('CHECK')
checkStartup()
log('DONE')

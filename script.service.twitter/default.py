import urllib,urllib2,re,xbmc,xbmcaddon,xbmcgui,os,sys
import word_resolver
try:
	from elementtree.SimpleXMLWriter import XMLWriter
except:
	from dummyelementtree.SimpleXMLWriter import XMLWriter

settings = xbmcaddon.Addon( id = 'script.service.twitter' )
translation = settings.getLocalizedString
twitter_icon = os.path.join( settings.getAddonInfo( 'path' ), 'icon.png' )
userdata = xbmc.translatePath('special://userdata/keymaps')
twitter_file = os.path.join(userdata, 'twitter.xml')




def _record_key():
    	dialog = KeyListener()
    	dialog.doModal()
    	key = dialog.key
    	del dialog
	w = XMLWriter(twitter_file, "utf-8")
	doc = w.start("keymap")
	w.start("global")
	w.start("keyboard")
        w.element("key", "addon.opensettings(script.service.twitter)", id=str(key))
	w.end()
	w.end()
	w.start("fullscreenvideo")
	w.start("keyboard")
	w.element("key", "addon.opensettings(script.service.twitter)", id=str(key))
	w.end()
	w.end()
	w.end()
	w.close(doc)

class KeyListener(xbmcgui.WindowXMLDialog):
  def __new__(cls):
    return super(KeyListener, cls).__new__(cls, "DialogKaiToast.xml", "")
  
  def onInit(self):
    try:
      self.getControl(401).addLabel(translation(30008))
      self.getControl(402).addLabel(translation(30009))
    except:
      self.getControl(401).setLabel(translation(30008))
      self.getControl(402).setLabel(translation(30009))
  
  def onAction(self, action):
    self.key = action.getButtonCode()
    self.close()

class TextBox:
    # constants
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    def __init__(self, *args, **kwargs):
        # activate the text viewer window
        xbmc.executebuiltin("ActivateWindow(%d)" % ( self.WINDOW, ))
        # get window
        self.win = xbmcgui.Window(self.WINDOW)
        # give window time to initialize
        xbmc.sleep(1000)
        self.setControls()

    def setControls(self):
        # set heading
        heading = translation(30011)
        self.win.getControl(self.CONTROL_LABEL).setLabel(heading)
        # set text
        root = settings.getAddonInfo( 'path' )
        faq_path = os.path.join(root, 'instructions.txt')
        f = open(faq_path)
        text = f.read()
        self.win.getControl(self.CONTROL_TEXTBOX).setText(text)

try:
	if sys.argv[1] == 'set_key':
		_record_key() 
		xbmc.sleep(1000)
		xbmc.executebuiltin('Action(reloadkeymaps)')
		sys.exit(0)
except:
	pass

try:
	if sys.argv[1] == 'display_file':
		TextBox()
		sys.exit(0)
except:
	pass

if (not settings.getSetting("firstrun")):
	dialog = xbmcgui.Dialog()
	tosetkey = dialog.yesno(translation(30011),translation(30012), translation(30013), translation(30014))
	if tosetkey == True:
		_record_key() 
		xbmc.sleep(1000)
		xbmc.executebuiltin('Action(reloadkeymaps)')
	else:
		dialog.ok(translation(30011),translation(30015),translation(30016))
	settings.setSetting("firstrun", "1")
	settings.openSettings()


while (not xbmc.abortRequested):


	try:
		if sys.argv[1] == 'display_file':
			go = False
		if sys.argv[1] == 'set_key':
			go = False
	except:
		go = True

	if go == True:
		if settings.getSetting("enable_service") == 'true':
			try:
				old_text = old_text
			except:
				old_text = ''
			language = settings.getSetting('language')
			language = re.sub("( \(.*?\))", "", language)
			language = word_resolver.lang(language)
			search_string = settings.getSetting("search_string")
			search_string = word_resolver.searchstr(search_string)
			if language != 'all':
				search_string = search_string + '%20lang%3A'+language
			display_time = settings.getSetting("display_time")
			display_time = str(display_time)+'000'
			display_time = int(display_time)
			wait_time = settings.getSetting("wait_time")
			wait_time = str(wait_time)+'000'
			wait_time = int(wait_time)
			req = urllib2.Request('http://www.twitter.com/search?q='+search_string+'&f=realtime')
			req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
			response = urllib2.urlopen(req)
			link=response.read()
			response.close()
			try:
				mistweet = re.compile('(data-promoted)').findall(link)
				mistweet2 = re.compile('(data-relevance-type)').findall(link)
				test_tweet = len(mistweet) + len(mistweet2)
				name=re.compile('data-screen-name="(.+?)" data-name="(.+?)"').findall(link)
				name=str(name[test_tweet])
				name=re.compile("'(.+?)'").findall(name)
				username=str(name[0])
				dispname=str(name[1])
				dispname=word_resolver.name(dispname)
				xbmc.log('Twitter URL = '+'http://www.twitter.com/search?q='+search_string+'&f=realtime'+'   Number of tweets to skip = '+str(test_tweet))
				text=re.compile('<p class="js-tweet-text tweet-text">(.+?)</p>').findall(link)
				text=text[test_tweet]
				text = word_resolver.text(text)
				if old_text != text:
					xbmc.executebuiltin('XBMC.Notification("%s","%s",%d,"%s")' % (dispname+'  @'+username, text, display_time, twitter_icon))
					xbmc.sleep(wait_time)
					old_text = text
				else:
					xbmc.sleep(500)
			except:
				xbmc.log('No Twitter Results, URL = '+'http://www.twitter.com/search?q='+search_string+'&f=realtime')
				xbmc.executebuiltin('XBMC.Notification("%s", "%s")' % (translation(30017),translation(30018)))
				xbmc.sleep(500)			
		
		else:
			xbmc.sleep(1000)
	


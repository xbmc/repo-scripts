import urllib
import xbmc, xbmcgui, xbmcaddon
import sys, os, time, re
import elementtree.ElementTree as etree
import jsonrpc
import difflib

__author__ = 'ruuk'
__url__ = 'http://code.google.com/p/tvragexbmc/'
__date__ = '10-07-2010'
__version__ = '0.9.5'
__settings__ = xbmcaddon.Addon(id='script.tvrage.com')
__language__ = __settings__.getLocalizedString

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources') )
sys.path.append (BASE_RESOURCE_PATH)

IMAGE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'skin','Default','media') )
THUMB_PATH = xbmc.translatePath('special://profile/addon_data/script.tvrage.com/images')
if not os.path.exists(THUMB_PATH): os.makedirs(THUMB_PATH)

ACTION_MOVE_LEFT      = 1
ACTION_MOVE_RIGHT     = 2
ACTION_MOVE_UP        = 3
ACTION_MOVE_DOWN      = 4
ACTION_PAGE_UP        = 5
ACTION_PAGE_DOWN      = 6
ACTION_SELECT_ITEM    = 7
ACTION_HIGHLIGHT_ITEM = 8
ACTION_PARENT_DIR     = 9
ACTION_PREVIOUS_MENU  = 10
ACTION_SHOW_INFO      = 11
ACTION_PAUSE          = 12
ACTION_STOP           = 13
ACTION_NEXT_ITEM      = 14
ACTION_PREV_ITEM      = 15
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_CONTEXT_MENU   = 117

class Show:
	def __init__(self,showid='',xmltree=None,offset=0):
		self.offset = offset
		self.showid = showid
		self.name = ''
		self.airtime = ''
		self.next = {}
		self.last = {}
		self.imagefile = os.path.join(THUMB_PATH,self.showid + '.jpg')
		self.nextUnix = 0
		self.status = ''
		self.canceled = ''
		self.lastEp = {'number':'?','title':'Unknown','date':'?'}
		self.nextEp = {'number':'?','title':'Unknown','date':'?'}
		if xmltree:
			self.tree = xmltree
			self.processTree(xmltree)
		
	def getShowData(self):
		tree = API.getShowInfo(self.showid)
		self.processTree(tree)
		return self
		
	def processTree(self,show):
		sid = show.attrib.get('id',self.showid)
		#if no show id keep our data
		if not sid: return
		self.showid = sid
		self.tree = show
		self.imagefile = os.path.join(THUMB_PATH,self.showid + '.jpg')
		self.name = show.find('name').text
		
		try: self.airtime = re.findall('\d+:\d\d\s\w\w',show.find('airtime').text)[0]
		except: pass
		if not self.airtime:
			try: self.airtime = show.find('airtime').text.rsplit('at ',1)[-1]
			except: pass
			
		self.status = show.find('status').text
		if 'Ended' in self.status or 'Cancel' in self.status:
			ended = show.find('ended').text
			sc = '?'
			if ended:
				try: sc = time.strftime('%b %d %Y',time.strptime(ended,'%Y-%m-%d'))
				except: pass
				if not sc:
					try: sc = time.strftime('%b %Y',time.strptime(ended,'%Y-%m-00'))
					except: pass
			self.canceled = sc
			
		last = show.find('latestepisode')
		self.lastEp = self.epInfo(last)
		
		next = show.find('nextepisode')
		if next: self.nextEp = self.epInfo(next)
		
		if not os.path.exists(self.imagefile):
			iurl = 'http://images.tvrage.com/shows/'+str(int(self.showid[0:-3]) + 1)+'/'+self.showid + '.jpg'
			saveURLToFile(iurl,self.imagefile)
		
		if self.offset: self.getOffsetAirtime()
		
	def getOffsetAirtime(self):
		self.getNextUnix(forceupdate=True)
		self.nextUnix += (self.offset * 3600)
		self.airtime = time.strftime('%I:%M %p',time.localtime(self.nextUnix))
		
	def epInfo(self,eptree):
		try: 		return {'number':eptree.find('number').text,'title':eptree.find('title').text,'date':eptree.find('airdate').text}
		except: 	return {'number':'?','title':'Unknown','date':'?'}
		
	def getSortValue(self):
		srt = self.getNextUnix(forceupdate=True)
		return str(srt) + '@' + self.name
		
	def getNextUnix(self,forceupdate=False):
		if forceupdate or not self.nextUnix:
			try:
				struct = time.strptime(self.nextEp['date'] + ' ' + self.airtime,'%Y-%m-%d %I:%M %p')
				srt = time.mktime(struct)
			except:
				srt = time.time()+60*60*24*365*10
				if self.canceled: srt += 3600
			self.nextUnix = srt
		return self.nextUnix
		
	def xml(self):
		return etree.tostring(self.tree)

		"""
			<link>http://www.tvrage.com/Futurama</link>
			<started>1999-03-28</started>
			<ended/>
			<country>USA</country>
			<classification>Animation</classification>
			<genres>
			<genre>Adult Cartoons</genre>
			<genre>Comedy</genre>
			<genre>Sci-Fi</genre>
			</genres>
			<runtime>30</runtime>
			<ended>1969-06-03</ended>
		"""
		
class Episode:
	_image_url_base = 'http://images.tvrage.com/screencaps/'

	def __init__(self,season,xmltree=None,showid=''):
		self.number = ''
		self.season = season
		self.prodnum = ''
		self.airdate = ''
		self.title = ''
		self.epnum = ''
		self.link = ''
		self.epid = ''
		self.showid = showid
		if xmltree:
			self.processTree(xmltree)
	
	def processTree(self,tree):
		self.title = tree.find('title').text
		self.number = tree.find('epnum').text
		self.epnum = tree.find('seasonnum').text
		self.airdate = tree.find('airdate').text
		self.prodnum = tree.find('prodnum').text
		self.link = tree.find('link').text
		self.epid = self.link.rsplit('/',1)[-1]
		
	def getEPxSEASON(self):
		return self.season + 'x' + self.epnum
	
	def getImageUrls(self):
		#This seems to work but...
		num = int(int(self.showid) / 200) + 1
		base = self._image_url_base + str(num) + '/' + self.showid + '/' + self.epid
		return (base + '.jpg',base + '.png')


class TVRageAPI:
	_search_url = 'http://services.tvrage.com/feeds/search.php?show='
	_info_url = 'http://services.tvrage.com/feeds/episodeinfo.php?sid='
	_eplist_url = 'http://services.tvrage.com/feeds/episode_list.php?sid='
	
	def getShowInfo(self,showid):
		url = self._info_url + str(showid)
		return self.getTree(url)
		
	def search(self,show):
		url = self._search_url + urllib.quote_plus(show)
		return self.getTree(url)
		
	def getEpList(self,showid):
		url = self._eplist_url + str(showid)
		return self.getTree(url)
		
	def getTree(self,url):
		xml = self.getURLData(url,readlines=False)
		return etree.fromstring(xml)
		
	def getEpSummary(self,url):
		html = self.getURLData(url,readlines=False)
		html = html.split('>Episode Summary</h')[-1]
		return re.findall('<br>(.*?)<br>',html,re.S)[0].strip()
	
	def getURLData(self,url,readlines=True):
		try:
			w = urllib.urlopen(url)
		except:
			return None
		try:
			if readlines: linedata = w.readlines()
			else: linedata = w.read()
		except:
			w.close()
			return None
		w.close()
		return linedata

class SummaryDialog(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
		self.link = kwargs.get('link','')
	
	def onInit(self):
		self.getControl(120).setText(__language__(30025))
		summary = self.htmlToText(API.getEpSummary(self.link))
		self.getControl(120).setText(summary)
		self.setFocusId(121)
		
	def onClick( self, controlId ):
		pass
                       
	def onFocus( self, controlId ):
		self.controlId = controlId
	
	def onAction(self,action):
		if action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		xbmcgui.WindowXMLDialog.onAction(self,action)
		
	def htmlToText(self,html):
		html = re.sub('<.*?>','',html)
		return html	.replace("&lt;", "<")\
					.replace("&gt;", ">")\
					.replace("&amp;", "&")\
					.replace("&quot;",'"')\
					.replace("&apos;","'")

class EpListDialog(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
		self.sid = kwargs.get('sid','')
		self.imagefile = os.path.join(THUMB_PATH,self.sid + '.jpg')
	
	def onInit(self):
		self.showEpList(self.sid)
		self.setFocusId(120)
		
	def onClick( self, controlId ):
		pass
                       
	def onFocus( self, controlId ):
		self.controlId = controlId
		
	def onAction(self,action):
		if action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		elif action == ACTION_SELECT_ITEM:
			self.summary()
		elif action == ACTION_MOUSE_LEFT_CLICK:
			if self.getFocusId() == 120: self.summary()
		xbmcgui.WindowXMLDialog.onAction(self,action)
			
	def summary(self):
		item = self.getControl(120).getSelectedItem()
		link = item.getProperty('link')
		w = SummaryDialog("script-tvrage-summary.xml" , os.getcwd(), "Default",link=link)
		w.doModal()
		del w
		
	def showEpList(self,sid):
		result = API.getEpList(sid)
		show = result.find('name').text
		self.getControl(100).setLabel(show)
		self.getControl(102).setImage(self.imagefile)
		
		self.getControl(120).reset()
		xbmcgui.lock()
		for season in result.find('Episodelist').findall('Season'):
			snum = season.attrib.get('no','')
			for e in season.findall('episode'):
				ep = Episode(snum,e,sid)
				iurls = ep.getImageUrls()
				item = xbmcgui.ListItem(label=ep.getEPxSEASON(),label2=ep.title,iconImage=iurls[1],thumbnailImage=iurls[0])
				item.setProperty('date',ep.airdate)
				item.setProperty('link',ep.link)
				self.getControl(120).addItem(item)
		xbmcgui.unlock()
				
class TVRageEps(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
	
	def onInit(self):
		self.lastUpdateFile = xbmc.translatePath('special://profile/addon_data/script.tvrage.com/last')
		self.dataFile = xbmc.translatePath('special://profile/addon_data/script.tvrage.com/data')
		hours = __settings__.getSetting('hours_between_updates')
		self.http_user = __settings__.getSetting('xbmc_http_user')
		self.http_pass = __settings__.getSetting('xbmc_http_pass')
		air_offset = __settings__.getSetting('air_offset')
		self.skip_canceled = (__settings__.getSetting('skip_canceled') == 'true')
		self.reverse_sort = (__settings__.getSetting('reverse_sort') == 'true')
		self.jump_to_bottom = (__settings__.getSetting('jump_to_bottom') == 'true')
		self.hours = [1,2,3,4,5,6,12,24][int(hours)]
		self.air_offset = [-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,8,9,10,11,12][int(air_offset)]
		
		self.shows = []
		self.loadData()
		self.update(force=self.isStale())

		self.setFocus(self.getControl(120))
	
	def isStale(self):
		last = self.fileRead(self.lastUpdateFile)
		if not last: return True
		return (time.time() - (3600 * self.hours) > float(last))
		
	def setLast(self):
		self.fileWrite(self.lastUpdateFile,str(time.time()))
		
	def onClick( self, controlId ):
		pass
                       
	def onFocus( self, controlId ):
		self.controlId = controlId

	def update(self,force=False):
		if force:
			self.updateData()
			self.saveData()
		self.updateDisplay()
		
	def addShow(self,sid):
		pdialog = xbmcgui.DialogProgress()
		pdialog.create(__language__(30016))
		pdialog.update(0)
		for s in self.shows:
			if s.showid == sid:
				pdialog.close()
				xbmcgui.Dialog().ok(__language__(30014),__language__(30015))
				return
		self.doAddShow(sid)
		self.saveData()
		pdialog.close()
		
	def doAddShow(self,sid,skipCanceled=False):
		show = Show(showid=sid,offset=self.air_offset).getShowData()
		if skipCanceled and show.canceled: return
		self.shows.append(show)
		
	def onAction(self,action):
		#print "ACTION: " + str(action.getId()) + " FOCUS: " + str(self.getFocusId()) + " BC: " + str(action.getButtonCode())
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		elif action == ACTION_SELECT_ITEM:
			self.eplist()
		elif action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		elif action == ACTION_MOUSE_LEFT_CLICK:
			if self.getFocusId() == 200:
				self.search()
			elif self.getFocusId() == 120:
				self.eplist()
		xbmcgui.WindowXMLDialog.onAction(self,action)
			
	def doMenu(self):
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30011),[__language__(30007),__language__(30026),__language__(30013),__language__(30006)])
		if idx == 0: self.search()
		elif idx == 1: self.addFromLibrary()
		elif idx == 2: self.reverse()
		elif idx == 3: self.deleteShow()
		
	def search(self):
		keyboard = xbmc.Keyboard('',__language__(30005))
		keyboard.doModal()
		if not keyboard.isConfirmed(): return
		term = keyboard.getText()
		pdialog = xbmcgui.DialogProgress()
		pdialog.create(__language__(30017))
		pdialog.update(0)
		result = API.search(term)
		pdialog.close()
		sid = self.userPickShow(result)
		if not sid: return
		self.addShow(sid)
		self.updateDisplay()

	def userPickShow(self,result,append=''):
		slist = []
		sids = []
		for s in result.findall('show'):
			slist.append(s.find('name').text)
			sids.append(s.find('showid').text)
		dialog = xbmcgui.Dialog()
		if append: append = ': ' + append
		idx = dialog.select(__language__(30008) + append,slist)
		if idx < 0: return None
		return sids[idx]
		
	def addFromLibrary(self):
		pdialog = xbmcgui.DialogProgress()
		pdialog.create(__language__(30027))
		try:
			pdialog.update(0)
			jrapi = jsonrpc.jsonrpcAPI(user=self.http_user,password=self.http_pass)
			try:
				shows = jrapi.VideoLibrary.GetTVShows()
			except jsonrpc.UserPassError:
				xbmcgui.Dialog().ok(__language__(30031),__language__(30032),__language__(30033),__language__(30034))
				return
			except jsonrpc.ConnectionError:
				xbmcgui.Dialog().ok(__language__(30031),__language__(30035),__language__(30036),__language__(30037))
				return
			tot = len(shows['tvshows'])
			ct=0.0
			for s in shows['tvshows']:
				title = s['label']
				pdialog.update(int((ct/tot)*100),title)
				for c in self.shows:
					if difflib.get_close_matches(title,[c.name],1,0.7):
						print "SHOW: " + title + " - EXISTS AS: " + c.name
						break
				else:
					result = API.search(title)
					#result = API.search(re.sub('(.*?)','',title.lower().replace('the ','')))
					matches = {}
					for f in result.findall('show'):
						matches[f.find('name').text] = f.find('showid').text
					close = difflib.get_close_matches(title,matches.keys(),1,0.8)
					if close:
						print "SHOW: " + title + " - MATCHES: " + close[0]
						pdialog.update(int((ct/tot)*100),__language__(30028) + title)
						self.doAddShow(matches[close[0]],skipCanceled=self.skip_canceled)
					else:
						sid = self.userPickShow(result,append=title)
						if sid: self.doAddShow(sid)
				ct+=1
			self.saveData()
			self.updateDisplay()
		finally:
			pdialog.close()
					
	def addShow(self,sid,okdialog=True,name=''):
		pdialog = xbmcgui.DialogProgress()
		pdialog.create(__language__(30016),name)
		pdialog.update(0)
		for s in self.shows:
			if s.showid == sid:
				pdialog.close()
				if okdialog: xbmcgui.Dialog().ok(__language__(30014),__language__(30015))
				return
		self.shows.append(Show(showid=sid).getShowData())
		self.saveData()
		pdialog.close()
			
	
	def reverse(self):
		self.reverse_sort = not self.reverse_sort
		self.updateDisplay()
		
	def deleteShow(self):
		item = self.getControl(120).getSelectedItem()
		sid = item.getProperty('id')
		ct=0
		for s in self.shows:
			if s.showid == sid:
				break
			ct+=1
		dialog = xbmcgui.Dialog()
		choice = dialog.yesno(__language__(30009),__language__(30010).replace('@REPLACE@',s.name))
		if not choice: return
		self.shows.pop(ct)
		self.saveData()
		self.updateDisplay()
		
	def eplist(self):
		item = self.getControl(120).getSelectedItem()
		sid = item.getProperty('id')
		w = EpListDialog("script-tvrage-eplist.xml" , os.getcwd(), "Default",sid=sid)
		w.doModal()
		del w
	
	def loadData(self):
		xml = self.fileRead(self.dataFile)
		try:
			shows = etree.fromstring(xml)
		except:
			print "Empty XML or XML Error"
			return
		for s in shows.findall('show'):
			self.shows.append(Show(xmltree=s,offset=self.air_offset))
			
	def saveData(self):
		sl = ['<shows>']
		for show in self.shows:
			sl.append(show.xml())
		sl.append('</shows>')
		self.fileWriteList(self.dataFile,sl)
			
	def updateProgress(self,level,lmax,text):
		percent = int((float(level)/lmax)*100)
		self.progress.update(percent,text)
		
	def updateData(self):
		self.progress = xbmcgui.DialogProgress()
		self.progress.create(__language__(30003),__language__(30004))
		lmax = len(self.shows)
		ct=0
		for show in self.shows:
			if not show.canceled: show.getShowData()
			ct+=1
			self.updateProgress(ct,lmax,show.name)
		self.progress.close()
		self.setLast()
		
	def updateDisplay(self):
		disp = {}
		for show in self.shows:
			disp[show.getSortValue()] = show
		sortd = disp.keys()
		sortd.sort()
		if self.reverse_sort: sortd.reverse()
		self.getControl(120).reset()
		xbmcgui.lock()
		for k in sortd:
			show = disp[k]
			nextUnix = show.getNextUnix()
			
			try: 	showdate = time.strftime('%a %b %d',time.strptime(show.nextEp['date'],'%Y-%m-%d'))
			except:	showdate = show.canceled
			
			item = xbmcgui.ListItem(label=show.name,label2=showdate)
			if time.strftime('%j:%Y',time.localtime()) == time.strftime('%j:%Y',time.localtime(nextUnix)):
				item.setInfo('video',{"Genre":'today'})
			elif time.strftime('%j:%Y',time.localtime(time.time() + 86400)) == time.strftime('%j:%Y',time.localtime(nextUnix)):
				item.setInfo('video',{"Genre":'tomorrow'})
			else:
				item.setInfo('video',{"Genre":''})
						
			item.setProperty("summary",show.airtime)
			if show.canceled: item.setProperty("summary",__language__(30030))
			
			item.setProperty("updated",show.nextEp['number'] + ' ' + show.nextEp['title'])
			if show.canceled: item.setProperty("updated",__language__(30029))
			item.setProperty("last",__language__(30012) + ' ' + show.lastEp['number'] + ' ' + show.lastEp['title'] + ' ' + show.lastEp['date'])
			item.setProperty("image",show.imagefile)
			item.setProperty("id",show.showid)
			self.getControl(120).addItem(item)
		if self.jump_to_bottom: self.getControl(120).selectItem(self.getControl(120).size()-1)
		xbmcgui.unlock()
		
	def fileRead(self,file):
		if not os.path.exists(file): return ''
		f = open(file,'r')
		data = f.read()
		f.close()
		return data
	
	def fileReadList(self,file):
		return self.fileRead(file).splitlines()
		
	def fileWrite(self,file,data):
		f = open(file,'w')
		f.write(data)
		f.close()

	def fileWriteList(self,file,dataList):
		self.fileWrite(file,'\n'.join(dataList))

		
def saveURLToFile(url,file,hook=None,e_hook=None):
	try:
		urllib.urlretrieve(url,file,hook)
	except:
		if e_hook: ehook()

API = TVRageAPI()

w = TVRageEps("script-tvrage-main.xml" , os.getcwd(), "Default")
w.doModal()
del w
sys.modules.clear()
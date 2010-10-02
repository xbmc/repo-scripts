import urllib
import xbmc, xbmcgui, xbmcaddon
import sys, os, time, re
import elementtree.ElementTree as etree

__author__ = 'ruuk'
__url__ = 'http://code.google.com/p/tvragexbmc/'
__date__ = '10-02-2010'
__version__ = '0.9.1'
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
ACTION_CONTEXT_MENU   = 117

class Show:
	def __init__(self,showid='',xmltree=None):
		self.showid = showid
		self.name = ''
		self.airtime = ''
		self.next = {}
		self.last = {}
		self.imagefile = os.path.join(THUMB_PATH,self.showid + '.jpg')
		self.nextUnix = 0
		self.status = ''
		self.cancelled = False
		self.lastEp = {'number':'?','title':'?','date':'?'}
		self.nextEp = {'number':'?','title':'?','date':'?'}
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
		
		try: self.airtime = show.find('airtime').text.rsplit('at ',1)[-1]
		except: pass
		
		self.status = show.find('status').text
		if 'Ended' in self.status or 'Cancel' in self.status:
			self.cancelled = True
			
		last = show.find('latestepisode')
		self.lastEp = self.epInfo(last)
		
		next = show.find('nextepisode')
		if next: self.nextEp = self.epInfo(next)
		
		if not os.path.exists(self.imagefile):
			iurl = 'http://images.tvrage.com/shows/'+str(int(self.showid[0:-3]) + 1)+'/'+self.showid + '.jpg'
			saveURLToFile(iurl,self.imagefile)
		
	def epInfo(self,eptree):
		try: 		return {'number':eptree.find('number').text,'title':eptree.find('title').text,'date':eptree.find('airdate').text}
		except: 	return {'number':'?','title':'?','date':'?'}
		
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
				if self.cancelled: srt += 3600
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
		url = self._search_url + show
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
		self.getControl(120).setText('Loading summary...')
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
		self.hours = [1,2,3,4,5,6,12,24][int(hours)]
		
		self.shows = []
		self.loadData()
		self.update(force=self.isStale())
		self.getControl(100).setLabel(__language__(30013))

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
		self.shows.append(Show(showid=sid).getShowData())
		self.saveData()
		pdialog.close()
		
	#def onControl(self, control):
	#	if control == self.clist:
	#		item = self.list.getSelectedItem()
	
	def onAction(self,action):
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		elif action == ACTION_SELECT_ITEM:
			self.eplist()
		elif action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		xbmcgui.WindowXMLDialog.onAction(self,action)
			
	def doMenu(self):
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30011),[__language__(30007),__language__(30006)])
		if idx == 0: self.search()
		elif idx == 1: self.deleteShow()
		
	def search(self):
		keyboard = xbmc.Keyboard('',__language__(30005))
		keyboard.doModal()
		if not keyboard.isConfirmed(): return
		term = keyboard.getText()
		pdialog = xbmcgui.DialogProgress()
		pdialog.create(__language__(30017))
		pdialog.update(0)
		result = API.search(term)
		slist = []
		sids = []
		for s in result.findall('show'):
			slist.append(s.find('name').text)
			sids.append(s.find('showid').text)
		pdialog.close()
		dialog = xbmcgui.Dialog()
		idx = dialog.select(__language__(30008),slist)
		if idx < 0: return
		self.addShow(sids[idx])
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
			self.shows.append(Show(xmltree=s))
			
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
			if not show.cancelled: show.getShowData()
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
		self.getControl(120).reset()
		xbmcgui.lock()
		for k in sortd:
			show = disp[k]
			nextUnix = show.getNextUnix()
			
			try: 	showdate = time.strftime('%a %b %d',time.strptime(show.nextEp['date'],'%Y-%m-%d'))
			except:	showdate = '?'
			
			item = xbmcgui.ListItem(label=show.name,label2=showdate)
			if time.strftime('%j:%Y',time.localtime()) == time.strftime('%j:%Y',time.localtime(nextUnix)):
				item.setInfo('video',{"Genre":'today'})
			elif time.strftime('%j:%Y',time.localtime(time.time() + 86400)) == time.strftime('%j:%Y',time.localtime(nextUnix)):
				item.setInfo('video',{"Genre":'tomorrow'})
			else:
				item.setInfo('video',{"Genre":''})
						
			item.setProperty("summary",show.airtime)
			if show.cancelled: item.setProperty("summary",'ENDED')
			
			item.setProperty("updated",show.nextEp['number'] + ' ' + show.nextEp['title'])
			if show.cancelled: item.setProperty("updated",'CANCELLED')
			item.setProperty("last",__language__(300012) + ' ' + show.lastEp['number'] + ' ' + show.lastEp['title'] + ' ' + show.lastEp['date'])
			item.setProperty("image",show.imagefile)
			item.setProperty("id",show.showid)
			self.getControl(120).addItem(item)
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
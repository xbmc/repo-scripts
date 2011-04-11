# -*- coding: utf-8 -*-
import xbmcaddon #@UnresolvedImport
import xbmc, xbmcgui #@UnresolvedImport
import sys, os, time, re, traceback
import elementtree.ElementTree as etree #@UnresolvedImport
import jsonrpc
import difflib
from tvrageapi import Episode, Show, TVRageAPI

__author__ = 'ruuk'
__url__ = 'http://code.google.com/p/tvragexbmc/'
__date__ = '1-26-2011'
__version__ = '1.0.5'
__addon__ = xbmcaddon.Addon(id='script.tvrage.com')
__language__ = __addon__.getLocalizedString

#for k in xbmc.__dict__.keys(): print k

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources') )
sys.path.append (BASE_RESOURCE_PATH)

IMAGE_PATH = xbmc.translatePath( os.path.join( __addon__.getAddonInfo('path'), 'resources', 'skin','Default','media') )
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
ACTION_SHOW_GUI       = 18
ACTION_PLAYER_PLAY           = 79
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_CONTEXT_MENU   = 117

def LOG(msg):
	xbmc.log(msg.encode('ascii','replace'))

def ERROR(msg):
	LOG(msg)
	traceback.print_exc()

class SummaryDialog(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
		self.link = kwargs.get('link','')
		self.parent = kwargs.get('parent',None)
	
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
		elif action == ACTION_PLAYER_PLAY:
			self.playEpisode()
		xbmcgui.WindowXMLDialog.onAction(self,action)
		
	def playEpisode(self):
		self.parent.playEpisode()
		self.close()
		
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
		self.showname = kwargs.get('showname','')
		self.parent = kwargs.get('parent',None)
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
		elif action == ACTION_PLAYER_PLAY:
			self.playEpisode()
		#else:
		#	print 'ACTION: ' + str(action.getId())
		xbmcgui.WindowXMLDialog.onAction(self,action)
			
	def summary(self):
		item = self.getControl(120).getSelectedItem()
		link = item.getProperty('link')
		w = SummaryDialog("script-tvrage-summary.xml" , __addon__.getAddonInfo('path'), "Default",link=link,parent=self)
		w.doModal()
		del w
		
	def playEpisode(self):
		item = self.getControl(120).getSelectedItem()
		season = item.getProperty('season')
		eptitle = item.getLabel2()
		efile = self.parent.findXBMCEpFile(self.showname,season,eptitle)
		if not efile:
			xbmcgui.Dialog().ok(__language__(30046),__language__(30047))
			return
		xbmc.Player().play(efile)
		self.close()
		
	def showEpList(self,sid):
		self.getControl(100).setLabel(__language__(30055))
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
				item.setProperty('season',ep.season)
				self.getControl(120).addItem(item)
		xbmcgui.unlock()
				
class TVRageEps(xbmcgui.WindowXML):
	def __init__( self, *args, **kwargs ):
		xbmcgui.WindowXML.__init__( self, *args, **kwargs )
	
	def onInit(self):
		self.lastUpdateFile = xbmc.translatePath('special://profile/addon_data/script.tvrage.com/last')
		self.dataFile = xbmc.translatePath('special://profile/addon_data/script.tvrage.com/data')
		self.loadSettings()
		
		self.shows = []
		self.loadData()
		self.update(force=self.isStale())

		self.setFocus(self.getControl(120))
	
	def loadSettings(self):
		hours = __addon__.getSetting('hours_between_updates')
		self.json_use_http = (__addon__.getSetting('json_use_http') == 'true')
		self.http_address = __addon__.getSetting('xbmc_http_address')
		self.http_user = __addon__.getSetting('xbmc_http_user')
		self.http_pass = __addon__.getSetting('xbmc_http_pass')
		air_offset = __addon__.getSetting('airtime_offset')
		self.skip_canceled = (__addon__.getSetting('skip_canceled') == 'true')
		self.reverse_sort = (__addon__.getSetting('reverse_sort') == 'true')
		self.jump_to_bottom = (__addon__.getSetting('jump_to_bottom') == 'true')
		self.ask_on_no_match = (__addon__.getSetting('ask_on_no_match') == 'true')
		self.hours = [1,2,3,4,5,6,12,24][int(hours)]
		self.air_offset = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,-23,-22,-21,-20,-19,-18,-17,-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1][int(air_offset)]
		
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
		
	def doAddShow(self,sid,skipCanceled=False,name=''):
		if sid == '0':
			self.shows.append(Show(showid=sid,name=name))
			return 1
		show = Show(showid=sid).getShowData()
		if skipCanceled and show.canceled: return 0
		self.shows.append(show)
		return 1
		
	def onAction(self,action):
		#print "ACTION: " + str(action.getId()) + " FOCUS: " + str(self.getFocusId()) + " BC: " + str(action.getButtonCode())
		if action == ACTION_CONTEXT_MENU:
			self.doMenu()
		elif action == ACTION_SELECT_ITEM:
			if self.getFocusId() == 200:
				self.search()
			elif self.getFocusId() == 201:
				self.addFromLibrary()
			elif self.getFocusId() == 202:
				self.openSettings()
			else:
				self.eplist()
		elif action == ACTION_PARENT_DIR:
			action = ACTION_PREVIOUS_MENU
		elif action == ACTION_MOUSE_LEFT_CLICK:
			if self.getFocusId() == 200:
				self.search()
			elif self.getFocusId() == 201:
				self.addFromLibrary()
			elif self.getFocusId() == 202:
				self.openSettings()
			elif self.getFocusId() == 120:
				self.eplist()
		xbmcgui.WindowXMLDialog.onAction(self,action)
			
	def openSettings(self):
		rs = self.reverse_sort
		ao = self.air_offset
		__addon__.openSettings()
		self.loadSettings()
		if rs != self.reverse_sort or ao != self.air_offset: self.updateDisplay()
		
	def doMenu(self):
		dialog = xbmcgui.Dialog()
		#idx = dialog.select(__language__(30011),[__language__(30007),__language__(30026),__language__(30013),__language__(30006)])
		idx = dialog.select(__language__(30011),[__language__(30013),__language__(30054),__language__(30006),__language__(30041)])
		#if idx == 0: self.search()
		#elif idx == 1: self.addFromLibrary()
		if idx == 0: self.reverse()
		elif idx == 1: self.update(force=True)
		elif idx == 2: self.deleteShow()
		
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
		sid = self.userPickShow(result,append=term)
		if not sid: return
		self.addShow(sid)
		self.updateDisplay()

	def userPickShow(self,result,append=''):
		slist = ['< %s >' % (__language__(30040)),__language__(30048).replace('@REPLACE@',append)]
		sids = [None,'0']
		if result:
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
			if self.json_use_http:
				jrapi = jsonrpc.jsonrpcAPI(mode='http',url=self.http_address + '/jsonrpc',user=self.http_user,password=self.http_pass)
			else:
				jrapi = jsonrpc.jsonrpcAPI()
			try:
				shows = jrapi.VideoLibrary.GetTVShows()
			except jsonrpc.UserPassError:
				xbmcgui.Dialog().ok(__language__(30031),__language__(30032),__language__(30033),__language__(30034))
				return
			except jsonrpc.ConnectionError:
				xbmcgui.Dialog().ok(__language__(30031),__language__(30035),__language__(30036),__language__(30037))
				return
			if not 'tvshows' in shows: return #TODO put a dialog here
			tot = len(shows['tvshows'])
			ct=0.0
			added=0
			exist=0
			at_end = []
			for s in shows['tvshows']:
			#for s in [{'label':u'Fight Ippatsu! Jūden-chan!!'}]:
				title = s['label']
				pdialog.update(int((ct/tot)*100),title)
				dummy = False
				for c in self.shows:
					if difflib.get_close_matches(title,[c.name],1,0.7):
						LOG("SHOW: " + title + " - EXISTS AS: " + c.name)
						exist+=1
						if c.isDummy():
							dummy = True
							continue
						break
				else:
					result = API.search(title)
					close = None
					if result:
						matches = {}
						for f in result.findall('show'):
							matches[f.find('name').text] = f.find('showid').text
						close = difflib.get_close_matches(title,matches.keys(),1,0.8)
					if close:
						LOG("SHOW: " + title + " - MATCHES: " + close[0])
						pdialog.update(int((ct/tot)*100),__language__(30028) + title)
						self.doAddShow(matches[close[0]],skipCanceled=self.skip_canceled)
						added+=1
					else:
						if self.ask_on_no_match:
							if dummy:
								ct+=1
								continue
							at_end.append((title,result))
				ct+=1
		finally:
			pdialog.close()
		while at_end:
			left = []
			for s in at_end: left.append(__language__(30051) + s[0])
			idx = xbmcgui.Dialog().select(__language__(30052),['< %s >' % (__language__(30053))] + left)
			if idx < 1: break
			title,result = at_end.pop(idx-1)
			sid = self.userPickShow(result,append=title)
			if sid: added+=self.doAddShow(sid,skipCanceled=self.skip_canceled,name=title)
			
		#for s in at_end:
		#	title,result = s
		#	sid = self.userPickShow(result,append=title)
		#	if sid: added+=self.doAddShow(sid,skipCanceled=self.skip_canceled,name=title)
		self.saveData()
		self.updateDisplay()
		skipped = ct - (added + exist)
		xbmcgui.Dialog().ok(	__language__(30042),
								__language__(30043).replace('@NUMBER1@',str(added)).replace('@NUMBER2@',str(int(ct))),
								__language__(30044).replace('@NUMBER@',str(exist)),
								__language__(30045).replace('@NUMBER@',str(int(skipped))))
		
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
		if not item: return
		sid = item.getProperty('id')
		if sid == '0':
			xbmcgui.Dialog().ok(__language__(30049),__language__(30050))
			return
		showname = item.getLabel()
		w = EpListDialog("script-tvrage-eplist.xml" , __addon__.getAddonInfo('path'), "Default",sid=sid,showname=showname,parent=self)
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
		
	def findXBMCEpFile(self,show,season,eptitle):
		if self.json_use_http:
			jrapi = jsonrpc.jsonrpcAPI(url=self.http_address + '/jsonrpc',user=self.http_user,password=self.http_pass)
		else:
			jrapi = jsonrpc.jsonrpcAPI()
		labels = []
		ids = []
		for s in jrapi.VideoLibrary.GetTVShows()['tvshows']:
			labels.append(s['label'])
			ids.append(s['tvshowid'])
		mshow = difflib.get_close_matches(show,labels,1,0.7)
		if not mshow: return
		mshow = mshow[0]
		eplist = jrapi.VideoLibrary.GetEpisodes(tvshowid=ids[labels.index(mshow)],season=season)
		if not 'episodes' in eplist: return
		labels = []
		files = []
		for e in eplist['episodes']:
			labels.append(e['label'])
			files.append(e['file'])
		mep = difflib.get_close_matches(eptitle,labels,1,0.7)
		if not mep: return
		#print mep
		#print labels
		efile = files[labels.index(mep[0])]
		#print efile
		return efile
		
	def updateData(self):
		progress = xbmcgui.DialogProgress()
		progress.create(__language__(30003),__language__(30004))
		try:
			lmax = len(self.shows)
			ct=0
			for show in self.shows:
				if show and not show.canceled and show.showid != '0': show.getShowData()
				if progress.iscanceled(): break
				ct+=1
				percent = int((float(ct)/lmax)*100)
				progress.update(percent,show.name)
		finally:
			progress.close()
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
			nextUnix = show.getNextUnix(offset=self.air_offset)
			
			#try: 	showdate = time.strftime('%a %b %d',time.strptime(show.nextEp['date'],'%Y-%m-%d'))
			if show.canceled:
				showdate = show.canceled
			elif show.isDummy():
				showdate = ''
			else:
				if show.nextEp['date']:
					ds = show.nextEp['date'].split('-')
					if '00' in ds:
						if ds.index('00') == 1:
							showdate = ds[0]
						else:
							showdate = time.strftime('%b %Y',time.strptime('-'.join(ds[:-1]),'%Y-%m'))
					else:
						try: 	showdate = time.strftime('%a %b %d',time.localtime(nextUnix))
						except:	showdate = show.canceled
				else:
					showdate = ''
			
			item = xbmcgui.ListItem(label=show.name,label2=showdate)
			if time.strftime('%j:%Y',time.localtime()) == time.strftime('%j:%Y',time.localtime(nextUnix)):
				item.setInfo('video',{"Genre":'today'})
			elif time.strftime('%j:%Y',time.localtime(time.time() + 86400)) == time.strftime('%j:%Y',time.localtime(nextUnix)):
				item.setInfo('video',{"Genre":'tomorrow'})
			else:
				item.setInfo('video',{"Genre":''})
						
			item.setProperty("summary",show.airtime(self.air_offset))
			if show.canceled:
				item.setProperty("summary",__language__(30030))
			elif show.isDummy():
				item.setProperty("summary",'')
			
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

API = TVRageAPI()
Show.API = API
Show.THUMB_PATH = THUMB_PATH

w = TVRageEps("script-tvrage-main.xml" , __addon__.getAddonInfo('path'), "Default")
w.doModal()
del w
#sys.modules.clear()
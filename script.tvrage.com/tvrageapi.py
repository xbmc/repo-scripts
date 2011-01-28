import os
import time
import re
import urllib
import traceback
try:
	import elementtree.ElementTree as etree #@UnresolvedImport @UnusedImport
except:
	import xml.etree.ElementTree as etree #@Reimport
	
def LOG(msg):
	print msg.encode('ascii','replace')
	
def ERROR(msg):
	LOG(msg)
	traceback.print_exc()
	
class Show:
	THUMB_PATH = ''
	API = None
	def __init__(self,showid='',xmltree=None,name=''):
		self.showid = showid
		self.name = name
		self._airtime = ''
		self.next = {}
		self.last = {}
		self.imagefile = os.path.join(self.THUMB_PATH,self.showid + '.jpg')
		self.nextUnix = 0
		self.status = ''
		self.canceled = ''
		self.lastEp = {'number':'?','title':'Unknown','date':''}
		self.nextEp = {'number':'?','title':'Unknown','date':''}
		if xmltree:
			self.tree = xmltree
			self.processTree(xmltree)
		elif self.isDummy():
			self.tree = etree.fromstring('<show id="0"><name>'+name+'</name></show>')
		
		
	def isDummy(self):
		return self.showid == '0'
		
	def getShowData(self):
		if self.isDummy(): return
		tree = self.API.getShowInfo(self.showid)
		self.processTree(tree)
		return self
		
	def processTree(self,show):
		if not show: return
		sid = show.attrib.get('id',self.showid)
		#if no show id keep our data
		if not sid:
			LOG('ERROR - NO SHOW ID')
			return
		self.showid = sid
		self.tree = show
		self.imagefile = os.path.join(self.THUMB_PATH,self.showid + '.jpg')
		self.name = show.find('name').text
		if self.isDummy(): return
		
		try: self._airtime = re.findall('\d+:\d\d\s\w\w',show.find('airtime').text)[0]
		except: pass
		if not self._airtime:
			try: self._airtime = show.find('airtime').text.rsplit('at ',1)[-1]
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
			try:
				iurl = 'http://images.tvrage.com/shows/'+str(int(self.showid[0:-3]) + 1)+'/'+self.showid + '.jpg'
			except:
				print "IMAGE ERROR - SHOWID: " + self.showid
				return
			saveURLToFile(iurl,self.imagefile)
				
	def airtime(self,offset=0):
		if not self.nextEp.get('date'):
			try:
				date = time.strftime('%Y-%m-%d',time.localtime(time.time()))
				struct = time.strptime(date + ' ' + self._airtime,'%Y-%m-%d %I:%M %p')
				unixtime = time.mktime(struct)+(offset*3600)
				return time.strftime('%I:%M %p',time.localtime(unixtime))
				ERROR('Failed to create airtime without nextEp, using TVRage airtime.')
			except:
				return self._airtime
		else:
			return time.strftime('%I:%M %p',time.localtime(self.getNextUnix(offset=offset)))
		
	def epInfo(self,eptree):
		try: 		return {'number':eptree.find('number').text,'title':eptree.find('title').text,'date':eptree.find('airdate').text}
		except: 	return {'number':'?','title':'Unknown','date':'?'}
		
	def getSortValue(self):
		srt = self.getNextUnix(forceupdate=True)
		return str(srt) + '@' + self.name
		
	def getNextUnix(self,forceupdate=False,offset=0):
		if forceupdate or not self.nextUnix:
			try:
				struct = time.strptime(self.nextEp['date'] + ' ' + self._airtime,'%Y-%m-%d %I:%M %p')
				srt = time.mktime(struct)
			except:
				srt = time.time()+60*60*24*365*10
				if self.canceled: srt += 3600
				elif self.isDummy(): srt += 3601
			self.nextUnix = srt
		return self.nextUnix + (offset * 3600)
		
	def xml(self):
		return etree.tostring(self.tree).strip()

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
		try:
			url = self._search_url + urllib.quote_plus(show.encode('utf-8'))
		except:
			url = self._search_url + show.replace(' ','_')
		return self.getTree(url)
		
	def getEpList(self,showid):
		url = self._eplist_url + str(showid)
		return self.getTree(url)
		
	def getTree(self,url):
		xml = self.getURLData(url,readlines=False)
		if not xml:
			LOG('TVRage-Eps: ERROR GETTING XML DATA')
			return None
		xml = re.sub('&(?!amp;)','&amp;',xml)
		try:
			return etree.fromstring(xml)
		except:
			LOG('TVRage-Eps: BAD XML DATA')
			return None
		
	def getEpSummary(self,url):
		html = self.getURLData(url,readlines=False)
		html = html.split('>Episode Summary</h')[-1]
		return re.findall('<br>(.*?)<br>',html,re.S)[0].strip()
	
	def getURLData(self,url,readlines=True):
		try:
			w = urllib.urlopen(url)
		except:
			ERROR('getURLData(): FAILED TO OPEN URL: %s' % url)
			return None
		try:
			if readlines: linedata = w.readlines()
			else: linedata = w.read()
		except:
			w.close()
			ERROR('getURLData(): FAILED TO READ DATA - URL: %s' % url)
			return None
		w.close()
		return linedata
	
def saveURLToFile(url,file,hook=None,e_hook=None):
	try:
		urllib.urlretrieve(url,file,hook)
	except:
		if e_hook: e_hook()
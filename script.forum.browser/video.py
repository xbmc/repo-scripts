import urllib2,re, sys, os
import xbmcaddon #@UnresolvedImport

LOG = sys.modules["__main__"].LOG
ERROR = sys.modules["__main__"].ERROR

def getVideoInfo(url):
	return WebVideo().getVideoObject(url)
	
def getVideoPlayable(sourceName,ID):
	if sourceName == 'Vimeo':
		return WebVideo().getVimeoFLV(ID)
	elif sourceName == 'YouTube':
		return WebVideo().getYoutubePluginURL(ID)
	
class Video():
	def __init__(self,ID=None):
		self.ID = ID
		self.thumbnail = ''
		self.swf = ''
		self.media = ''
		self.embed = ''
		self.page = ''
		self.playable = ''
		self.title = ''
		self.sourceName = ''
		self.playableCallback = None
		self.isVideo = True
		
	def playableURL(self):
		return self.playable or self.media
	
	def getPlayableURL(self):
		if not self.playableCallback: return self.playableURL()
		url = self.playableCallback(self.ID)
		LOG('Video URL: ' + url)
		return url
		
class WebVideo():
	alphabetB58 = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
	countB58 = len(alphabetB58)
	
	def __init__(self):
		self.modules = {}
		
	def getVideoObject(self,url,just_test=False):
		if 'youtu.be' in url or 'youtube.com' in url:
			if just_test: return True
			ID = self.extractYoutubeIDFromURL(url)
			if not ID: return None
			video = Video(ID)
			video.sourceName = 'YouTube'
			video.thumbnail = self.getYoutubeThumbURL(ID)
			video.playable = self.getYoutubePluginURL(ID)
			video.swf = self.getYoutubeSWFUrl(ID)
		elif 'vimeo.com' in url:
			if just_test: return True
			ID = self.extractVimeoIDFromURL(url)
			if not ID: return None
			video = Video(ID)
			video.sourceName = 'Vimeo'
			info = self.getVimeoInfo(ID)
			video.thumbnail = info.get('thumbnail','')
			video.title = info.get('title','')
			#video.playableCallback = self.getVimeoFLV
			video.isVideo = False #Vimeo support is broken
		elif 'flic.kr/' in url or 'flickr.com/' in url:
			if just_test: return True
			ID = self.getFlickrIDFromURL(url)
			if not ID: return None
			info = self.getFlickrInfo(ID)
			video = Video(ID)
			video.sourceName = 'flickr'
			video.thumbnail = info.get('thumbnail','')
			video.title = info.get('title','')
			if not info.get('type') == 'video':
				video.isVideo = False
				return video
			video.playable = self.getFlickrPluginURL(ID)
		else:
			return None
		LOG('Video ID: ' + video.ID)
		return video
	
	def mightBeVideo(self,url):
		return self.getVideoObject(url, just_test=True)
	
	def getFlickrPluginURL(self,ID):
		return 'plugin://plugin.image.flickr/?video_id=' + ID
	
	def getYoutubePluginURL(self,ID):
		return 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=' + ID
			
	def getYoutubeThumbURL(self,ID):
		return 'http://i1.ytimg.com/vi/%s/default.jpg' % ID
	
	def getYoutubeSWFUrl(self,ID):
		return 'http://www.youtube.com/v/' + ID
		
	def extractYoutubeIDFromURL(self,url):
		if '//youtu.be' in url:
			#http://youtu.be/sSMbOuNBV0s
			sp = url.split('.be/',1)
			if len(sp) == 2: return sp[1]
			return ''
		elif 'youtube.com' in url:
			#http://www.youtube.com/watch?v=MuLDUws0Zh8&feature=autoshare
			ID = url.split('v=',1)[-1].split('&',1)[0]
			if 'youtube.com' in ID:
				ID = url.split('/v/',1)[-1].split('&',1)[0]
			if 'youtube.com' in ID: return ''
			return ID
	
	def getFlickrIDFromURL(self,url):
		#try:
		#	longURL = urllib2.urlopen(url).geturl()
		#except:
		#	return ''
		#if longURL.endswith('/'): longURL = longURL[:-1]
		#return longURL.rsplit('/',1)[-1]
		end = url
		if end.endswith('/'): end = end[:-1]
		end = end.rsplit('/',1)[-1]
		if 'flic.kr/' in url:
			return str(self.decodeBase58(end))
		else:
			return end
		
	def getFlickrInfo(self,ID):
		fImport = self.doImport('plugin.image.flickr', '', 'default')
		if not fImport: return {}
		fsession = fImport.FlickrSession()
		if not fsession.authenticate(): return {}
		info = fsession.flickr.photos_getInfo(photo_id=ID)
		photo = info.find('photo')
		title = photo.find('title').text
		media = photo.get('media','')
		thumb = fImport.photoURL(photo.get('farm',''),photo.get('server',''),ID,photo.get('secret',''))
		#<location latitude="47.574433" longitude="-122.640611" accuracy="16" context="0" place_id="pqEP2S9UV7P8W60smQ" woeid="55995994">
		return {'title':title,'type':media,'thumbnail':thumb}
		
	def extractVimeoIDFromURL(self,url):
		#TODO: Finish this :)
		if url.endswith('/'): url = url[:-1]
		ID = url.rsplit('/',1)[-1]
		return ID
	
	def getVimeoInfo(self,ID):
		infoURL = 'http://vimeo.com/api/v2/video/%s.xml' % ID
		xml = urllib2.urlopen(urllib2.Request(infoURL,None,{'User-Agent':'Wget/1.9.1'})).read()
		ret = {}
		try:
			ret = {}
			ret['title'] = re.search('<url>([^<]*)</url>',xml).group(1)
			ret['thumbnail'] = re.search('<thumbnail_large>([^<]*)</thumbnail_large>',xml).group(1)
		except:
			pass
		return ret
		
	def getVimeoFLV(self,ID):
		#TODO: Make this better
		infoURL = 'http://www.vimeo.com/moogaloop/load/clip:' + ID
		try:
			o = urllib2.urlopen(infoURL)
			info = o.read()
			sig = re.search('<request_signature>([^<]*)</request_signature>',info).group(1)
			exp = re.search('<request_signature_expires>([^<]*)</request_signature_expires>',info).group(1)
			hd_or_sd = int(re.search('isHD>([^<]*)</isHD>',info).group(1)) and 'hd' or 'sd'
		except:
			ERROR('Failed to get vimeo URL')
			return ''
		flvURL = 'http://www.vimeo.com/moogaloop/play/clip:%s/%s/%s/?q=%s' % (ID,sig,exp,hd_or_sd)
		try:
			flvURL = urllib2.urlopen(urllib2.Request(flvURL,None,{'User-Agent':'Wget/1.9.1'})).geturl()
		except:
			ERROR('Failed to get vimeo URL')
			return ''
		#print flvURL
		return flvURL
	
	def decodeBase58(self,s):
		""" Decodes the base58-encoded string s into an integer """
		decoded = 0
		multi = 1
		s = s[::-1]
		for char in s:
			decoded += multi * self.alphabetB58.index(char)
			multi = multi * self.countB58
		return decoded
	
	def doImport(self,addonID,path,module):
		full = '/'.join((addonID,path,module))
		if full in self.modules: return self.modules[full]
		addonPath = xbmcaddon.Addon(addonID).getAddonInfo('path')
		importPath = os.path.join(addonPath,path)
		sys.path.insert(0,importPath)
		try:
			mod = __import__(module)
			reload(mod)
			del sys.path[0]
			self.modules[full] = mod
			return mod
		except ImportError:
			ERROR('Error importing module %s for share target %s.' % (self.importPath,self.addonID))
		except:
			ERROR('ShareTarget.getModule(): Error during target sharing import')
		return 
#http://vimeo.com/moogaloop.swf?clip_id=38759453
#http://vimeo.com/api/v2/video/38759453.json

#http://www.vimeo.com/moogaloop/load/clip:82739
#http://www.vimeo.com/moogaloop/play/clip:82739/38c7be0cecb92a0a3623c2769bccf73b/1221451200/?q=sd
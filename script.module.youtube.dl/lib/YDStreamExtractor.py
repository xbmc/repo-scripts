import urllib, sys, os, urlparse, httplib
import xbmc
import YDStreamUtils as StreamUtils
from youtube_dl.utils import (
	std_headers,
)

DEBUG = False

def LOG(text,debug=False):
	if debug and not DEBUG: return
	print 'script.module.youtube.dl: %s' % text

def ERROR(message):
	errtext = sys.exc_info()[1]
	print 'script.module.youtube.dl - %s::%s (%d) - %s' % (message, sys.exc_info()[2].tb_frame.f_code.co_name, sys.exc_info()[2].tb_lineno, errtext)
	if DEBUG:
		import traceback
		traceback.print_exc()
		
###############################################################################
# FIX: xbmcout instance in sys.stderr does not have isatty(), so we add it
###############################################################################
class replacement_stderr(sys.stderr.__class__):
	def isatty(self): return False
	
sys.stderr.__class__ = replacement_stderr
###############################################################################

try:
	import youtube_dl
except:
	ERROR('Failded to import youtube-dl')
	youtube_dl = None

###############################################################################
# FIXES: datetime.datetime.strptime evaluating as None?
###############################################################################
_utils_unified_strdate = youtube_dl.utils.unified_strdate
def _unified_strdate_wrap(date_str):
	try:
		return _utils_unified_strdate(date_str)
	except:
		return '00000000'
youtube_dl.utils.unified_strdate = _unified_strdate_wrap

import datetime		
_utils_date_from_str = youtube_dl.utils.date_from_str
def _date_from_str_wrap(date_str):
	try:
		return _utils_date_from_str(date_str)
	except:
		return datetime.datetime.now().date()
youtube_dl.utils.date_from_str = _date_from_str_wrap
###############################################################################

_YTDL = None
_DISABLE_DASH_VIDEO = True
_CALLBACK = None
_BLACKLIST = ['youtube:playlist', 'youtube:toplist', 'youtube:channel', 'youtube:user', 'youtube:search', 'youtube:show', 'youtube:favorites', 'youtube:truncated_url','vimeo:channel', 'vimeo:user', 'vimeo:album', 'vimeo:group', 'vimeo:review','dailymotion:playlist', 'dailymotion:user','generic']

class VideoInfo:
	"""
	Represents resolved site video
	Has the properties title, description, thumbnail and webpage
	The info property contains the original youtube-dl info
	"""
	def __init__(self,ID=None):
		self.ID = ID
		self.title = ''
		self.description = ''
		self.thumbnail = ''
		self.webpage = ''
		self._streams = None
		self.sourceName = ''
		self.info = None
		self._selection = None
		
	def __len__(self):
		return len(self._streams)
		
	def streamURL(self):
		"""
		Returns the resolved xbmc ready url of the selected stream
		"""
		return self.selectedStream()['xbmc_url']
	
	def streams(self):
		"""
		Returns a list of dicts of stream data:
			{'xbmc_url':<xbmc ready resolved stream url>,
			'url':<base resolved stream url>,
			'title':<stream specific title>,
			'thumbnail':<stream specific thumbnail>,
			'formatID':<chosen format id>}
		"""
		return self._streams
		
	def hasMultipleStreams(self):
		"""
		Return True if there is more than one stream
		"""
		if not self._streams: return False
		if len(self._streams) > 1: return True
		return False
		
	def selectStream(self,idx):
		"""
		Select the default stream by index or by passing the stream dict
		"""
		if isinstance(idx,dict):
			self._selection = idx['idx']
		else:
			self._selection = idx
		
	def selectedStream(self):
		"""
		Returns the info of the currently selected stream
		"""
		if self._selection == None: return self._streams[0]
		return self._streams[self._selection]

class DownloadResult:
	"""
	Represents a download result. Evaluates as non-zero on success.
	Ex. usage:
	dr = handleDownload(url,formatID,title)
	if dr:
		print 'Successfully downloaded %s' % dr.filepath
	else:
		if not dr.status == 'canceled':
			print 'Download failed: %s' % dr.message 
	
	"""
	def __init__(self,success, message='',status='',filepath=''):
		self.success = success
		self.message = message
		self.status = status
		self.filepath = filepath
		
	def __nonzero__(self):
		return self.success
		
class DownloadCanceledException(Exception): pass

class CallbackMessage(str):
	"""
	A callback message. Subclass of string so can be displayed/printed as is.
	Has the following extra properties:
		percent		<- Integer download progress or 0 if not available
		etaStr		<- ETA string ex: 3m 25s
		speedStr	<- Speed string ex: 35 KBs
		info		<- dict of the youtube-dl progress info
	"""
	def __new__(self, value, pct=0, eta_str='', speed_str='', info=None):
		return str.__new__(self, value)
		
	def __init__(self, value, pct=0, eta_str='', speed_str='', info=None):
		self.percent = pct
		self.etaStr = eta_str
		self.speedStr = speed_str
		self.info = info
		
class YoutubeDLWrapper(youtube_dl.YoutubeDL):
	"""
	A wrapper for youtube_dl.YoutubeDL providing message handling and 
	progress callback.
	It also overrides XBMC environment error causing methods.
	"""
	def __init__(self,*args,**kwargs):
		self._lastDownloadedFilePath = ''
		youtube_dl.YoutubeDL.__init__(self,*args,**kwargs)
		
	def showMessage(self, msg):
		global _CALLBACK
		if _CALLBACK:
			try:
				return _CALLBACK(msg)
			except:
				ERROR('Error in callback. Removing.')
				_CALLBACK = None
		else:
			if xbmc.abortRequested: raise Exception('abortRequested')
			#print msg.encode('ascii','replace')
		return True
		
	def progressCallback(self,info):
		if xbmc.abortRequested: raise DownloadCanceledException('abortRequested')
		if not _CALLBACK: return
		#'downloaded_bytes': byte_counter,
		#'total_bytes': data_len,
		#'tmpfilename': tmpfilename,
		#'filename': filename,
		#'status': 'downloading',
		#'eta': eta,
		#'speed': speed
		sofar = info.get('downloaded_bytes')
		total = info.get('total_bytes')
		if info.get('filename'): self._lastDownloadedFilePath = info.get('filename')
		pct = ''
		pct_val = 0
		if sofar != None and total:
			pct_val = int((float(sofar)/total) * 100)
			pct = ' (%s%%)' % pct_val
		eta = info.get('eta') or ''
		eta_str = ''
		if eta:
			eta_str = StreamUtils.durationToShortText(eta)
			eta = '  ETA: ' + eta_str
		speed = info.get('speed') or ''
		speed_str = ''
		if speed:
			speed_str = StreamUtils.simpleSize(speed) + 's'
			speed = '  ' + speed_str
		status = '%s%s:' % (info.get('status','?').title(),pct)
		text = CallbackMessage(status + eta + speed, pct_val, eta_str, speed_str, info)
		ok = self.showMessage(text)
		if not ok:
			LOG('Download canceled')
			raise DownloadCanceledException()
	
	def clearDownloadParams(self):
		self.params['quiet'] = False
		self.params['format'] = None
		self.params['matchtitle'] = None
		
	def clear_progress_hooks(self):
		self._progress_hooks = []
		
	def add_info_extractor(self, ie):
		if ie.IE_NAME in _BLACKLIST: return
		# Fix ##################################################################
		module = sys.modules.get(ie.__module__)
		if module:
			if hasattr(module,'unified_strdate'): module.unified_strdate = _unified_strdate_wrap
			if hasattr(module,'date_from_str'): module.date_from_str = _date_from_str_wrap
		########################################################################
		youtube_dl.YoutubeDL.add_info_extractor(self,ie)

	def to_stdout(self, message, skip_eol=False, check_quiet=False):
		"""Print message to stdout if not in quiet mode."""
		if self.params.get('logger'):
			self.params['logger'].debug(message)
		elif not check_quiet or not self.params.get('quiet', False):
			message = self._bidi_workaround(message)
			terminator = ['\n', ''][skip_eol]
			output = message + terminator
			self.showMessage(output)

	def to_stderr(self, message):
		"""Print message to stderr."""
		assert type(message) == type('') or type(message) == type(u'')
		if self.params.get('logger'):
			self.params['logger'].error(message)
		else:
			message = self._bidi_workaround(message)
			output = message + '\n'
			self.showMessage(output)
												
	def report_warning(self, message):
		#overidden to get around error on missing stderr.isatty attribute
		_msg_header = 'WARNING:'
		warning_message = '%s %s' % (_msg_header, message)
		self.to_stderr(warning_message)
		
	def report_error(self, message, tb=None):
		#overidden to get around error on missing stderr.isatty attribute
		_msg_header = 'ERROR:'
		error_message = '%s %s' % (_msg_header, message)
		self.trouble(error_message, tb)

###############################################################################
# Private Methods					
###############################################################################
def _getYTDL():
	global _YTDL
	if _YTDL: return _YTDL
	if DEBUG:
		_YTDL = YoutubeDLWrapper({'verbose':True})
	else:
		_YTDL = YoutubeDLWrapper()
	_YTDL.add_progress_hook(_YTDL.progressCallback)
	_YTDL.add_default_info_extractors()
	return _YTDL
	
def _selectVideoQuality(r,quality=1):
		if 'entries' in r and not 'formats' in r:
			entries = r['entries']
		elif 'formats' in r and r['formats']:
			entries = [r]
		elif 'url' in r:
			r['formats'] = [r]
			entries = [r]
		minHeight = 0
		maxHeight = 480
		if quality > 1:
			minHeight = 721
			maxHeight = 1080
		elif quality > 0:
			minHeight = 481
			maxHeight = 720
		LOG('Quality: {0}'.format(quality),debug=True)
		urls = []
		idx=0
		for entry in entries:
			defFormat = None
			defMax = 0
			defPref = -1000
			prefFormat = None
			prefMax = 0
			prefPref = -1000
			index = {}
			if 'formats' in entry:
				formats = entry['formats']
			else:
				formats = [entry]
			for i in range(0,len(formats)): index[formats[i]['format_id']] = i
			keys = sorted(index.keys())
			fallback = formats[index[keys[0]]]
			for fmt in keys:
				fdata = formats[index[fmt]]
				if not 'height' in fdata: continue
				if _DISABLE_DASH_VIDEO and 'dash' in fdata.get('format_note','').lower(): continue
				h = fdata['height']
				p = fdata.get('preference',1)
				if h >= minHeight and h <= maxHeight:
					if (h >= prefMax and p > prefPref) or (h > prefMax and p >= prefPref):
						prefMax = h
						prefPref = p
						prefFormat = fdata
				elif(h >= defMax and h <= maxHeight and p > defPref) or (h > defMax and h <= maxHeight and p >= defPref):
						defMax = h
						defFormat = fdata
						defPref = p
			formatID = None
			if prefFormat:
				info = prefFormat
				logBase = '[{3}] Using Preferred Format: {0} ({1}x{2})'
			elif defFormat:
				info = defFormat
				logBase = '[{3}] Using Default Format: {0} ({1}x{2})'
			else:
				info = fallback
				logBase = '[{3}] Using Fallback Format: {0} ({1}x{2})'
			url = info['url']
			formatID = info['format_id']
			LOG(logBase.format(formatID,info.get('width','?'),info.get('height','?'),entry.get('title','').encode('ascii','replace')),debug=True)
			if url.find("rtmp") == -1:
				url += '|' + urllib.urlencode({'User-Agent':entry.get('user_agent') or std_headers['User-Agent']})
			else:
				url += ' playpath='+fdata['play_path']
			new_info = dict(entry)
			new_info.update(info)
			urls.append({'xbmc_url':url,'url':info['url'],'title':entry.get('title',''),'thumbnail':entry.get('thumbnail',''),'formatID':formatID,'idx':idx,'ytdl_format':new_info})
			idx+=1
		return urls
		

# Recursively follow redirects until there isn't a location header
# Credit to: Zachary Witte @ http://www.zacwitte.com/resolving-http-redirects-in-python
def resolve_http_redirect(url, depth=0):
	if depth > 10:
		raise Exception("Redirected "+depth+" times, giving up.")
	o = urlparse.urlparse(url,allow_fragments=True)
	conn = httplib.HTTPConnection(o.netloc)
	path = o.path
	if o.query:
		path +='?'+o.query
	conn.request("HEAD", path,headers={'User-Agent':std_headers['User-Agent']})
	res = conn.getresponse()
	headers = dict(res.getheaders())
	if headers.has_key('location') and headers['location'] != url:
		return resolve_http_redirect(headers['location'], depth+1)
	else:
		return url
								
def _getYoutubeDLVideo(url,quality=1,resolve_redirects=False):
	if resolve_redirects:
		try:
			url = resolve_http_redirect(url)
		except:
			ERROR('_getYoutubeDLVideo(): Failed to resolve URL')
			return None
	ytdl = _getYTDL()
	ytdl.clearDownloadParams()
	r = ytdl.extract_info(url,download=False)
	urls =  _selectVideoQuality(r, quality)
	if not urls: return None
	info = VideoInfo(r.get('id',''))
	info._streams = urls
	info.title = r.get('title',urls[0]['title'])
	info.description = r.get('description','')
	info.thumbnail = r.get('thumbnail',urls[0]['thumbnail'])
	info.sourceName = r.get('extractor','')
	info.info = r
	return info

###############################################################################
# Public Methods					
###############################################################################
def setOutputCallback(callback):
	"""
	Sets a callback for youtube-dl output or progress updates.
	Must return True to continue or False to cancel.
	Will be called with CallbackMessage object.
	If the callback raises an exception it will be disabled.
	"""
	global _CALLBACK
	_CALLBACK = callback
	
def getVideoInfo(url,quality=1,resolve_redirects=False):
	"""
	Returns a VideoInfo object or None.
	Quality is 0=SD, 1=720p, 2=1080p and is a maximum.
	"""
	try:
		info = _getYoutubeDLVideo(url,quality,resolve_redirects)
		if not info: return None
	except:
		ERROR('_getYoutubeDLVideo() failed')
		return None
	return info

def downloadVideo(vidinfo,path,template='%(title)s-%(id)s.%(ext)s'):
	"""
	Download the selected video in vidinfo to path.
	Template sets the youtube-dl format which defaults to TITLE-ID.EXT.
	Returns a DownloadResult object.
	"""
			
	path_template = os.path.join(path,template)
	ytdl = _getYTDL()
	ytdl._lastDownloadedFilePath = ''
	ytdl.params['quiet'] = True
	ytdl.params['outtmpl'] = path_template

	try:
		downloadDirect(vidinfo)
	except youtube_dl.DownloadError, e:
		return DownloadResult(False,e.message,filepath=ytdl._lastDownloadedFilePath)
	except DownloadCanceledException:
		return DownloadResult(False,status='canceled',filepath=ytdl._lastDownloadedFilePath)
	finally:
		ytdl.clearDownloadParams()
		
	return DownloadResult(True,filepath=ytdl._lastDownloadedFilePath)
	
def downloadDirect(vidinfo):
	ytdl = _getYTDL()
	return ytdl.process_info(vidinfo.selectedStream()['ytdl_format'])
		
def handleDownload(vidinfo):
	"""
	Download the selected video in vidinfo to a path the user chooses.
	Displays a progress dialog and ok/error message when finished.
	Returns a DownloadResult object.
	"""
	path = StreamUtils.getDownloadPath()
	with StreamUtils.DownloadProgress() as prog:
		try:
			setOutputCallback(prog.updateCallback)
			result = downloadVideo(vidinfo,StreamUtils.TMP_PATH)
		finally:
			setOutputCallback(None)
	if not result and result.status != 'canceled':
			StreamUtils.showMessage(StreamUtils.T(32013),result.message)
	elif result:
		StreamUtils.showMessage(StreamUtils.T(32011),StreamUtils.T(32012),'',result.filepath)
	StreamUtils.moveFile(result.filepath,path)
	return result
			
def mightHaveVideo(url,resolve_redirects=False):
	"""
	Returns True if the url matches against one of the handled site URLs.
	"""
	if resolve_redirects:
		try:
			url = resolve_http_redirect(url)
		except:
			ERROR('mightHaveVideo(): Failed to resolve URL')
			return False
			
	ytdl = _getYTDL()
	for ies in ytdl._ies:
		if ies.suitable(url):
			return True
	return False
	
def disableDASHVideo(disable=True):
	"""
	True to disable choosing MPEG DASH streams.
	"""
	global _DISABLE_DASH_VIDEO
	_DISABLE_DASH_VIDEO = disable

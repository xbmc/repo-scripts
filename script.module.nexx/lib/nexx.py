# -*- coding: utf-8 -*-
import libmediathek3 as libmediathek
import json

#needs:
#operations = {}, hashes of possible operations
#channelId = '', channel id, 3 digets
#origin = '', base url of the website

#optional:
#blacklist = [], blacklists directory ids

base = 'https://api.nexx.cloud/v3/'
additional = '?limit=100&additionalfields=all'
blacklist = []
path = False


#depricated functions
def listDir():
	return getDir()
def listVideos():
	return getVideos()


	
def getDir():
	cid = _initSession()
	response = libmediathek.getUrl(base + channelId + '/' + streamtype + '/all' + additional, _header('all',cid))
	#libmediathek.log(response)
	j = json.loads(response)
	l = []
	for item in j['result']:
		d = _grepMetadata(item)
		d['_type'] = 'dir'
		d['mode'] = 'listVideos'
		d['streamtype'] = 'videos'
		d['operation'] = streamtype2operation[streamtype]
		if not d['id'] in blacklist:
			l.append(d)
	return l

def getVideos():
	cid = _initSession()
	if path:
		response = libmediathek.getUrl(base + channelId + path + additional, _header(operation,cid))
	else:
		response = libmediathek.getUrl(base + channelId + '/' + streamtype + '/' + operation + '/' + id + additional, _header(operation,cid))
	j = json.loads(response)
	items = j['result']
	l = []
	for item in items:
		d = _grepMetadata(item)
		d['_type'] = 'episode'
		d['mode'] = 'play'
		l.append(d)
	return l
	
def getVideoUrl(id):	
	cid = _initSession()
	response = libmediathek.getUrl(base + channelId + '/videos/byid/' + id + '?additionalfields=language%2Cchannel%2Cactors%2Cstudio%2Clicenseby%2Cslug%2Csubtitle%2Cteaser%2Cdescription&addInteractionOptions=1&addStatusDetails=1&addStreamDetails=1&addCaptions=1&addScenes=1&addHotSpots=1&addBumpers=1&captionFormat=data',_header('byid',cid))
	libmediathek.log(response)
	j = json.loads(response)
	token = ''
	if j['result']['protectiondata']['token'] != '':
		token = '?hdnts=' + j['result']['protectiondata']['token']
	if 'tokenHLS' in j['result']['protectiondata'] and j['result']['protectiondata']['tokenHLS'] != '':
		tokenHLS = '?hdnts=' + j['result']['protectiondata']['tokenHLS']
	else:
		tokenHLS = token
	if 'tokenDASH' in j['result']['protectiondata'] and j['result']['protectiondata']['tokenDASH'] != '':
		tokenDASH = '?hdnts=' + j['result']['protectiondata']['tokenDASH']
	else:
		tokenDASH = token
	#tokenDASH = '?hdnts=' + j['result']['protectiondata']['tokenDASH']
	HLS  = 'http://'+j['result']['streamdata']['cdnShieldHTTP']+j['result']['streamdata']['azureLocator']+'/'+str(j['result']['general']['ID'])+'_src.ism/Manifest(format=m3u8-aapl)'+tokenHLS
	DASH = 'http://'+j['result']['streamdata']['cdnShieldHTTP']+j['result']['streamdata']['azureLocator']+'/'+str(j['result']['general']['ID'])+'_src.ism/Manifest(format=mpd-time-csf)'+tokenDASH
	d = {}
	d['media'] = []
	#d['media'].append({'url':HLS, 'type': 'video', 'stream':'HLS'})
	d['media'].append({'url':DASH, 'type': 'video', 'stream':'DASH'})
	return d

def _initSession():
	response = libmediathek.getUrl(base + channelId + '/session/init?nxp_devh=1%3A1498445517%3A395527',_header())
	j = json.loads(response)
	return j['result']['general']['cid']

def _grepMetadata(j):
	d = {}
	d['id'] = str(j['general']['ID'])
	d['_name'] = j['general']['title']
	d['_tvshowtitle'] = j['general']['subtitle']
	d['_epoch'] = str(j['general']['updated'])
	if 'runtime' in j['general'] and j['general']['runtime'] != '':
		HH,MM,SS = j['general']['runtime'].split(':')
		d['duration'] = str(int(HH)*3600+int(MM)*60+int(SS))
	if 'studio_adref' in j['general'] and j['general']['studio_adref'] != '':
		d['channel'] = j['general']['studio_adref']
	if 'teaser' in j['general'] and j['general']['teaser'] != '':
		d['_plotoutline'] = j['general']['teaser']
	if 'textcontent' in j['general'] and j['general']['textcontent'] != '':
		d['_plot'] = j['general']['textcontent']
	elif 'description' in j['general'] and j['general']['description'] != '':
		d['_plot'] = j['general']['description']
	d['_thumb'] = j['imagedata']['thumb']
	d['_fanart'] = j['imagedata']['thumb_action']
	return d
	

def _header(operation=False,c=False):
	header = {}
	header['Accept'] = '*/*'
	header['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0'
	header['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
	header['Accept-Encoding'] = 'gzip, deflate'
	header['Host'] = 'api.nexx.cloud'
	if operation:
		header['Origin'] = origin
		if not c:
			c = cid
		header['X-Request-CID'] = c
		header['X-Request-Token'] = operations[operation]
	else:
		header['X-Request-Enable-Auth-Fallback'] = '1'
	return header
# -*- coding: utf-8 -*-
import sys
import xbmcplugin
import urllib
import libhrparser as libHrParser
import libmediathek3 as libMediathek

translation = libMediathek.getTranslation

ardhack = True


def libHrListMain():
	#l = []
	#l.append({'_name':translation(31033), 'mode':'libHrListDate'})
	#return l
	return libHrListDate()

def libHrListDate():
	return libMediathek.populateDirDate('libHrListDateVideos')
		
def libHrListDateVideos():
	return libHrParser.getDate(params['yyyymmdd'])
		
def libHrPlay():
	url = params['url']
	if ardhack:#ugly hack to get better quality videos
		s = params['url'].split('/')
		testurl = 'http://www.hr.gl-systemhaus.de/mp4/ARDmediathek/' + s[-2] + '/' + s[-1]
		libMediathek.log(testurl[-10:-4])
		id = int(testurl[-10:-4]) + 1
		testurl = testurl[:-10] + str(id) + '_webl_ard.mp4'
		try:
			headUrl(testurl)
			url = testurl
		except: pass
	d = {}
	d['media'] = []
	d['media'].append({'url':url, 'type': 'video', 'stream':'HLS'})
	
	#the libmediathek3 ttml parser can't handle this file now :(
	#if 'subUrl' in params:
	#	d['subtitle'] = [{'url':params['subUrl'], 'type': 'ttml', 'lang':'de'}]
	return d
	
def headUrl(url):#TODO: move to libmediathek3
	libMediathek.log(url)
	import urllib2
	req = urllib2.Request(url)
	req.get_method = lambda : 'HEAD'
	req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:25.0) Gecko/20100101 Firefox/25.0')
	
	response = urllib2.urlopen(req)
	info = response.info()
	response.close()
	return info
	
def list():	
	modes = {
	'libHrListMain': libHrListMain,
	'libHrListDate': libHrListDate,
	'libHrListDateVideos': libHrListDateVideos,
	'libHrPlay': libHrPlay,
	}
	
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	mode = params.get('mode','libHrListMain')
	if mode == 'libHrPlay':
		libMediathek.play(libHrPlay())
	else:
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	

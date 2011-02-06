# -*- coding: utf-8 -*- 

import cPickle
import StringIO
import md5
import sys
import os
import random
import re
import time
import urllib
import urllib2
import xbmc
import xbmcgui
from utilities import log, toOpenSubtitles_two, twotofull

_ = sys.modules[ "__main__" ].__language__

base_url = 'http://api.thesubdb.com/?%s'
user_agent = 'SubDB/1.0 (XBMCSubtitles/0.1; https://github.com/jrhames/script.xbmc.subtitles)'

def get_languages(languages):
	subdb_languages = []
	for language in languages:
		code = toOpenSubtitles_two(language)
		if code == 'pb':
			code = 'pt'
		subdb_languages.append(code)
	return subdb_languages

def get_hash(name):
	data = ""
	m = md5.new()
	readsize = 64 * 1024
	# with open(name, 'rb') as f:
	f = open(name, 'rb')
	try:
		size = os.path.getsize(name)
		data = f.read(readsize)
		f.seek(-readsize, 2)
		data += f.read(readsize)
	finally:
		f.close()
		
	m.update(data)
	return m.hexdigest()

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
	subtitles_list = []
	msg = ""
	
	if len(file_original_path) > 0:
		# get file hash
		hash = get_hash(file_original_path)
		# do the search
		languages = get_languages([lang1, lang2, lang3])
		params = {'action': 'search', 'hash': hash} #, 'language': ','.join(languages)
		url = base_url % urllib.urlencode(params)
		req = urllib2.Request(url)
		req.add_header('User-Agent', user_agent)
		try:
			# HTTP/1.1 200
			response = urllib2.urlopen(req)
			result = response.readlines()
			subtitles = result[0].split(',')
			for subtitle in subtitles:
				if subtitle in languages:
					filename = os.path.split(file_original_path)[1]
					params = {'action': 'download', 'language': subtitle, 'hash': hash }
					link = base_url % urllib.urlencode(params)
					if subtitle == "pt":						
						flag_image = 'flags/pb.gif'
					else:
						flag_image = "flags/%s.gif" % subtitle
						
					subtitles_list.append({'filename': filename,'link': link,'language_name': twotofull(subtitle),'language_id':"0",'language_flag':flag_image,'movie':filename,"ID":subtitle,"rating":"10","format": "srt","sync": True})
		except urllib2.HTTPError, e:
			# HTTP/1.1 !200
			return subtitles_list, "", msg #standard output
		except urllib2.URLError, e:
			# Unknown or timeout url
			log( __name__ ,"Service did not respond in time, aborting...")
			msg = _(755)
			return subtitles_list, "", msg #standard output
	        
	return subtitles_list, "", msg #standard output
    
def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
	language = subtitles_list[pos][ "language_name" ]
	link = subtitles_list[pos][ "link" ]
	file = os.path.splitext(subtitles_list[pos]["filename"])[0]
	ext = ""
	req = urllib2.Request(link)
	req.add_header('User-Agent', user_agent)
	try:
		response = urllib2.urlopen(req)
		ext = response.info()['Content-Disposition'].split(".")[1]
		filename = os.path.join(tmp_sub_dir, "%s.%s" % (file, ext))
		local_file = open(filename, "w" + "b")
		local_file.write(response.read())
		local_file.close()
		return False, language, filename #standard output
	except:
		return False , language, "" #standard output	

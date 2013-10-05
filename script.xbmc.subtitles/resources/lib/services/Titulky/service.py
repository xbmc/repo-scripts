# -*- coding: UTF-8 -*-

################################   Titulky.com #################################


import sys
import os
import xbmc,xbmcgui

import time,calendar
import urllib2,urllib,re,cookielib
from utilities import languageTranslate, log

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__addon__      = sys.modules[ "__main__" ].__addon__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
	# need to filter titles like <Localized movie name> (<Movie name>)
	br_index = title.find('(')
	if br_index > -1:
		title = title[:br_index]
	title = title.strip()
	session_id = "0"
	client = TitulkyClient()    
	subtitles_list = client.search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 )   
	return subtitles_list, session_id, ""  #standard output



def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

	subtitle_id =  subtitles_list[pos][ 'ID' ]
	client = TitulkyClient()
	username = __addon__.getSetting( "Titulkyuser" )
	password = __addon__.getSetting( "Titulkypass" )
	if password == '' or username == '':
		log(__name__,'Credentials to Titulky.com not provided')
	else:
		if client.login(username,password) == False:
			log(__name__,'Login to Titulky.com failed. Check your username/password at the addon configuration')
			dialog = xbmcgui.Dialog()
			dialog.ok(__scriptname__,_( 756 ))
			return True,subtitles_list[pos]['language_name'], ""
		log(__name__,'Login successfull')
	log(__name__,'Get page with subtitle (id=%s)'%(subtitle_id))
	content = client.get_subtitle_page(subtitle_id)
	control_img = client.get_control_image(content)
	if not control_img == None:
		log(__name__,'Found control image :(, asking user for input')
		# subtitle limit was reached .. we need to ask user to rewrite image code :(
		log(__name__,'Download control image')
		img = client.get_file(control_img)
		img_file = open(os.path.join(tmp_sub_dir,'image.png'),'w')
		img_file.write(img)
		img_file.close()

		solver = CaptchaInputWindow(captcha = os.path.join(tmp_sub_dir,'image.png'))
		solution = solver.get()
		if solution:
			log(__name__,'Solution provided: %s' %solution)
			content = client.get_subtitle_page2(content,solution,subtitle_id)
			control_img2 = client.get_control_image(content)
			if not control_img2 == None:
				log(__name__,'Invalid control text')
				return True,subtitles_list[pos]['language_name'], ""
		else:
			log(__name__,'Dialog was canceled')
			log(__name__,'Control text not confirmed, returning in error')
			return True,subtitles_list[pos]['language_name'], ""

	wait_time = client.get_waittime(content)
	cannot_download = client.get_cannot_download_error(content)
	if not None == cannot_download:
		log(__name__,'Subtitles cannot be downloaded, user needs to login')
		dialog = xbmcgui.Dialog()
		dialog.ok(__scriptname__,_( 761 ))
		return True,subtitles_list[pos]['language_name'], ""
	link = client.get_link(content)
	log(__name__,'Got the link, wait %i seconds before download' % (wait_time))
	delay = wait_time
	icon =  os.path.join(__cwd__,'icon.png')
	for i in range(wait_time+1):
		line2 = 'Download will start in %i seconds' % (delay,)
		xbmc.executebuiltin("XBMC.Notification(%s,%s,1000,%s)" % (__scriptname__,line2,icon))
		delay -= 1
		time.sleep(1)

	log(__name__,'Downloading subtitle zip')
	data = client.get_file(link)
	log(__name__,'Saving to file %s' % zip_subs)
	zip_file = open(zip_subs,'wb')
	zip_file.write(data)
	zip_file.close()
	return True,subtitles_list[pos]['language_name'], "zip" #standard output

def lang_titulky2xbmclang(lang):
	if lang == 'CZ': return 'Czech'
	if lang == 'SK': return 'Slovak'
	return 'English'

def lang_xbmclang2titulky(lang):
	if lang == 'Czech': return 'CZ'
	if lang == 'Slovak': return 'SK'
	return 'EN'	

def get_episode_season(episode,season):
	return 'S%sE%s' % (get2DigitStr(int(season)),get2DigitStr(int(episode)))
def get2DigitStr(number):
	if number>9:
		return str(number)
	else:
		return '0'+str(number)

def lang2_opensubtitles(lang):
	lang = lang_titulky2xbmclang(lang)
	return languageTranslate(lang,0,2)


class CaptchaInputWindow(xbmcgui.WindowDialog):
   def __init__(self, *args, **kwargs):
      self.cptloc = kwargs.get('captcha')
      self.img = xbmcgui.ControlImage(435,50,524,90,self.cptloc)
      self.addControl(self.img)
      self.kbd = xbmc.Keyboard('',_( 759 ),False)

   def get(self):
      self.show()
      self.kbd.doModal()
      if (self.kbd.isConfirmed()):
         text = self.kbd.getText()
         self.close()
         return text
      self.close()
      return False

class TitulkyClient(object):

	def __init__(self):
		self.server_url = 'http://www.titulky.com'
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
		opener.version = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'
		urllib2.install_opener(opener)
	def login(self,username,password):
			log(__name__,'Logging in to Titulky.com')
			login_postdata = urllib.urlencode({'Login': username, 'Password': password, 'foreverlog': '1','Detail2':''} )
			request = urllib2.Request(self.server_url + '/index.php',login_postdata)
			response = urllib2.urlopen(request).read()
			log(__name__,'Got response')
			return not response.find('BadLogin')>-1

	def search_subtitles(self, file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ):
		url = self.server_url+'/index.php?'+urllib.urlencode({'Fulltext':title,'FindUser':''})
		if not (tvshow == None or tvshow == ''):
			title2 = tvshow+' '+get_episode_season(episode,season)
			url = self.server_url+'/index.php?'+urllib.urlencode({'Fulltext':title2,'FindUser':''})
		req = urllib2.Request(url)
		try:
			size, SubHash = xbmc.subHashAndFileSize(file_original_path)
			file_size='%.2f' % (float(size)/(1024*1024))
		except:
			file_size='-1'
		log(__name__,'Opening %s' % (url))
		response = urllib2.urlopen(req)
		content = response.read()
		response.close()
		log(__name__,'Done')
		subtitles_list = []
		max_downloads=1
		log(__name__,'Searching for subtitles')
		for row in re.finditer('<tr class=\"r(.+?)</tr>', content, re.IGNORECASE | re.DOTALL):
			item = {}
			log(__name__,'New subtitle found')
			try:
				item['ID'] = re.search('[^<]+<td[^<]+<a href=\"[\w-]+-(?P<data>\d+).htm\"',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['title'] = re.search('[^<]+<td[^<]+<a[^>]+>(<div[^>]+>)?(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['sync'] = ''
				sync_found = re.search('((.+?)</td>)[^>]+>[^<]*<a(.+?)title=\"(?P<data>[^\"]+)',row.group(1),re.IGNORECASE | re.DOTALL )
				if sync_found:
					item['sync'] = sync_found.group('data')
				item['tvshow'] = re.search('((.+?)</td>){2}[^>]+>(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['year'] = re.search('((.+?)</td>){3}[^>]+>(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['downloads'] = re.search('((.+?)</td>){4}[^>]+>(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['lang'] = re.search('((.+?)</td>){5}[^>]+><img alt=\"(?P<data>\w{2})\"',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['numberOfDiscs'] = re.search('((.+?)</td>){6}[^>]+>(?P<data>[^<]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
				item['size'] = re.search('((.+?)</td>){7}[^>]+>(?P<data>[\d\.]+)',row.group(1),re.IGNORECASE | re.DOTALL ).group('data')
			except:
				log(__name__,'Exception when parsing subtitle, all I got is  %s' % str(item))
				continue
			if item['sync'] == '': # if no sync info is found, just use title instead of None
				item['filename'] = item['title']
			else:
				item['filename'] = item['sync']
			item['language_flag'] = "flags/%s.gif" % (lang2_opensubtitles(item['lang']))
			
			sync = False
			if not item['sync'] == '' and file_original_path.find(item['sync']) > -1:
				log(__name__,'found sync : filename match')
				sync = True
			if file_size==item['size']:
				log(__name__,'found sync : size match')
				sync = True
			item['sync'] = sync
			
			try:
				downloads = int(item['downloads'])
				if downloads>max_downloads:
					max_downloads=downloads
			except:
				downloads=0
			item['downloads'] = downloads
			
			if not year == '':
				if not item['year'] == year:
					log(__name__,'year does not match, ignoring %s' % str(item))
					continue
			lang = lang_titulky2xbmclang(item['lang'])
			
			item['language_name'] = lang
			item['mediaType'] = 'mediaType'
			item['rating'] = '0'
			
			if lang in [lang1,lang2,lang3]:
				subtitles_list.append(item)
			else:
				log(__name__,'language does not match, ignoring %s' % str(item))
		# computing ratings is based on downloads
		for subtitle in subtitles_list:
			subtitle['rating'] = str((subtitle['downloads']*10/max_downloads))
		return subtitles_list

	def get_cannot_download_error(self,content):
		if content.find('CHYBA') > -1:
			return True

	def get_waittime(self,content):
		for matches in re.finditer('CountDown\((\d+)\)', content, re.IGNORECASE | re.DOTALL):
			return int(matches.group(1))

	def get_link(self,content):
		for matches in re.finditer('<a.+id=\"downlink\" href="([^\"]+)\"', content, re.IGNORECASE | re.DOTALL):
			return str(matches.group(1))

	def get_control_image(self,content):
		for matches in re.finditer('\.\/(captcha\/captcha\.php)', content, re.IGNORECASE | re.DOTALL):
			return '/'+str(matches.group(1))
		return None

	def get_file(self,link):
		url = self.server_url+link
		log(__name__,'Downloading file %s' % (url))
		req = urllib2.Request(url)
		response = urllib2.urlopen(req)
		content = response.read()
		log(__name__,'Done')
		response.close()
		return content

	def get_subtitle_page2(self,content,code,id):
		url = self.server_url+'/idown.php'
		post_data = {'downkod':code,'titulky':id,'zip':'z','securedown':'2','histstamp':''}
		req = urllib2.Request(url,urllib.urlencode(post_data))
		log(__name__,'Opening %s POST:%s' % (url,str(post_data)))
		response = urllib2.urlopen(req)
		content = response.read()
		log(__name__,'Done')
		response.close()
		return content
		
	def get_subtitle_page(self,id):
		timestamp = str(calendar.timegm(time.gmtime()))
		url = self.server_url+'/idown.php?'+urllib.urlencode({'R':timestamp,'titulky':id,'histstamp':'','zip':'z'})
		log(__name__,'Opening %s' % (url))
		req = urllib2.Request(url)
		response = urllib2.urlopen(req)
		content = response.read()
		log(__name__,'Done')
		response.close()
		return content


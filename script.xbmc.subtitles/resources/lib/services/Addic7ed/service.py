# -*- coding: utf-8 -*-

import os, sys, re, xbmc, xbmcgui, string, urllib, urllib2, socket
from utilities import log, toOpenSubtitles_two
from BeautifulSoup import BeautifulSoup


_ = sys.modules[ "__main__" ].__language__

self_host = "http://www.addic7ed.com"
self_release_pattern = re.compile(" \nVersion (.+), ([0-9]+).([0-9])+ MBs")

def compare_columns(b,a):
    return cmp( a["sync"], b["sync"] ) or cmp( b["language_name"], a["language_name"] )
    
def get_url(url):
    req_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.13 (KHTML, like Gecko) Chrome/0.A.B.C Safari/525.13',
    'Referer': 'http://www.addic7ed.com'}
    request = urllib2.Request(url, headers=req_headers)
    opener = urllib2.build_opener()
    response = opener.open(request)

    contents = response.read() 
    return contents    

def query_TvShow(name, season, episode, file_original_path, langs):
    sublinks = []
    name = name.lower().replace(" ", "_").replace("$#*!","shit").replace("'","") # need this for $#*! My Dad Says and That 70s show
    searchurl = "%s/serie/%s/%s/%s/addic7ed" %(self_host, name, season, episode)
    socket.setdefaulttimeout(3)
    page = urllib2.urlopen(searchurl)
    content = page.read()
    content = content.replace("The safer, easier way", "The safer, easier way \" />")
    soup = BeautifulSoup(content)
    for subs in soup("td", {"class":"NewsTitle", "colspan" : "3"}):
      try:  
        langs_html = subs.findNext("td", {"class" : "language"})
        fullLanguage = str(langs_html).split('class="language">')[1].split('&nbsp;<a')[0].replace("\n","")
        subteams = self_release_pattern.match(str(subs.contents[1])).groups()[0].lower()
        file_name = os.path.basename(file_original_path).lower()
        if (file_name.find(str(subteams))) > -1:
          hashed = True
        else:
          hashed = False
        try:
          lang = toOpenSubtitles_two(fullLanguage)
        except:
          lang = ""
        statusTD = langs_html.findNext("td")
        status = statusTD.find("strong").string.strip()
        link = "%s%s"%(self_host,statusTD.findNext("td").find("a")["href"])
        if status == "Completed" and (lang in langs) :
            sublinks.append({'filename':"%s.S%.2dE%.2d-%s" %(name.replace("_", ".").title(), int(season), int(episode),subteams ),'link':link,'language_name':fullLanguage,'language_id':lang,'language_flag':"flags/%s.gif" % (lang,),'movie':"movie","ID":"subtitle_id","rating":"0","format":"srt","sync":hashed})
      except:
        print "Error"
        pass      
    return sublinks
 
def query_Film(name, file_original_path,year, langs):
    sublinks = []
    name = urllib.quote(name.replace(" ", "_"))
    searchurl = "%s/film/%s_(%s)-Download" %(self_host,name, str(year))
    socket.setdefaulttimeout(5)
    page = urllib2.urlopen(searchurl)
    content = page.read()
    content = content.replace("The safer, easier way", "The safer, easier way \" />")
    soup = BeautifulSoup(content)
    for subs in soup("td", {"class":"NewsTitle", "colspan" : "3"}):
      try:
        langs_html = subs.findNext("td", {"class" : "language"})
        fullLanguage = str(langs_html).split('class="language">')[1].split('&nbsp;<a')[0].replace("\n","")
        subteams = self_release_pattern.match(str(subs.contents[1])).groups()[0].lower()
        file_name = os.path.basename(file_original_path).lower()
        if (file_name.find(str(subteams))) > -1:
          hashed = True
        else:
          hashed = False  
        try:
          lang = toOpenSubtitles_two(fullLanguage)
        except:
          lang = ""
        statusTD = langs_html.findNext("td")
        status = statusTD.find("strong").string.strip()
        link = "%s%s"%(self_host,statusTD.findNext("td").find("a")["href"])
        if status == "Completed" and (lang in langs) :
            sublinks.append({'filename':"%s-%s" %(name.replace("_", ".").title(),subteams ),'link':link,'language_name':fullLanguage,'language_id':lang,'language_flag':"flags/%s.gif" % (lang,),'movie':"movie","ID":"subtitle_id","rating":"0","format":"srt","sync":hashed})
      except:
        pass
    return sublinks    


def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3 ): #standard input
    subtitles_list = []
    langs = []
    langs.append(toOpenSubtitles_two(lang1))
    if lang1 != lang2:
      langs.append(toOpenSubtitles_two(lang2))
    if lang3 != lang1 and lang3 != lang2:
      langs.append(toOpenSubtitles_two(lang3))
    msg = ""
    log( __name__ ,"Title = %s" %  title)
    if len(tvshow) == 0: # TV Shows
        subtitles_list = query_Film(title, file_original_path,year, langs)
    else:
        subtitles_list = query_TvShow(tvshow, str(season), str(episode),file_original_path, langs)
        if( len ( subtitles_list ) > 0 ):
            subtitles_list = sorted(subtitles_list, compare_columns)
    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    url = subtitles_list[pos][ "link" ]
    file = os.path.join(tmp_sub_dir, "adic7ed.srt")

    f = get_url(url)

    local_file_handle = open(file, "w" + "b")
    local_file_handle.write(f)
    local_file_handle.close() 
   
    language = subtitles_list[pos][ "language_name" ]
    return False, language, file #standard output

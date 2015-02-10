# -*- coding: utf-8 -*- 

import sys
import os
import urllib2
import re
import xbmc, xbmcgui, xbmcvfs
from BeautifulSoup import BeautifulSoup
from utilities import log, languageTranslate
from utilities import hashFileMD5

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, language1, language2, language3, stack ): #standard input
    subtitles_list = []
    msg = ""

    log(__name__, "Search GomTV with a file name, "+file_original_path)
    movieFullPath = xbmc.Player().getPlayingFile()
    video_hash = hashFileMD5( movieFullPath, buff_size=1024*1024 )
    if video_hash is None:
        msg = _(755)
        return subtitles_list, "", msg  #standard output
    webService = GomTvWebService()
    if len(tvshow) > 0:                                            # TvShow
        OS_search_string = ("%s S%.2dE%.2d" % (tvshow,
                                           int(season),
                                           int(episode),)
                                          ).replace(" ","+")      
    else:                                                          # Movie or not in Library
        if str(year) == "":                                          # Not in Library
            title, year = xbmc.getCleanMovieTitle( title )
        else:                                                        # Movie in Library
            year  = year
            title = title
        OS_search_string = title.replace(" ","+")
    subtitles_list = webService.SearchSubtitlesFromTitle( OS_search_string ,video_hash)
    log(__name__, "Found %d subtitles in GomTV" %len(subtitles_list))

    return subtitles_list, "", msg  #standard output

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    language = subtitles_list[pos][ "language_name" ]
    link = subtitles_list[pos][ "link" ]
    webService = GomTvWebService()
    log(__name__,  "parse subtitle page at %s" %link)
    url = webService.GetSubtitleUrl( link )
    log(__name__,  "download subtitle from %s" %url)
    try:
        fname = "gomtv-%s.smi" % subtitles_list[pos]["ID"]
        tmp_fname = os.path.join(tmp_sub_dir, fname)
        resp = urllib2.urlopen(url)
        f = open(tmp_fname, "w")
        f.write(resp.read())
        f.close()
    except:
        return False, language, ""
    return False, language, tmp_fname    #standard output
  
class GomTvWebService:
    root_url = "http://gom.gomtv.com"
    agent_str = "GomPlayer 2, 1, 23, 5007 (KOR)"

    def __init__ (self):
        pass

        
    def SearchSubtitlesFromTitle (self, searchString,key):
        subtitles = []
        subtitles = []

        q_url = "http://gom.gomtv.com/jmdb/search.html?key=%s" %key
        log(__name__, "search subtitle at %s"  %q_url)

        # main page
        req = urllib2.Request(q_url)
        req.add_header("User-Agent", self.agent_str)
        html = urllib2.urlopen(req).read()
        if "<div id='search_failed_smi'>" in html:
            log(__name__, "no result found")
            return []
        elif "<script>location.href" in html:
            log(__name__, "redirected")
            if "key=';</script>" in html:
                log(__name__, "fail to search with given key")
                return []
            q_url = self.parseRedirectionPage(html)
            req = urllib2.Request(q_url)
            req.add_header("User-Agent", self.agent_str)
            html = urllib2.urlopen(req).read()
        elif "<script>top.location.replace" in html:
            log(__name__, "redirected")
            if "key=';</script>" in html:
                log(__name__, "fail to search with given key")
                return []
            q_url = self.parseRedirectionPage(html)
            req = urllib2.Request(q_url)
            req.add_header("User-Agent", self.agent_str)
            html = urllib2.urlopen(req).read()
        # regular search result page
        soup = BeautifulSoup(html)
        subtitles = []
        for row in soup.find("table",{"class":"tbl_lst"}).findAll("tr")[1:]:
            a_node = row.find("a")
            if a_node is None:
                continue
            title = a_node.text
            lang_node_string = row.find("span",{"class":"txt_clr3"}).string
            url = self.root_url + a_node["href"]
            if u"한글" in lang_node_string:
                langlong  = "Korean"
            elif u"영문" in lang_node_string:
                langlong  = "English"
            else:   # [통합]
                langlong  = "Korean"
            langshort = languageTranslate(langlong, 0, 2)
            subtitles.append( {
                "link"          : url,
                "filename"      : title,
                "ID"            : key,
                "format"        : "smi",
                "sync"          : True,
                "rating"        : "0",
                "language_name" : langlong,
                "language_flag" : "flags/%s.gif" %langshort
            } )            
            
        q_url = "http://gom.gomtv.com/main/index.html?ch=subtitles&pt=l&menu=subtitles&lang=0&sValue=%s" %searchString
        print q_url
        log(__name__, "search subtitle at %s"  %q_url)

        # main page
        req = urllib2.Request(q_url)
        req.add_header("User-Agent", self.agent_str)
        html = urllib2.urlopen(req).read()
        if "<div id='search_failed_smi'>" in html:
            log(__name__, "no result found")
            return []
        elif "<script>location.href" in html:
            log(__name__, "redirected")
            if "key=';</script>" in html:
                log(__name__, "fail to search with given key")
                return []
            q_url = self.parseRedirectionPage(html)
            req = urllib2.Request(q_url)
            req.add_header("User-Agent", self.agent_str)
            html = urllib2.urlopen(req).read()
        elif "<script>top.location.replace" in html:
            log(__name__, "redirected")
            if "key=';</script>" in html:
                log(__name__, "fail to search with given key")
                return []
            q_url = self.parseRedirectionPage(html)
            req = urllib2.Request(q_url)
            req.add_header("User-Agent", self.agent_str)
            html = urllib2.urlopen(req).read()
        # regular search result page
        soup = BeautifulSoup(html)
        for row in soup.find("table",{"class":"tbl_lst"}).findAll("tr")[1:]:
            if row is None:
        	      continue
            a_node = row.find("a")
            if a_node is None:
                continue
            title = a_node.text
            lang_node_string = row.find("span",{"class":"txt_clr3"}).string
            url = self.root_url + a_node["href"]
            if u"한글" in lang_node_string:
                langlong  = "Korean"
            elif u"영문" in lang_node_string:
                langlong  = "English"
            else:   # [통합]
                langlong  = "Korean"
            langshort = languageTranslate(langlong, 0, 2)
            subtitles.append( {
                "link"          : url,
                "filename"      : title,
                "ID"            : key,
                "format"        : "smi",
                "sync"          : False,
                "rating"        : "0",
                "language_name" : langlong,
                "language_flag" : "flags/%s.gif" %langshort
            } )            
        return subtitles

    def parseRedirectionPage(self, html):
        url = re.split("\'",html)[1]
        if 'noResult' in url:   # no result (old style)
            print "Unusual result page, "+page_url
            return subtitles
        return self.root_url+url

    def GetSubtitleUrl (self, page_url):
        html = urllib2.urlopen(page_url).read()
        sp2 = ""
        if "a href=\"jamak://gom.gomtv.com" in html:
            sp = re.split("a href=\"jamak://gom.gomtv.com",html)[1]
            sp2 = re.split("\"",sp)[0]
        elif "onclick=\"downJm(" in html:
            s1 = re.split("onclick=\"downJm",html)[1]
            intSeq = re.split("'",s1)[1]
            capSeq = re.split("'",s1)[3]
            sp2 = "/main/index.html?pt=down&ch=subtitles&intSeq="+intSeq+"&capSeq="+capSeq
        else:
       	    return None
       	print sp2
        return self.root_url+sp2

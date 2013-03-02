# -*- coding: utf-8 -*- 

import sys
import os
import urllib2
import re
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
    video_hash = hashFileMD5( file_original_path, buff_size=1024*1024 )
    if video_hash is None:
        msg = _(755)
        return subtitles_list, "", msg  #standard output
    webService = GomTvWebService()
    subtitles_list = webService.SearchSubtitles( video_hash )
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
    return True, language, tmp_fname    #standard output
  
class GomTvWebService:
    root_url = "http://gom.gomtv.com"
    agent_str = "GomPlayer 2, 1, 23, 5007 (KOR)"

    def __init__ (self):
        pass

    def SearchSubtitles (self, key):
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
        # regular search result page
        soup = BeautifulSoup(html)
        subtitles = []
        for row in soup.find("table",{"class":"smi_list"}).findAll("tr")[1:]:
            a_node = row.find("a")
            if a_node is None:
                    continue
            title = a_node.text
            url = self.root_url + a_node["href"]
            if title.startswith(u"[한글]"):
                langlong  = "Korean"
                title = title[4:]
            elif title.startswith(u"[영문]"):
                langlong  = "English"
                title = title[4:]
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
        return subtitles

    def parseRedirectionPage(self, html):
        match = re.match('''<script>location.href = '([^']*)';</script>''', html)
        if match is None:
            raise UnknownFormat
        url = match.group(1)
        if 'noResult' in url:   # no result (old style)
            print "Unusual result page, "+page_url
            return subtitles
        return self.root_url+'/jmdb/'+url

    def GetSubtitleUrl (self, page_url):
        html = urllib2.urlopen(page_url).read()
        downids = re.search('''javascript:save[^\(]*\('(\d+)','(\d+)','[^']*'\);''', html).group(1,2)
        return self.root_url+"/jmdb/save.html?intSeq=%s&capSeq=%s" %downids

import cookielib
import datetime
import urllib2
import urllib
import time
import re
import zlib
import bs4

import xbmcaddon

from SubtitleHelper import log

__addon__      = xbmcaddon.Addon()
__version__    = __addon__.getAddonInfo('version') # Module version
__scriptname__ = __addon__.getAddonInfo('name')

class SubtitleOption(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        
    def __repr__(self):
        return "%s" % (self.name)
    
class SubtitlePage(object):
    def __init__(self, id, name, url, data):
        self.id = id
        self.name = name
        self.url = url
        self.options = self._parseOptions(data)
        
    def _parseOptions(self, data):
        subtitleSoup = bs4.BeautifulSoup(data)
        subtitleOptions = subtitleSoup("div", {'class' : 'download_box' })[0].findAll("option")
        filteredSubtitleOptions = filter(lambda x: x.has_key("value"), subtitleOptions)
        return map(lambda x: SubtitleOption(x.string.strip(), x["value"]), filteredSubtitleOptions)
        
class Response(object):
    def __init__(self, response):
        self.data = self._handleData(response)
        self.headers = response.headers
        
    def _handleData(self, resp):
        data = resp.read()
        if (len(data) != 0):
            try:
                data = zlib.decompress(data, 16+zlib.MAX_WBITS)
            except zlib.error:
                pass
        return data

class FirefoxURLHandler:
    def __init__(self):
        cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        self.opener.addheaders = [('Accept-Encoding','gzip, deflate'),
                                  ('Accept-Language', 'en-us,en;q=0.5'),
                                  ('Pragma', 'no-cache'),
                                  ('Cache-Control', 'no-cache'),
                                  ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36')]
    
    def request(self, url, data=None, ajax=False, referer=None, cookie=None):
        if (data != None):
            data = urllib.urlencode(data)
        if (ajax == True):
            self.opener.addheaders += [('X-Requested-With', 'XMLHttpRequest')]
        if (referer != None):
            self.opener.addheaders += [('Referer', referer)]
        if (cookie != None):
            self.opener.addheaders += [('Cookie', cookie)]
  
        resp = self.opener.open(url, data)        
        return Response(resp)

class TorecSubtitlesDownloader:
    DEFAULT_SEPERATOR = " "
    BASE_URL          = "http://www.torec.net"
    SUBTITLE_PATH     = "sub.asp?sub_id="
    DEFAULT_COOKIE    = "Torec_NC_s=%(screen_width)d; Torec_NC_sub_%(subId)s=sub=%(current_datetime)s"

    def __init__(self):
        self.urlHandler = FirefoxURLHandler()
        
    def _buildDefaultCookie(self, subID):
        currentTime = datetime.datetime.now().strftime("%m/%d/%Y+%I:%M:%S+%p")
        return self.DEFAULT_COOKIE % {"screen_width" : 1440, 
                                      "subId" : subID, 
                                      "current_datetime" : currentTime}
    
    def search(self, movie_name):
        santized_name = self.sanitize(movie_name)
        log(__name__ , "Searching for %s" % santized_name)
        subtitlePage = self.search_by_movie_name(santized_name)
        if subtitlePage is None:
            log(__name__ ,"Couldn't find relevant subtitle page")
            return None
        else:
            log(__name__ , "Found relevant meta data")
            return subtitlePage

    def search_by_movie_name(self, movie_name):
        response = self.urlHandler.request("%s/ssearch.asp" % self.BASE_URL, {"search" : movie_name})
        match = re.search('sub\.asp\?sub_id=(\w+)', response.data)
        if (match is None):
            return None
          
        subtitle_id = match.groups()[0]
        subtitle_url = "%s/%s%s" % (self.BASE_URL, self.SUBTITLE_PATH, subtitle_id)
        subtitle_data = self.urlHandler.request(subtitle_url).data
        return SubtitlePage(subtitle_id, movie_name, subtitle_url, subtitle_data)
        
    def _requestSubtitle(self, subID, subURL):
        params = {"sub_id"  : subID, 
                  "s"       : 1440}
                  
        return self.urlHandler.request("%s/ajax/sub/guest_time.asp" % self.BASE_URL, params, 
                                        ajax=True, referer=subURL, cookie=self._buildDefaultCookie(subID)).data
        
    def getDownloadLink(self, subID, optionID, subURL, persist=True):        
        requestID = self._requestSubtitle(subID, subURL)
        
        params = {"sub_id" : subID, "code": optionID, "sh" : "yes", "guest" : requestID, "timewaited" : "12"}
        for i in xrange(16):
            response = self.urlHandler.request("%s/ajax/sub/downloadun.asp" % self.BASE_URL, params, ajax=True)
            if (not persist):
                break

            if (len(response.data) != 0 and (not response.data.startswith("ERROR"))):
                break

            print "Response received is inadequate (" + response.data + "). Sleeping a bit"
            time.sleep(0.5)
            
        return response.data
        
    def download(self, downloadLink):
        response = self.urlHandler.request("%s%s" % (self.BASE_URL, downloadLink))
        fileName = re.search("filename=(.*)", response.headers["content-disposition"]).groups()[0]
        return (response.data, fileName)
            
    def sanitize(self, name):
        cleaned_name = re.sub('[\']', '', name.upper())
        return re.sub('[\.\[\]\-]', self.DEFAULT_SEPERATOR, cleaned_name)
        
    def find_most_relevant_option(self, name, subtitles_options):
        tokenized_name = self.sanitize(name).split()
        # Find the most likely subtitle (the subtitle which adheres to most of the movie properties)
        maxLikelihood = 0
        most_relevant_option = None
        for option in subtitles_options:
            subtitleName = self.sanitize(option.name).split()
            subtitleLikelihood = 0
            for token in subtitleName:
                if token in tokenized_name:
                    subtitleLikelihood += 1
                if (subtitleLikelihood > maxLikelihood):
                    maxLikelihood = subtitleLikelihood
                    most_relevant_option = option

        return most_relevant_option

    def get_best_match_id(self, name, subtitle_page):
        most_relevant_option = self.find_most_relevant_option(name, subtitle_page.options)
        return most_relevant_option.id if most_relevant_option != None else None

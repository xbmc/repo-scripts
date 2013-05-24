import cookielib
import datetime
import zipfile
import urllib2
import urllib
import codecs
import shutil
import time
import os
import sys
import re
import zlib
import os.path
from BeautifulSoup import BeautifulSoup

from utilities import *

def convert_file(inFile,outFile):
	''' Convert a file in cp1255 encoding to utf-8
	
	:param inFile: the path to the intput file
	:param outFile: the path to the output file
	'''
	with codecs.open(inFile,"r","cp1255") as f:
		with codecs.open(outFile, 'w', 'utf-8') as output:
			for line in f:
				output.write(line)
	return

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
        subtitleSoup = BeautifulSoup(data)
        subtitleOptions = subtitleSoup("div", {'class' : 'download_box' })[0].findAll("option")
        return map(lambda x: SubtitleOption(x.string.strip(), x["value"]), subtitleOptions)

    def __str__(self):
        log(__name__ ,self.name)
        for option in self.options:
            log(__name__ ,option)
        
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

class FirefoxURLHandler():
    def __init__(self):
        cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        self.opener.addheaders = [('Accept-Encoding','gzip, deflate'),
                                  ('Accept-Language', 'en-us,en;q=0.5'),
                                  ('Pragma', 'no-cache'),
                                  ('Cache-Control', 'no-cache'),
                                  ('User-Agent', 'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:16.0) Gecko/20100101 Firefox/16.0')]
    
    def request(self, url, data=None, ajax=False, referer=None, cookie=None):
        if (data != None):
            data = urllib.urlencode(data)
        # FIXME: Awful code duplication
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
    BASE_URL = "http://www.torec.net"
    SUBTITLE_PATH = "sub.asp?sub_id="
    DEFAULT_COOKIE = "Torec_NC_s=%(screen_width)d; Torec_NC_sub_%(subId)s=sub=%(current_datetime)s"

    def __init__(self):
        self.urlHandler = FirefoxURLHandler()
        
    def _buildDefaultCookie(self, subID):
        currentTime = datetime.datetime.now().strftime("%m/%d/%Y+%I:%M:%S+%p")
        return self.DEFAULT_COOKIE % {"screen_width" : 1760, 
                                      "subId" : subID, 
                                      "current_datetime" : currentTime}
    
    def searchMovieName(self, movieName):
        response = self.urlHandler.request("%s/ssearch.asp" % self.BASE_URL, {"search" : movieName})
        match = re.search('sub\.asp\?sub_id=(\w+)', response.data)
        if (match is None):
            return None
          
        id = match.groups()[0]
        subURL = "%s/%s%s" % (self.BASE_URL, self.SUBTITLE_PATH, id)
        subtitleData = self.urlHandler.request(subURL).data
        return SubtitlePage(id, movieName, subURL, subtitleData)
        
    def findChosenOption(self, name, subtitlePage):
        name = name.split(self.DEFAULT_SEPERATOR)
        # Find the most likely subtitle (the subtitle which adheres to most of the movie properties)
        maxLikelihood = 0
        chosenOption = None
        for option in subtitlePage.options:
            subtitleName = self.sanitize(option.name).split(" ")
            subtitleLikelihood = 0
            for token in subtitleName:
                if token in name:
                    subtitleLikelihood += 1
                if (subtitleLikelihood > maxLikelihood):
                    maxLikelihood = subtitleLikelihood
                    chosenOption = option

        return chosenOption
        
    def _requestSubtitle(self, subID, subURL):
        params = {"sub_id"  : subID, 
                  "s"       : 1760}
                  
        return self.urlHandler.request("%s/ajax/sub/guest_time.asp" % self.BASE_URL, params, 
                                        ajax=True, referer=subURL, cookie=self._buildDefaultCookie(subID)).data
        
    def getDownloadLink(self, subID, optionID, subURL, persist=True):        
        requestID = self._requestSubtitle(subID, subURL)
        
        params = {"sub_id" : subID, "code": optionID, "sh" : "yes", "guest" : requestID, "timewaited" : "16"}
        for i in xrange(16):
            response = self.urlHandler.request("%s/ajax/sub/downloadun.asp" % self.BASE_URL, params, ajax=True)
            if (len(response.data) != 0 or not persist):
                break
            time.sleep(1)
            
        return response.data
        
    def download(self, downloadLink):
        response = self.urlHandler.request("%s%s" % (self.BASE_URL, downloadLink))
        fileName = re.search("filename=(.*)", response.headers["content-disposition"]).groups()[0]
        return (response.data, fileName)
        
    def saveData(self, fileName, data, shouldUnzip=True):
        log(__name__ ,"Saving to %s (size %d)" % (fileName, len(data)))
        # Save the downloaded zip file
        with open( fileName,"wb") as f:
            f.write(data)
        
        shouldUnzip = True
        if shouldUnzip:
            # Unzip the zip file
            log(__name__ ,"Unzip the zip file")
            zipDirPath = os.path.dirname(fileName)
            zip = zipfile.ZipFile(fileName, "r")
            zip.extractall(zipDirPath)
            zip.close()
            # Remove the unneeded zip file
            os.remove(fileName)
            
            for srtFile in os.listdir(zipDirPath):
	        if srtFile.endswith(".srt"):
                    srtFile = os.path.join(zipDirPath,srtFile)
                    
                    #convert file from cp1255 to utf-8
                    tempFileName=srtFile+ ".tmp"
                    convert_file(srtFile,tempFileName)
                    shutil.copy(tempFileName,srtFile)
                    os.remove(tempFileName)
            
    def sanitize(self, name):
        return re.sub('[\.\[\]\-]', self.DEFAULT_SEPERATOR, name.upper())

    def getSubtitleMetaData(self, movieName):
        sanitizedName = self.sanitize(movieName)
        log(__name__ , "Searching for %s" % sanitizedName)
        subtitlePage = self.searchMovieName(sanitizedName)
        if subtitlePage is None:
            log(__name__ ,"Couldn't find relevant subtitle page")
            return
            
        log(__name__ , "Found relevant meta data")
        return subtitlePage
        
    def getSubtitleData(self, movieName, resultSubtitleDirectory):
        subtitlePage = self.getSubtitleMetaData(movieName)
        # Try to choose the most relevant option according to the file name
        chosenOption = self.findChosenOption(subtitlePage.name, subtitlePage)
        if chosenOption != None:
            log(__name__ ,"Found the subtitle type - %s" % chosenOption)
        else:
            
            log(__name__ ,"No suitable subtitle found!")
            log(__name__ ,"Available options are:")
            options = enumerate(subtitlePage.options, start=1)
            for num, option in options:
                log(__name__ ,"\t(%d) %s" % (num, option))
                
            choice = int(raw_input("What subtitle do you want to download? "))
            while (choice < 0 or choice > len(subtitlePage.options)):
                log(__name__ ,"bad choice")
                choice = int(raw_input("What subtitle do you want to download? "))
        
            chosenOption = subtitlePage.options[choice-1]

        # Retrieve the download link and download the subtitle
        downloadLink = self.getDownloadLink(subtitlePage.id, chosenOption.id, subtitlePage.url)
        if (downloadLink == ""):
            log(__name__ ,"Download Unsuccessful!")
            return
        
        (subtitleData, subtitleName) = self.download(downloadLink)
        
        resultSubtitlePath = os.path.join(resultSubtitleDirectory, subtitleName)
        self.saveData(resultSubtitlePath, subtitleData)

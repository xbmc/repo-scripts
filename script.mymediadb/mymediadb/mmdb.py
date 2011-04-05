import urllib2
import base64
import simplejson as json
from mymediadb.commonutils import debug,addon

class MMDB: 
    
    apiurl = 'http://mymediadb.org/api/0.1'
    session_cookie = None
    
    def __init__(self,username,password):
        self.username = username;
        self.password = password;
       
    def getRemoteMovieLibrary(self):
        request = self.__makeRequest(self.apiurl+'/user')
        f = self.__openRequest(request)
        if(f == None):
            return None
        library = json.load(f)['mediaLibrary']
        for i, media in enumerate(library):
            tags = self._getRemoteMovieTags(media['mediaId'])
            library[i].update(tags)
        return library
    
    def setRemoteMovieTag(self,imdbId,postdata):
        if(addon.getSetting('testmode') == 'false'):          
            request = self.__makeRequest(self.apiurl+'/userMedia?mediaType=movie&idType=imdb&id=%s' % imdbId)
            request.add_data(json.dumps(postdata))
            request.get_method = lambda: 'PUT'
            f = self.__openRequest(request)
            if(f != None):
                json.load(f)
        else:
            debug('MMDB Testmode cancelled API request "setRemoteMovieTag"')

    def _getRemoteMovieTags(self,mediaId):
        request = self.__makeRequest(self.apiurl+'/userMedia?mediaType=movie&idType=mmdb&id=%s' % mediaId)
        f = self.__openRequest(request)
        if(f != None):
            return json.load(f)
        return None

    def __makeRequest(self,url):
        request = urllib2.Request(url)
        if(self.session_cookie != None):
            request.add_header("Cookie", self.session_cookie)
            
        base64string = base64.encodestring('%s:%s' % (self.username, self.password)).replace('\n', '')            
        request.add_header("Authorization", "Basic %s" % base64string)
        request.add_header("Content-Type","text/json")
        return request
    
    def __openRequest(self,request):
        opener = urllib2.build_opener()
        response = opener.open(request)
        headers = response.info()
        if('set-cookie' in headers):
            self.session_cookie = headers['set-cookie']
        return response        
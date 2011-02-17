#!/usr/bin/python

__all__ = ["jsonrpcSession", "Request", "JsonRPC", "song", "playlist", "artist", "album", "search", "popular"]

#import song
#import playlist
#import artist
#import album
#import search
#import popular

# Grooveshark module

import urllib2
import urllib
import re
import uuid
#import json
try:
    import json
except ImportError:
    from main_thirdp import simplejson as json
import hashlib
import random
import time

# Constants
DOMAIN = "grooveshark.com"
HOME_URL = "http://listen." + DOMAIN
TOKEN_URL = "http://cowbell." + DOMAIN + "/more.php" #"https://cowbell." + DOMAIN + "/service.php"
API_URL = "http://cowbell." + DOMAIN + "/more.php"
SERVICE_URL = "http://cowbell." + DOMAIN + "/service.php"

RANDOM_CHARS = "1234567890abcdef"

CLIENT_NAME = "gslite" #htmlshark #jsqueue
CLIENT_VERSION = "20101012.37" #"20100831.25"

RE_SESSION = re.compile('"sessionID":"\s*?([A-z0-9]+)"') #re.compile('sessionID:\s*?\'([A-z0-9]+)\',')


class Request:
    """class: For making a standard API request"""

    def __init__(self, api, parameters, method, type="default", clientVersion=None):
        """function: Initiates the Request"""
        
        if clientVersion != None:
            if float(clientVersion) < float(CLIENT_VERSION):
                clientVersion = CLIENT_VERSION
        if clientVersion == None:
            clientVersion = CLIENT_VERSION
            
        postData = {
            "header": {
                "client": CLIENT_NAME,
                "clientRevision": clientVersion,
                "uuid": api._uuid,
                "session": api._session},
                "country": {"IPR":"1021", "ID":"223", "CC1":"0", "CC2":"0", "CC3":"0", "CC4":"2147483648"},
                "privacy": 1,
            "parameters": parameters,
            "method": method}
            
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.12) Gecko/20101026 Firefox/3.6.12 (.NET CLR 3.5.30729)",            
            "Referer": "http://listen.grooveshark.com/main.swf?cowbell=fe87233106a6cef919a1294fb2c3c05f"
            }

        if "token" == type:
            url = TOKEN_URL
        else:
            postData["header"]["token"] = api._generateToken(method)

            if "service" == type:
                url = SERVICE_URL + "?" + method
            else:
                url = API_URL + "?" + method

        postData = json.dumps(postData)
        print url
        #print headers
        #print postData
        self._request = urllib2.Request(url, postData, headers)

    def send(self):
        """function: Makes the request"""
        response = urllib2.urlopen(self._request).read()
        #print response

        try:
            response = json.loads(response)
        except:
            raise StandardError("API error: " + response)

        try:
            response["fault"]
        except KeyError:
            return response
        else:
            raise StandardError("API error: " + response["fault"]["message"])


def jsonrpcSession(clientUuid=None, clientVersion=None):
    """function: Makes an API instance"""
    if None == clientUuid:
        clientUuid = str(uuid.uuid4())

    return JsonRPC(clientUuid, clientVersion)


class JsonRPC:
    """class: An abstraction for the Grooveshark JSON-RPC API"""

    def __init__(self, uuid, clientVersion):
        """function: Init the Grooveshark API class"""
        self._uuid = uuid
        self.clientVersion = clientVersion

    _token = None
    _lastTokenTime = None
    _uuid = None
    _session = None

    def startSession(self):
        """function: Abstracts the authentication process for Grooveshark"""
        self._session = self._parseHomePage()
        self._token = self._getToken()
        self._lastTokenTime = time.time()

    def _generateUUID(self):
        """function: Generate a random uuid"""
        return str(uuid.uuid4())

    def _getToken(self):
        """function: Get a communication token"""
        parameters = {
            "secretKey": self._generateSecretKey(self._session)}
        response = self.request(parameters, "getCommunicationToken",
                "token").send()
        try:
            return response["result"]
        except TypeError, error:
            raise error

    def _generateToken(self, method):
        """function: Make a token ready for a request header"""
        if 1000 <= (time.time() - self._lastTokenTime):
            self._token = self._getToken()
            self._lastTokenTime = time.time()

        randomChars = ""
        while 6 > len(randomChars):
            randomChars = randomChars + random.choice(RANDOM_CHARS)

        token = hashlib.sha1(method + ":" + self._token +
                ":quitStealinMahShit:" + randomChars).hexdigest()
                #:quitBasinYoBidnessPlanOnBuildingALargeUserbaseViaCopyrightInfringment:
        return randomChars + token

    def _generateSecretKey(self, session):
        """function: Generate a secret key from a sessionID"""
        return hashlib.md5(session).hexdigest()

    def _getSession(self, html):
        """function: Parse a sessionId from some HTML"""
        html = RE_SESSION.search(html)

        if html:
            return html.group(1)
        else:
            return None

    def _parseHomePage(self):
        """function: Parse the Grooveshark home page for session ID's etc"""
        response = urllib2.urlopen(HOME_URL).read()
        #print response
        session = self._getSession(response)
        #print session
        if None == session:
            raise StandardError("Failed to parse sessionID")

        return session

    def request(self, parameters, method, type="default"):
        """function: Create a request"""
        return Request(self, parameters, method, type, self.clientVersion)

    def getSearchResults(self, query, type="Songs"):
        """function: Get some search results :p"""
        parameters = {
            "query": query,
            "type": type}

        response = Request(self, parameters, "getSearchResultsEx").send()

        return {
            "query": query,
            "songs": self._parseSongs(response["result"]["Return"])}

    def getPopular(self):
        """function: Get popular songs from Grooveshark"""
        parameters = {}
        response = self.request(parameters, "popularGetSongs").send()

        return self._parseSongs(response["result"]["Songs"])

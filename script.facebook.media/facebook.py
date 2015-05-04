#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Python client library for the Facebook Platform.

This client library is designed to support the Graph API and the official
Facebook JavaScript SDK, which is the canonical way to implement
Facebook authentication. Read more about the Graph API at
http://developers.facebook.com/docs/api. You can download the Facebook
JavaScript SDK at http://github.com/facebook/connect-js/.

If your application is using Google AppEngine's webapp framework, your
usage of this module might look like this:

    user = facebook.get_user_from_cookie(self.request.cookies, key, secret)
    if user:
        graph = facebook.GraphAPI(user["access_token"])
        profile = graph.get_object("me")
        friends = graph.get_connections("me", "friends")

"""
from poster.encode import multipart_encode
import poster.streaminghttp
import urllib, urllib2
import sys, re, codecs
from urllib2 import HTTPError
from cgi import parse_qs

import os, xbmc, xbmcaddon
__addon__ = xbmcaddon.Addon(id='script.facebook.media')

poster.streaminghttp.register_openers()

# Find a JSON parser
try:
    import json
    _parse_json = lambda s: json.loads(s)
    _dump_json = lambda s: json.dumps(s)
except ImportError:
    try:
        import simplejson
        _parse_json = lambda s: simplejson.loads(s)
        _dump_json = lambda s: simplejson.dumps(s)
    except ImportError:
        # For Google AppEngine
        from django.utils import simplejson
        _parse_json = lambda s: simplejson.loads(s)
        _dump_json = lambda s: simplejson.dumps(s)

import locale
loc = locale.getdefaultlocale()
print loc
ENCODING = loc[1] or 'utf-8'

def ENCODE(string):
    return string.encode(ENCODING,'replace')

def LOG(string):
    try:
        print 'FACEBOOK MEDIA:facebook.py - %s' % ENCODE(str(string))
        return
    except:
        print "FACEBOOK MEDIA:facebook.py - COULDN'T ENCODE FOR LOG - RETRYING"

    try:
        print 'FACEBOOK MEDIA:facebook.py - %s' % repr(string)
        return
    except:
        print "FACEBOOK MEDIA:facebook.py - COULDN'T ENCODE FOR LOG - FINAL"

class GraphAPI(object):
    """A client for the Facebook Graph API.

    See http://developers.facebook.com/docs/api for complete documentation
    for the API.

    The Graph API is made up of the objects in Facebook (e.g., people, pages,
    events, photos) and the connections between them (e.g., friends,
    photo tags, and event RSVPs). This client provides access to those
    primitive types in a generic way. For example, given an OAuth access
    token, this will fetch the profile of the active user and the list
    of the user's friends:

       graph = facebook.GraphAPI(access_token)
       user = graph.get_object("me")
       friends = graph.get_connections(user["id"], "friends")

    You can see a list of all of the objects and connections supported
    by the API at http://developers.facebook.com/docs/reference/api/.

    You can obtain an access token via OAuth or by using the Facebook
    JavaScript SDK. See http://developers.facebook.com/docs/authentication/
    for details.

    If you are using the JavaScript SDK, you can use the
    get_user_from_cookie() method below to get the OAuth access token
    for the active user from the cookie saved by the SDK.
    """
    def __init__(self, access_token=None):
        self.access_token = access_token

    def get_object(self, ID, **args):
        """Fetchs the given object from the graph."""
        return self.request(ID, args)

    def get_objects(self, ids, **args):
        """Fetchs all of the given object from the graph.

        We return a map from ID to object. If any of the IDs are invalid,
        we raise an exception.
        """
        args["ids"] = ",".join(ids)
        return self.request("", args)

    def get_connections(self, ID, connection_name, **args):
        """Fetchs the connections for given object."""
        return self.request(ID + "/" + connection_name, args,update_prog=True)

    def put_object(self, parent_object, connection_name, **data):
        """Writes the given object to the graph, connected to the given parent.

        For example,

            graph.put_object("me", "feed", message="Hello, world")

        writes "Hello, world" to the active user's wall. Likewise, this
        will comment on a the first post of the active user's feed:

            feed = graph.get_connections("me", "feed")
            post = feed["data"][0]
            graph.put_object(post["id"], "comments", message="First!")

        See http://developers.facebook.com/docs/api#publishing for all of
        the supported writeable objects.

        Most write operations require extended permissions. For example,
        publishing wall posts requires the "publish_stream" permission. See
        http://developers.facebook.com/docs/authentication/ for details about
        extended permissions.
        """
        assert self.access_token, "Write operations require an access token"
        return self.request(parent_object + "/" + connection_name, post_args=data)

    def put_wall_post(self, message, attachment={}, profile_id="me"):
        """Writes a wall post to the given profile's wall.

        We default to writing to the authenticated user's wall if no
        profile_id is specified.

        attachment adds a structured attachment to the status message being
        posted to the Wall. It should be a dictionary of the form:

            {"name": "Link name"
             "link": "http://www.example.com/",
             "caption": "{*actor*} posted a new review",
             "description": "This is a longer description of the attachment",
             "picture": "http://www.example.com/thumbnail.jpg"}

        """
        return self.put_object(profile_id, "feed", message=message, **attachment)

    def put_comment(self, object_id, message):
        """Writes the given comment on the given post."""
        return self.put_object(object_id, "comments", message=message)

    def put_like(self, object_id):
        """Likes the given post."""
        return self.put_object(object_id, "likes")

    def delete_object(self, ID):
        """Deletes the object with the given ID from the graph."""
        self.request(ID, post_args={"method": "delete"})

    def request(self, path, args=None, post_args=None,update_prog=False):
        """Fetches the given path in the Graph API.

        We translate args to a valid query string. If post_args is given,
        we send a POST request to the given path with the given arguments.
        """
        if not args: args = {}
        headers = None
        post_data = None
        if self.access_token:
            if post_args is None:
                args["access_token"] = self.access_token
                post_data = None
            else:
                post_args["access_token"] = self.access_token
                post_data, headers = multipart_encode(post_args)

        pre = "https://graph.facebook.com/v2.3/"
        args = "?" + urllib.urlencode(args)
        if path.startswith('http'):
            pre = ''
            args = ''

        url = pre + path + args
        try:
            if headers:
                request = urllib2.Request(url, post_data, headers)
                fileob = urllib2.urlopen(request)
            else:
                fileob = urllib2.urlopen(url,post_data)
        except HTTPError, e:
            if e.code == 400:
                reason = e.headers.get('WWW-Authenticate')
                LOG('\nMessage: %s\nReason: %s' % (e.msg,reason))
                if 'invalid_token' in reason or 'invalid_request' in reason:
                    if 'unsupported get request' in reason.lower():
                        raise GraphAPIError(    'BadGetException',
                                                'Unsupported get request')
                    else:
                        raise GraphAPIError(    'OAuthException',
                                                'Expired/bad token')
            raise

        encoding = fileob.info().get('content-type').split('charset=')[-1]
        fileob = codecs.EncodedFile(fileob, encoding)

        if update_prog: self.updateProgress(30)
        try:
            data = ''
            try:
                total = int(fileob.info()['content-length'])
            except:
                total = 1
                update_prog = False
            chunk = 4096
            sofar = 0
            while True:
                d = fileob.read(chunk)
                if not d: break
                data += d
                if update_prog:
                    sofar += chunk
                    prog = int((sofar * 40) / total)
                    if update_prog and not self.updateProgress(30 + prog): return
            response = _parse_json(data)
        finally:
            fileob.close()

        if type(response) == type({}) and response.get("error"):
            raise GraphAPIError(response["error"]["type"],
                                response["error"]["message"])
        return response

    def updateProgress(self,pct):
        return True


class GraphAPIError(Exception):
    def __init__(self, type_, message):
        Exception.__init__(self, message)
        self.type = type_

class GraphWrapAuthError(Exception):
    def __init__(self, type_, message):
        Exception.__init__(self, message)
        self.type = type_
        self.message = message

class Connections(list):
    def __init__(self,graph,connections=None,first=True,progress=True):
        list.__init__(self)
        self.first = first
        self.graph = graph
        self.progress = progress
        self.previous = ''
        self.next = ''
        self.count = 0
        if connections:
            self.count = connections.get('count',0)
        if connections: self.processConnections(connections)

    def processConnections(self,connections):
        cons = []
        for c in connections['data']:
            if hasattr(c,'get'):
                cons.append(GraphObject(c.get('id'),self.graph,c))
        self._getPaging(connections,len(cons))
        self.extend(cons)
        if self.progress: self.graph.updateProgress(100)

    def _getPaging(self,obj,count):
        paging = obj.get('paging')
        if not paging: return
        next_ = paging.get('next','')
        prev = paging.get('previous','')
        limit = self._areTheSame(next_, prev, count)
        if limit:
            self.previous = self._checkForContent(prev)
            if not self.previous and count < limit and self.first: return
            self.next = self._checkForContent(next_)

    def _checkForContent(self,url):
        if not url: return ''
        connections = self.graph.request(url)
        if not 'data' in connections: return ''
        if not len(connections['data']): return ''
        return url

    def _areTheSame(self,next_,prev,count):
        try:
            limit = int(parse_qs(next_.split('?')[-1])['limit'][0])
        except:
            limit = count

        try:
            next_ut = int(parse_qs(next_.split('?')[-1])['until'][0])
            prev_ut = int(parse_qs(prev.split('?')[-1])['since'][0])
            if prev_ut == next_ut: return 0
            return limit
        except:
            return limit

import UserDict
class UTF8DictWrap(UserDict.UserDict):
    def get(self,key,failobj=None):
        val = UserDict.UserDict.get(self, key, failobj)
        if hasattr(val,'encode'): return unicode(val.encode('utf-8'),'utf-8')
        return val


class GraphObject:
    def __init__(self,ID=None,graph=None,data=None,**args):
        if (not ID) and data:
            if 'id' in data: ID = data['id']
        self.id = ID
        self.args = args
        self.graph = graph
        self._cache = {}
        self._data = data
        self.connections = GraphConnections(self)
        if ID == 'me':
            self._data = self._getObjectData(ID,**args)
            self.id = self._data.get('id') or 'me'

    def updateData(self):
        self._data = self._getObjectData(self.id,**self.args)
        return self

    def toJSON(self):
        return self._toJSON(self._data)

    def get(self,key,default=None,as_json=False):
        return self._getData(key,default,as_json)

    def hasProperty(self,prop):
        return prop in self._data

    def comment(self,comment):
        self.graph.put_comment(self.id,comment)

    def like(self):
        self.graph.put_like(self.id)

    def __getattr__(self, prop):
        if prop.startswith('_'): return object.__getattr__(self,prop)
        if prop.endswith('_'): prop = prop[:-1]
        if prop in self._cache:
            return self._cache[prop]

        if not self._data:
            self._data = self._getObjectData(self.id,**self.args)
            if self.id == 'me': self.id = self._data.get('id') or 'me'

        def handler(default=None,as_json=False):
            return self._getData(prop,default,as_json)

        handler.method = prop

        self._cache[prop] = handler
        return handler

    def _getData(self,prop,default,as_json):
        val = self._data.get(prop)
        if not val: return default
        if type(val) == type({}):
            if 'data' in val:
                if as_json:
                    return self._toJSON(val)
                elif isinstance(val['data'],list):
                    return Connections(self.graph,val,progress=False)
                else:
                    val = val['data']
            return UTF8DictWrap(val)
        if hasattr(val,'encode'): return unicode(val.encode('utf-8'),'utf-8')
        return val

    def _getObjectData(self,ID,**args):
        fail = False
        try:
            return self.graph.get_object(ID,**args)
        except GraphAPIError,e:
            if not e.type == 'OAuthException': raise
            fail = True

        if fail:
            LOG("ERROR GETTING OBJECT - GETTING NEW TOKEN")
            if not self.graph.getNewToken():
                if self.graph.access_token: raise GraphWrapAuthError('RENEW_TOKEN_FAILURE','Failed to get new token')
                else: return None
            return self.graph.get_object(ID,**args)

    def _toJSON(self,data_obj):
        return _dump_json(data_obj)

class GraphData:
    def __init__(self,graphObject,data=None):
        self.graphObject = graphObject
        self.graph = self.graphObject.graph


    def __getattr__(self, prop):
        if prop.startswith('_'): return object.__getattr__(self,prop)
        if prop in self._cache:
            return self._cache[prop]

        if not self._data: self._data = self._getObjectData(self.graphObject.id)

        def handler(default=None):
            val = self._data.get(prop,default)
            if hasattr(val,'encode'): return unicode(val.encode('utf-8'),'utf-8')
            return val

        handler.method = prop

        self._cache[prop] = handler
        return handler

    def _getObjectData(self,ID,**args):
        fail = False
        try:
            return self.graph.get_object(ID,**args)
        except GraphAPIError,e:
            if not e.type == 'OAuthException': raise
            fail = True

        if fail:
            LOG("ERROR GETTING OBJECT - GETTING NEW TOKEN")
            if not self.graph.getNewToken():
                if self.graph.access_token: raise GraphWrapAuthError('RENEW_TOKEN_FAILURE','Failed to get new token')
                else: return None
            return self.graph.get_object(ID,**args)

class GraphConnections:
    def __init__(self,graphObject):
        self.graphObject = graphObject
        self.graph = self.graphObject.graph
        self.cache = {}

    def __getattr__(self, method):
        if method.startswith('_'): return object.__getattr__(self,method)
        if method in self.cache:
            return self.cache[method]

        def handler(**args):
            fail = False
            try:
                return self._getConnections(method,**args)
            except GraphAPIError,e:
                LOG(e.type)
                if not e.type == 'OAuthException': raise
                fail = True

            if fail:
                LOG("ERROR GETTING CONNECTIONS - GETTING NEW TOKEN")
                if not self.graph.getNewToken():
                    if self.graph.access_token: raise GraphWrapAuthError('RENEW_TOKEN_FAILURE','Failed to get new token')
                    else: return None
                return self._getConnections(method,**args)
        handler.method = method

        self.cache[method] = handler
        return handler

    def _getConnections(self,method,**args):
        connections = self.graph.get_connections(self.graphObject.id, method.replace('__','/'), **args)
        self.graph.updateProgress(70)
        return Connections(self.graph,connections)

    def _processConnections(self,connections,paging):
        return self.graph._processConnections(connections,paging)

class GraphWrap(GraphAPI):
    def __init__(self,token,new_token_callback=None,credentials_callback=None,version='8.0'):
        GraphAPI.__init__(self,token)
        self.uid = None
        self._newTokenCallback = new_token_callback
        self._progCallback = None
        self._progModifier = 1
        self._progTotal = 100
        self._progMessage = ''
        self.uid = None
        self.cookieJar = None
        self.version = version
        self.credentialsCallback = credentials_callback

    def withProgress(self,callback,modifier=1,total=100,message=''):
        poster.streaminghttp.PROGRESS_CALLBACK = callback
        self._progCallback = callback
        self._progModifier = modifier
        self._progTotal = total
        self._progMessage = message
        return self

    def updateProgress(self,level):
        if self._progCallback:
            level *= self._progModifier
            return self._progCallback(int(level),self._progTotal,self._progMessage)
        return True

    def fromJSON(self,json_string):
        if not json_string: return None
        data_obj = _parse_json(json_string)
        if type(data_obj) == type({}):
            if 'data' in data_obj:
                return Connections(self,data_obj,progress=False)
            elif 'id' in data_obj:
                return GraphObject(graph=self,data=data_obj)
        return data_obj

    def putWallPost(self,message, attachment={}, profile_id="me"):
        fail = False
        try:
            return self.put_wall_post(message, attachment, profile_id)
        except GraphAPIError,e:
            LOG(e.type)
            if not e.type == 'OAuthException': raise
            fail = True

        if fail:
            LOG("ERROR POSTING TO WALL - GETTING NEW TOKEN")
            if not self.getNewToken():
                if self.access_token: raise GraphWrapAuthError('RENEW_TOKEN_FAILURE','Failed to get new token')
                else: return None
            return self.put_wall_post(message, attachment, profile_id)

    def putObject(self,parent_object, connection_name, **data):
        fail = False
        try:
            return self.put_object(parent_object, connection_name, **data)
        except GraphAPIError,e:
            LOG(e.type)
            if not e.type == 'OAuthException': raise
            fail = True

        if fail:
            LOG("ERROR POSTING OBJECT - GETTING NEW TOKEN")
            if not self.getNewToken():
                if self.access_token: raise GraphWrapAuthError('RENEW_TOKEN_FAILURE','Failed to get new token')
                else: return None
            return self.put_object(parent_object, connection_name, **data)

    def getObject(self,ID,**args):
        return GraphObject(ID,self,**args)

    def getObjects(self,ids=[]):
        data = self.get_objects(ids)
        objects = {}
        for ID in data:
            objects[ID] = GraphObject(ID,self,data[ID])
        return objects

    def urlRequest(self,url):
        connections = self.request(url)
        return Connections(self,connections,first=False)

    def setLogin(self,email,passw,uid=None,token=None):
        self.uid = uid or self.uid
        self.login_email = email
        self.login_pass = passw
        if token: self.access_token = token

    def setAppData(self,aid,redirect='https://www.facebook.com/connect/login_success.html',scope=None):
        self.client_id = aid
        self.redirect = redirect
        self.scope = scope

    def checkHasPermission(self,permission):
        url = 'https://api.facebook.com/method/users.hasAppPermission?format=json&ext_perm='+permission+'&access_token='+self.access_token
        fobj = urllib2.urlopen(url)
        try:
            response = _parse_json(fobj.read())
        finally:
            fobj.close()
        return (response == 1)

    def browserRead(self,readable,post=''):
        html = readable.read()
        if False:
            htmlFile = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')),'cache','DEBUG_HTML%s.html' % post)
            with open(htmlFile,'w') as f:
                f.write(html.strip("'"))
        return html

    def checkIsAppUser(self):
        url = 'https://api.facebook.com/method/users.isAppUser?format=json&access_token='+self.access_token
        fobj = urllib2.urlopen(url)
        try:
            response = _parse_json(fobj.read())
        finally:
            fobj.close()
        return response

    def getNewToken(self):
        if self.credentialsCallback:
            credentials = self.credentialsCallback()
            if 'token' in credentials:
                self.saveToken(credentials['token'])
                return credentials['token']
            elif 'password'in credentials:
                email = credentials['email']
                password = credentials['password']
            else:
                return None

        import mechanize #@UnresolvedImport
        br = mechanize.Browser()
        __addon__ = xbmcaddon.Addon(id='script.facebook.media')
        cookiesPath = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')),'cache','cookies')
        LOG('Cookies will be saved to: ' + cookiesPath)
        cookies = mechanize.LWPCookieJar(cookiesPath)
        if os.path.exists(cookiesPath): cookies.load()
        self.cookieJar = cookies
        opener = mechanize.build_opener(mechanize.HTTPCookieProcessor(cookies))
        mechanize.install_opener(opener)
        br.set_cookiejar(self.cookieJar)
        br._ua_handlers["_cookies"].cookiejar.clear()
        br.set_handle_robots(False)
        agent = 'XBMC/{0} Facebook-Media/{1}'.format(xbmc.getInfoLabel('System.BuildVersion'),self.version)
        LOG('Setting User Agent: {0}'.format(agent))
        br.addheaders = [('User-agent',agent)]
        scope = ''
        if self.scope: scope = '&scope=' + self.scope
        url =     'https://www.facebook.com/dialog/oauth?client_id='+self.client_id+\
                '&redirect_uri='+self.redirect+\
                '&type=user_agent&display=popup'+scope
        LOG(url)
        try:
            res = br.open(url)
            html = res.read()
        except:
            LOG("ERROR: TOKEN PAGE INITIAL READ")
            raise

        script = False
        try:
            #check for login form
            br.select_form(nr=0)
            LOG("HTML")
        except:
            self.genericError()
            script = True
            LOG("SCRIPT")

        if script:
            #no form, maybe we're logged in and the token is in javascript on the page
            url = res.geturl()
            token = self.extractTokenFromURL(url)
            if not token: token = self.parseTokenFromScript(html)
        else:
            try:
                #fill out the form and submit
                br['email'] = email
                br['pass'] = password
                res = br.submit()
                url = res.geturl()
                LOG("FORM")
            except:
                LOG("FORM ERROR")
                raise

            script = False
            token = self.extractTokenFromURL(url)
            html = self.browserRead(res,'-noscript')
            if not token:
                #if 'class="checkpoint"' in html:
                token = self.handleLoginNotificationCrap(br)

            if not token: script = True

            if script:
                LOG("SCRIPT TOKEN")
                #no token in the url, let's try to parse it from javascript on the page
                try:
                    __addon__ = xbmcaddon.Addon(id='script.facebook.media')
                    htmlFile = os.path.join(xbmc.translatePath(__addon__.getAddonInfo('profile')),'cache','DEBUG_HTML.html')
                    open(htmlFile,'w').write(html)
                    LOG('html output written to: ' + htmlFile)
                except:
                    pass
                token = self.parseTokenFromScript(html)
                token = urllib.unquote(token.decode('unicode-escape'))

        if not self.tokenIsValid(token):
            #if script: LOG("HTML:" + html)
            return False
        LOG("\n|--------------------\n|TOKEN: %s\n|--------------------"  % token)
        self.saveToken(token)
        if self.cookieJar is not None:
            self.cookieJar.save()
        return token

    def handleLoginNotificationCrap(self,br):
        LOG('Handling Login Notification Crap')
        br.select_form(nr=0)
        res = br.submit()
        self.browserRead(res,'-loginnotifycrap1')
        #if not 'Media XBMC' in html: return None
        url = res.geturl()
        LOG('LN First URL: ' + url)
        if 'login.php' in url:
            raise GraphWrapAuthError('BAD_USERPASS','Failed: Probable bad user/pass')
        if 'access_token' in url: return self.extractTokenFromURL(url)
        br.select_form(nr=0)
        try:
            res = br.submit(name='submit[Continue]')
        except:
            res = br.submit()
        res.read()
        url = res.geturl()
        LOG('LN Second URL: ' + url)
        if 'access_token' in url: return self.extractTokenFromURL(url)
        br.select_form(nr=0)
        self.isolateSubmitButton(br, 'save_device')
        res = br.submit()

        html = res.read()
        url = res.geturl()
        LOG('LN Third URL: ' + url)
        if 'access_token' in url: return self.extractTokenFromURL(url)
        if 'name="submit[Continue]"' in html:
            LOG("Found 'Continue' page: submitting")
            br.select_form(nr=0)
            res = br.submit()
            url = res.geturl()
            if 'access_token' in url:
                return self.extractTokenFromURL(url)
            else:
                LOG("No Token In URL: {0}".format(url))
        return None

    def isolateSubmitButton(self,br,value):
        return
        submit_buttons = self.find_controls(br,ctype="submit")
        for button in submit_buttons[:]:
            if button.value != value: br.form.controls.remove(button)

    def find_controls(self, br,name=None, ctype=None, kind=None, cid=None, predicate=None, label=None):
        i = 0
        results = []

        try :
            while(True):
                results.append(br.find_control(name, ctype, kind, cid, predicate, label, nr=i))
                i += 1
        except Exception: #Exception tossed if control not found @UnusedVariable
            pass
        return results

    def extractTokenFromURL(self,url):
        try:
            #we submitted the form, check the result url for the access token
            import urlparse
            token = parse_qs(urlparse.urlparse(url.replace('#','?',1).replace('??','?'))[4])['access_token'][0]
            LOG("URL TOKEN: %s" % token)
            return token
        except:
            LOG("TOKEN URL: %s" % url)
            self.genericError()
            return None

    def tokenIsValid(self,token):
        if not token: return False
        if 'login_form' in token and 'standard_explanation' in token:
            reason = re.findall('id="standard_explanation">(?:<p>)?([^<]*)<',token)
            if reason: LOG(reason[0])
            LOG("TOKEN: " + token)
            raise GraphWrapAuthError('LOGIN_FAILURE',reason)
            return False
        if 'html' in token or 'script' in token or len(token) > 250:
            LOG("TOKEN: " + token)
            raise GraphWrapAuthError('RENEW_TOKEN_FAILURE','Failed to get new token')
            return False
        if 'login notifications' in token:
            LOG("TOKEN: " + token)
            raise GraphWrapAuthError('RENEW_TOKEN_FAILURE','Disable login notifications, then retry')
            return False
        if 'temporarily locked' in token:
            LOG("TOKEN: " + token)
            raise GraphWrapAuthError('RENEW_TOKEN_FAILURE','Facebook account is locked')
            return False
        #Because you enabled login notifications, your account is temporarily locked.
        return True

    def genericError(self):
        LOG('ERROR: %s::%s (%d) - %s' % (self.__class__.__name__
                                   , sys.exc_info()[2].tb_frame.f_code.co_name, sys.exc_info()[2].tb_lineno, sys.exc_info()[1]))

    def parseTokenFromScript(self,html):
        return urllib.unquote_plus(html.split("#access_token=")[-1].split("&expires")[0])

    def saveToken(self,token=None):
        if token:
            self.access_token = token
            if self._newTokenCallback: self._newTokenCallback(token)
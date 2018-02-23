import os
import sys
import time
import socket
import urllib.request
import urllib.parse
import base64
import hashlib
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import json

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')

APIURL = 'http://ws.audioscrobbler.com/2.0/'
AUTHURL = 'https://ws.audioscrobbler.com/2.0/'
HEADERS = {'User-Agent': 'Kodi Media center', 'Accept-Charset': 'utf-8'}
LANGUAGE = ADDON.getLocalizedString
ADDONVERSION = ADDON.getAddonInfo('version')
CWD = ADDON.getAddonInfo('path')
STATUS = ADDON.getSetting('lastfmstatus')
DATAPATH = xbmc.translatePath(ADDON.getAddonInfo('profile'))
WINDOW = xbmcgui.Window(10000)

socket.setdefaulttimeout(10)

def log(txt, session):
    message = '%s - %s: %s' % (ADDONID, session, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def parse_argv():
    # parse argv
    params = dict(arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ))
    return True, params

def read_settings(session, puser=False, ppwd=False):
    # read settings
    settings = {}
    user = ADDON.getSetting('lastfmuser')
    pwd = ADDON.getSetting('lastfmpass')
    songs = ADDON.getSetting('lastfmsubmitsongs') == 'true'
    radio = ADDON.getSetting('lastfmsubmitradio') == 'true'
    confirm = ADDON.getSetting('lastfmconfirm') == 'true'
    sesskey = ADDON.getSetting('lastfmkey')
    # if puser or ppwd is true, we were called by onSettingsChanged
    if puser or ppwd:
        # check if user has changed it's username or password
        if (puser != user) or (ppwd != pwd):
            # username or password changed, we need to get a new sessionkey
            sesskey = False
    # get a session key if needed
    if user and pwd and (not sesskey):
        # collect post data
        data = {}
        data['username'] = user
        data['password'] = pwd
        data['method'] = 'auth.getMobileSession'
        response = lastfm.post(data, session, True)
        if not response:
            sesskey = ''
        elif 'session' in response:
            sesskey = response['session']['key']
            # set property for skins
            set_prop('LastFM.CanLove', 'True')
            set_prop('LastFM.CanBan', 'True')
        elif 'error' in response:
            msg  = response['message'] 
            xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), msg, 7000))
            log('Last.fm returned failed response: %s' % msg, session)
            sesskey = ''
        else:
            log('Last.fm an unknown authentication response', session)
            sesskey = ''
        if sesskey:
            ADDON.setSetting('lastfmkey', sesskey)
    elif not (user and pwd):
        # no username or password
        xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), LANGUAGE(32027), 7000))
    settings['user'] = user
    settings['pwd'] = pwd
    settings['songs'] = songs
    settings['radio'] = radio
    settings['confirm'] = confirm
    settings['sesskey'] = sesskey
    if sesskey:
        set_prop('LastFM.CanLove', 'True')
        set_prop('LastFM.CanBan', 'True')
    return settings

def set_prop(key, val):
    # set property for skins
    WINDOW.setProperty(key, val)

def clear_prop(key):
    # clear skin property
    val = WINDOW.clearProperty(key)
    return val

def read_file(item):
    # read the queue file if we have one
    path = os.path.join(DATAPATH, item)
    if xbmcvfs.exists( path ):
        f = open(path, 'r')
        data =  f.read() 
        if data:
            data = eval(data)
        f.close()
        return data
    else:
        return None

def write_file(item, data):
    # create the data dir if needed
    if not xbmcvfs.exists( DATAPATH ):
        xbmcvfs.mkdir( DATAPATH )
    # save data to file
    queue_file = os.path.join(DATAPATH, item)
    f = open(queue_file, 'w')
    f.write(repr(data))
    f.close()

def md5sum(txt):
    # generate a md5 hash
    if isinstance (txt,str):
        txt = txt
    md5hash = hashlib.md5()
    md5hash.update(txt.encode("utf-8"))
    return md5hash.hexdigest()

def getsig(params):
    app = base64.b64decode(STATUS)[::-1].decode("utf-8")
    params['api_key'] = ''.join([app[48:64], app[16:32]])
    # dict to list
    # signature params need to be sorted
    siglist = sorted(params.items())
    # create signature string
    sigstring = ''.join(map(''.join,siglist))
    # add api secret and create a request signature
    sig = md5sum(sigstring + ''.join([app[32:48], app[0:16]]))
    return sig

def jsonparse(response):
    # parse response
    return json.loads(response)

def drop_sesskey():
    # drop our key, this will trigger onsettingschanged to fetch a new key
    ADDON.setSetting('lastfmkey', '')

class LastFM:
    def __init__(self):
        pass

    def post(self, params, session, auth=False):
        # create a signature
        apisig = getsig(params)
        # add response format
        params['format'] = 'json'
        # add api signature
        params['api_sig'] = apisig
        # get the url we need
        if auth:
            baseurl = AUTHURL
        else:
            baseurl = APIURL
        # encode the data
        str_params = {}
        for k, v in params.items():
            str_params[k] = v.encode('utf-8')
        data = urllib.parse.urlencode(str_params).encode('utf-8')
        # prepare post data
        url = urllib.request.Request(baseurl, data, HEADERS)
        return self.connect(url, session)

    def get(self, params, session):
        app = base64.b64decode(STATUS)[::-1]
        # create request url
        url = APIURL + '?method=' + params[0] + '&' + params[2] + '=' + params[1].replace(' ', '%20') + '&api_key=' + ''.join([app[48:64], app[16:32]]) + '&format=json'
        log('list url %s' % url, session)
        return self.connect(url, session)

    def connect(self, url, session):
        # connect to last.fm
        try:
            req = urllib.request.urlopen(url)
            result = req.read()
            req.close()
        except urllib.request.HTTPError as err:
            if err.code == 403:
                result = '{"error":9, "message":"updating session key"}'
        except:
            xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), LANGUAGE(32026), 7000))
            log('Failed to connect to Last.fm', session)
            return
        log('response %s' % result, session)
        return jsonparse(result)

lastfm = LastFM()

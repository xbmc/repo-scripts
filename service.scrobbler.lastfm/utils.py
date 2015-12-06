import os, sys, time, socket, urllib, urllib2, urlparse, httplib, base64, hashlib
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')

APIURL       = 'http://ws.audioscrobbler.com/2.0/'
AUTHURL      = 'https://ws.audioscrobbler.com/2.0/'
HEADERS      = {'User-Agent': 'Kodi Media center', 'Accept-Charset': 'utf-8'}
LANGUAGE     = __addon__.getLocalizedString
ADDONVERSION = __addon__.getAddonInfo('version')
CWD          = __addon__.getAddonInfo('path').decode("utf-8")
STATUS       = __addon__.getSetting('lastfmstatus')
DATAPATH     = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')).decode('utf-8')
WINDOW       = xbmcgui.Window(10000)

socket.setdefaulttimeout(10)

def log(txt, session):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s - %s: %s' % (__addonid__, session, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def parse_argv():
    # parse argv
    params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    return True, params

def read_settings(session, puser=False, ppwd=False):
    # read settings
    settings = {}
    user      = __addon__.getSetting('lastfmuser').decode("utf-8")
    pwd       = __addon__.getSetting('lastfmpass').decode("utf-8")
    songs     = __addon__.getSetting('lastfmsubmitsongs') == 'true'
    radio     = __addon__.getSetting('lastfmsubmitradio') == 'true'
    confirm   = __addon__.getSetting('lastfmconfirm') == 'true'
    sesskey   = __addon__.getSetting('lastfmkey')
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
        elif response.has_key('session'):
            sesskey = response['session']['key']
            # set property for skins
            set_prop('LastFM.CanLove', 'True')
            set_prop('LastFM.CanBan', 'True')
        elif response.has_key('error'):
            msg  = response['message'] 
            xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), msg, 7000))
            log('Last.fm returned failed response: %s' % msg, session)
            sesskey = ''
        else:
            log('Last.fm an unknown authentication response', session)
            sesskey = ''
        if sesskey:
            __addon__.setSetting('lastfmkey', sesskey)
    elif not (user and pwd):
        # no username or password
        xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), LANGUAGE(32027), 7000))
    settings['user']    = user
    settings['pwd']     = pwd
    settings['songs']   = songs
    settings['radio']   = radio
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

def read_file( item ):
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

def write_file( item, data ):
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
        txt = txt.decode("utf-8")
    md5hash = hashlib.md5()
    md5hash.update(txt.encode("utf-8"))
    return md5hash.hexdigest()

def getsig( params ):
    app = base64.b64decode(STATUS)[::-1]
    params['api_key'] = ''.join([app[48:64], app[16:32]])
    # dict to list
    siglist = params.items()
    # signature params need to be sorted
    siglist.sort()
    # create signature string
    sigstring = ''.join(map(''.join,siglist))
    # add api secret and create a request signature
    sig = md5sum(sigstring + ''.join([app[32:48], app[0:16]]))
    return sig

def jsonparse( response ):
    # parse response
    data = unicode(response, 'utf-8', errors='ignore')
    return simplejson.loads(data)

def drop_sesskey():
    # drop our key, this will trigger onsettingschanged to fetch a new key
    __addon__.setSetting('lastfmkey', '')

class LastFM:
    def __init__( self ):
        pass

    def post( self, params, session, auth=False ):
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
        for k, v in params.iteritems():
            str_params[k] = unicode(v).encode('utf-8')
        data = urllib.urlencode(str_params)
        # prepare post data
        url = urllib2.Request(baseurl, data, HEADERS)
        return self.connect(url, session)

    def get( self, params, session ):
        app = base64.b64decode(STATUS)[::-1]
        # create request url
        url = APIURL + '?method=' + params[0] + '&' + params[2] + '=' + params[1].replace(' ', '%20') + '&api_key=' + ''.join([app[48:64], app[16:32]]) + '&format=json'
        log('list url %s' % url, session)
        return self.connect(url, session)

    def connect( self, url, session ):
        # connect to last.fm
        try:
            req = urllib2.urlopen(url)
            result = req.read()
            req.close()
        except urllib2.HTTPError, err:
            if err.code == 403:
                result = '{"error":9, "message":"updating session key"}'
        except:
            xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), LANGUAGE(32026), 7000))
            log('Failed to connect to Last.fm', session)
            return
        log('response %s' % result, session)
        return jsonparse(result)

lastfm = LastFM()

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

import urllib, urllib2, socket, hashlib, time
import xbmc, xbmcgui, xbmcaddon

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__language__     = __addon__.getLocalizedString

socket.setdefaulttimeout(10)

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Main:
    def __init__( self ):
        self._service_setup()
        while (not xbmc.abortRequested) and (not self.Exit):
            xbmc.sleep(1000)

    def _service_setup( self ):
        self.LibrefmURL           = 'http://turtle.libre.fm/'
        self.ClientId             = 'xbm'
        self.ClientVersion        = '0.2'
        self.ClientProtocol       = '1.2.1'
        self.Exit                 = False
        self.Monitor              = MyMonitor(action = self._get_settings)
        self._get_settings()

    def _get_settings( self ):
        log('#DEBUG# reading settings')
        service    = []
        LibrefmSubmitSongs = __addon__.getSetting('librefmsubmitsongs') == 'true'
        LibrefmSubmitRadio = __addon__.getSetting('librefmsubmitradio') == 'true'
        LibrefmUser        = __addon__.getSetting('librefmuser').lower()
        LibrefmPass        = __addon__.getSetting('librefmpass')
        if (LibrefmSubmitSongs or LibrefmSubmitRadio) and LibrefmUser and LibrefmPass:
            # [service, auth-url, user, pass, submitsongs, submitradio, sessionkey, np-url, submit-url, auth-fail, failurecount, timercounter, timerexpiretime, queue]
            service = ['librefm', self.LibrefmURL, LibrefmUser, LibrefmPass, LibrefmSubmitSongs, LibrefmSubmitRadio, '', '', '', False, 0, 0, 0, []]
            self.Player = MyPlayer(action = self._service_scrobble, service = service)

    def _service_scrobble( self, tags, service ):
        tstamp = int(time.time())
        # don't proceed if we had an authentication failure
        if not service[9]:
            # test if we are authenticated
            if not service[6]:
                # authenticate                    
                service = self._service_authenticate(service, str(tstamp))
            # only proceed if authentication was succesful
            if service[6]:
                # check if there's something in our queue for submission
                if len(service[13]) != 0:
                    service = self._service_submit(service, tstamp)
                # nowplaying announce if we still have a valid session key after submission and have an artist and title
                if service[6] and tags and tags[0] and tags[2]:
                    service = self._service_nowplaying(service, tags)
                    # check if the song qualifies for submission
                    if (service[4] and not (tags[7].startswith('http://') or tags[7].startswith('rtmp://'))) or (service[5] and (tags[7].startswith('http://') or tags[7].startswith('rtmp://'))):
                        # add track to the submission queue
                        service[13].extend([tags])

    def _service_authenticate( self, service, timestamp ):
        # don't proceed if timeout timer has not expired
        if service[12] > int(timestamp):
            return service
        # create a pass hash
        md5pass = hashlib.md5()
        md5pass.update(service[3])
        # generate an authentication token
        md5token = hashlib.md5()
        md5token.update(md5pass.hexdigest() + timestamp)
        url = service[1] + '?hs=true' + '&p=' + self.ClientProtocol + '&c=' + self.ClientId + '&v=' + self.ClientVersion + '&u=' + service[2] + '&t=' + timestamp + '&a=' + md5token.hexdigest()
        try:
            # authentication request
            req = urllib2.urlopen(url)
            # authentication response
            result = req.read()
            req.close()
            log('#DEBUG# %s authentication %s' % (service[0], result))
            data = result.split('\n')
            log('#DEBUG# authentication result %s' % data)
        except:
            service = self._service_fail( service, True )
            log('%s failed to connect for authentication' % service[0])   
            return service         
        # parse results
        if data[0] == 'OK':
            # get sessionid, np-url and submit url
            service[6] = data[1]
            service[7] = data[2]
            service[8] = data[3]
            # reset failure count
            service[10] = 0
            # reset timer
            service[11] = 0
            service[12] = 0
        elif data[0] == 'BANNED':
            # uh-oh
            xbmc.executebuiltin((u'Notification(%s,%s)' % ('Scrobbler: ' + service[0], __language__(32003))).encode('utf-8', 'ignore'))
            log('%s has banned our app id' % service[0])
            # disable the service, the monitor class will pick up the changes
            __addon__.setSetting('%ssubmitsongs' % service[0], 'false')
            __addon__.setSetting('%ssubmitradio' % service[0], 'false')
        elif data[0] == 'BADAUTH':
            # user has to change username / password
            xbmc.executebuiltin((u'Notification(%s,%s)' % ('Scrobbler: ' + service[0], __language__(32001))).encode('utf-8', 'ignore'))
            log('%s invalid credentials' % service[0])
            service[9] = True
        elif data[0] == 'BADTIME':
            # user needs to change the system time
            xbmc.executebuiltin((u'Notification(%s,%s)' % ('Scrobbler: ' + service[0], __language__(32002))).encode('utf-8', 'ignore'))
            log('%s invalid system time' % service[0])
            self.Exit = True
        else:
            # temporary server error
            service = self._service_fail( service, True )
            log('%s server error while authenticating: %s' % (service[0], data[0]))
        return service

    def _service_nowplaying( self, service, tags ):
        url = service[7]
        data = {'s':service[6], 'a':tags[0], 'b':tags[1], 't':tags[2], 'l':tags[3], 'n':tags[4]}
        try:
            # nowplaying request
            body = urllib.urlencode(data)
            req = urllib2.Request(url, body)
            # nowplaying response
            response = urllib2.urlopen(req)
            result = response.read()
            response.close()
            data = result.split('\n')
        except:
            service = self._service_fail( service, False )
            log('%s failed to connect for nowplaying notification' % service[0])
            return service
        log('#DEBUG# %s nowplaying announce result %s' % (service[0], data[0]))
        # parse results
        if data[0] == 'BADSESSION':
            # drop our session key
            service[6] = ''
            log('%s bad session for nowplaying notification' % service[0])
        return service

    def _service_submit( self, service, tstamp ):
        # we're allowed to submit 50 tracks max
        while len(service[13]) > 50:
            service[13].pop(0)
        # get the submission url
        url = service[8]
        # get the session id
        data = {'s':service[6]}
        # create a list of songs to remove from the queue
        removesongs = []
        # set submit bool to false
        submit = False
        # iterate through the queue
        for count, item in enumerate(service[13]):
            # only submit items that are at least 30 secs long and have been played at least half or at least 4 minutes
            if (int(item[3]) > 30) and ((tstamp - int(item[8]) > int(int(item[3])/2)) or (tstamp - int(item[8]) > 240)):
                key1 = 'a[%i]' % count
                key2 = 'b[%i]' % count
                key3 = 't[%i]' % count
                key4 = 'l[%i]' % count
                key5 = 'n[%i]' % count
                key6 = 'i[%i]' % count
                key7 = 'o[%i]' % count
                key8 = 'r[%i]' % count
                key9 = 'm[%i]' % count
                data.update({key1:item[0], key2:item[1], key3:item[2], key4:item[3], key5:item[4], key6:item[8], key7:item[9], key8:'', key9:item[5]})
                # we have at least one item to submit
                submit = True
            else:
                # keep a list of songs that don't qualify
                removesongs.append(count)
        # remove disqualified songs, starting with the last one (else we mess up the list order and incorrectly remove items)
        removesongs.reverse()
        for song in removesongs:
            service[13].pop(song)
        # return if we have nothing to submit
        if not submit:
            return service
        log('#DEBUG# %s submission data %s' % (service[0], data))
        try:
            # submit request
            body = urllib.urlencode(data)
            req = urllib2.Request(url, body)
            # submit response
            response = urllib2.urlopen(req)
            result = response.read()
            response.close()
            data = result.split('\n')
        except:
            service = self._service_fail( service, False )
            log('%s failed to connect for song submission' % service[0])
            return service
        log('#DEBUG# %s submit result %s' % (service[0], data[0]))
        # parse results
        if data[0] == 'OK':
            # empty our queue
            service[13] = []
        elif data[0] == 'BADSESSION':
            # drop our session key
            service[6] = ''
            log('%s bad session for song submission' % service[0])
        else:
            # temporary server error
            service = self._service_fail( service, False )
            log('%s failure for song submission: %s' % (service[0], data[0]))
        return service

    def _service_fail( self, service, timer ):
        timestamp = int(time.time())
        # increment failure counter
        service[10] += 1
        # drop our session key if we encouter three failures
        if service[10] > 2:
            service[6] = ''
        # set a timer if failure occurred during authentication phase
        if timer:
            # wrap timer if we cycled through all timeout values
            if service[11] == 0 or service[11] == 7680:
                service[11] = 60
            else:
                # increment timer
                service[11] = 2 * service[11]
        # set timer expire time
        service[12] = timestamp + service[11]
        return service

class MyPlayer(xbmc.Player):
    def __init__( self, *args, **kwargs ):
        xbmc.Player.__init__( self )
        self.action = kwargs['action']
        self.service = kwargs['service']
        self.Audio = False
        self.Count = 0
        log('#DEBUG# Player Class Init')

    def onPlayBackStarted( self ):
        # only do something if we're playing audio
        if self.isPlayingAudio():
            # we need to keep track of this bool for stopped/ended notifications
            self.Audio = True
            # keep track of onPlayBackStarted events http://trac.xbmc.org/ticket/13064
            self.Count += 1
            log('#DEBUG# onPlayBackStarted: %i' % self.Count)
            # tags are not available instantly and we don't what to announce right away as the user might be skipping through the songs
            xbmc.sleep(2000)
            # don't announce if user already skipped to the next track
            if self.Count == 1:
                # reset counter
                self.Count = 0
                # get tags
                tags = self._get_tags()
                # announce song
                self.action(tags, self.service)
            else:
                # multiple onPlayBackStarted events occurred, only act on the last one
                log('#DEBUG# skipping onPlayBackStarted event')
                self.Count -= 1

    def onPlayBackEnded( self ):
        if self.Audio:
            self.Audio = False
            log('#DEBUG# onPlayBackEnded')
            self.action(None, self.service)

    def onPlayBackStopped( self ):
        if self.Audio:
            self.Audio = False
            log('#DEBUG# onPlayBackStopped')
            self.action(None, self.service)

    def _get_tags( self ):
        # get track tags
        artist      = self.getMusicInfoTag().getArtist()
        album       = self.getMusicInfoTag().getAlbum()
        title       = self.getMusicInfoTag().getTitle()
        duration    = str(self.getMusicInfoTag().getDuration())
        track       = str(self.getMusicInfoTag().getTrack())
        mbid        = '' # musicbrainz id is not available
        comment     = self.getMusicInfoTag().getComment()
        path        = self.getPlayingFile()
        timestamp   = int(time.time())
        source      = 'P'
        tracktags   = [artist, album, title, duration, track, mbid, comment, path, timestamp, source]
        log('#DEBUG# tracktags: %s' % tracktags)
        return tracktags

class MyMonitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.action = kwargs['action']

    def onSettingsChanged( self ):
        log('#DEBUG# onSettingsChanged')
        self.action()

if ( __name__ == "__main__" ):
    log('script version %s started' % __addonversion__)
    Main()

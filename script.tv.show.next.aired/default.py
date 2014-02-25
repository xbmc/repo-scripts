from time import strftime, strptime, time, mktime, localtime
import os, sys, re, socket, urllib, unicodedata, threading
from traceback import print_exc
from datetime import datetime, date, timedelta
from dateutil import tz
from operator import attrgetter, itemgetter
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson
# http://mail.python.org/pipermail/python-list/2009-June/540579.html
import _strptime

__addon__     = xbmcaddon.Addon()
__addonid__   = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path').decode('utf-8')
__author__    = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__language__  = __addon__.getLocalizedString
__useragent__ = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
__datapath__ = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ )
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

from thetvdbapi import TheTVDB
from country_lookup import CountryLookup

NEXTAIRED_DB = 'next.aired.db'
COUNTRY_DB = 'country.db'
OLD_FILES = [ 'nextaired.db', 'next_aired.db', 'canceled.db', 'cancelled.db' ]

STATUS = { '0' : __language__(32201),
           '1' : __language__(32202),
           '2' : __language__(32203),
           '3' : __language__(32204),
           '4' : __language__(32205),
           '5' : __language__(32206),
           '6' : __language__(32207),
           '7' : __language__(32208),
           '8' : __language__(32209),
           '9' : __language__(32210),
           '10' : __language__(32211),
           '11' : __language__(32212),
           '-1' : ''}

# Get localized date format
DATE_FORMAT = xbmc.getRegion('dateshort').lower()
if DATE_FORMAT[0] == 'd':
    DATE_FORMAT = '%d-%m-%y'
elif DATE_FORMAT[0] == 'm':
    DATE_FORMAT = '%m-%d-%y'
elif DATE_FORMAT[0] == 'y':
    DATE_FORMAT = '%y-%m-%d'

MAIN_DB_VER = 2
COUNTRY_DB_VER = 1

FAILURE_PAUSE = 5*60

INT_REGEX = re.compile(r"^([0-9]+)$")
NEW_REGEX = re.compile(r"^01x")

if not xbmcvfs.exists(__datapath__):
    xbmcvfs.mkdir(__datapath__)

# TODO make this settable via the command-line?
verbosity = 1

# if level <= 0, sends LOGERROR msg.  For positive values, sends LOGNOTICE
# if level <= verbosity, else LOGDEBUG.  If level is omitted, we assume 10.
def log(txt, level=10):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    log_level = (xbmc.LOGERROR if level <= 0 else (xbmc.LOGNOTICE if level <= verbosity else xbmc.LOGDEBUG))
    xbmc.log(msg=message.encode("utf-8"), level=log_level)

def footprints(bkgnd, force, reset):
    style = 'background' if bkgnd else 'GUI'
    force = 'w/FORCEUPDATE ' if force else ''
    reset = 'w/RESET ' if reset else ''
    log("### %s starting %s proc %s%s..." % (__addonname__, style, force, reset), level=1)
    log("### author: %s" % __author__, level=4)
    log("### version: %s" % __version__, level=2)
    log("### dateformat: %s" % DATE_FORMAT, level=4)

def _unicode( text, encoding='utf-8' ):
    try: text = unicode( text, encoding )
    except: pass
    return text

def normalize(d, key, default = ""):
    text = d.get(key, default)
    try:
        text = unicodedata.normalize('NFKD', _unicode(text)).encode('ascii', 'ignore')
    except:
        pass
    return text

def maybe_int(d, key, default = 0):
    v = d.get(key, str(default))
    return int(v) if INT_REGEX.match(v) else v

class NextAired:
    def __init__(self):
        self.WINDOW = xbmcgui.Window( 10000 )
        self.set_today()
        self.days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        self.local_days = []
        for j in range(41, 48):
            self.local_days.append(xbmc.getLocalizedString(j))
        self.local_months = []
        for j in range(51, 63):
            self.local_months.append(xbmc.getLocalizedString(j))
        self.ampm = xbmc.getCondVisibility('substring(System.Time,Am)') or xbmc.getCondVisibility('substring(System.Time,Pm)')
        # "last_success" is when we last successfully made it through an update pass without fetch errors.
        # "last_update" is when we last successfully marked-up the shows to note which ones need an update.
        # "last_failure" is when we last failed to fetch data, with failure_cnt counting consecutive failures.
        self.last_success = self.last_update = self.last_failure = self.failure_cnt = 0
        self._parse_argv()
        footprints(self.SILENT != "", self.FORCEUPDATE, self.RESET)
        self.check_xbmc_version()
        if self.TVSHOWTITLE:
            self.return_properties(self.TVSHOWTITLE)
        elif self.BACKEND:
            self.run_backend()
        elif self.SILENT == "":
            self.show_gui()
        elif self.STOP:
            self.stop_background_updating()
        else:
            for old_file in OLD_FILES:
                self.rm_file(old_file)
            self.do_background_updating()

    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            params = {}
        log("### params: %s" % params, level=5)
        self.SILENT = params.get( "silent", "" )
        self.BACKEND = params.get( "backend", False )
        self.TVSHOWTITLE = params.get( "tvshowtitle", False )
        self.FORCEUPDATE = params.get("force", False)
        self.RESET = params.get( "reset", False )
        self.STOP = params.get("stop", False)

    def set_today(self):
        self.now = time()
        self.date = date.today()
        self.datestr = str(self.date)
        self.in_dst = localtime().tm_isdst
        self.day_limit = str(self.date + timedelta(days=6))

    # Returns elapsed seconds since last update failure.
    def get_last_failure(self):
        v = self.WINDOW.getProperty("NextAired.last_failure")
        v = float(v) if v != "" else 0
        self.last_failure = max(v, self.last_failure)
        return self.now - self.last_failure

    def set_last_failure(self):
        self.last_failure = self.now
        self.failure_cnt += 1
        self.get_last_failure()
        self.WINDOW.setProperty("NextAired.last_failure", str(self.last_failure))

    def is_time_for_update(self, update_after_seconds):
        self.now = time()
        if self.FORCEUPDATE:
            return True
        if update_after_seconds == 0:
            return False
        if self.now - self.last_success < update_after_seconds:
            return False
        if self.get_last_failure() < FAILURE_PAUSE * min(self.failure_cnt, 24):
            return False
        return True

    def do_background_updating(self):
        my_unique_id = "%s,%s" % (os.getpid(), threading.currentThread().ident)
        self.WINDOW.setProperty("NextAired.background_id", my_unique_id)
        while not xbmc.abortRequested:
            bg_lock = self.WINDOW.getProperty("NextAired.bgnd_lock")
            if bg_lock == "" or time() - float(bg_lock) > 10*60:
                break
            xbmc.sleep(1000)
        profile_dir = xbmc.translatePath("special://profile/addon_data/")
        next_chk = self.now
        this_day = ''
        while not xbmc.abortRequested:
            self.now = time()
            if self.now < next_chk:
                # We can't sleep for very long at a time or a shutdown bogs down.
                # To combat this, we do very little most of the times that we wake
                # up, and the rest of the work after enough time has passed.
                xbmc.sleep(1000)
                continue
            if self.now > next_chk + 15:
                # We slept for a longer time than expected, so this probably means that
                # the computer is waking up from suspend.  Since the networking may not
                # be ready to go just yet, we'll delay our upgrade checking a bit more.
                next_chk = self.now + 60
                continue
            if self.WINDOW.getProperty("NextAired.background_id") != my_unique_id:
                self.close("another background script was started -- stopping older background proc")
            if xbmc.translatePath("special://profile/addon_data/") != profile_dir:
                self.close("profile directory changed -- stopping background proc")
            try:
                update_every = int(__addon__.getSetting('update_every'))*60*60 # hours -> seconds
            except:
                update_every = 0
            # Note that we run the update routine at least once a day to age the episode lists,
            # even if we don't grab any new data (if it's not update time just yet).
            self.set_today()
            next_chk = self.now + 20
            if self.datestr != this_day or self.is_time_for_update(update_every):
                if self.update_data(update_every):
                    this_day = self.datestr
                else:
                    next_chk = self.now + FAILURE_PAUSE * min(self.failure_cnt, 24)
                self.nextlist = [] # Discard the in-memory data until the next update
            else:
                xbmc.sleep(1000)
        self.close("xbmc is closing -- stopping background processing")

    def stop_background_updating(self):
        self.WINDOW.setProperty("NextAired.background_id", 'stop')

    def load_data(self):
        if self.RESET:
            self.rm_file(NEXTAIRED_DB)
            self.rm_file(COUNTRY_DB)

        # Snag our TV-network -> Country + timezone mapping DB, or create it.
        cl = self.get_list(COUNTRY_DB)
        if cl and len(cl) == 3 and self.now - cl[2] < 7*24*60*60: # We'll recreate it every week.
            self.country_dict = cl[0]
        else:
            try:
                log("### grabbing a new country mapping list", level=1)
                self.country_dict = CountryLookup().get_country_dict()
                self.save_file([self.country_dict, COUNTRY_DB_VER, self.now], COUNTRY_DB)
            except:
                # Well, if we couldn't grab a new one, lets try to keep using the old...
                self.country_dict = (cl[0] if cl and len(cl) == 3 else {})

        ep_list = self.get_list(NEXTAIRED_DB)
        ep_list_len = len(ep_list)
        show_dict = (ep_list.pop(0) if ep_list else {})
        self.last_success = (ep_list.pop() if ep_list else None)
        db_ver = (ep_list.pop(0) if ep_list else 999999)
        self.last_update = (ep_list.pop() if ep_list else self.last_success)
        if db_ver > MAIN_DB_VER or not self.last_success:
            if self.RESET:
                log("### starting without prior data (DB RESET requested)", level=1)
            elif ep_list_len:
                log("### ignoring bogus %s file" % NEXTAIRED_DB, level=1)
            else:
                log("### no prior data found", level=1)
            show_dict = {}
            self.last_success = self.last_update = 0
        elif db_ver != MAIN_DB_VER:
            self.upgrade_data_format(show_dict, db_ver)

        self.RESET = False # Make sure we don't honor this multiple times.

        return (show_dict, self.now - self.last_update)

    def update_data(self, update_after_seconds):
        self.nextlist = []
        show_dict, elapsed_secs = self.load_data()

        # This should prevent the background and user code from updating the DB at the same time.
        if self.SILENT != "":
            # We double-check this here, just in case it changed.
            if self.is_time_for_update(update_after_seconds):
                self.WINDOW.setProperty("NextAired.bgnd_status", "0|0|...")
                self.WINDOW.setProperty("NextAired.bgnd_lock", str(self.now))
                locked_for_update = True
                xbmc.sleep(2000) # try to avoid a race-condition
                # Background updating: we will just skip our update if the user is doing an update.
                user_lock = self.WINDOW.getProperty("NextAired.user_lock")
                if user_lock != "":
                    if self.now - float(user_lock) <= 10*60:
                        self.WINDOW.clearProperty("NextAired.bgnd_lock")
                        # We failed to get data, so this will cause us to check on the update in a bit.
                        # (No need to save it as a failure property -- this is just for us.)
                        self.last_failure = self.now
                        return False
                    # User's lock has sat around for too long, so just ignore it.
                self.max_fetch_failures = 8
            else:
                locked_for_update = False
            socket.setdefaulttimeout(60)
        elif self.is_time_for_update(update_after_seconds): # We only lock if we're going to do some updating.
            # User updating: we will wait for a background update to finish, then see if we have recent data.
            DIALOG_PROGRESS = xbmcgui.DialogProgress()
            DIALOG_PROGRESS.create(__language__(32101), __language__(32102))
            self.max_fetch_failures = 4
            # Create our user-lock file and check if the background updater is running.
            self.WINDOW.setProperty("NextAired.user_lock", str(self.now))
            locked_for_update = True
            newest_time = 0
            prior_name = ''
            while 1:
                bg_lock = self.WINDOW.getProperty("NextAired.bgnd_lock")
                if bg_lock == "":
                    break
                if newest_time == 0:
                    newest_time = float(bg_lock)
                bg_status = self.WINDOW.getProperty("NextAired.bgnd_status")
                bg_status = bg_status.split('|', 2)
                if len(bg_status) == 3:
                    status_time, percent, show_name = (float(bg_status[0]), int(bg_status[1]), bg_status[2])
                    if show_name != prior_name:
                        DIALOG_PROGRESS.update(percent, __language__(32102), show_name)
                        prior_name = show_name
                    if DIALOG_PROGRESS.iscanceled():
                        DIALOG_PROGRESS.close()
                        xbmcgui.Dialog().ok(__language__(32103),__language__(32104))
                        self.WINDOW.clearProperty("NextAired.user_lock")
                        locked_for_update = False
                        break
                    if status_time > newest_time:
                        newest_time = status_time
                if time() - newest_time > 2*60:
                    # Background lock has sat around for too long, so just ignore it.
                    newest_time = 0
                    break
                xbmc.sleep(500)
            if newest_time:
                # If we had to wait for the bgnd updater, re-read the data and unlock if they did an update.
                show_dict, elapsed_secs = self.load_data()
                if locked_for_update and not self.is_time_for_update(update_after_seconds):
                    DIALOG_PROGRESS.close()
                    self.WINDOW.clearProperty("NextAired.user_lock")
                    locked_for_update = False
            socket.setdefaulttimeout(10)
        else:
            locked_for_update = False

        if locked_for_update:
            log("### starting data update", level=1)
            tvdb = TheTVDB('1D62F2F90030C444', 'en', want_raw = True)
            # This typically asks TheTVDB for an update-zip file and tweaks the show_dict to note needed updates.
            tv_up = tvdb_updater(tvdb)
            need_full_scan, got_update = tv_up.note_updates(show_dict, elapsed_secs)
            if need_full_scan or got_update:
                self.last_update = self.now
            elif not got_update:
                self.max_fetch_failures = 0
            tv_up = None
        else:
            tvdb = None # We don't use this unless we're locked for the update.
            need_full_scan = False
            # A max-fetch of 0 disables all updating.
            self.max_fetch_failures = 0

        title_dict = {}
        for tid, show in show_dict.iteritems():
            show['unused'] = True
            title_dict[show['localname']] = tid

        TVlist = self.listing()
        total_show = len(TVlist)
        if total_show == 0:
            if self.SILENT != "":
                self.WINDOW.clearProperty("NextAired.bgnd_lock")
                self.WINDOW.clearProperty("NextAired.bgnd_status")
            elif locked_for_update:
                DIALOG_PROGRESS.close()
                self.WINDOW.clearProperty("NextAired.user_lock")
            self.set_last_failure()
            return False

        count = 0
        id_re = re.compile(r"http%3a%2f%2fthetvdb\.com%2f[^']+%2f([0-9]+)-")
        for show in TVlist:
            count += 1
            percent = int(float(count * 100) / total_show)
            if self.SILENT != "":
                self.WINDOW.setProperty("NextAired.bgnd_status", "%f|%d|%s" % (time(), percent, show[0]))
            elif locked_for_update and self.max_fetch_failures > 0:
                DIALOG_PROGRESS.update( percent , __language__(32102) , "%s" % show[0] )
                if DIALOG_PROGRESS.iscanceled():
                    DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok(__language__(32103),__language__(32104))
                    self.max_fetch_failures = 0
            log( "### %s" % show[0] )
            current_show = {
                    "localname": show[0],
                    "path": show[1],
                    "art": show[2],
                    "dbid": show[3],
                    "thumbnail": show[4],
                    }
            # Try to figure out what the tvdb number is by using the art URLs and the imdbnumber value
            m2 = id_re.search(str(show[2]))
            m2_num = int(m2.group(1)) if m2 else 0
            m4 = id_re.search(show[4])
            m4_num = int(m4.group(1)) if m4 else 0
            m5 = INT_REGEX.match(show[5])
            m5_num = int(m5.group(1)) if m5 else 0
            if m5_num and (m2_num == m5_num or m4_num == m5_num):
                # Most shows will be in agreement on the id when the scraper is using thetvdb.
                tid = m5_num
            else:
                old_id = title_dict.get(current_show["localname"], 0)
                if old_id and (m2_num == old_id or m4_num == old_id):
                    tid = old_id
                elif m2_num and m2_num == m4_num:
                    # This will override the old_id value if both artwork URLs change.
                    tid = m2_num
                elif old_id:
                    tid = old_id
                else:
                    tid = 0 # We'll query it from thetvdb.com

            try:
                prior_data = show_dict[tid]
                if 'unused' not in prior_data:
                    continue # How'd we get a duplicate?? Skip it...
                del prior_data['unused']
                while len(prior_data['episodes']) > 1 and prior_data['episodes'][1]['aired'][:10] < self.datestr:
                    prior_data['episodes'].pop(0)
            except:
                prior_data = None

            if self.max_fetch_failures > 0:
                tid = self.check_show_info(tvdb, tid, current_show, prior_data)
            else:
                tid = -tid
            if tid <= 0:
                if not prior_data or tid == 0:
                    continue
                for item in prior_data:
                    if item not in current_show:
                        current_show[item] = prior_data[item]
                tid = -tid
            if current_show.get('canceled', False):
                log("### Canceled/Ended", level=4)
            log( "### %s" % current_show )
            show_dict[tid] = current_show

        # If we did a lot of work, make sure we save it prior to doing anything else.
        # This ensures that a bug in the following code won't make us redo everything.
        if need_full_scan and locked_for_update:
            self.save_file([show_dict, MAIN_DB_VER, self.last_update, self.last_success], NEXTAIRED_DB)

        if show_dict:
            log("### data available", level=5)
            remove_list = []
            for tid, show in show_dict.iteritems():
                if 'unused' in show:
                    remove_list.append(tid)
                    continue
                if len(show['episodes']) > 1:
                    show['RFC3339'] = show['episodes'][1]['aired']
                    self.nextlist.append(show)
                elif 'RFC3339' in show:
                    del show['RFC3339']
            for tid in remove_list:
                log('### Removing obsolete show %s' % show_dict[tid]['localname'], level=2)
                del show_dict[tid]
            self.nextlist.sort(key=itemgetter('RFC3339'))
            log("### next list: %s shows ### %s" % (len(self.nextlist) , self.nextlist), level=5)
            self.check_today_show()
            self.push_data()
        else:
            log("### no current show data...", level=5)

        if locked_for_update:
            if self.max_fetch_failures > 0:
                self.last_success = self.now
            self.save_file([show_dict, MAIN_DB_VER, self.last_update, self.last_success], NEXTAIRED_DB)
            log("### data update finished", level=1)

            if self.SILENT != "":
                self.WINDOW.clearProperty("NextAired.bgnd_lock")
                xbmc.sleep(1000)
                self.WINDOW.clearProperty("NextAired.bgnd_status")
            else:
                DIALOG_PROGRESS.close()
                self.WINDOW.clearProperty("NextAired.user_lock")
            if self.max_fetch_failures <= 0:
                self.set_last_failure()
            else:
                self.failure_cnt = 0

        self.FORCEUPDATE = False
        return True

    def check_xbmc_version(self):
        # retrieve current installed version
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log("### %s" % json_response)
        try:
            self.xbmc_version = json_response['result']['version']['major']
        except:
            self.xbmc_version = 12

        self.videodb = 'videodb://tvshows/titles/' if self.xbmc_version >= 13 else 'videodb://2/2/'

    def listing(self):
        failures = 0
        # If the computer is waking up from a sleep, this call might fail for a little bit.
        while not xbmc.abortRequested:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "file", "thumbnail", "art", "imdbnumber"], "sort": { "method": "title" } }, "id": 1}')
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            log("### %s" % json_response)
            if 'result' in json_response:
                break
            failures += 1
            if failures >= 5:
                break
            xbmc.sleep(5000)
        try:
            tvshows = json_response['result']['tvshows']
        except:
            tvshows = []
        TVlist = []
        for item in tvshows:
            tvshowname = normalize(item, 'title')
            path = item['file']
            art = item['art']
            thumbnail = item['thumbnail']
            dbid = self.videodb + str(item['tvshowid']) + '/'
            TVlist.append((tvshowname, path, art, dbid, thumbnail, item['imdbnumber']))
        log( "### list: %s" % TVlist )
        return TVlist

    def check_show_info(self, tvdb, tid, current_show, prior_data):
        name = current_show['localname']
        log("### check if %s is up-to-date" % name, level=4)
        if tid == 0:
            log("### searching for thetvdb ID by name - %s" % name, level=2)
            try:
                show_list = tvdb.get_matching_shows(name)
            except Exception, e:
                log('### ERROR returned by get_matching_shows(): %s' % e, level=0)
                show_list = None
            if not show_list:
                log("### no match found", level=2)
                return 0
            got_id, got_title, got_tt_id = show_list[0]
            tid = int(got_id)
            log("### found id of %d" % tid, level=2)
        else:
            log("### thetvdb id = %d" % tid, level=5)
        # If the prior_data isn't in need of an update, use it unchanged.
        if prior_data:
            earliest_id, eps_last_updated = prior_data.get('eps_changed', (None, 0))
            if earliest_id is None:
                eps_last_updated = prior_data['eps_last_updated']
            show_changed = prior_data.get('show_changed', 0)
            if show_changed:
                if earliest_id is None:
                    earliest_id = 0
            elif earliest_id is None:
                log("### no changes needed", level=5)
                return -tid
            for ep in prior_data['episodes']:
                if ep['id'] and ep['id'] < earliest_id:
                    earliest_id = ep['id']
        else:
            show_changed = 0
            earliest_id = 1
            eps_last_updated = 0

        if earliest_id != 0:
            log("### earliest_id = %d" % earliest_id, level=5)
            for cnt in range(2):
                log("### getting series & episode info for #%d - %s" % (tid, name), level=1)
                try:
                    result = tvdb.get_show_and_episodes(tid, earliest_id)
                    break
                except Exception, e:
                    log('### ERROR returned by get_show_and_episodes(): %s' % e, level=0)
                    self.max_fetch_failures -= 1
                    result = None
            if result:
                show = result[0]
                episodes = result[1]
            else:
                show = None
        else: # earliest_id == 0 when only the series-info changed
            for cnt in range(2):
                log("### getting series info for #%d - %s" % (tid, name), level=1)
                try:
                    show = tvdb.get_show(tid)
                    break
                except Exception, e:
                    log('### ERROR returned by get_show(): %s' % e, level=0)
                    self.max_fetch_failures -= 1
                    show = None
            episodes = None
        if not show:
            if prior_data:
                log("### no result: continuing to use the old data", level=1)
            else:
                log("### no result and no prior data", level=1)
            return -tid

        network = normalize(show, 'Network', 'Unknown')
        country = self.country_dict.get(network, 'Unknown')
        # XXX TODO allow the user to specify an override country that gets the local timezone.
        tzone = CountryLookup.get_country_timezone(country, self.in_dst)
        if not tzone:
            tzone = ''
        tz_re = re.compile(r"([-+])(\d\d):(\d\d)")
        m = tz_re.match(tzone)
        if m:
            tz_offset = (int(m.group(2)) * 3600) + (int(m.group(3)) * 60)
            if m.group(1) == '-':
                tz_offset *= -1
        else:
            tz_offset = 1 * 3600 # Default to +01:00
        try:
            airtime = TheTVDB.convert_time(show.get('Airs_Time', ""))
        except:
            airtime = None
        local_airtime = airtime if airtime is not None else TheTVDB.convert_time('00:00')
        local_airtime = datetime.combine(self.date, local_airtime).replace(tzinfo=tz.tzoffset(None, tz_offset))
        if airtime is not None: # Don't backtrack an assumed midnight time (for an invalid airtime) into the prior day.
            local_airtime = local_airtime.astimezone(tz.tzlocal())

        current_show['Show Name'] = normalize(show, 'SeriesName')
        first_aired = show.get('FirstAired', None)
        if first_aired:
            first_aired = TheTVDB.convert_date(first_aired)
            current_show['Premiered'] = first_aired.year
            current_show['Started'] = first_aired.isoformat()
        else:
            current_show['Premiered'] = current_show['Started'] = ""
        current_show['Country'] = country
        current_show['Status'] = normalize(show, 'Status')
        current_show['Genres'] = normalize(show, 'Genre').strip('|').replace('|', ' | ')
        current_show['Network'] = network
        current_show['Airtime'] = local_airtime.strftime('%H:%M') if airtime is not None else ''
        current_show['Runtime'] = maybe_int(show, 'Runtime', '')

        can_re = re.compile(r"canceled|ended", re.IGNORECASE)
        if can_re.search(current_show['Status']):
            current_show['canceled'] = True
        elif 'canceled' in current_show:
            del current_show['canceled']

        if episodes is not None:
            episode_list = []

            max_eps_utime = 0
            if episodes:
                good_eps = []
                for ep in episodes:
                    ep['id'] = int(ep['id'])
                    ep['SeasonNumber'] = maybe_int(ep, 'SeasonNumber')
                    ep['EpisodeNumber'] = maybe_int(ep, 'EpisodeNumber')
                    last_updated = maybe_int(ep, 'lastupdated')
                    if last_updated > max_eps_utime:
                        max_eps_utime = last_updated
                    first_aired = ep.get('FirstAired', "")
                    log("### fetched ep=%d last_updated=%d first_aired=%s" % (ep['id'], last_updated, first_aired))
                    first_aired = TheTVDB.convert_date(first_aired)
                    if not first_aired:
                        continue
                    ep['FirstAired'] = local_airtime + timedelta(days = (first_aired - self.date).days)
                    good_eps.append(ep)
                episodes = sorted(good_eps, key=itemgetter('FirstAired', 'SeasonNumber', 'EpisodeNumber'))
            if episodes and episodes[0]['FirstAired'].date() < self.date:
                while len(episodes) > 1 and episodes[1]['FirstAired'].date() < self.date:
                    ep = episodes.pop(0)
            else: # If we have no prior episodes, prepend a "None" episode
                episode_list.append({ 'id': None })

            for ep in episodes:
                cur_ep = {
                        'id': ep['id'],
                        'name': normalize(ep, 'EpisodeName'),
                        'number': '%02dx%02d' % (ep['SeasonNumber'], ep['EpisodeNumber']),
                        'aired': ep['FirstAired'].isoformat(),
                        'wday': self.days[ep['FirstAired'].weekday()]
                        }
                episode_list.append(cur_ep)

            current_show['episodes'] = episode_list
        elif prior_data:
            max_eps_utime = eps_last_updated
            current_show['episodes'] = prior_data['episodes']
            if current_show['Airtime'] != prior_data['Airtime']:
                for ep in current_show['episodes']:
                    if not ep['id']:
                        continue
                    aired = TheTVDB.convert_date(ep['aired'][:10])
                    aired = local_airtime + timedelta(days = (aired - self.date).days)
                    ep['aired'] = aired.isoformat()
                    ep['wday'] = self.days[aired.weekday()]
        else:
            max_eps_utime = 0
            current_show['episodes'] = [{ 'id': None }]

        if prior_data:
            last_updated = int(show['lastupdated'])
            if 'show_changed' in prior_data and last_updated < show_changed:
                log("### didn't get latest show info yet (%d < %d)" % (last_updated, show_changed), level=1)
                current_show['show_changed'] = show_changed
            if 'eps_changed' in prior_data and max_eps_utime < eps_last_updated:
                log("### didn't get latest episode info yet (%d < %d)" % (max_eps_utime, eps_last_updated), level=1)
                current_show['eps_changed'] = (earliest_id, eps_last_updated)

        current_show['last_updated'] = max(show_changed, last_updated)
        current_show['eps_last_updated'] = max(eps_last_updated, max_eps_utime)
        return tid

    @staticmethod
    def upgrade_data_format(show_dict, from_ver):
        log("### upgrading DB from version %d to %d" % (from_ver, MAIN_DB_VER), level=1)
        for tid, show in show_dict.iteritems():
            if from_ver < 2:
                # Convert Started into isoformat date:
                started = ''
                for fmt in ('%b/%d/%Y', '%a, %b %d, %Y', '%Y-%m-%d'):
                    try:
                        started = strftime('%Y-%m-%d', strptime(show['Started'], fmt))
                        break
                    except:
                        pass
                show['Started'] = started
                # Convert airtime into HH:MM (never AM/PM):
                airtime = TheTVDB.convert_time(show['Airtime'])
                show['Airtime'] = airtime.strftime('%H:%M') if airtime is not None else ''

    def set_episode_info(self, label, prefix, when, ep):
        if ep and ep['id']:
            name = ep['name']
            number = ep['number']
            aired = self.nice_date(TheTVDB.convert_date(ep['aired'][:10]))
        else:
            name = number = aired = ''
        num_array = number.split('x')
        num_array.extend([''])

        label.setProperty(prefix + when + 'Date', aired)
        label.setProperty(prefix + when + 'Title', name)
        label.setProperty(prefix + when + 'Number', number)
        label.setProperty(prefix + when + 'SeasonNumber', num_array[0])
        label.setProperty(prefix + when + 'EpisodeNumber', num_array[1])

    def check_today_show(self):
        self.set_today()
        self.todayshow = 0
        self.todaylist = []
        log( "### %s" % self.datestr )
        for show in self.nextlist:
            name = show["localname"]
            when = show["RFC3339"]
            log( "################" )
            log( "### %s" % name )
            if when[:10] == self.datestr:
                self.todayshow += 1
                self.todaylist.append(name)
                log( "### TODAY" )
            log( "### %s" % when )
        log( "### today show: %s - %s" % ( self.todayshow , str(self.todaylist).strip("[]") ) )

    def nice_date(self, d, force_year = False):
        if d is None:
            return ''
        tt = d.timetuple()
        d = "%s, %s %d" % (self.local_days[tt[6]], self.local_months[tt[1]-1], tt[2])
        if force_year or tt[0] != self.date.year:
            d += ", %d" % tt[0]
        return d

    @staticmethod
    def get_list(listname):
        path = os.path.join( __datapath__ , listname )
        if xbmcvfs.exists(path):
            log( "### Load list: %s" % path )
            return NextAired.load_file(path)
        else:
            log( "### Load list: %s not found!" % path )
            return []

    @staticmethod
    def load_file(file_path):
        try:
            return eval( file( file_path, "r" ).read() )
        except:
            print_exc()
            log("### ERROR could not load file %s" % file_path, level=0)
            return []

    @staticmethod
    def save_file(txt, filename):
        path = os.path.join( __datapath__ , filename )
        try:
            if txt:
                file( path , "w" ).write( repr( txt ) )
            else:
                self.rm_file(filename)
        except:
            print_exc()
            log("### ERROR could not save file %s" % path, level=0)

    @staticmethod
    def rm_file(filename):
        path = os.path.join(__datapath__, filename)
        try:
            if xbmcvfs.exists(path):
                xbmcvfs.delete(path)
        except:
            pass

    def push_data(self):
        try:
            oldTotal = int(self.WINDOW.getProperty("NextAired.Total"))
        except:
            oldTotal = 1
        self.WINDOW.setProperty("NextAired.Total" , str(len(self.nextlist)))
        self.WINDOW.setProperty("NextAired.TodayTotal" , str(self.todayshow))
        self.WINDOW.setProperty("NextAired.TodayShow" , str(self.todaylist).strip("[]"))
        for count in range(oldTotal):
            self.WINDOW.clearProperty("NextAired.%d.Label" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Thumb" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.AirTime" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Path" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Library" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Status" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.StatusID" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Network" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Started" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Classification" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Genre" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Premiered" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Country" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Runtime" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Fanart" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Art(fanart)" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Art(poster)" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Art(landscape)" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Art(banner)" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Art(clearlogo)" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Art(characterart)" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Art(clearart)" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Today" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.NextDate" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.NextTitle" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.NextNumber" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.NextEpisodeNumber" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.NextSeasonNumber" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.LatestDate" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.LatestTitle" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.LatestNumber" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.LatestEpisodeNumber" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.LatestSeasonNumber" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.Airday" % ( count + 1, ))
            self.WINDOW.clearProperty("NextAired.%d.ShortTime" % ( count + 1, ))
        self.count = 0
        for current_show in self.nextlist:
            if ((current_show.get("RFC3339" , "" )[:10] == self.datestr) or (__addon__.getSetting( "ShowAllTVShowsOnHome" ) == 'true')):
                self.count += 1
                self.set_labels('windowpropertytoday', current_show)

    def show_gui(self):
        try:
            update_after = int(__addon__.getSetting('update_after'))*60*60 # hours -> seconds
        except:
            update_after = 0
        self.update_data(update_after)
        weekday = self.date.weekday()
        self.WINDOW.setProperty("NextAired.TodayDate", self.date.strftime(DATE_FORMAT))
        for count in range(0, 7):
            date = self.date
            if count != weekday:
                date += timedelta(days = (count - weekday + 7) % 7)
            self.WINDOW.setProperty("NextAired.%d.Date" % (count + 1), date.strftime(DATE_FORMAT))
        import next_aired_dialog
        next_aired_dialog.MyDialog(self.nextlist, self.set_labels)

    def run_backend(self):
        self._stop = False
        self.previousitem = ''
        ep_list = self.get_list(NEXTAIRED_DB)
        show_dict = (ep_list.pop(0) if ep_list else {})
        if not show_dict:
            self._stop = True
        while not self._stop:
            self.selecteditem = xbmc.getInfoLabel("ListItem.TVShowTitle")
            if self.selecteditem != self.previousitem:
                self.WINDOW.clearProperty("NextAired.Label")
                self.previousitem = self.selecteditem
                for tid, item in show_dict.iteritems():
                    if self.selecteditem == item["localname"]:
                        self.set_labels('windowproperty', item)
                        break
            xbmc.sleep(100)
            if not xbmc.getCondVisibility("Window.IsVisible(10025)"):
                self.WINDOW.clearProperty("NextAired.Label")
                self._stop = True

    def return_properties(self,tvshowtitle):
        ep_list = self.get_list(NEXTAIRED_DB)
        show_dict = (ep_list.pop(0) if ep_list else {})
        log("### return_properties started", level=6)
        if show_dict:
            self.WINDOW.clearProperty("NextAired.Label")
            for tid, item in show_dict.iteritems():
                if tvshowtitle == item["localname"]:
                    self.set_labels('windowproperty', item)

    def set_labels(self, infolabel, item, want_ep_ndx = None):
        art = item.get("art", "")
        if (infolabel == 'windowproperty') or (infolabel == 'windowpropertytoday'):
            label = xbmcgui.Window( 10000 )
            if infolabel == "windowproperty":
                prefix = 'NextAired.'
            else:
                prefix = 'NextAired.' + str(self.count) + '.'
                if __addon__.getSetting( "ShowAllTVShowsOnHome" ) == 'true':
                    label.setProperty('NextAired.' + "ShowAllTVShows", "true")
                else:
                    label.setProperty('NextAired.' + "ShowAllTVShows", "false")
            label.setProperty(prefix + "Label", item.get("localname", ""))
            label.setProperty(prefix + "Thumb", item.get("thumbnail", ""))
        else:
            label = xbmcgui.ListItem()
            prefix = ''
            label.setLabel(item.get("localname", ""))
            label.setThumbnailImage(item.get("thumbnail", ""))

        if want_ep_ndx:
            next_ep = item['episodes'][want_ep_ndx]
            latest_ep = item['episodes'][want_ep_ndx-1]
            airdays = next_ep['wday']
        else:
            ep_len = len(item['episodes'])
            next_ep = item['episodes'][1] if ep_len > 1 else None
            latest_ep = item['episodes'][0]
            airdays = []
            if ep_len > 1:
                for ep in item['episodes'][1:]:
                    if ep['aired'][:10] > self.day_limit:
                        break
                    airdays.append(ep['wday'])
            airdays = ', '.join(airdays)
        is_today = 'True' if next_ep and next_ep['aired'][:10] == self.datestr else 'False'

        started = TheTVDB.convert_date(item["Started"])
        airtime = TheTVDB.convert_time(item["Airtime"])
        if airtime is not None:
            airtime = airtime.strftime('%I:%M %p' if self.ampm else '%H:%M')
        else:
            airtime = '??:??'

        status = item.get("Status", "")
        if status == 'Continuing':
            ep = next_ep if next_ep else latest_ep if latest_ep else None
            if not ep or not ep['id'] or NEW_REGEX.match(ep['number']):
                status_id = '4' # New
            else:
                status_id = '0' # Returning
        elif status == 'Ended':
            if next_ep:
                status_id = '6' # Final Season
            else:
                status_id = '1' # Cancelled/Ended
        elif status == '':
            status_id = '2' # TBD/On the bubble
        else:
            status_id = '-1' # An unknown value shouldn't be possible...
        if status_id != '-1':
            status = STATUS[status_id]

        label.setProperty(prefix + "AirTime", '%s at %s' % (airdays, airtime))
        label.setProperty(prefix + "Path", item.get("path", ""))
        label.setProperty(prefix + "Library", item.get("dbid", ""))
        label.setProperty(prefix + "Status", status)
        label.setProperty(prefix + "StatusID", status_id)
        label.setProperty(prefix + "Network", item.get("Network", ""))
        label.setProperty(prefix + "Started", self.nice_date(started, force_year = True))
        # XXX Note that Classification is always unset at the moment!
        label.setProperty(prefix + "Classification", item.get("Classification", ""))
        label.setProperty(prefix + "Genre", item.get("Genres", ""))
        label.setProperty(prefix + "Premiered", str(item.get("Premiered", "")))
        label.setProperty(prefix + "Country", item.get("Country", ""))
        label.setProperty(prefix + "Runtime", str(item.get("Runtime", "")))
        # Keep old fanart property for backwards compatibility
        label.setProperty(prefix + "Fanart", art.get("fanart", ""))
        # New art properties
        label.setProperty(prefix + "Art(fanart)", art.get("fanart", ""))
        label.setProperty(prefix + "Art(poster)", art.get("poster", ""))
        label.setProperty(prefix + "Art(banner)", art.get("banner", ""))
        label.setProperty(prefix + "Art(landscape)", art.get("landscape", ""))
        label.setProperty(prefix + "Art(clearlogo)", art.get("clearlogo", ""))
        label.setProperty(prefix + "Art(characterart)", art.get("characterart", ""))
        label.setProperty(prefix + "Art(clearart)", art.get("clearart", ""))
        label.setProperty(prefix + "Today", is_today)
        label.setProperty(prefix + "AirDay", airdays)
        label.setProperty(prefix + "ShortTime", airtime)

        # This sets NextDate, NextTitle, etc.
        self.set_episode_info(label, prefix, 'Next', next_ep)
        # This sets LatestDate, LatestTitle, etc.
        self.set_episode_info(label, prefix, 'Latest', latest_ep)

        if want_ep_ndx:
            return label

    def close(self , msg ):
        log("### %s" % msg, level=1)
        sys.exit()

class tvdb_updater:
    def __init__(self, tvdb):
        self.tvdb = tvdb

    def note_updates(self, show_dict, elapsed_update_secs):
        self.show_dict = show_dict

        if elapsed_update_secs < 24*60*60:
            period = 'day'
        elif elapsed_update_secs < 7*24*60*60:
            period = 'week'
        elif elapsed_update_secs < 30*24*60*60:
            period = 'month'
        else:
            # Flag all non-canceled shows as needing new data
            for tid, show in show_dict.iteritems():
                if not show.get('canceled', False):
                    show['show_changed'] = 1
                    show['eps_changed'] = (1, 0)
            return (True, False) # Alert caller that a full-scan is in progress.

        log("### Update period: %s (%d mins)" % (period, int(elapsed_update_secs / 60)), level=2)

        got_update = False
        try:
            self.tvdb.get_updates(self.change_callback, period)
            got_update = True
        except Exception, e:
            log('### ERROR retreiving updates from thetvdb.com: %s' % e, level=0)

        return (False, got_update)

    def change_callback(self, name, attrs):
        if name == 'Episode':
            episode_id = int(attrs['id'])
            series_id = int(attrs['Series'])
        elif name == 'Series':
            series_id = int(attrs['id'])
            episode_id = 0
        elif name == 'Data':
            when = int(attrs['time'])
            # Do something with this?
            return
        else:
            return # Ignore Banner and anything else that may show up
        try:
            show = self.show_dict[series_id]
        except:
            return # Ignore shows we don't care about
        when = int(attrs['time'])
        if episode_id == 0:
            if when <= show['last_updated']:
                return
            log("### Found series change (series: %d, time: %d) for %s" % (series_id, when, show['localname']), level=2)
            show['show_changed'] = when
        else:
            if when <= show['eps_last_updated']:
                return
            log("### Found episode change (series: %d, ep: %d, time=%d) for %s" % (series_id, episode_id, when, show['localname']), level=2)
            earliest_id, latest_time = show.get('eps_changed', (episode_id, when))
            if episode_id < earliest_id:
                earliest_id = episode_id
            if when > latest_time:
                latest_time = when
            show['eps_changed'] = (earliest_id, latest_time)
        return

if ( __name__ == "__main__" ):
    NextAired()

# vim: sw=4 ts=8 et

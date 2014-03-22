from time import strftime, strptime, time, mktime, localtime, tzname
import os, sys, re, socket, urllib, unicodedata, threading
from traceback import print_exc
from datetime import datetime, date, timedelta
from dateutil import tz
from operator import itemgetter
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
try:
    import simplejson as json
except ImportError:
    import json
# http://mail.python.org/pipermail/python-list/2009-June/540579.html
import _strptime

__addon__     = xbmcaddon.Addon()
__addonid__   = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path').decode('utf-8')
__author__    = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__language__  = __addon__.getLocalizedString
__datapath__  = os.path.join(xbmc.translatePath("special://profile/addon_data/").decode('utf-8'), __addonid__)
__resource__  = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib').encode("utf-8")).decode("utf-8")

sys.path = [__resource__] + sys.path

from thetvdbapi import TheTVDB
from country_lookup import CountryLookup
from fanarttv import FanartTV

NEXTAIRED_DB = 'next.aired.db'
COUNTRY_DB = 'country.db'
OLD_FILES = [ 'nextaired.db', 'next_aired.db', 'canceled.db', 'cancelled.db' ]
LISTITEM_ART = [ 'poster', 'banner', 'clearlogo' ] # This order MUST match the settings.xml list!!
USEFUL_ART = LISTITEM_ART + [ 'characterart', 'clearart', 'fanart', 'landscape' ]
CLASSIFICATION_REGEX = re.compile(r"(?:^| \| )(Scripted|Mini-Series|Documentary|Animation|Game Show|Reality|Talk Show|Variety)( \| |$)")

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

leftover_re = re.compile(r"%[a-z]")
NICE_DATE_FORMAT = xbmc.getRegion('datelong').lower().replace('%d%d', '%d')
for xx, yy in (('%a', '%(wday)s'), ('%b', '%(month)s'), ('%d', '%(day)s'), ('%y', '%(year)s'), ('%m', '%(mm)s')):
    NICE_DATE_FORMAT = NICE_DATE_FORMAT.replace(xx, yy)
NICE_DATE_FORMAT = leftover_re.sub('%(unk)s', NICE_DATE_FORMAT)

year_remove_regex = re.compile(r"(?<=\)s)[^%]*%\(year\)s|^%\(year\)s[^%]*")
NICE_DATE_NO_YEAR = year_remove_regex.sub('', NICE_DATE_FORMAT)
wday_remove_regex = re.compile(r"%\(wday\)s[^%]*")
NICE_SHORT_DATE = wday_remove_regex.sub('', NICE_DATE_NO_YEAR)

MAIN_DB_VER = 5
COUNTRY_DB_VER = 1

FAILURE_PAUSE = 5*60

INT_REGEX = re.compile(r"^([0-9]+)$")

if not xbmcvfs.exists(__datapath__):
    xbmcvfs.mkdir(__datapath__)

MAX_INFO_LOG_LEVEL = 1
MAX_DEBUG_LOG_LEVEL = 3

# if level <= 0, sends LOGERROR msg.  For positive values, sends LOGNOTICE
# if level <= MAX_INFO_LOG_LEVEL, else LOGDEBUG.  If level is omitted, we assume 10.
def log(txt, level=10):
    if level > max(MAX_DEBUG_LOG_LEVEL, MAX_INFO_LOG_LEVEL):
        return
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    log_level = (xbmc.LOGERROR if level <= 0 else (xbmc.LOGNOTICE if level <= MAX_INFO_LOG_LEVEL else xbmc.LOGDEBUG))
    xbmc.log(msg=message.encode("utf-8"), level=log_level)

def footprints(bkgnd, force, reset):
    style = 'background' if bkgnd else 'GUI'
    force = 'w/FORCEUPDATE ' if force else ''
    reset = 'w/RESET ' if reset else ''
    log("### %s starting %s proc %s%s(%s)" % (__addonname__, style, force, reset, __version__), level=1)
    log("### dateformat: %s" % DATE_FORMAT, level=4)
    log("### nice-date-format: %s" % NICE_DATE_FORMAT, level=4)
    log("### nice-date-no-year: %s" % NICE_DATE_NO_YEAR, level=4)
    log("### nice-short-date: %s" % NICE_SHORT_DATE, level=4)

def _unicode(text, encoding='utf-8'):
    try: text = unicode(text, encoding)
    except: pass
    return text

def normalize(d, key = None, default = ""):
    if key is None:
        text = d
    else:
        text = d.get(key, default)
        if not text:
            return text
    try:
        text = unicodedata.normalize('NFKD', _unicode(text)).encode('ascii', 'ignore')
    except:
        pass
    return text

STRIP_PUNCT_RE = re.compile("[.,:;?!*$^#|<>'\"]")
STRIP_EXTRA_SPACES_RE = re.compile(r"\s{2,}")

def lc_stripped_name(show_name):
    show_name = STRIP_EXTRA_SPACES_RE.sub(' ', show_name.lower())
    return STRIP_PUNCT_RE.sub('', show_name.strip())

def maybe_int(d, key, default = 0):
    v = d.get(key, str(default))
    return int(v) if INT_REGEX.match(v) else v

class NextAired:
    def __init__(self):
        self.WINDOW = xbmcgui.Window(10000)
        self.set_today()
        self.tznames = ','.join(map(str,tzname))
        self.weekdays = []
        for j in range(11, 18):
            self.weekdays.append(xbmc.getLocalizedString(j))
        self.wdays = []
        for j in range(41, 48):
            self.wdays.append(xbmc.getLocalizedString(j))
        self.local_months = []
        for j in range(51, 63):
            self.local_months.append(xbmc.getLocalizedString(j))
        self.ampm = xbmc.getCondVisibility('substring(System.Time,Am)') or xbmc.getCondVisibility('substring(System.Time,Pm)')
        self.improve_dates = __addon__.getSetting("ImproveDates") == 'true'
        # "last_success" is when we last successfully made it through an update pass without fetch errors.
        # "last_update" is when we last successfully marked-up the shows to note which ones need an update.
        # "last_failure" is when we last failed to fetch data, with failure_cnt counting consecutive failures.
        self.last_success = self.last_update = self.last_failure = self.failure_cnt = 0
        self._parse_argv()
        footprints(self.SILENT != "", self.FORCEUPDATE, self.RESET)
        self.check_xbmc_version()
        if self.TVSHOWTITLE:
            self.return_properties(self.TVSHOWTITLE)
        elif self.UPDATESHOW:
            self.update_show(self.UPDATESHOW)
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

    def _parse_argv(self):
        try:
            self.params = dict(arg.split("=") for arg in sys.argv[1].split("&"))
        except:
            self.params = {}
        log("### params: %s" % self.params, level=3)
        self.SILENT = self.params.get("silent", "")
        self.BACKEND = self.params.get("backend", False)
        self.TVSHOWTITLE = normalize(self.params, "tvshowtitle", False)
        self.UPDATESHOW = normalize(self.params, "updateshow", False)
        self.FORCEUPDATE = self.params.get("force", False)
        self.RESET = self.params.get("reset", False)
        self.STOP = self.params.get("stop", False)

    def set_today(self):
        self.now = time()
        self.date = date.today()
        self.datestr = str(self.date)
        self.yesterday = self.date - timedelta(days=1)
        self.yesterstr = str(self.yesterday)
        self.tomorrow = self.date + timedelta(days=1)

    # Returns elapsed seconds since last update failure.
    def get_last_failure(self):
        v = self.WINDOW.getProperty("NextAired.last_failure")
        v = float(v) if v != "" else 0
        if v and self.failure_cnt == 0:
            self.failure_cnt += 1
        self.last_failure = max(v, self.last_failure)
        return self.now - self.last_failure

    def set_last_failure(self):
        self.last_failure = self.now
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
            latest_version = xbmcaddon.Addon().getAddonInfo('version')
            if latest_version != __version__:
                self.handle_bg_version_change(latest_version)
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
                    self.failure_cnt = 0
                    this_day = self.datestr
                else:
                    self.failure_cnt += 1
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

        # Snag our TV-network -> Country mapping DB.
        cl = self.get_list(COUNTRY_DB)
        self.country_dict = (cl.pop(0) if cl else {})
        self.country_last_update = (cl.pop() if cl else 0)
        db_ver = (cl.pop(0) if cl else 0)
        if db_ver != COUNTRY_DB_VER:
            self.country_dict = {}

        ep_list = self.get_list(NEXTAIRED_DB)
        ep_list_len = len(ep_list)
        show_dict = (ep_list.pop(0) if ep_list else {})
        self.last_success = (ep_list.pop() if ep_list else None)
        db_ver = (ep_list.pop(0) if ep_list else None)
        self.last_update = (ep_list.pop() if ep_list else self.last_success)
        self.old_tznames = (ep_list.pop(0) if ep_list else '')
        if not db_ver or not self.last_success:
            if self.RESET:
                log("### starting without prior data (DB RESET requested)", level=1)
            elif ep_list_len:
                log("### ignoring bogus %s file" % NEXTAIRED_DB, level=1)
            else:
                log("### no prior data found", level=1)
            show_dict = {}
            self.last_success = self.last_update = 0
        elif db_ver < MAIN_DB_VER:
            self.upgrade_data_format(show_dict, db_ver)
        elif db_ver > MAIN_DB_VER:
            self.close("ERROR: DB version is too new for this script (%d > %d) -- exiting" % (db_ver, MAIN_DB_VER))

        self.RESET = False # Make sure we don't honor this multiple times.

        return (show_dict, self.now - self.last_update)

    def save_data(self, show_dict):
        self.save_file([show_dict, MAIN_DB_VER, self.tznames, self.last_update, self.last_success], NEXTAIRED_DB)

    def set_update_lock(self, DIALOG_PROGRESS = None):
        if DIALOG_PROGRESS:
            self.WINDOW.setProperty("NextAired.user_lock", str(self.now))
        else:
            self.WINDOW.setProperty("NextAired.bgnd_status", "0|0|...")
            self.WINDOW.setProperty("NextAired.bgnd_lock", str(self.now))

    def clear_update_lock(self, DIALOG_PROGRESS = None):
        if DIALOG_PROGRESS:
            DIALOG_PROGRESS.close()
            self.WINDOW.clearProperty("NextAired.user_lock")
        else:
            self.WINDOW.clearProperty("NextAired.bgnd_lock")
            xbmc.sleep(1000)
            self.WINDOW.clearProperty("NextAired.bgnd_status")

    def update_data(self, update_after_seconds, force_show = None):
        self.nextlist = []
        show_dict, elapsed_secs = self.load_data()

        # This should prevent the background and user code from updating the DB at the same time.
        if self.SILENT != "":
            DIALOG_PROGRESS = None
            # We double-check this here, just in case it changed.
            if self.is_time_for_update(update_after_seconds):
                self.set_update_lock()
                locked_for_update = True
                xbmc.sleep(2000) # try to avoid a race-condition
                # Background updating: we will just skip our update if the user is doing an update.
                user_lock = self.WINDOW.getProperty("NextAired.user_lock")
                if user_lock != "":
                    if self.now - float(user_lock) <= 10*60:
                        self.clear_update_lock()
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
            self.set_update_lock(DIALOG_PROGRESS)
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
                        self.clear_update_lock(DIALOG_PROGRESS)
                        xbmcgui.Dialog().ok(__language__(32103),__language__(32104))
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
                    self.clear_update_lock(DIALOG_PROGRESS)
                    locked_for_update = False
            socket.setdefaulttimeout(10)
        else:
            locked_for_update = False

        if locked_for_update:
            log("### starting data update", level=1)
            self.last_failure = 0
            # If the local timezone changed, we will need to recompute the Airtime values.
            if self.tznames != self.old_tznames:
                for tid, show in show_dict.iteritems():
                    show['show_changed'] = 1
            # We want to recreate our country DB every week.
            if len(self.country_dict) < 500 or self.now - self.country_last_update >= 7*24*60*60:
                try:
                    log("### grabbing a new country mapping list", level=1)
                    if self.SILENT == "":
                        DIALOG_PROGRESS.update(0, __language__(32102), "country.db")
                    self.country_dict = CountryLookup().get_country_dict()
                    self.save_file([self.country_dict, COUNTRY_DB_VER, self.now], COUNTRY_DB)
                except:
                    pass
            tvdb = TheTVDB('1D62F2F90030C444', 'en', want_raw = True)
            if force_show is None:
                # This typically asks TheTVDB for an update-zip file and tweaks the show_dict to note needed updates.
                tv_up = tvdb_updater(tvdb)
                need_full_scan, got_update = tv_up.note_updates(show_dict, elapsed_secs)
                if need_full_scan or got_update:
                    self.last_update = self.now
                elif not got_update:
                    self.set_last_failure()
                    self.max_fetch_failures = 0
                tv_up = None
            else:
                need_full_scan = False
            art_rescan_after = 24*60*60 - 5*60
        else:
            tvdb = None # We don't use this unless we're locked for the update.
            need_full_scan = False
            # A max-fetch of 0 disables all updating.
            self.max_fetch_failures = 0
            art_rescan_after = 0
        art_rescan_type = LISTITEM_ART[int(__addon__.getSetting("ThumbType"))]

        title_dict = {}
        for tid, show in show_dict.iteritems():
            show['unused'] = True
            title_dict[show['localname']] = tid

        if force_show is not None and force_show in title_dict:
            show = show_dict[title_dict[force_show]]
            show['show_changed'] = 1
            show['eps_changed'] = (1, 0)

        TVlist = self.listing()
        total_show = len(TVlist)
        if total_show == 0:
            if locked_for_update:
                self.clear_update_lock(DIALOG_PROGRESS)
            self.set_last_failure()
            return False

        count = 0
        user_canceled = False
        id_re = re.compile(r"http%3a%2f%2fthetvdb\.com%2f[^']+%2f([0-9]+)-")
        for show in TVlist:
            count += 1
            name = show[0]
            if force_show is not None and name != force_show:
                continue
            art = show[2]
            premiered_year = show[6][:4] if show[6] != '' else None
            percent = int(float(count * 100) / total_show)
            if self.SILENT != "":
                self.WINDOW.setProperty("NextAired.bgnd_status", "%f|%d|%s" % (time(), percent, name))
            elif locked_for_update and self.max_fetch_failures > 0:
                DIALOG_PROGRESS.update(percent, __language__(32102), name)
                if DIALOG_PROGRESS.iscanceled():
                    DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok(__language__(32103),__language__(32104))
                    user_canceled = True
                    self.set_last_failure()
                    self.max_fetch_failures = 0
            log("### TVlist #%s = %s" % (show[5], name), level=(3 if locked_for_update else 10))
            current_show = {
                    "localname": name,
                    "path": show[1],
                    "art": {},
                    "dbid": show[3],
                    "thumbnail": show[4],
                    }
            # Try to figure out what the tvdb number is by using the art URLs and the imdbnumber value
            m2 = id_re.search(str(art))
            m2_num = int(m2.group(1)) if m2 else 0
            m4 = id_re.search(show[4])
            m4_num = int(m4.group(1)) if m4 else 0
            m5 = INT_REGEX.match(show[5])
            m5_num = int(m5.group(1)) if m5 else 0
            if m5_num and (m2_num == m5_num or m4_num == m5_num):
                # Most shows will be in agreement on the id when the scraper is using thetvdb.
                tid = m5_num
            else:
                old_id = title_dict.get(name, 0)
                old_data = show_dict.get(m5_num, None) if m5_num else None
                if old_id and old_id == m5_num:
                    tid = m5_num
                elif old_data and current_show['path'] == old_data['path']:
                    # This handles a localname change where we knew what the ID was before -- keep that info.
                    tid = m5_num
                elif old_id and (m2_num == old_id or m4_num == old_id):
                    tid = old_id
                elif m2_num and m2_num == m4_num:
                    # This will override the old_id value if both artwork URLs change.
                    tid = m2_num
                elif old_id and force_show is None:
                    # This is an "iffy" ID.  We'll keep using it unless the user asked for a fresh start.
                    tid = old_id
                else:
                    if self.max_fetch_failures <= 0:
                        continue
                    tid = self.find_show_id(tvdb, name, m5_num, premiered_year)
                    if tid == 0:
                        continue

            prior_data = show_dict.get(tid, None)
            if prior_data:
                if 'unused' not in prior_data:
                    continue # How'd we get a duplicate?? Skip it...
                del prior_data['unused']
                self.age_episodes(prior_data)

            for art_type in USEFUL_ART:
                xart = art.get(art_type, None)
                fudged_flag = 'fudged.' + art_type
                if not xart:
                    if prior_data and fudged_flag in prior_data['art']:
                        xart = prior_data['art'][art_type]
                    elif art_rescan_type != art_type:
                        continue
                    else:
                        scan_ndx = 'last_%s_scan' % art_type
                        last_scan = prior_data['art'].get(scan_ndx, 0) if prior_data else 0
                        if not art_rescan_after or self.now < last_scan + art_rescan_after:
                            if last_scan:
                                current_show['art'][scan_ndx] = last_scan
                            continue
                        try:
                            xart = FanartTV.find_artwork(tid, art_type)
                        except:
                            pass
                        if xart:
                            log("### found missing %s for %s" % (art_type, name), level=1)
                        else:
                            log("### still missing a %s for %s" % (art_type, name), level=2)
                            current_show['art'][scan_ndx] = self.now
                            continue
                    try:
                        img_re = re.compile(r"^image:")
                        if not img_re.match(xart):
                            xart = "image://%s/" % urllib.quote(xart, '')
                    except:
                        pass
                    current_show['art'][fudged_flag] = True
                current_show['art'][art_type] = xart

            if self.max_fetch_failures > 0:
                tid = self.check_show_info(tvdb, tid, current_show, prior_data)
            else:
                tid = -tid
            if tid < 0:
                if not prior_data:
                    continue
                for item in prior_data:
                    if item not in current_show:
                        current_show[item] = prior_data[item]
                tid = -tid
            elif prior_data and 'tvrage' in prior_data:
                current_show['tvrage'] = prior_data['tvrage']
            log("### %s" % current_show)
            show_dict[tid] = current_show

        # If we did a lot of work, make sure we save it prior to doing anything else.
        # This ensures that a bug in the following code won't make us redo everything.
        if need_full_scan and locked_for_update:
            self.save_data(show_dict)

        if show_dict:
            log("### data available", level=5)
            remove_list = []
            for tid, show in show_dict.iteritems():
                if 'unused' in show:
                    if force_show is None:
                        remove_list.append(tid)
                        continue
                    del show['unused']
                if show['ep_ndx']:
                    self.nextlist.append(show)
            for tid in remove_list:
                log('### Removing obsolete show %s' % show_dict[tid]['localname'], level=2)
                del show_dict[tid]
            self.nextlist.sort(key=lambda x: (x['episodes'][x['ep_ndx']]['aired'], x['Show Name']))
            log("### next list: %s shows ### %s" % (len(self.nextlist), self.nextlist), level=7)
            self.check_today_show()
            self.push_data()
        else:
            log("### no current show data...", level=5)

        if locked_for_update:
            if not self.last_failure and force_show is None:
                self.last_success = self.now
            self.save_data(show_dict)
            log("### data update finished", level=1)

            self.clear_update_lock(DIALOG_PROGRESS)
            if self.SILENT == "" and self.last_failure and not user_canceled:
                xbmcgui.Dialog().ok(__language__(32105), __language__(32106))

        self.FORCEUPDATE = False
        return not self.last_failure

    def age_episodes(self, show):
        episodes = show['episodes']
        ep_len = len(episodes)
        ep_ndx = show['ep_ndx']
        if ep_ndx == 0: # 0 indicates no future episodes, so point past the end of the list.
            ep_ndx = ep_len
        # Start by finding the spot (if any) in the list where future episodes start.
        while ep_ndx < ep_len and episodes[ep_ndx]['aired'][:10] < self.datestr:
            ep_ndx += 1
        # Next we remove episodes older than yesterday, but keep one prior ep that is older than that.
        while ep_ndx > 1 and episodes[1]['aired'][:10] < self.yesterstr:
            episodes.pop(0)
            ep_len -= 1
            ep_ndx -= 1
        # Make a note of the index of the first upcoming episode or 0 if there are none.
        show['ep_ndx'] = (ep_ndx if ep_ndx < ep_len else 0)

    def check_xbmc_version(self):
        # retrieve current installed version
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        log("### %s" % json_response)
        try:
            self.xbmc_version = json_response['result']['version']['major']
        except:
            self.xbmc_version = 12

        self.videodb = 'videodb://tvshows/titles/' if self.xbmc_version >= 13 else 'videodb://2/2/'

    def handle_bg_version_change(self, latest_version):
        log("### NextAired version changed from %s to %s -- starting a replacement background proc" % (__version__, latest_version), level=1)
        # Delay a bit, just to be sure that it is ready to run.
        for cnt in range(15):
            if xbmc.abortRequested:
                sys.exit()
            xbmc.sleep(1000)
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.ExecuteAddon", "params": {"addonid": "script.tv.show.next.aired", "params": %s}, "id": 0}' % json.dumps(self.params))
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        log("### %s" % json_response)
        self.close("stopping this older background proc")

    def listing(self):
        failures = 0
        # If the computer is waking up from a sleep, this call might fail for a little bit.
        while not xbmc.abortRequested:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "file", "thumbnail", "art", "imdbnumber", "premiered"], "sort": { "method": "title" } }, "id": 1}')
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = json.loads(json_query)
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
            TVlist.append((tvshowname, path, art, dbid, thumbnail, item['imdbnumber'], item['premiered']))
        log("### list: %s" % TVlist)
        return TVlist

    @staticmethod
    def find_show_id(tvdb, show_name, maybe_id, want_year = None, strip_year = True):
        log("### find_show_id(%s, %s, %s, %s)" % (show_name, maybe_id, want_year, strip_year), level=2)
        year_re = re.compile(r" \((\d\d\d\d)\)")
        cntry_re = re.compile(r" \(([a-z][a-z])\)$", re.IGNORECASE)
        lc_name = lc_stripped_name(show_name)
        want_names = [ lc_name ]
        removed_year = False
        name_has_year = year_re.search(show_name)
        if want_year:
            want_year = str(want_year)
        if strip_year and name_has_year:
            want_year = name_has_year.group(1)
            show_name = year_re.sub('', show_name)
            lc_name = year_re.sub('', lc_name)
            want_names.append(lc_name) # Add (stripped-year) "Show"
            removed_year = True
            name_has_year = False
        if want_year and not name_has_year and not removed_year:
            want_names.insert(0, "%s (%s)" % (lc_name, want_year)) # Add "Show (1999)"
        cntry_match = cntry_re.search(lc_name)
        if cntry_match:
            alt_name = cntry_re.sub(' ' + cntry_match.group(1), lc_name)
            want_names.append(alt_name) # Since we have "Show (XX)", add "Show XX"
            if want_year and not name_has_year:
                want_names.insert(1, "%s (%s)" % (alt_name, want_year)) # Add "Show XX (1999)"
                alt_name = cntry_re.sub(" (%s) (%s)" % (want_year, cntry_match.group(1)), lc_name)
                if want_names[0] != alt_name:
                    want_names.insert(1, alt_name) # Add "Show (1999) (XX)"
                else:
                    want_names.insert(1, "%s (%s)" % (lc_name, want_year)) # Add "Show (XX) (1999)"

        log("### want_names: %s" % want_names, level=6)
        log("### want_year: %s" % want_year, level=6)

        try:
            show_list = tvdb.get_matching_shows(show_name, language='all', want_raw=True)
        except Exception, e:
            log('### ERROR returned by get_matching_shows(): %s' % e, level=0)
            return 0

        if show_list:
            for attrs in show_list:
                attrs['SeriesName'] = lc_stripped_name(normalize(attrs, 'SeriesName'))
                log("### id: %s, FirstAired: %s, SeriesName: %s" % (attrs['id'], attrs.get('FirstAired', '????')[:4], attrs['SeriesName']), level=6)
                if int(attrs['id']) == maybe_id:
                    log("### verified id of %s" % maybe_id, level=2)
                    return maybe_id
            for want_name in want_names:
                for attrs in show_list:
                    match_names = [ attrs['SeriesName'] ]
                    if 'AliasNames' in attrs:
                        for alias in normalize(attrs, 'AliasNames').split('|'):
                            match_names.append(lc_stripped_name(alias))
                    year = attrs.get('FirstAired', '')[:4]
                    if want_year and year != want_year:
                        continue
                    for j in range(len(match_names)):
                        mname = match_names[j]
                        if len(year) == 4 and not year_re.search(mname):
                            match_names.append("%s (%s)" % (mname, year))
                            m = cntry_re.search(mname)
                            if m:
                                match_names.append(cntry_re.sub(" (%s) (%s)" % (year, m.group(1)), mname))
                    log("### match_names: %s" % match_names, level=6)
                    if want_name in match_names:
                        log("### found id of %s" % attrs['id'], level=2)
                        return int(attrs['id'])

        if len(show_list) == 0 and cntry_re.search(show_name):
            return find_show_id(tvdb, cntry_re.sub('', show_name), maybe_id, want_year)

        if removed_year and len(show_list) >= 25:
            return find_show_id(tvdb, "%s (%s)" % (show_name, want_year), maybe_id, want_year, False)

        log("### no match found", level=2)
        return 0

    def check_show_info(self, tvdb, tid, current_show, prior_data):
        name = current_show['localname']
        log("### check if %s is up-to-date (%d)" % (name, tid), level=4)
        # If the prior_data isn't in need of an update, use it unchanged.
        if prior_data:
            earliest_id, eps_last_updated = prior_data.get('eps_changed', (None, 0))
            if earliest_id is None:
                eps_last_updated = prior_data['eps_last_updated']
            show_changed = prior_data.get('show_changed', 0)
            if prior_data['Country'] == 'Unknown' and self.country_dict.get(prior_data['Network'], None):
                log("### Forcing show-change for %s to fix unknown country" % name, level=2)
                show_changed = 1
            if show_changed:
                if earliest_id is None:
                    earliest_id = 0
            elif earliest_id is None:
                log("### no changes needed", level=5)
                return -tid
        else:
            show_changed = 0
            earliest_id = 1
            eps_last_updated = 0

        if earliest_id != 0:
            for cnt in range(2):
                log("### getting series & episode info for #%d - %s" % (tid, name), level=1)
                try:
                    result = tvdb.get_show_and_episodes(tid)
                    break
                except Exception, e:
                    log('### ERROR returned by get_show_and_episodes(): %s' % e, level=0)
                    self.set_last_failure()
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
                    self.set_last_failure()
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
        tzone = CountryLookup.get_country_timezone(country)
        if tzone is None:
            tzone = 'UTC'
        try:
            tzinfo = tz.gettz(tzone)
        except:
            tzinfo = tz.tzutc()
        try:
            airtime = TheTVDB.convert_time(show.get('Airs_Time', ""))
        except:
            airtime = None
        if airtime is not None:
            hh_mm = airtime.strftime('%H:%M')
            dt = datetime.combine(self.date, airtime).replace(tzinfo=tzinfo).astimezone(tz.tzlocal())
            early_aired = '1900-01-01T' + dt.strftime('%H:%M:%S%z')
        else:
            hh_mm = ''
            airtime = TheTVDB.convert_time('00:00')
            early_aired = '1900-01-01T00:00:00+0000'

        current_show['Show Name'] = normalize(show, 'SeriesName')
        first_aired = show.get('FirstAired', None)
        if first_aired:
            first_aired = TheTVDB.convert_date(first_aired)
            current_show['Premiered'] = first_aired.year
            current_show['Started'] = first_aired.isoformat()
        else:
            current_show['Premiered'] = current_show['Started'] = ""
        current_show['Country'] = country
        current_show['TZ'] = tzone
        current_show['Status'] = normalize(show, 'Status')
        current_show['Genres'] = normalize(show, 'Genre').strip('|').replace('|', ' | ')
        current_show['Network'] = network
        current_show['Airtime'] = hh_mm
        current_show['Runtime'] = maybe_int(show, 'Runtime', '')

        can_re = re.compile(r"canceled|ended", re.IGNORECASE)
        if can_re.search(current_show['Status']):
            current_show['canceled'] = True
        elif 'canceled' in current_show:
            del current_show['canceled']

        # Let's assume we need a "None" episode -- it will get cleaned if we don't.
        # The early_aired value has an accurate tzlocal time in it just in case it is
        # the only item in the list ('aired' is where localized Airtime comes from).
        episode_list = [ {'name': None, 'aired': early_aired, 'sn': 0, 'en': 0} ]
        if episodes is not None:
            max_eps_utime = 0
            if episodes:
                for ep in episodes:
                    last_updated = maybe_int(ep, 'lastupdated')
                    if last_updated > max_eps_utime:
                        max_eps_utime = last_updated
                    first_aired = TheTVDB.convert_date(ep.get('FirstAired', ""))
                    if not first_aired:
                        continue
                    dt = datetime.combine(first_aired, airtime).replace(tzinfo=tzinfo)
                    if hh_mm != '':
                        dt = dt.astimezone(tz.tzlocal())
                    got_ep = {
                            'name': normalize(ep, 'EpisodeName'),
                            'sn': maybe_int(ep, 'SeasonNumber'),
                            'en': maybe_int(ep, 'EpisodeNumber'),
                            'date': str(first_aired), # We never use this for "today" comparisons!
                            'aired': dt.isoformat(),
                            'wday': dt.weekday(),
                            }
                    episode_list.append(got_ep)
                episodes = None
                episode_list.sort(key=itemgetter('aired', 'sn', 'en'))
            current_show['ep_ndx'] = 1
            current_show['episodes'] = episode_list
            self.age_episodes(current_show)
        elif prior_data:
            max_eps_utime = eps_last_updated
            current_show['ep_ndx'] = prior_data['ep_ndx']
            current_show['episodes'] = prior_data['episodes']
            if current_show['Airtime'] != prior_data['Airtime'] or current_show['TZ'] != prior_data['TZ']:
                for ep in current_show['episodes']:
                    if ep['name'] is None:
                        ep['aired'] = early_aired
                        continue
                    first_aired = TheTVDB.convert_date(ep['date'])
                    dt = datetime.combine(first_aired, airtime).replace(tzinfo=tzinfo)
                    if hh_mm != '':
                        dt = dt.astimezone(tz.tzlocal())
                    ep['aired'] = dt.isoformat(),
                    ep['wday'] = dt.weekday(),
        else:
            max_eps_utime = 0
            current_show['ep_ndx'] = 0
            current_show['episodes'] = episode_list

        last_updated = maybe_int(show, 'lastupdated')
        if prior_data:
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
        daymap = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
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
            if from_ver < 4:
                if 'RFC3339' in show:
                    del show['RFC3339']
                show['ep_ndx'] = (1 if len(show['episodes']) >= 1 else 0)
                ep0 = show['episodes'][0]
                if ep0['id'] is None:
                    ep0['name'] = None
                    ep0['aired'] = '0000-00-00T00:00:00+00:00'
                    ep0['sn'] = ep0['en'] = 0
            if from_ver < 5:
                show['TZ'] = ''
                show['show_changed'] = 1
                show['eps_changed'] = (1, 0)
            for ep in show['episodes']:
                if from_ver < 3 and 'wday' in ep:
                    # Convert wday from a string to an index:
                    ep['wday'] = daymap[ep['wday']]
                if from_ver < 4:
                    if 'number' in ep:
                        nums = ep['number'].split('x')
                        ep['sn'] = int(nums[0])
                        ep['en'] = int(nums[1])
                        del ep['number']
                    del ep['id']
                if from_ver < 5:
                    ep['date'] = ep['aired'][:10] # not strictly true, but good enough for now.

    def set_episode_info(self, label, prefix, when, ep):
        if ep and ep['name'] is not None:
            name = ep['name']
            season_num = '%02d' % ep['sn']
            episode_num = '%02d' % ep['en']
            number = season_num + 'x' + episode_num
            aired = TheTVDB.convert_date(ep['aired'][:10])
            if aired is not None:
                nice_aired = self.nice_date(aired, 'DropThisYear')
                aired = nice_aired if self.improve_dates else aired.strftime(DATE_FORMAT)
            else:
                aired = nice_aired = ""
        else:
            name = season_num = episode_num = number = aired = nice_aired = ''

        label.setProperty(prefix + when + 'Date', aired)
        label.setProperty(prefix + when + 'Day', nice_aired)
        label.setProperty(prefix + when + 'Title', name)
        label.setProperty(prefix + when + 'Number', number)
        label.setProperty(prefix + when + 'SeasonNumber', season_num)
        label.setProperty(prefix + when + 'EpisodeNumber', episode_num)

    def check_today_show(self):
        self.set_today()
        self.todayshow = 0
        self.todaylist = []
        log("### %s" % self.datestr)
        for show in self.nextlist:
            name = show["localname"]
            when = show['episodes'][show['ep_ndx']]['aired']
            log("################")
            log("### %s" % name)
            if when[:10] == self.datestr:
                self.todayshow += 1
                self.todaylist.append(name)
                log("### TODAY")
            log("### %s" % when)
        log("### today show: %s - %s" % (self.todayshow, str(self.todaylist).strip("[]")))

    # The style setting only affects "nice" dates, not the historic format.
    def str_date(self, d, style=None):
        if d is None:
            return ''
        return self.nice_date(d, style) if self.improve_dates else d.strftime(DATE_FORMAT)

    # Specify style DropThisYear, DropYear, or Short (or omit for the full info).
    def nice_date(self, d, style=None):
        tt = d.timetuple()
        if style == 'Short':
            fmt = NICE_SHORT_DATE
        elif style == 'DropYear' or (style == 'DropThisYear' and tt[0] == self.date.year):
            fmt = NICE_DATE_NO_YEAR
        else:
            fmt = NICE_DATE_FORMAT
        d = fmt % {'year': tt[0], 'mm': tt[1], 'month': self.local_months[tt[1]-1], 'day': tt[2], 'wday': self.wdays[tt[6]], 'unk': '??'}
        return d

    @staticmethod
    def get_list(listname):
        path = os.path.join(__datapath__, listname)
        if xbmcvfs.exists(path):
            log("### Load list: %s" % path)
            return NextAired.load_file(path)
        else:
            log("### Load list: %s not found!" % path)
            return []

    @staticmethod
    def load_file(file_path):
        try:
            return eval(file(file_path, "r").read())
        except:
            print_exc()
            log("### ERROR could not load file %s" % file_path, level=0)
            return []

    @staticmethod
    def save_file(txt, filename):
        path = os.path.join(__datapath__, filename)
        try:
            if txt:
                file(path, "w").write(repr(txt))
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
        # Set the counts to 0 during the time that we're clearing and re-setting the data.
        self.WINDOW.setProperty("NextAired.Total", "0")
        self.WINDOW.setProperty("NextAired.TodayTotal", "0")
        self.WINDOW.setProperty("NextAired.TodayShow", str(self.todaylist).strip("[]"))
        for count in range(oldTotal):
            prefix = "NextAired.%d." % (count+1)
            for prop in ("AirTime", "Airday", "Art(banner)", "Art(characterart)", "Art(clearart)", "Art(clearlogo)", "Art(fanart)", "Art(landscape)", "Art(poster)", "Classification", "Country", "Fanart", "Genre", "Label", "LatestDate", "LatestDay", "LatestEpisodeNumber", "LatestNumber", "LatestSeasonNumber", "LatestTitle", "Library", "Network", "NextDate", "NextDay", "NextEpisodeNumber", "NextNumber", "NextSeasonNumber", "NextTitle", "Path", "Premiered", "Runtime", "ShortTime", "Started", "Status", "StatusID", "Thumb", "Today"):
                self.WINDOW.clearProperty(prefix + prop)
        self.count = 0
        all_days = __addon__.getSetting("ShowAllTVShowsOnHome") == 'true'
        for current_show in self.nextlist:
            if all_days or current_show['episodes'][current_show['ep_ndx']]['aired'][:10] == self.datestr:
                self.count += 1
                self.set_labels('windowpropertytoday', current_show)
        self.WINDOW.setProperty("NextAired.Total", str(len(self.nextlist)))
        self.WINDOW.setProperty("NextAired.TodayTotal", str(self.todayshow))

    def show_gui(self):
        try:
            update_after = int(__addon__.getSetting('update_after'))*60*60 # hours -> seconds
        except:
            update_after = 0
        self.update_data(update_after)
        weekday = self.date.weekday()
        self.WINDOW.setProperty("NextAired.Today", xbmc.getLocalizedString(33006))
        self.WINDOW.setProperty("NextAired.Tomorrow", xbmc.getLocalizedString(33007))
        self.WINDOW.setProperty("NextAired.Yesterday", __addon__.getLocalizedString(32018))
        self.WINDOW.setProperty("NextAired.TodayDate", self.str_date(self.date, 'DropYear'))
        self.WINDOW.setProperty("NextAired.TomorrowDate", self.str_date(self.tomorrow, 'DropThisYear'))
        self.WINDOW.setProperty("NextAired.YesterdayDate", self.str_date(self.yesterday, 'DropThisYear'))
        for count in range(0, 7):
            wdate = self.date
            if count != weekday:
                wdate += timedelta(days = (count - weekday + 7) % 7)
            self.WINDOW.setProperty("NextAired.%d.Date" % (count + 1), self.str_date(wdate, 'DropThisYear'))
        import next_aired_dialog
        TodayStyle = __addon__.getSetting("TodayStyle") == 'true'
        ScanDays = int(__addon__.getSetting("ScanDays2" if TodayStyle else "ScanDays"))
        WantYesterday = __addon__.getSetting("WantYesterday") == 'true'
        next_aired_dialog.MyDialog(self.nextlist, self.set_labels, self.nice_date, ScanDays, TodayStyle, WantYesterday)

    def run_backend(self):
        self._stop = False
        self.previousitem = ''
        show_dict, elapsed_secs = self.load_data()
        if not show_dict:
            self._stop = True
        while not self._stop:
            self.selecteditem = normalize(xbmc.getInfoLabel("ListItem.TVShowTitle"))
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

    def return_properties(self, tvshowtitle):
        show_dict, elapsed_secs = self.load_data()
        log("### return_properties started", level=2)
        if show_dict:
            self.WINDOW.clearProperty("NextAired.Label")
            for tid, item in show_dict.iteritems():
                if tvshowtitle == item["localname"]:
                    self.set_labels('windowproperty', item)
                    break

    def update_show(self, tvshowtitle):
        log("### update_show started", level=2)
        self.FORCEUPDATE = True
        self.update_data(1, tvshowtitle)

    def set_labels(self, infolabel, item, want_ep_ndx = None):
        art = item["art"]
        must_have = None
        if infolabel == 'listitem':
            label = xbmcgui.ListItem()
            prefix = ''
            label.setLabel(item["localname"])
            label.setThumbnailImage(item.get("thumbnail", ""))
            try:
                must_have = LISTITEM_ART[int(__addon__.getSetting("ThumbType"))]
            except:
                pass
        else:
            label = xbmcgui.Window(10000)
            if infolabel == "windowproperty":
                prefix = 'NextAired.'
            elif infolabel == "windowpropertytoday":
                prefix = 'NextAired.' + str(self.count) + '.'
                label.setProperty("NextAired.ShowAllTVShows", __addon__.getSetting("ShowAllTVShowsOnHome"))
            else:
                return # Impossible...
            label.setProperty(prefix + "Label", item["localname"])
            label.setProperty(prefix + "Thumb", item.get("thumbnail", ""))

        if want_ep_ndx is not None:
            next_ep = item['episodes'][want_ep_ndx]
            latest_ep = item['episodes'][want_ep_ndx-1] if want_ep_ndx else None
            airdays = [ next_ep['wday'] ]
        else:
            ep_ndx = item['ep_ndx']
            next_ep = item['episodes'][ep_ndx] if ep_ndx >= 1 else None
            latest_ep = item['episodes'][ep_ndx-1] # Note that 0-1 gives us the last item in the array -- nice!
            airdays = []
            if ep_ndx >= 1:
                date_limit = (TheTVDB.convert_date(item['episodes'][ep_ndx]['aired'][:10]) + timedelta(days=6)).isoformat()
                for ep in item['episodes'][ep_ndx:]:
                    if ep['aired'][:10] > date_limit:
                        break
                    if not airdays or ep['wday'] != airdays[-1]:
                        airdays.append(ep['wday'])
        airdays.sort()
        airdays = ', ' . join([self.weekdays[wday] for wday in airdays])

        is_today = 'True' if next_ep and next_ep['aired'][:10] == self.datestr else 'False'

        started = TheTVDB.convert_date(item["Started"])
        if item["Airtime"] == '':
            airtime = ''
        else:
            ndx = item['ep_ndx'] if item['ep_ndx'] else -1
            airtime = item['episodes'][ndx]['aired'][11:16]
            if self.ampm:
                airtime = TheTVDB.convert_time(airtime).strftime('%I:%M %p')

        status = item.get("Status", "")
        if status == 'Continuing':
            ep = next_ep if next_ep else latest_ep if latest_ep else None
            if not ep or ep['name'] is None or ep['sn'] == 1:
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

        m = CLASSIFICATION_REGEX.search(item.get("Genres", ""))
        classification = m.group(1) if m else 'Scripted'

        label.setProperty(prefix + "AirTime", airdays + ": " + airtime if airdays != "" else airtime)
        label.setProperty(prefix + "Path", item.get("path", ""))
        label.setProperty(prefix + "Library", item.get("dbid", ""))
        label.setProperty(prefix + "Status", status)
        label.setProperty(prefix + "StatusID", status_id)
        label.setProperty(prefix + "Network", item.get("Network", ""))
        label.setProperty(prefix + "Started", self.str_date(started))
        label.setProperty(prefix + "Classification", classification)
        label.setProperty(prefix + "Genre", item.get("Genres", ""))
        label.setProperty(prefix + "Premiered", str(item.get("Premiered", "")))
        label.setProperty(prefix + "Country", item.get("Country", ""))
        label.setProperty(prefix + "Runtime", str(item.get("Runtime", "")))
        # Keep old fanart property for backwards compatibility
        label.setProperty(prefix + "Fanart", art.get("fanart", ""))
        # New art properties
        for art_type in ('fanart', 'poster', 'banner', 'landscape', 'clearlogo', 'characterart', 'clearart'):
            art_url = art.get(art_type, "")
            if must_have and art_url == "" and art_type == must_have:
                try:
                    url = "http://opencoder.net/next-aired-missing/" + art_type + "/" + urllib.quote(item["localname"])
                    art_url = "image://%s.png/" % urllib.quote(url, '')
                except:
                    pass
            label.setProperty("%sArt(%s)" % (prefix, art_type), art_url)
        label.setProperty(prefix + "Today", is_today)
        label.setProperty(prefix + "AirDay", airdays)
        label.setProperty(prefix + "ShortTime", airtime)

        # This sets NextDate, NextTitle, etc.
        self.set_episode_info(label, prefix, 'Next', next_ep)
        # This sets LatestDate, LatestTitle, etc.
        self.set_episode_info(label, prefix, 'Latest', latest_ep)

        if infolabel == 'listitem':
            return label

    def close(self, msg):
        log("### %s" % msg, level=1)
        sys.exit()

class tvdb_updater:
    def __init__(self, tvdb):
        self.tvdb = tvdb
        self.bad_episode_info = False

    def note_updates(self, show_dict, elapsed_update_secs):
        self.show_dict = show_dict

        if elapsed_update_secs < 24*60*60:
            period = 'day'
        elif elapsed_update_secs < 7*24*60*60:
            period = 'week'
        elif elapsed_update_secs < 30*24*60*60:
            period = 'month'
            # My testing showed that the month file was missing some episode changes, so
            # we'll assume that any series change indicates we should check the episodes.
            self.bad_episode_info = True
        else:
            # Flag all shows as needing new data.  We include canceled shows because
            # they sometimes have new info (or may have become non-canceled).
            for tid, show in show_dict.iteritems():
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
            if self.bad_episode_info:
                show['eps_changed'] = (1, 0)
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

if (__name__ == "__main__"):
    NextAired()

# vim: sw=4 ts=8 et

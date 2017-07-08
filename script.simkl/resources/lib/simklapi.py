#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys, os, time
#import urllib
#import request
import json

import xbmc
import interface
import httplib
import utils

from socket import gaierror

__addon__ = interface.__addon__
def getstr(strid): return interface.getstr(strid)

REDIRECT_URI = "http://simkl.com"
USERFILE     = os.path.join(xbmc.translatePath(__addon__.getAddonInfo("profile")).decode("utf-8"), "simkl_key")
xbmc.translatePath("special://profile/simkl_key")

if not os.path.exists(USERFILE):
    os.mkdir(os.path.dirname(USERFILE))
    with open(USERFILE, "w+") as f:
        f.write("")
else:
    with open(USERFILE, "r") as f:
        xbmc.log("Simkl: Userfile " + str(f.read()))

APIFILE = os.path.join(os.path.dirname(os.path.realpath(__file__)).strip("lib"), "data", "apikey")
xbmc.log("Simkl: APIFILE: {0}".format(APIFILE))
with open(APIFILE, "r") as f:
    rd = f.read()
    d = json.loads(rd)
    APIKEY = d["apikey"]
    SECRET = d["secret"]
    xbmc.log("Simkl: {0}".format(rd))
    xbmc.log("Simkl: APIKEY: {0}".format(APIKEY))
ATOKEN = 0 #Get atoken from file
headers = {"Content-Type": "application-json",
    "simkl-api-key": APIKEY}

class API:
    def __init__(self):
        self.scrobbled_dict = {} #So it doesn't scrobble 5 times the same chapter
        #{"Label":expiration_time}
        with open(USERFILE, "r") as f:
            self.token = f.readline().strip("\n")
            headers["authorization"] = "Bearer " + self.token
        try:
            self.get_usersettings()
            self.internet = True
            #if not os.path.exists(USERFILE):
            #    api.login()
        except gaierror:
            xbmc.log("Simkl: {0}".format("No INTERNET"))
            #interface.notify(getstr(32027))
            self.internet = False

    def get_usersettings(self):
        self.con = httplib.HTTPSConnection("api.simkl.com")
        self.con.request("GET", "/users/settings", headers=headers)
        r = self.con.getresponse().read().decode("utf-8")
        xbmc.log("Simkl: get_usersettings: %s" %r)
        self.USERSETTINGS = json.loads(r)
        xbmc.log("Simkl: Usersettings: " + str(self.USERSETTINGS))

    def login(self):
        utils.systemLock("SimklTrackerRunLogin")
        url = "/oauth/pin?client_id="
        url += APIKEY + "&redirect=" + REDIRECT_URI

        log = httplib.HTTPSConnection("api.simkl.com")
        log.request("GET", url, headers=headers)
        r = log.getresponse().read().decode("utf-8")
        xbmc.log(r)
        rdic = json.loads(r)
        #interface.loginDialog(rdic["verification_url"],
        #  rdic["user_code"], self.check_login, log, rdic["expires_in"],
        #  rdic["interval"], self)

        pin = rdic["user_code"]
        url = rdic["verification_url"]
        exp = int(rdic["expires_in"])
        ntv = int(rdic["interval"])

        self.logindialog = interface.loginDialog("simkl-LoginDialog.xml",
            __addon__.getAddonInfo("path"), pin=pin, url=url,
            check_login=self.check_login, log=log, exp=exp, inter=ntv, api=self)
        self.logindialog.doModal()
        del self.logindialog

    def set_atoken(self, token):
        global ATOKEN
        with open(USERFILE, "w") as f:
            f.write(token)
        ATOKEN = token
        headers["authorization"] = "Bearer "+token
        self.token = token

    def check_login(self, ucode, log): #Log is the connection
        url = "/oauth/pin/" + ucode + "?client_id=" + APIKEY
        log.request("GET", url, headers=headers)
        r = json.loads(log.getresponse().read().decode("utf-8"))
        xbmc.log("Simkl:" + str(r))
        if r["result"] == "OK":
            self.set_atoken(r["access_token"])
            log.request("GET", "/users/settings", headers=headers)
            r = json.loads(log.getresponse().read().decode("utf-8"))
            self.USERSETTINGS = r
            return True
        elif r["result"] == "KO":
            return False

    def is_user_logged(self):
        """ Checks if user is logged in """
        failed = False
        if self.internet == False: return False
        if "error" in self.USERSETTINGS.keys(): failed = self.USERSETTINGS["error"]
        if self.token == "" or failed == "user_token_failed":
            xbmc.log("Simkl: User not logged in")
            interface.login(0)
            return False
        else:
            #interface.login(self.USERSETTINGS["user"]["name"])
            interface.login(1)
            return True

    ### SCROBBLING OR CHECKIN
    def lock(self, fname, duration):
        xbmc.log("Duration: %s" %duration)
        exp = self.scrobbled_dict
        exp[fname] = int(time.time() + (105 - float(__addon__.getSetting("scr-pct"))) / 100 * duration)
        xbmc.log("Simkl: Locking {0}".format(exp))
        self.scrobbled_dict = {fname:exp[fname]} #So there is always only one entry on the dict

    def is_locked(self, fname):
        exp = self.scrobbled_dict
        if not (fname in exp.keys()): return 0
        xbmc.log("Time: {0}, exp: {1}, Dif: {2}".format(int(time.time()), exp[fname], int(exp[fname]-time.time())))
        #When Dif reaches 0, scrobble.
        if time.time() < exp[fname]:
            xbmc.log("Simkl: Can't scrobble, file locked (alredy scrobbled)")
            xbmc.log(str(exp))
            return 1
        else:
            del exp[fname]
            return 0

    def watched(self, item, duration, date=time.strftime('%Y-%m-%d %H:%M:%S'), cnt=0): #OR IDMB, member: only works with movies
        filename = item["file"].replace("\\", "/")
        if self.is_user_logged() and not self.is_locked(filename):
            try:
                con = httplib.HTTPSConnection("api.simkl.com")
                mediadict = {"movie": "movies", "episode":"shows", "show":"shows"}

                if item["imdbnumber"] != "":
                    if item["type"] == "movie": toappend = {"ids":{"imdb": item["imdbnumber"]}, "watched_at":date}
                    elif item["type"] == "episode":
                        toappend = {"ids":{"tvdb":item["imdbnumber"]}, "watched_at":date,
                        "seasons":[{
                            "number":item["season"],
                            "episodes":[{"number":item["episode"]}]}]}
                    media = mediadict[item["type"]]
                else:
                    xbmc.log("Simkl: Filename - {0}".format(filename))
                    values = json.dumps({"file":filename})
                    xbmc.log("Simkl: Query: {0}".format(values))
                    con.request("GET", "/search/file/", body=values, headers=headers)
                    r1 = con.getresponse().read()#.decode("utf-8")
                    xbmc.log("Simkl: Response: {0}".format(r1))
                    r = json.loads(str(r1))
                    self.lastwatched = r
                    if r == []:
                        xbmc.log("Simkl: Couldn't scrobble: Null Response")
                        return 0
                    media = mediadict[r["type"]]
                    toappend = {"ids": r[r["type"]]["ids"], "watched_at":date}

                tosend = {}
                tosend[media] = []
                tosend[media].append(toappend)
                tosend = json.dumps(tosend)

                xbmc.log("Simkl: values {0}".format(tosend))
                con.request("GET", "/sync/history/", body=tosend, headers=headers)
                r = con.getresponse().read().decode("utf-8")
                xbmc.log("Simkl: {0}".format(r))

                success = max(json.loads(r)["added"].values())
                if success:
                    self.scrobbled_dict
                    self.lock(filename, duration)
                return success

            #except httplib.BadStatusLine:
            #    xbmc.log("Simkl: {0}".format("ERROR: httplib.BadStatusLine"))
            except:
                xbmc.log("Simkl: ERROR: SSLError, retrying?")
                interface.notify(getstr(32029).format(cnt+1))
                time.sleep(5)
                if cnt <= 3:
                    self.watched(item, duration, date, cnt=cnt+1)
                else: interface.notify(getstr(32027))

        else:
            xbmc.log("Simkl: Can't scrobble. User not logged in or file locked")
            return 0

    def check_connection(self, cnt=0):
        if cnt < 3:
            try:
                self.get_usersettings()
                self.internet = True
            except Exception:
                time.sleep(5)
                self.check_connection(cnt=cnt+1)
        else:
            self.internet = False
            interface.notify(getstr(32027))

api = API()
if __name__ == "__main__":
    if sys.argv[1] == "login":
        xbmc.log("Logging in", level=xbmc.LOGDEBUG)
        api.login()

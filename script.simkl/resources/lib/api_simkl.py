#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import json
import time
import xbmc

import httplib

from interface import notify
from interface import LoginDialog
from utils import get_str
from utils import get_setting
from utils import set_setting
from utils import log
from utils import __addon__

REDIRECT_URI = "http://simkl.com"
APIKEY = '62a587ec2a82dbed02c6ab48b923d72e775cb1096d2de60d04502413e36ef100'
SECRET = '3e9d1563659a94a930c282d3d38cc01ece2ab5d769ae449cff1ff6f13d9b732e'


class Simkl:
    def __init__(self):
        self.userSettings = {}
        self.isLoggedIn = False
        self.loginInProgress = False

        self.headers = {"Content-Type": "application-json", "simkl-api-key": APIKEY}
        # set_setting('token', '')
        token = get_setting('token')
        if token:
            self.headers["authorization"] = "Bearer " + token
            r = self.get_user_settings()
            if r:
                notify(get_str(32025).format(self.userSettings["user"]["name"]))
                return
            elif r is None:
                notify(get_str(32027))
                return
        self.login()

    def get_user_settings(self):
        r = self._http("/users/settings", headers=self.headers)
        if isinstance(r, dict):
            self.userSettings = r
            self.isLoggedIn = True
            log("Usersettings = " + str(self.userSettings))
            return True
        return r

    def login(self):
        if self.loginInProgress: return
        self.loginInProgress = True

        if not self.isLoggedIn:
            rdic = self._http("/oauth/pin?client_id=" + APIKEY + "&redirect=" + REDIRECT_URI, headers=self.headers)

            if isinstance(rdic, dict) and "error" not in rdic.keys():
                pin = rdic["user_code"]
                url = rdic["verification_url"]

                login = LoginDialog("simkl-LoginDialog.xml", __addon__.getAddonInfo("path"), pin=pin, url=url,
                                    pin_check=self.pin_check, pin_success=self.pin_success)
                login.doModal()
                del login
        else:
            notify(get_str(32025).format(self.userSettings["user"]["name"]))
        self.loginInProgress = False

    def pin_check(self, pin):
        r = self._http("/oauth/pin/" + pin + "?client_id=" + APIKEY, headers=self.headers)
        log("PIN Check = " + str(r))
        if r["result"] == "OK":
            set_setting('token', r["access_token"])
            self.headers["authorization"] = "Bearer " + r["access_token"]
            return self.get_user_settings()
        elif r["result"] == "KO":
            return False

    def pin_success(self):
        notify(get_str(32030).format(self.userSettings["user"]["name"]))

    def detect_by_file(self, filename):
        values = json.dumps({"file": filename})
        r = self._http("/search/file/", headers=self.headers, body=values)
        if r:
            log("Response: {0}".format(r))
        return r

    def mark_as_watched(self, item):
        if not item: return False

        log("MARK: {0}".format(item))
        _watched_at = time.strftime('%Y-%m-%d %H:%M:%S')
        _count = 0

        s_data = {}
        if item["type"] == "episodes":
            s_data[item["type"]] = [{
                "watched_at": _watched_at,
                "ids": {
                    "simkl": item["simkl"]
                }
            }]
        elif item["type"] == "shows":
            # TESTED
            s_data[item["type"]] = [{
                "title": item["title"],
                "ids": {
                    "tvdb": item["tvdb"]
                },
                "seasons": [{
                    "number": item['season'],
                    "episodes": [{
                        "number": item['episode']
                    }]
                }]
            }]
        elif item["type"] == "movies":
            _prep = {
                "title": item["title"],
                "year": item["year"],
            }
            if "simkl" in item:
                _prep["ids"] = {"simkl": item["simkl"]}
            elif "imdb" in item:
                _prep["ids"] = {"imdb": item["imdb"]}

            s_data[item["type"]] = [_prep]

        log("Send: {0}".format(json.dumps(s_data)))
        while True and s_data:
            r = self._http("/sync/history/", body=json.dumps(s_data), headers=self.headers)

            #retry 3 times
            if r is None:
                _count += 1
                if _count <= 3:
                    notify(get_str(32029).format(_count))
                    time.sleep(10)
                    continue
                notify(get_str(32027))
                return False
            break
        return True

    def _http(self, url, headers={}, body=None, is_json=True):
        try:
            con = httplib.HTTPSConnection("api.simkl.com")
            con.request("GET", url, headers=headers, body=body)
            r = con.getresponse().read().decode("utf-8")
            if r.find('user_token_failed') != -1:
                self.isLoggedIn = False
                set_setting('token', '')
                notify(get_str(32031))
                return False
            return json.loads(r) if is_json else r
        except Exception:
            return None

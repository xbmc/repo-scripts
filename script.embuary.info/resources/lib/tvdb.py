#!/usr/bin/python
# coding: utf-8

########################

import json
import requests
import xbmc

from resources.lib.helper import *

########################

class TVDB_API():
    def __init__(self):
        self.token = winprop('token')

        if not self.token:
            self.token = get_cache('tvdb_token')

        if not self.token:
            self.token = self.login()

    def login(self):
        payload = {'apikey': 'b98b96493e710838fd74312a18eb09cf'}

        headers = {
                  'Content-Type': 'application/json',
                  'Accept': 'application/json',
                  'User-agent': 'Mozilla/5.0'
                  }

        for i in range(1,4): # loop if heavy server load
            try:
                request = requests.post('https://api.thetvdb.com/login', data=json.dumps(payload), headers=headers)

                if not request.ok:
                    raise Exception(str(request.status_code))

            except Exception as error:
                xbmc.sleep(500)

            else:
                token = request.json().get('token')
                winprop('token', token)
                write_cache('tvdb_token', token, 12)
                return token

    def call(self,call=None,lang=None):
        if not lang:
            lang = COUNTRY_CODE.lower()

        headers = {
                  'Content-Type': 'application/json',
                  'Authorization': 'Bearer %s' % self.token,
                  'Accept-Language': lang
                  }

        request_url = 'https://api.thetvdb.com' + call

        for i in range(1,4): # loop if heavy server load
            try:
                request = requests.get(request_url, timeout=5, headers=headers)

                if not request.ok:
                    raise Exception(str(request.status_code))

            except Exception as error:
                xbmc.sleep(500)

            else:
                result = request.json()
                result = result.get('data')

                if result:
                    return result
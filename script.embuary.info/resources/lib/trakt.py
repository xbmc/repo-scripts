#!/usr/bin/python
# coding: utf-8

########################

import xbmc
import requests

from resources.lib.helper import *

########################

TRAKT_API_KEY = ADDON.getSettingString('trakt_api_key')

########################

def trakt_api(call=None):
    headers = {
              'Content-Type': 'application/json',
              'trakt-api-version': '2',
              'trakt-api-key': TRAKT_API_KEY
              }

    request_url = 'https://api.trakt.tv' + call

    for i in range(1,4): # loop if heavy server load
        try:
            request = requests.get(request_url, timeout=5, headers=headers)

            if not request.ok:
                raise Exception(str(request.status_code))

        except Exception as error:
            log('Trakt server error: Code ' + str(error), ERROR)
            xbmc.sleep(500)

        else:
            return request.json()
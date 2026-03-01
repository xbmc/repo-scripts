# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements functions specific to systems where the widevine library is available from Google's repository"""

import json
import random

from ..utils import arch, http_post, system_os


def cdm_from_repo():
    """Whether the Widevine CDM is available from Google's library CDM repository"""
    # Based on https://source.chromium.org/chromium/chromium/src/+/master:third_party/widevine/cdm/widevine.gni
    if 'x86' in arch() or arch() == 'arm64' and system_os() in ('Darwin', 'Windows'):
        return True
    return False


def latest_widevine_available_from_repo(cdm_os, cdm_arch):
    """Returns the latest available Widevine CDM version and url from Google's library CDM repository"""
    cdm = {}
    version = '1.4.9.1088'
    url = 'https://update.googleapis.com/service/update2/json'
    headers = {
        'User-Agent': 'Mozilla/5.0',
    }
    payload = {
        'request': {
            '@os': '',
            '@updater': '',
            'acceptformat': 'crx3,download,puff,run,xz,zucc',
            'apps': [
                {
                    'appid': 'oimompecagnajdejgnnjijobebaeigek',
                    'installsource': 'ondemand',
                    'updatecheck': {},
                    'version': version
                }
            ],
            'dedup': 'cr',
            'ismachine': False,
            'arch': cdm_arch,
            'os': {
                'arch': cdm_arch,
                'platform': cdm_os,
            },
            'protocol': '4.0',
            'updaterversion': '142.0.7444.175'
        }
    }
    text = http_post(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    text = text.lstrip(')]}\'')
    cdm_json = json.loads(text)
    cdm['version'] = cdm_json.get('response').get('apps')[0].get('updatecheck').get('nextversion')
    cdm_urls = cdm_json.get('response').get('apps')[0].get('updatecheck').get('pipelines')[0].get('operations')[0].get('urls')
    cdm['url'] = random.choice(cdm_urls).get('url')
    return cdm

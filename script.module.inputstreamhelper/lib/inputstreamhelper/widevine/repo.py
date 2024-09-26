# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements functions specific to systems where the widevine library is available from Google's repository"""

from __future__ import absolute_import, division, unicode_literals

from .. import config
from ..kodiutils import localize, log, select_dialog
from ..utils import arch, http_get, http_head, parse_version, system_os


def cdm_from_repo():
    """Whether the Widevine CDM is available from Google's library CDM repository"""
    # Based on https://source.chromium.org/chromium/chromium/src/+/master:third_party/widevine/cdm/widevine.gni
    if 'x86' in arch() or arch() == 'arm64' and system_os() == 'Darwin':
        return True
    return False


def widevines_available_from_repo():
    """Returns all available Widevine CDM versions and urls from Google's library CDM repository"""
    cdm_versions = http_get(config.WIDEVINE_VERSIONS_URL).strip('\n').split('\n')
    try:
        cdm_os = config.WIDEVINE_OS_MAP[system_os()]
        cdm_arch = config.WIDEVINE_ARCH_MAP_REPO[arch()]
    except KeyError:
        cdm_os = "mac"
        cdm_arch = "x64"
    available_cdms = []
    for cdm_version in cdm_versions:
        cdm_url = config.WIDEVINE_DOWNLOAD_URL.format(version=cdm_version, os=cdm_os, arch=cdm_arch)
        http_status = http_head(cdm_url)
        if http_status == 200:
            available_cdms.append({'version': cdm_version, 'url': cdm_url})

    if not available_cdms:
        log(4, "could not find any available cdm in repo")

    return available_cdms


def latest_widevine_available_from_repo(available_cdms=None):
    """Returns the latest available Widevine CDM version and url from Google's library CDM repository"""
    if not available_cdms:
        available_cdms = widevines_available_from_repo()

    try:
        latest = available_cdms[-1]  # That's probably correct, but the following for loop makes sure
    except IndexError:
        # widevines_available_from_repo() already logged if there are no available cdms
        return None

    for cdm in available_cdms:
        if parse_version(cdm['version']) > parse_version(latest['version']):
            latest = cdm

    return latest


def choose_widevine_from_repo():
    """Choose from the widevine versions available in Google's library CDM repository"""
    available_cdms = widevines_available_from_repo()
    latest = latest_widevine_available_from_repo(available_cdms)

    opts = tuple(cdm['version'] for cdm in available_cdms)
    preselect = opts.index(latest['version'])

    version_index = select_dialog(localize(30069), opts, preselect=preselect)
    if version_index == -1:
        log(1, 'User did not choose a version to install!')
        return False

    cdm = available_cdms[version_index]
    log(0, 'User chose to install Widevine version {version} from {url}', version=cdm['version'], url=cdm['url'])

    return cdm

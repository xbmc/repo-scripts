# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements generic widevine functions used across architectures"""

from __future__ import absolute_import, division, unicode_literals
import os
from time import time

from .. import config
from ..kodiutils import addon_profile, exists, get_setting_int, listdir, localize, log, mkdirs, ok_dialog, open_file, select_dialog, set_setting, translate_path, yesno_dialog
from ..utils import arch, cmd_exists, hardlink, http_download, http_get, http_head, parse_version, remove_tree, run_cmd, store, system_os
from ..unicodes import compat_path, to_unicode


def install_cdm_from_backup(version):
    """Copies files from specified backup version to cdm dir"""
    filenames = listdir(os.path.join(backup_path(), version))

    for filename in filenames:
        backup_fpath = os.path.join(backup_path(), version, filename)
        install_fpath = os.path.join(ia_cdm_path(), filename)
        hardlink(backup_fpath, install_fpath)

    log(0, 'Installed CDM version {version} from backup', version=version)
    set_setting('last_modified', time())
    remove_old_backups(backup_path())


def widevine_eula():
    """Displays the Widevine EULA and prompts user to accept it."""
    if cdm_from_repo():
        cdm_version = latest_widevine_available_from_repo().get('version')
        cdm_os = config.WIDEVINE_OS_MAP[system_os()]
        cdm_arch = config.WIDEVINE_ARCH_MAP_REPO[arch()]
    else:  # Grab the license from the x86 files
        log(0, 'Acquiring Widevine EULA from x86 files.')
        cdm_version = latest_widevine_version(eula=True)
        cdm_os = 'mac'
        cdm_arch = 'x64'

    url = config.WIDEVINE_DOWNLOAD_URL.format(version=cdm_version, os=cdm_os, arch=cdm_arch)
    downloaded = http_download(url, message=localize(30025), background=True)  # Acquiring EULA
    if not downloaded:
        return False

    from zipfile import ZipFile
    with ZipFile(compat_path(store('download_path'))) as archive:
        with archive.open(config.WIDEVINE_LICENSE_FILE) as file_obj:
            eula = file_obj.read().decode().strip().replace('\n', ' ')

    return yesno_dialog(localize(30026), eula, nolabel=localize(30028), yeslabel=localize(30027))  # Widevine CDM EULA


def cdm_from_repo():
    """Whether the Widevine CDM is available from Google's library CDM repository"""
    # Based on https://source.chromium.org/chromium/chromium/src/+/master:third_party/widevine/cdm/widevine.gni
    if 'x86' in arch() or arch() == 'arm64' and system_os() == 'Darwin':
        return True
    return False

def backup_path():
    """Return the path to the cdm backups"""
    path = os.path.join(addon_profile(), 'backup', '')
    if not exists(path):
        mkdirs(path)
    return path


def widevine_config_path():
    """Return the full path to the widevine or recovery config file"""
    iacdm = ia_cdm_path()
    if iacdm is None:
        return None
    if cdm_from_repo():
        return os.path.join(iacdm, config.WIDEVINE_CONFIG_NAME)
    return os.path.join(iacdm, 'config.json')


def load_widevine_config():
    """Load the widevine or recovery config in JSON format"""
    from json import loads
    if exists(widevine_config_path()):
        with open_file(widevine_config_path(), 'r') as config_file:
            return loads(config_file.read())
    return None


def widevinecdm_path():
    """Get full Widevine CDM path"""
    widevinecdm_filename = config.WIDEVINE_CDM_FILENAME[system_os()]
    if widevinecdm_filename is None:
        return None
    if ia_cdm_path() is None:
        return None
    return os.path.join(ia_cdm_path(), widevinecdm_filename)


def has_widevinecdm():
    """Whether a Widevine CDM is installed on the system"""
    if system_os() == 'Android':  # Widevine CDM is built into Android
        return True

    widevinecdm = widevinecdm_path()
    if widevinecdm is None:
        return False
    if not exists(widevinecdm):
        log(3, 'Widevine CDM is not installed.')
        return False
    log(0, 'Found Widevine CDM at {path}', path=widevinecdm)
    return True


def ia_cdm_path():
    """Return the specified CDM path for inputstream.adaptive, usually ~/.kodi/cdm"""
    from xbmcaddon import Addon
    try:
        addon = Addon('inputstream.adaptive')
    except RuntimeError:
        return None

    cdm_path = translate_path(os.path.join(to_unicode(addon.getSetting('DECRYPTERPATH')), ''))
    if not exists(cdm_path):
        mkdirs(cdm_path)

    return cdm_path


def missing_widevine_libs():
    """Parses ldd output of libwidevinecdm.so and displays dialog if any depending libraries are missing."""
    if system_os() != 'Linux':  # this should only be needed for linux
        return None

    if cmd_exists('ldd'):
        widevinecdm = widevinecdm_path()
        if not os.access(widevinecdm, os.X_OK):
            log(0, 'Changing {path} permissions to 744.', path=widevinecdm)
            os.chmod(widevinecdm, 0o744)

        missing_libs = []
        cmd = ['ldd', widevinecdm]
        output = run_cmd(cmd, sudo=False)
        if output['success']:
            for line in output['output'].splitlines():
                if '=>' not in str(line):
                    continue
                lib_path = str(line).strip().split('=>')
                lib = lib_path[0].strip()
                path = lib_path[1].strip()
                if path == 'not found':
                    missing_libs.append(lib)

            if missing_libs:
                log(4, 'Widevine is missing the following libraries: {libs}', libs=missing_libs)
                return missing_libs

            log(0, 'There are no missing Widevine libraries! :-)')
            return None

    log(4, 'Failed to check for missing Widevine libraries.')
    return None


def latest_widevine_version(eula=False):
    """Returns the latest available version of Widevine CDM/Chrome OS."""
    if eula or cdm_from_repo():
        url = config.WIDEVINE_VERSIONS_URL
        versions = http_get(url)
        return versions.split()[-1]

    from .arm import chromeos_config, select_best_chromeos_image
    devices = chromeos_config()
    arm_device = select_best_chromeos_image(devices)
    if arm_device is None:
        log(4, 'We could not find an ARM device in the Chrome OS recovery.json')
        ok_dialog(localize(30004), localize(30005))
        return ''
    return arm_device.get('version')

def widevines_available_from_repo():
    """Returns all available Widevine CDM versions and urls from Google's library CDM repository"""
    cdm_versions = http_get(config.WIDEVINE_VERSIONS_URL).strip('\n').split('\n')
    cdm_os = config.WIDEVINE_OS_MAP[system_os()]
    cdm_arch = config.WIDEVINE_ARCH_MAP_REPO[arch()]
    available_cdms = []
    for cdm_version in cdm_versions:
        cdm_url = config.WIDEVINE_DOWNLOAD_URL.format(version=cdm_version, os=cdm_os, arch=cdm_arch)
        http_status = http_head(cdm_url)
        if http_status == 200:
            available_cdms.append({'version': cdm_version, 'url': cdm_url})

    return available_cdms

def latest_widevine_available_from_repo(available_cdms=None):
    """Returns the latest available Widevine CDM version and url from Google's library CDM repository"""
    if not available_cdms:
        available_cdms = widevines_available_from_repo()
    latest = available_cdms[-1]  # That's probably correct, but the following for loop makes sure
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

def remove_old_backups(bpath):
    """Removes old Widevine backups, if number of allowed backups is exceeded"""
    max_backups = get_setting_int('backups', 4)
    versions = sorted([parse_version(version) for version in listdir(bpath)])

    if len(versions) < 2:
        return

    try:
        installed_version = load_widevine_config()['version']
    except TypeError:
        log(2, "could not determine installed version. Aborting cleanup of old versions.")
        return

    while len(versions) > max_backups + 1:
        remove_version = str(versions[1] if versions[0] == parse_version(installed_version) else versions[0])
        log(0, 'Removing oldest backup which is not installed: {version}', version=remove_version)
        remove_tree(os.path.join(bpath, remove_version))
        versions = sorted([parse_version(version) for version in listdir(bpath)])

    return

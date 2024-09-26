# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements generic widevine functions used across architectures"""

from __future__ import absolute_import, division, unicode_literals

import os
from time import time

from .. import config
from ..kodiutils import (addon_profile, exists, get_setting_int, listdir,
                         localize, log, mkdirs, ok_dialog, open_file,
                         set_setting, translate_path, yesno_dialog)
from ..unicodes import compat_path, to_unicode
from ..utils import (arch, cmd_exists, hardlink, http_download, parse_version,
                     remove_tree, run_cmd, system_os)
from .arm_lacros import cdm_from_lacros, latest_lacros
from .repo import cdm_from_repo, latest_widevine_available_from_repo


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
        cdm_version = '4.10.2830.0' # fine to hardcode as it's only used for the EULA
        cdm_os = 'mac'
        cdm_arch = 'x64'

    url = config.WIDEVINE_DOWNLOAD_URL.format(version=cdm_version, os=cdm_os, arch=cdm_arch)
    dl_path = http_download(url, message=localize(30025), background=True)  # Acquiring EULA
    if not dl_path:
        return False

    from zipfile import ZipFile
    with ZipFile(compat_path(dl_path)) as archive:
        with archive.open(config.WIDEVINE_LICENSE_FILE) as file_obj:
            eula = file_obj.read().decode().strip().replace('\n', ' ')

    return yesno_dialog(localize(30026), eula, nolabel=localize(30028), yeslabel=localize(30027))  # Widevine CDM EULA


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
    if cdm_from_repo() or cdm_from_lacros():
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


def latest_widevine_version():
    """Returns the latest available version of Widevine CDM/Chrome OS/Lacros Image."""
    if cdm_from_repo():
        return latest_widevine_available_from_repo().get('version')

    if cdm_from_lacros():
        return latest_lacros()

    from .arm import chromeos_config, select_best_chromeos_image
    devices = chromeos_config()
    arm_device = select_best_chromeos_image(devices)
    if arm_device is None:
        log(4, 'We could not find an ARM device in the Chrome OS recovery.json')
        ok_dialog(localize(30004), localize(30005))
        return ''
    return arm_device.get('version')


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

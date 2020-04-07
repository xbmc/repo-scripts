# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements generic widevine functions used across architectures"""

from __future__ import absolute_import, division, unicode_literals
import os

from .. import config
from ..kodiutils import addon_profile, get_setting_int, localize, log, ok_dialog, translate_path, yesno_dialog
from ..utils import arch, cmd_exists, http_download, http_get, run_cmd, store, system_os


def install_cdm_from_backup(version):
    """Copies files from specified backup version to cdm dir"""
    from xbmcvfs import copy, delete, exists

    filenames = os.listdir(os.path.join(backup_path(), version))

    for filename in filenames:
        backup_fpath = os.path.join(backup_path(), version, filename)
        install_fpath = os.path.join(ia_cdm_path(), filename)

        if exists(install_fpath):
            delete(install_fpath)

        try:
            os.link(backup_fpath, install_fpath)
        except (AttributeError, OSError):
            copy(backup_fpath, install_fpath)

    log('Installed CDM version {version} from backup', version=version)
    remove_old_backups(backup_path())


def has_widevine():
    """Checks if Widevine CDM is installed on system."""
    if system_os() == 'Android':  # widevine is built in on android
        return True

    if widevine_path():
        log('Found Widevine binary at {path}', path=widevine_path())
        return True

    log('Widevine is not installed.')
    return False


def widevine_eula():
    """Displays the Widevine EULA and prompts user to accept it."""

    cdm_version = latest_widevine_version(eula=True)
    if 'x86' in arch():
        cdm_os = config.WIDEVINE_OS_MAP[system_os()]
        cdm_arch = config.WIDEVINE_ARCH_MAP_X86[arch()]
    else:  # grab the license from the x86 files
        log('Acquiring Widevine EULA from x86 files.')
        cdm_os = 'mac'
        cdm_arch = 'x64'

    url = config.WIDEVINE_DOWNLOAD_URL.format(version=cdm_version, os=cdm_os, arch=cdm_arch)
    downloaded = http_download(url, message=localize(30025))  # Acquiring EULA
    if not downloaded:
        return False

    from zipfile import ZipFile
    with ZipFile(store('download_path')) as archive:
        with archive.open(config.WIDEVINE_LICENSE_FILE) as file_obj:
            eula = file_obj.read().decode().strip().replace('\n', ' ')

    return yesno_dialog(localize(30026), eula, nolabel=localize(30028), yeslabel=localize(30027))  # Widevine CDM EULA


def backup_path():
    """Return the path to the cdm backups"""
    from xbmcvfs import exists, mkdir
    path = os.path.join(addon_profile(), 'backup')
    if not exists(path):
        mkdir(path)
    return path


def widevine_config_path():
    """Return the full path to the widevine or recovery config file"""
    if 'x86' in arch():
        return os.path.join(ia_cdm_path(), config.WIDEVINE_CONFIG_NAME)
    return os.path.join(ia_cdm_path(), os.path.basename(config.CHROMEOS_RECOVERY_URL) + '.json')


def load_widevine_config():
    """Load the widevine or recovery config in JSON format"""
    from json import loads
    with open(widevine_config_path(), 'r') as config_file:
        return loads(config_file.read())


def widevine_path():
    """Get full widevine path"""
    widevine_cdm_filename = config.WIDEVINE_CDM_FILENAME[system_os()]
    if widevine_cdm_filename is None:
        return False

    if ia_cdm_path():
        wv_path = os.path.join(ia_cdm_path(), widevine_cdm_filename)
        from xbmcvfs import exists

        if exists(wv_path):
            return wv_path

    return False


def ia_cdm_path():
    """Return the specified CDM path for inputstream.adaptive, usually ~/.kodi/cdm"""
    from xbmcaddon import Addon
    try:
        addon = Addon('inputstream.adaptive')
    except RuntimeError:
        return None

    cdm_path = translate_path(addon.getSetting('DECRYPTERPATH'))
    from xbmcvfs import exists, mkdir
    if not exists(cdm_path):
        mkdir(cdm_path)

    return cdm_path


def missing_widevine_libs():
    """Parses ldd output of libwidevinecdm.so and displays dialog if any depending libraries are missing."""
    if system_os() != 'Linux':  # this should only be needed for linux
        return None

    if cmd_exists('ldd'):
        if not os.access(widevine_path(), os.X_OK):
            log('Changing {path} permissions to 744.', path=widevine_path())
            os.chmod(widevine_path(), 0o744)

        missing_libs = []
        cmd = ['ldd', widevine_path()]
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
                log('Widevine is missing the following libraries: {libs}', libs=missing_libs)
                return missing_libs

            log('There are no missing Widevine libraries! :-)')
            return None

    if arch() == 'arm64':
        import struct
        if struct.calcsize('P') * 8 == 64:
            log('ARM64 ldd check failed. User needs 32-bit userspace.')
            ok_dialog(localize(30004), localize(30039))  # Widevine not available on ARM64

    log('Failed to check for missing Widevine libraries.')
    return None


def latest_widevine_version(eula=False):
    """Returns the latest available version of Widevine CDM/Chrome OS."""
    if eula or 'x86' in arch():
        url = config.WIDEVINE_VERSIONS_URL
        versions = http_get(url)
        return versions.split()[-1]

    from .arm import chromeos_config, select_best_chromeos_image
    devices = chromeos_config()
    arm_device = select_best_chromeos_image(devices)
    if arm_device is None:
        log('We could not find an ARM device in the Chrome OS recovery.conf')
        ok_dialog(localize(30004), localize(30005))
        return ''
    return arm_device['version']


def remove_old_backups(bpath):
    """Removes old Widevine backups, if number of allowed backups is exceeded"""
    from distutils.version import LooseVersion  # pylint: disable=import-error,no-name-in-module,useless-suppression
    from shutil import rmtree

    max_backups = get_setting_int('backups', 4)
    versions = sorted([LooseVersion(version) for version in os.listdir(bpath)])

    if len(versions) < 2:
        return

    if 'x86' in arch():
        installed_version = load_widevine_config()['version']
    else:
        from .arm import select_best_chromeos_image
        installed_version = select_best_chromeos_image(load_widevine_config())['version']

    while len(versions) > max_backups + 1:
        remove_version = str(versions[1] if versions[0] == LooseVersion(installed_version) else versions[0])
        log('removing oldest backup which is not installed: {version}', version=remove_version)
        rmtree(os.path.join(bpath, remove_version))
        versions = sorted([LooseVersion(version) for version in os.listdir(bpath)])

    return

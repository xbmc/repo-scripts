# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements generic widevine functions used across architectures"""

from __future__ import absolute_import, division, unicode_literals
import os

from .. import config
from ..kodiutils import addon_profile, exists, get_setting_int, localize, log, mkdir, ok_dialog, translate_path, yesno_dialog
from ..utils import arch, cmd_exists, hardlink, http_download, http_get, run_cmd, store, system_os


def install_cdm_from_backup(version):
    """Copies files from specified backup version to cdm dir"""
    filenames = os.listdir(os.path.join(backup_path(), version))

    for filename in filenames:
        backup_fpath = os.path.join(backup_path(), version, filename)
        install_fpath = os.path.join(ia_cdm_path(), filename)
        hardlink(backup_fpath, install_fpath)

    log(0, 'Installed CDM version {version} from backup', version=version)
    remove_old_backups(backup_path())


def widevine_eula():
    """Displays the Widevine EULA and prompts user to accept it."""

    cdm_version = latest_widevine_version(eula=True)
    if 'x86' in arch():
        cdm_os = config.WIDEVINE_OS_MAP[system_os()]
        cdm_arch = config.WIDEVINE_ARCH_MAP_X86[arch()]
    else:  # grab the license from the x86 files
        log(0, 'Acquiring Widevine EULA from x86 files.')
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

    cdm_path = translate_path(addon.getSetting('DECRYPTERPATH'))
    if not exists(cdm_path):
        mkdir(cdm_path)

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
    if eula or 'x86' in arch():
        url = config.WIDEVINE_VERSIONS_URL
        versions = http_get(url)
        return versions.split()[-1]

    from .arm import chromeos_config, select_best_chromeos_image
    devices = chromeos_config()
    arm_device = select_best_chromeos_image(devices)
    if arm_device is None:
        log(4, 'We could not find an ARM device in the Chrome OS recovery.conf')
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
        log(0, 'Removing oldest backup which is not installed: {version}', version=remove_version)
        rmtree(os.path.join(bpath, remove_version))
        versions = sorted([LooseVersion(version) for version in os.listdir(bpath)])

    return

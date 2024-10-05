# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements the main InputStream Helper class"""

from __future__ import absolute_import, division, unicode_literals
import os
import json

from . import config
from .kodiutils import (addon_version, browsesingle, delete, exists, get_proxies, get_setting, get_setting_bool, get_setting_float, get_setting_int, jsonrpc,
                        kodi_to_ascii, kodi_version, listdir, localize, log, notification, ok_dialog, progress_dialog, select_dialog,
                        set_setting, set_setting_bool, textviewer, translate_path, yesno_dialog)
from .utils import arch, download_path, http_download, parse_version, remove_tree, system_os, temp_path, unzip, userspace64
from .widevine.arm import dl_extract_widevine_chromeos, extract_widevine_chromeos, install_widevine_arm
from .widevine.arm_lacros import cdm_from_lacros, latest_lacros
from .widevine.widevine import (backup_path, has_widevinecdm, ia_cdm_path,
                                install_cdm_from_backup, latest_widevine_version,
                                load_widevine_config, missing_widevine_libs, widevine_config_path,
                                widevine_eula, widevinecdm_path)
from .widevine.repo import cdm_from_repo, choose_widevine_from_repo, latest_widevine_available_from_repo
from .unicodes import compat_path

# NOTE: Work around issue caused by platform still using os.popen()
#       This helps to survive 'IOError: [Errno 10] No child processes'
if hasattr(os, 'popen'):
    del os.popen


class InputStreamException(Exception):
    """Stub Exception"""


def cleanup_decorator(func):
    """Decorator which runs cleanup before and after a function"""

    def clean_before_after(self, *args, **kwargs):  # pylint: disable=missing-docstring
        # pylint only complains about a missing docstring on py2.7?
        self.cleanup()
        result = func(self, *args, **kwargs)
        self.cleanup()
        return result
    return clean_before_after


class Helper:
    """The main InputStream Helper class"""

    def __init__(self, protocol, drm=None):
        """Initialize InputStream Helper class"""

        self.protocol = protocol
        self.drm = drm

        from platform import uname
        log(0, 'Platform information: {uname}', uname=uname())

        if self.protocol not in config.INPUTSTREAM_PROTOCOLS:
            raise InputStreamException('UnsupportedProtocol')

        self.inputstream_addon = config.INPUTSTREAM_PROTOCOLS[self.protocol]

        if self.drm:
            if self.drm not in config.DRM_SCHEMES:
                raise InputStreamException('UnsupportedDRMScheme')

            self.drm = config.DRM_SCHEMES[drm]

        # Add proxy support to HTTP requests
        proxies = get_proxies()
        if proxies:
            try:  # Python 3
                from urllib.request import build_opener, install_opener, ProxyHandler
            except ImportError:  # Python 2
                from urllib2 import build_opener, install_opener, ProxyHandler
            install_opener(build_opener(ProxyHandler(proxies)))

    def __repr__(self):
        """String representation of Helper class"""
        return 'Helper({protocol}, drm={drm})'.format(protocol=self.protocol, drm=self.drm)

    @staticmethod
    def disable():
        """Disable plugin"""
        if not get_setting_bool('disabled', False):
            set_setting_bool('disabled', True)

    @staticmethod
    def enable():
        """Enable plugin"""
        if get_setting('disabled', False):
            set_setting_bool('disabled', False)

    def _inputstream_version(self):
        """Return the requested inputstream version"""
        from xbmcaddon import Addon
        try:
            addon = Addon(self.inputstream_addon)
        except RuntimeError:
            return None

        from .unicodes import to_unicode
        return to_unicode(addon.getAddonInfo('version'))

    @staticmethod
    def _get_lib_version(path):
        if not path or not exists(path):
            return '(Not found)'
        import re
        with open(compat_path(path), 'rb') as library:
            match = re.search(br'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', library.read())
        if not match:
            return '(Undetected)'
        from .unicodes import to_unicode
        return to_unicode(match.group(0))

    def _has_inputstream(self):
        """Checks if selected InputStream add-on is installed."""
        data = jsonrpc(method='Addons.GetAddonDetails', params={'addonid': self.inputstream_addon})
        if 'error' in data:
            log(3, '{addon} is not installed.', addon=self.inputstream_addon)
            return False

        log(0, '{addon} is installed.', addon=self.inputstream_addon)
        return True

    def _inputstream_enabled(self):
        """Returns whether selected InputStream add-on is enabled.."""
        data = jsonrpc(method='Addons.GetAddonDetails', params={'addonid': self.inputstream_addon, 'properties': ['enabled']})
        if data.get('result', {}).get('addon', {}).get('enabled'):
            log(0, '{addon} {version} is enabled.', addon=self.inputstream_addon, version=self._inputstream_version())
            return True

        log(3, '{addon} is disabled.', addon=self.inputstream_addon)
        return False

    def _enable_inputstream(self):
        """Enables selected InputStream add-on."""
        data = jsonrpc(method='Addons.SetAddonEnabled', params={'addonid': self.inputstream_addon, 'enabled': True})
        if 'error' in data:
            return False
        return True

    def _supports_widevine(self):
        """Checks if Widevine is supported on the architecture/operating system/Kodi version."""
        if arch() not in config.WIDEVINE_SUPPORTED_ARCHS:
            log(4, 'Unsupported Widevine architecture found: {arch}', arch=arch())
            ok_dialog(localize(30004), localize(30007, arch=arch()))  # Widevine not available on this architecture
            return False

        if arch() == 'arm64' and system_os() not in ['Android', 'Darwin'] and userspace64():
            is_version = parse_version(addon_version(self.inputstream_addon))
            try:
                compat_version = parse_version(config.MINIMUM_INPUTSTREAM_VERSION_ARM64[self.inputstream_addon])
            except KeyError:
                log(4, 'Minimum version of {addon} for 64bit support unknown. Continuing into the unknown...'.format(addon=self.inputstream_addon))
                compat_version = parse_version("0.0.0")

            if is_version < compat_version:
                log(4, 'Unsupported 64bit userspace found. Needs 32bit or newer ISA (currently {v}) on {arch}', arch=arch(), v=is_version)
                ok_dialog(localize(30004), localize(30068, addon=self.inputstream_addon, version=compat_version))  # Need newer ISA or 32bit userspace
                return False

        if system_os() not in config.WIDEVINE_SUPPORTED_OS:
            log(4, 'Unsupported Widevine OS found: {os}', os=system_os())
            ok_dialog(localize(30004), localize(30011, os=system_os()))  # Operating system not supported by Widevine
            return False

        if parse_version(config.WIDEVINE_MINIMUM_KODI_VERSION[system_os()]) > parse_version(kodi_version()):
            log(4, 'Unsupported Kodi version for Widevine: {version}', version=kodi_version())
            ok_dialog(localize(30004), localize(30010, version=config.WIDEVINE_MINIMUM_KODI_VERSION[system_os()]))  # Kodi too old
            return False

        if 'WindowsApps' in translate_path('special://xbmcbin/'):  # uwp is not supported
            log(4, 'Unsupported UWP Kodi version detected.')
            ok_dialog(localize(30004), localize(30012))  # Windows Store Kodi falls short
            return False

        return True

    @staticmethod
    def _install_widevine_from_repo(bpath, choose_version=False):
        """Install Widevine CDM from Google's library CDM repository"""
        if choose_version:
            cdm = choose_widevine_from_repo()
        else:
            cdm = latest_widevine_available_from_repo()

        if not cdm:
            return cdm

        cdm_version = cdm.get('version')
        dl_path = download_path(cdm.get('url'))

        if not exists(dl_path):
            dl_path = http_download(cdm.get('url'))

        if dl_path:
            progress = progress_dialog()
            progress.create(heading=localize(30043), message=localize(30044))  # Extracting Widevine CDM
            unzip(dl_path, os.path.join(bpath, cdm_version, ''))

            return (progress, cdm_version)

        return False

    def install_and_finish(self, progress, version):
        """Installs the cdm from backup and runs checks"""

        progress.update(97, message=localize(30049))  # Installing Widevine CDM
        install_cdm_from_backup(version)

        progress.update(98, message=localize(30050))  # Finishing
        if has_widevinecdm():
            wv_check = self._check_widevine()
            if wv_check:
                progress.update(100, message=localize(30051))  # Widevine CDM successfully installed.
                notification(localize(30037), localize(30051))  # Success! Widevine CDM successfully installed.
            progress.close()
            return wv_check

        progress.close()
        return False

    @cleanup_decorator
    def install_widevine(self, choose_version=False):
        """Wrapper function that calls Widevine installer method depending on architecture"""
        if not self._supports_widevine():
            return False

        if not widevine_eula():
            return False

        if cdm_from_repo():
            result = self._install_widevine_from_repo(backup_path(), choose_version=choose_version)
        else:
            if choose_version:
                log(1, "Choosing a version to install is only implemented if the lib is found in googles repo.")
            result = install_widevine_arm(backup_path())
        if not result:
            return result

        if self.install_and_finish(*result):
            from time import time
            set_setting('last_check', time())
            return True

        ok_dialog(localize(30004), localize(30005))  # An error occurred
        return False

    @cleanup_decorator
    def install_widevine_from(self):
        """Install Widevine from a given URL or file."""
        if yesno_dialog(None, localize(30066)):  # download resource with widevine from url? no means specify local
            result = dl_extract_widevine_chromeos(get_setting("image_url"), backup_path())
            if not result:
                return result

            if self.install_and_finish(*result):
                return True

        else:
            image_path = browsesingle(1, localize(30067), "files")
            if not image_path:
                return False

            image_version = os.path.basename(image_path).split("_")[1]
            progress = extract_widevine_chromeos(backup_path(), image_path, image_version)
            if not progress:
                return False

            if self.install_and_finish(progress, image_version):
                return True

        return False

    @staticmethod
    def remove_widevine():
        """Removes Widevine CDM"""
        if has_widevinecdm():
            widevinecdm = widevinecdm_path()
            log(0, 'Removed Widevine CDM at {path}', path=widevinecdm)
            delete(widevinecdm)
            notification(localize(30037), localize(30052))  # Success! Widevine successfully removed.
            set_setting('last_modified', '0.0')
            return True
        notification(localize(30004), localize(30053))  # Error. Widevine CDM not found.
        return False

    @staticmethod
    def _first_run():
        """Check if this add-on version is running for the first time"""

        # Get versions
        settings_version = get_setting('version', '0.3.4')  # settings_version didn't exist in version 0.3.4 and older

        # Compare versions
        if parse_version(addon_version()) > parse_version(settings_version):
            # New version found, save addon_version to settings
            set_setting('version', addon_version())
            log(2, 'InputStreamHelper version {version} is running for the first time', version=addon_version())
            return True
        return False

    @staticmethod
    def get_current_wv():
        """Returns which component is used (widevine/chromeos/lacros) and the current version"""
        wv_config = load_widevine_config()
        component = 'Widevine CDM'
        current_version = '0'

        if not wv_config:
            log(3, 'Widevine config missing. Could not determine current version, forcing update.')
        elif cdm_from_repo():
            current_version = wv_config['version']
        elif cdm_from_lacros():
            component = 'Lacros image'
            try:
                current_version = wv_config['img_version']  # if lib was installed from chromeos image, there is no img_version
            except KeyError:
                pass
        else:
            component = 'Chrome OS'
            current_version = wv_config['version']

        return component, current_version

    def _update_widevine(self):
        """Prompts user to upgrade Widevine CDM when a newer version is available."""
        from time import localtime, strftime, time

        update_declined_at = get_setting_float('update_declined_at', 0.0)
        if update_declined_at + 3600 * 24 * 2 >= time():
            log(2, 'User had declined an update on {date}', date=strftime('%Y-%m-%d %H:%M', localtime(update_declined_at)))
            return

        last_check = get_setting_float('last_check', 0.0)
        if last_check and not self._first_run():
            if last_check + 3600 * 24 * get_setting_int('update_frequency', 14) >= time():
                log(2, 'Widevine update check was made on {date}', date=strftime('%Y-%m-%d %H:%M', localtime(last_check)))
                return

        component, current_version = self.get_current_wv()

        latest_version = latest_widevine_version()

        log(0, 'Latest {component} version is {version}', component=component, version=latest_version)
        log(0, 'Current {component} version installed is {version}', component=component, version=current_version)

        if parse_version(latest_version) > parse_version(current_version):
            log(2, 'There is an update available for {component}', component=component)
            if yesno_dialog(localize(30040), localize(30033), nolabel=localize(30028), yeslabel=localize(30034)):
                self.install_widevine()
            else:
                set_setting('update_declined_at', time())
                log(3, 'User declined to update {component}.', component=component)
        else:
            set_setting('last_check', time())
            log(0, 'User is on the latest available {component} version.', component=component)

    def _check_widevine(self):
        """Checks that all Widevine components are installed and available."""
        if system_os() == 'Android':  # no checks needed for Android
            return True

        if not exists(widevine_config_path()):
            log(4, 'Widevine or Chrome OS recovery.json is missing. Reinstall is required.')
            ok_dialog(localize(30001), localize(30031))  # An update of Widevine is required
            return self.install_widevine()

        if cdm_from_repo():  # check that widevine arch matches system arch
            wv_config = load_widevine_config()
            if config.WIDEVINE_ARCH_MAP_REPO[arch()] != wv_config['arch']:
                log(4, 'Widevine/system arch mismatch. Reinstall is required.')
                ok_dialog(localize(30001), localize(30031))  # An update of Widevine is required
                return self.install_widevine()

        if missing_widevine_libs():
            ok_dialog(localize(30004), localize(30032, libs=', '.join(missing_widevine_libs())))  # Missing libraries
            return False

        self._update_widevine()
        return True

    @staticmethod
    def cleanup():
        """Clean up function after Widevine CDM installation"""
        if not has_widevinecdm():
            remove_tree(ia_cdm_path())

        remove_tree(temp_path())
        return True

    def _supports_hls(self):
        """Return if HLS support is available in inputstream.adaptive."""
        if parse_version(self._inputstream_version()) >= parse_version(config.HLS_MINIMUM_IA_VERSION):
            return True

        log(3, 'HLS is unsupported on {addon} version {version}', addon=self.inputstream_addon, version=self._inputstream_version())
        return False

    def _check_drm(self):
        """Main function for ensuring that specified DRM system is installed and available."""
        if not self.drm or self.inputstream_addon != 'inputstream.adaptive':
            return True

        if self.drm != 'widevine':
            return True

        if has_widevinecdm():
            return self._check_widevine()

        if yesno_dialog(localize(30041), localize(30002), nolabel=localize(30028), yeslabel=localize(30038)):  # Widevine required
            return self.install_widevine()

        return False

    def _install_inputstream(self):
        """Install inputstream addon."""
        from xbmc import executebuiltin
        from xbmcaddon import Addon
        try:
            # See if there's an installed repo that has it
            executebuiltin('InstallAddon({})'.format(self.inputstream_addon), wait=True)

            # Check if InputStream add-on exists!
            Addon('{}'.format(self.inputstream_addon))

            log(0, 'InputStream add-on installed from repo.')
            return True
        except RuntimeError:
            log(3, 'InputStream add-on not installed.')
            return False

    def check_inputstream(self):
        """Main function. Ensures that all components are available for InputStream add-on playback."""
        if get_setting_bool('disabled', False):  # blindly return True if helper has been disabled
            log(3, 'InputStreamHelper is disabled in its settings.xml.')
            return True
        if self.drm == 'widevine' and not self._supports_widevine():
            return False
        if not self._has_inputstream():
            # Try to install InputStream add-on
            if not self._install_inputstream():
                ok_dialog(localize(30004), localize(30008, addon=self.inputstream_addon))  # inputstream is missing on system
                return False
        elif not self._inputstream_enabled():
            ret = yesno_dialog(localize(30001), localize(30009, addon=self.inputstream_addon))  # inputstream is disabled
            if not ret:
                return False
            self._enable_inputstream()
        log(0, '{addon} {version} is installed and enabled.', addon=self.inputstream_addon, version=self._inputstream_version())

        if self.protocol == 'hls' and not self._supports_hls():
            ok_dialog(localize(30004),  # HLS Minimum version is needed
                      localize(30017, addon=self.inputstream_addon, version=config.HLS_MINIMUM_IA_VERSION))
            return False

        return self._check_drm()

    def info_dialog(self):
        """ Show an Info box with useful info e.g. for bug reports"""
        text = localize(30800, version=kodi_version(), system=system_os(), arch=arch()) + '\n'  # Kodi information
        text += '\n'

        disabled_str = ' ({disabled})'.format(disabled=localize(30054))
        ishelper_state = disabled_str if get_setting_bool('disabled', False) else ''
        istream_state = disabled_str if not self._inputstream_enabled() else ''
        text += localize(30810, version=addon_version(), state=ishelper_state) + '\n'
        text += localize(30811, version=self._inputstream_version(), state=istream_state) + '\n'
        text += '\n'

        if system_os() == 'Android':
            text += localize(30820) + '\n'
        else:
            from time import localtime, strftime
            if get_setting_float('last_modified', 0.0):
                wv_updated = strftime('%Y-%m-%d %H:%M', localtime(get_setting_float('last_modified', 0.0)))
            else:
                wv_updated = 'Never'
            text += localize(30821, version=self._get_lib_version(widevinecdm_path()), date=wv_updated) + '\n'
            if not cdm_from_repo():
                wv_cfg = load_widevine_config()
                if wv_cfg and cdm_from_lacros():  # Lacros image version
                    text += localize(30825, image="Lacros", version=wv_cfg['img_version']) + '\n'
                elif wv_cfg:  # Chrome OS version
                    text += localize(30822, name=wv_cfg['hwidmatch'].split()[0].lstrip('^'), version=wv_cfg['version']) + '\n'
            if get_setting_float('last_check', 0.0):
                wv_check = strftime('%Y-%m-%d %H:%M', localtime(get_setting_float('last_check', 0.0)))
            else:
                wv_check = 'Never'
            text += localize(30823, date=wv_check) + '\n'
            text += localize(30824, path=ia_cdm_path()) + '\n'

        text += '\n'

        text += localize(30830, url=config.SHORT_ISSUE_URL)  # Report issues

        log(2, '\n{info}'.format(info=kodi_to_ascii(text)))
        textviewer(localize(30901), text)

    def rollback_libwv(self):
        """Rollback lib to a version specified by the user"""
        bpath = backup_path()
        versions = listdir(bpath)

        # Return if Widevine is not installed
        if not exists(widevine_config_path()):
            notification(localize(30004), localize(30041))
            return

        try:
            installed_version = load_widevine_config()['img_version']
        except KeyError:
            installed_version = load_widevine_config()['version']

        del versions[versions.index(installed_version)]

        if cdm_from_repo():
            show_versions = versions
        else:
            show_versions = []

            for version in versions:
                lib_version = self._get_lib_version(os.path.join(bpath, version, config.WIDEVINE_CDM_FILENAME[system_os()]))
                show_versions.append('{}    ({})'.format(lib_version, version))

        if not show_versions:
            notification(localize(30004), localize(30056))
            return

        version = select_dialog(localize(30057), show_versions)
        if version != -1:
            log(0, 'Rollback to version {version}', version=versions[version])
            install_cdm_from_backup(versions[version])
            notification(localize(30037), localize(30051))  # Success! Widevine successfully installed.

        return

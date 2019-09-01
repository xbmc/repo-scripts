# -*- coding: utf-8 -*-
''' Implements the main InputStream Helper class '''
from __future__ import absolute_import, division, unicode_literals

import os
import platform
import zipfile
import json
import time
import subprocess
import shutil
import re
from distutils.version import LooseVersion  # pylint: disable=import-error,no-name-in-module
from datetime import datetime, timedelta
import struct

try:  # Python 3
    from urllib.error import HTTPError
    from urllib.request import build_opener, install_opener, ProxyHandler, urlopen
except ImportError:  # Python 2
    from urllib2 import build_opener, HTTPError, install_opener, ProxyHandler, urlopen

import config

from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs

ADDON = xbmcaddon.Addon('script.module.inputstreamhelper')
ADDON_PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')


# NOTE: Work around issue caused by platform still using os.popen()
#       This helps to survive 'IOError: [Errno 10] No child processes'
if hasattr(os, 'popen'):
    del os.popen


class InputStreamException(Exception):
    ''' Stub Exception '''


class SafeDict(dict):
    ''' A safe dictionary implementation that does not break down on missing keys '''
    def __missing__(self, key):
        ''' Replace missing keys with the original placeholder '''
        return '{' + key + '}'


def log(msg, **kwargs):
    ''' InputStream Helper log method '''
    xbmc.log(msg='[{addon}-{version}]: {msg}'.format(addon=ADDON_ID, version=ADDON_VERSION, msg=msg.format(**kwargs)), level=xbmc.LOGDEBUG)


def localize(string_id, **kwargs):
    ''' Return the translated string from the .po language files, optionally translating variables '''
    if kwargs:
        import string
        return string.Formatter().vformat(ADDON.getLocalizedString(string_id), (), SafeDict(**kwargs))

    return ADDON.getLocalizedString(string_id)


def has_socks():
    ''' Test if socks is installed, and remember this information '''

    # If it wasn't stored before, check if socks is installed
    if not hasattr(has_socks, 'installed'):
        try:
            import socks  # noqa: F401; pylint: disable=unused-variable,unused-import
            has_socks.installed = True
        except ImportError:
            has_socks.installed = False
            return None  # Detect if this is the first run

    # Return the stored value
    return has_socks.installed


def system_os():
    ''' Get system platform, and remember this information '''

    # If it wasn't stored before, get the correct value
    if not hasattr(system_os, 'name'):
        if xbmc.getCondVisibility('system.platform.android'):
            system_os.name = 'Android'
        else:
            system_os.name = platform.system()

    # Return the stored value
    return system_os.name


class Helper:
    ''' The main InputStream Helper class '''

    def __init__(self, protocol, drm=None):
        ''' Initialize InputStream Helper class '''
        self._download_path = None
        self._loop_dev = None
        self._modprobe_loop = False
        self._attached_loop_dev = False

        self.protocol = protocol
        self.drm = drm

        log('Platform information: {platform}', platform=platform.uname())

        if self.protocol not in config.INPUTSTREAM_PROTOCOLS:
            raise InputStreamException('UnsupportedProtocol')

        self.inputstream_addon = config.INPUTSTREAM_PROTOCOLS[self.protocol]

        if self.drm:
            if self.drm not in config.DRM_SCHEMES:
                raise InputStreamException('UnsupportedDRMScheme')

            self.drm = config.DRM_SCHEMES[drm]

        # Add proxy support to HTTP requests
        install_opener(build_opener(ProxyHandler(self._get_proxies())))

    def __repr__(self):
        ''' String representation of Helper class '''
        return 'Helper({protocol}, drm={drm})'.format(protocol=self.protocol, drm=self.drm)

    @classmethod
    def _diskspace(cls):
        """Return the free disk space available (in bytes) in temp_path."""
        statvfs = os.statvfs(cls._temp_path())
        return statvfs.f_frsize * statvfs.f_bavail

    @classmethod
    def _temp_path(cls):
        ''' Return temporary path, usually ~/.kodi/userdata/addon_data/tmp '''
        temp_path = os.path.join(ADDON_PROFILE, 'tmp')
        if not xbmcvfs.exists(temp_path):
            xbmcvfs.mkdir(temp_path)

        return temp_path

    @classmethod
    def _mnt_path(cls):
        ''' Return mount path, usually ~/.kodi/userdata/addon_data/tmp/mnt '''
        mnt_path = os.path.join(cls._temp_path(), 'mnt')
        if not xbmcvfs.exists(mnt_path):
            xbmcvfs.mkdir(mnt_path)

        return mnt_path

    @classmethod
    def _ia_cdm_path(cls):
        ''' Return the specified CDM path for inputstream.adaptive, usually ~/.kodi/cdm '''
        addon = xbmcaddon.Addon('inputstream.adaptive')
        cdm_path = xbmc.translatePath(addon.getSetting('DECRYPTERPATH'))
        if not xbmcvfs.exists(cdm_path):
            xbmcvfs.mkdir(cdm_path)

        return cdm_path

    @classmethod
    def _widevine_config_path(cls):
        ''' Return the full path to the widevine or recovery config file '''
        if 'x86' in cls._arch():
            return os.path.join(cls._ia_cdm_path(), config.WIDEVINE_CONFIG_NAME)
        return os.path.join(cls._ia_cdm_path(), os.path.basename(config.CHROMEOS_RECOVERY_URL) + '.json')

    @classmethod
    def _load_widevine_config(cls):
        ''' Load the widevine or recovery config in JSON format '''
        with open(cls._widevine_config_path(), 'r') as config_file:
            return json.loads(config_file.read())

    @classmethod
    def _widevine_path(cls):
        ''' Get full widevine path '''
        widevine_cdm_filename = config.WIDEVINE_CDM_FILENAME[system_os()]
        if widevine_cdm_filename is None:
            return False

        widevine_path = os.path.join(cls._ia_cdm_path(), widevine_cdm_filename)
        if xbmcvfs.exists(widevine_path):
            return widevine_path

        return False

    @classmethod
    def _kodi_version(cls):
        ''' Return the current Kodi version '''
        version = xbmc.getInfoLabel('System.BuildVersion')
        return version.split(' ')[0]

    @classmethod
    def _arch(cls):
        """Map together and return the system architecture."""
        arch = platform.machine()
        if arch == 'aarch64' and (struct.calcsize('P') * 8) == 32:
            # Detected 64-bit kernel in 32-bit userspace, use 32-bit arm widevine
            arch = 'arm'
        if arch == 'AMD64':
            arch_bit = platform.architecture()[0]
            if arch_bit == '32bit':
                arch = 'x86'  # else, arch = AMD64
        elif 'armv' in arch:
            arm_version = re.search(r'\d+', arch.split('v')[1])
            if arm_version:
                arch = 'armv' + arm_version.group()
        if arch in config.ARCH_MAP:
            return config.ARCH_MAP[arch]

        return arch

    @staticmethod
    def _sizeof_fmt(num, suffix='B'):
        """Return size of file in a human readable string."""
        # https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

    @staticmethod
    def _cmd_exists(cmd):
        """Check whether cmd exists on system."""
        # https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
        return subprocess.call('type ' + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

    def _helper_disabled(self):
        """Return if inputstreamhelper has been disabled in settings.xml."""
        disabled = ADDON.getSetting('disabled')
        if disabled is None:
            self.disable()  # Create default entry
            disabled = 'true'

        if disabled == 'true':
            log('inputstreamhelper is disabled in settings.xml.')
            return True

        return False

    @staticmethod
    def disable():
        ''' Disable plugin '''
        if ADDON.getSetting('disabled') == 'false':
            ADDON.setSetting('disabled', 'true')

    @staticmethod
    def enable():
        ''' Enable plugin '''
        if ADDON.getSetting('disabled') == 'true':
            ADDON.setSetting('disabled', 'false')

    def _inputstream_version(self):
        ''' Return the requested inputstream version '''
        addon = xbmcaddon.Addon(self.inputstream_addon)
        return addon.getAddonInfo('version')

    def _chromeos_offset(self, bin_path):
        ''' Calculate the Chrome OS start offset using fdisk or parted '''
        # Prefer parted over fdisk because it is more reliable
        if self._cmd_exists('parted'):
            cmd = ['parted', '-s', bin_path, 'unit s print']
        else:
            cmd = ['fdisk', '-l', bin_path]

        header = None
        best_size = 0
        best_offset = 0
        output = self._run_cmd(cmd, sudo=False)
        if not output['success']:
            log('Failed to run: %s' % cmd)
            return False

        # Routine that works for both fdisk and parted
        for line in output['output'].splitlines():
            # Split by whitespace is not sufficient, some header titles use whitespace
            partition_data = list([_f for _f in re.split(r'\s{2,}', line) if _f])
            if not partition_data:
                continue

            # Find the Size and Start columns
            if 'Size' in partition_data and 'Start' in partition_data:
                header = partition_data
                continue
            elif 'Blocks' in partition_data and 'Start' in partition_data:
                header = partition_data
                continue

            # Discard data if we did not find a header
            if header is None:
                continue

            # Create a dictionary from header and data
            partition = dict(list(zip(header, partition_data)))
            if partition.get('Size') is None and partition.get('Blocks') is None or partition.get('Start') is None:
                continue

            # Find the largest partition, and store the offset
            # NOTE: For parted we need to remove the 's' unit
            partition_size = int((partition.get('Size') or partition.get('Blocks')).replace('s', ''))
            if partition.get('Name') == 'ROOT-A' or partition_size > best_size:
                # The name or id is always stored in the first column
                partition_name = partition_data[0]
                best_size = partition_size
                best_offset = int(partition.get('Start').replace('s', ''))
                if partition.get('Name') == 'ROOT-A':
                    log('Partition {partition} is named {name}, using offset {offset}', partition=partition_name, name='ROOT-A', offset=best_offset)
                    break
                else:
                    log('Partition {partition} is larger ({size}), using offset {offset}', partition=partition_name, size=best_size, offset=best_offset)

        if best_offset == 0:
            log('Failed to calculate partition offset.')
            return False

        return str(best_offset * config.CHROMEOS_BLOCK_SIZE)

    def _run_cmd(self, cmd, sudo=False, shell=False):
        ''' Run subprocess command and return if it succeeds as a bool '''
        if sudo and os.getuid() != 0 and self._cmd_exists('sudo'):
            cmd.insert(0, 'sudo')
        try:
            output = subprocess.check_output(cmd, shell=shell, stderr=subprocess.STDOUT)
            success = True
            log('{cmd} cmd executed successfully.', cmd=cmd)
        except subprocess.CalledProcessError as error:
            output = error.output
            success = False
            log('{cmd} cmd failed.', cmd=cmd)
        except OSError as error:
            output = ''
            success = False
            log('{cmd} cmd doesn\'t exist. {error}', cmd=cmd, error=error)
        if output.rstrip():
            log('{cmd} cmd output:\n{output}', cmd=cmd, output=output)
        if 'sudo' in cmd:
            subprocess.call(['sudo', '-k'])  # reset timestamp

        return {
            'output': output.decode(),
            'success': success
        }

    def _check_loop(self):
        """Check if loop module needs to be loaded into system."""
        if not self._run_cmd(['modinfo', 'loop'])['success']:
            log('loop is built in the kernel.')
            return True  # assume loop is built in the kernel

        self._modprobe_loop = True
        cmd = ['modprobe', '-q', 'loop']
        output = self._run_cmd(cmd, sudo=True)
        return output['success']

    def _set_loop_dev(self):
        """Set an unused loop device that's available for use."""
        cmd = ['losetup', '-f']
        output = self._run_cmd(cmd, sudo=False)
        if output['success']:
            self._loop_dev = output['output'].strip()
            log('Found free loop device: {device}', device=self._loop_dev)
            return True

        log('Failed to find free loop device.')
        return False

    def _losetup(self, bin_path):
        """Setup Chrome OS loop device."""
        cmd = ['losetup', '-o', self._chromeos_offset(bin_path), self._loop_dev, bin_path]
        output = self._run_cmd(cmd, sudo=True)
        if output['success']:
            self._attached_loop_dev = True
            return True

        return False

    def _mnt_loop_dev(self):
        """Mount loop device to self._mnt_path()"""
        cmd = ['mount', '-t', 'ext2', '-o', 'ro', self._loop_dev, self._mnt_path()]
        output = self._run_cmd(cmd, sudo=True)
        if output['success']:
            return True

        return False

    def _has_widevine(self):
        """Checks if Widevine CDM is installed on system."""
        if system_os() == 'Android':  # widevine is built in on android
            return True

        if self._widevine_path():
            log('Found Widevine binary at {path}', path=self._widevine_path().encode('utf-8'))
            return True

        log('Widevine is not installed.')
        return False

    @staticmethod
    def _json_rpc_request(payload):
        """Kodi JSON-RPC request. Return the response in a dictionary."""
        log('jsonrpc payload: {payload}', payload=payload)
        response = xbmc.executeJSONRPC(json.dumps(payload))
        log('jsonrpc response: {response}', response=response)

        return json.loads(response)

    @staticmethod
    def _http_get(url):
        ''' Perform an HTTP GET request and return content '''
        log('Request URL: {url}', url=url)
        try:
            req = urlopen(url)
            log('Response code: {code}', code=req.getcode())
            if 400 <= req.getcode() < 600:
                raise HTTPError('HTTP %s Error for url: %s' % (req.getcode(), url), response=req)
        except HTTPError:
            xbmcgui.Dialog().ok(localize(30004), localize(30013, filename=url.split('/')[-1]))  # Failed to retrieve file
            return None
        content = req.read()
        # NOTE: Do not log reponse (as could be large)
        # log('Response: {response}', response=content)
        return content.decode()

    def _http_download(self, url, message=None):
        """Makes HTTP request and displays a progress dialog on download."""
        log('Request URL: {url}', url=url)
        filename = url.split('/')[-1]
        try:
            req = urlopen(url)
            log('Response code: {code}', code=req.getcode())
            if 400 <= req.getcode() < 600:
                raise HTTPError('HTTP %s Error for url: %s' % (req.getcode(), url), response=req)
        except HTTPError:
            xbmcgui.Dialog().ok(localize(30004), localize(30013, filename=filename))  # Failed to retrieve file
            return False

        if not message:  # display "downloading [filename]"
            message = localize(30015, filename=filename)  # Downloading file

        self._download_path = os.path.join(self._temp_path(), filename)
        total_length = float(req.info().get('content-length'))
        progress_dialog = xbmcgui.DialogProgress()
        progress_dialog.create(localize(30014), message)  # Download in progress

        chunk_size = 32 * 1024
        with open(self._download_path, 'wb') as f:
            dl = 0
            while True:
                chunk = req.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                dl += len(chunk)
                percent = int(dl * 100 / total_length)
                if progress_dialog.iscanceled():
                    progress_dialog.close()
                    req.close()
                    return False
                progress_dialog.update(percent)

        progress_dialog.close()
        return True

    def _has_inputstream(self):
        """Checks if selected InputStream add-on is installed."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': self.inputstream_addon
            }
        }
        data = self._json_rpc_request(payload)
        if 'error' in data:
            log('{addon} is not installed.', addon=self.inputstream_addon)
            return False

        log('{addon} is installed.', addon=self.inputstream_addon)
        return True

    def _inputstream_enabled(self):
        """Returns whether selected InputStream add-on is enabled.."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': self.inputstream_addon,
                'properties': ['enabled']
            }
        }
        data = self._json_rpc_request(payload)
        if data['result']['addon']['enabled']:
            log('{addon} {version} is enabled.', addon=self.inputstream_addon, version=self._inputstream_version())
            return True

        log('{addon} is disabled.', addon=self.inputstream_addon)
        return False

    def _enable_inputstream(self):
        """Enables selected InputStream add-on."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.SetAddonEnabled',
            'params': {
                'addonid': self.inputstream_addon,
                'enabled': True
            }
        }
        data = self._json_rpc_request(payload)
        if 'error' in data:
            return False

        return True

    def _supports_widevine(self):
        """Checks if Widevine is supported on the architecture/operating system/Kodi version."""
        if self._arch() not in config.WIDEVINE_SUPPORTED_ARCHS:
            log('Unsupported Widevine architecture found: {arch}', arch=self._arch())
            xbmcgui.Dialog().ok(localize(30004), localize(30007))  # Widevine not available on this architecture
            return False

        if system_os() not in config.WIDEVINE_SUPPORTED_OS:
            log('Unsupported Widevine OS found: {os}', os=system_os())
            xbmcgui.Dialog().ok(localize(30004), localize(30011, os=system_os()))  # Operating system not supported by Widevine
            return False

        if LooseVersion(config.WIDEVINE_MINIMUM_KODI_VERSION[system_os()]) > LooseVersion(self._kodi_version()):
            log('Unsupported Kodi version for Widevine: {version}', version=self._kodi_version())
            xbmcgui.Dialog().ok(localize(30004), localize(30010, version=config.WIDEVINE_MINIMUM_KODI_VERSION[system_os()]))  # Kodi too old
            return False

        if 'WindowsApps' in xbmc.translatePath('special://xbmcbin/'):  # uwp is not supported
            log('Unsupported UWP Kodi version detected.')
            xbmcgui.Dialog().ok(localize(30004), localize(30012))  # Windows Store Kodi falls short
            return False

        return True

    @staticmethod
    def _select_best_chromeos_image(devices):
        log('Find best ARM image to use from recovery.conf')

        best = None
        for device in devices:
            # Select ARM hardware only
            for arm_hwid in config.CHROMEOS_RECOVERY_ARM_HWIDS:
                if arm_hwid in device['hwidmatch']:
                    hwid = arm_hwid
                    break  # We found an ARM device, rejoice !
            else:
                continue  # Not ARM, skip this device

            device['hwid'] = hwid

            # Select the first ARM device
            if best is None:
                best = device
                continue  # Go to the next device

            # Skip identical hwid
            if hwid == best['hwid']:
                continue

            # Select the newest version
            if LooseVersion(device['version']) > LooseVersion(best['version']):
                log('{device[hwid]} ({device[version]}) is newer than {best[hwid]} ({best[version]})', device=device, best=best)  # pylint: disable=invalid-format-index
                best = device

            # Select the smallest image (disk space requirement)
            elif LooseVersion(device['version']) == LooseVersion(best['version']):
                if int(device['filesize']) + int(device['zipfilesize']) < int(best['filesize']) + int(best['zipfilesize']):
                    log('{device[hwid]} ({device_size}) is smaller than {best[hwid]} ({best_size})', device=device, best=best, device_size=int(device['filesize']) + int(device['zipfilesize']), best_size=int(best['filesize']) + int(best['zipfilesize']))  # pylint: disable=invalid-format-index
                    best = device

        return best

    def _latest_widevine_version(self, eula=False):
        """Returns the latest available version of Widevine CDM/Chrome OS."""
        if eula:
            url = config.WIDEVINE_VERSIONS_URL
            versions = self._http_get(url)
            return versions.split()[-1]

        ADDON.setSetting('last_update', str(time.mktime(datetime.utcnow().timetuple())))
        if 'x86' in self._arch():
            url = config.WIDEVINE_VERSIONS_URL
            versions = self._http_get(url)
            return versions.split()[-1]

        devices = self._chromeos_config()
        arm_device = self._select_best_chromeos_image(devices)
        if arm_device is None:
            log('We could not find an ARM device in recovery.conf')
            xbmcgui.Dialog().ok(localize(30004), localize(30005))
            return ''
        return arm_device['version']

    def _chromeos_config(self):
        ''' Parse the Chrome OS recovery configuration and put it in a dictionary '''
        url = config.CHROMEOS_RECOVERY_URL
        conf = [x for x in self._http_get(url).split('\n\n') if 'hwidmatch=' in x]

        devices = []
        for device in conf:
            device_dict = dict()
            for device_info in device.splitlines():
                if not device_info:
                    continue
                try:
                    key, value = device_info.split('=')
                    device_dict[key] = value
                except ValueError:
                    continue
            devices.append(device_dict)

        return devices

    def _install_widevine_x86(self):
        """Install Widevine CDM on x86 based architectures."""
        cdm_version = self._latest_widevine_version()
        cdm_os = config.WIDEVINE_OS_MAP[system_os()]
        cdm_arch = config.WIDEVINE_ARCH_MAP_X86[self._arch()]
        url = config.WIDEVINE_DOWNLOAD_URL.format(version=cdm_version, os=cdm_os, arch=cdm_arch)

        downloaded = self._http_download(url)
        if downloaded:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(heading=localize(30043), line1=localize(30044))  # Extracting Widevine CDM
            progress_dialog.update(94, line1=localize(30049))  # Installing Widevine CDM
            self._unzip(self._ia_cdm_path())

            progress_dialog.update(97, line1=localize(30050))  # Finishing
            self._cleanup()
            if not self._widevine_eula():
                return False

            if self._has_widevine():
                if os.path.lexists(self._widevine_config_path()):
                    os.remove(self._widevine_config_path())
                os.rename(os.path.join(self._ia_cdm_path(), config.WIDEVINE_MANIFEST_FILE), self._widevine_config_path())
                wv_check = self._check_widevine()
                if wv_check:
                    progress_dialog.update(100, line1=localize(30051))  # Widevine CDM successfully installed.
                    xbmcgui.Dialog().notification(localize(30037), localize(30051))  # Success! Widevine successfully installed.
                progress_dialog.close()
                return wv_check

            progress_dialog.close()
            xbmcgui.Dialog().ok(localize(30004), localize(30005))  # An error occurred

        return False

    def _install_widevine_arm(self):
        """Installs Widevine CDM on ARM-based architectures."""
        root_cmds = ['mount', 'umount', 'losetup', 'modprobe']
        devices = self._chromeos_config()
        arm_device = self._select_best_chromeos_image(devices)
        if arm_device is None:
            log('We could not find an ARM device in recovery.conf')
            xbmcgui.Dialog().ok(localize(30004), localize(30005))
            return ''
        required_diskspace = int(arm_device['filesize']) + int(arm_device['zipfilesize'])
        if xbmcgui.Dialog().yesno(localize(30001),  # Due to distributing issues, this takes a long time
                                  localize(30006, diskspace=self._sizeof_fmt(required_diskspace))) and self._widevine_eula():
            if system_os() != 'Linux':
                xbmcgui.Dialog().ok(localize(30004), localize(30019, os=system_os()))
                return False

            if required_diskspace >= self._diskspace():
                xbmcgui.Dialog().ok(localize(30004),  # Not enough free disk space
                                    localize(30018, diskspace=self._sizeof_fmt(required_diskspace)))
                return False

            if not self._cmd_exists('fdisk') and not self._cmd_exists('parted'):
                xbmcgui.Dialog().ok(localize(30004), localize(30020, command1='fdisk', command2='parted'))  # Commands are missing
                return False

            if not self._cmd_exists('mount'):
                xbmcgui.Dialog().ok(localize(30004), localize(30021, command='mount'))  # Mount command is missing
                return False

            if not self._cmd_exists('losetup'):
                xbmcgui.Dialog().ok(localize(30004), localize(30021, command='losetup'))  # Losetup command is missing
                return False

            if os.getuid() != 0:  # ask for permissions to run cmds as root
                if not xbmcgui.Dialog().yesno(localize(30001), localize(30030, cmds=', '.join(root_cmds)), yeslabel=localize(30027), nolabel=localize(30028)):
                    return False

            # Clean up any remaining mounts
            self._unmount()

            url = arm_device['url']
            downloaded = self._http_download(url, message=localize(30022))  # Downloading the recovery image
            if downloaded:
                progress_dialog = xbmcgui.DialogProgress()
                progress_dialog.create(heading=localize(30043), line1=localize(30044))  # Extracting Widevine CDM
                bin_filename = url.split('/')[-1].replace('.zip', '')
                bin_path = os.path.join(self._temp_path(), bin_filename)

                progress_dialog.update(5, line1=localize(30045), line2=localize(30046), line3=localize(30047))  # Uncompressing image
                success = [
                    self._unzip(self._temp_path(), bin_filename),
                    self._check_loop(),
                    self._set_loop_dev(),
                    self._losetup(bin_path),
                    self._mnt_loop_dev(),
                ]
                if all(success):
                    progress_dialog.update(91, line1=localize(30048))  # Extracting Widevine CDM
                    self._extract_widevine_from_img()
                    progress_dialog.update(94, line1=localize(30049))  # Installing Widevine CDM
                    progress_dialog.update(97, line1=localize(30050))  # Finishing
                    self._cleanup()
                    if self._has_widevine():
                        with open(self._widevine_config_path(), 'w') as config_file:
                            config_file.write(json.dumps(devices, indent=4))
                        wv_check = self._check_widevine()
                        if wv_check:
                            progress_dialog.update(100, line1=localize(30051))  # Widevine CDM successfully installed.
                            xbmcgui.Dialog().notification(localize(30037), localize(30051))  # Success! Widevine CDM successfully installed.
                        progress_dialog.close()
                        return wv_check
                else:
                    progress_dialog.update(100, line1=localize(30050))  # Finishing
                    self._cleanup()

                progress_dialog.close()
                xbmcgui.Dialog().ok(localize(30004), localize(30005))  # An error occurred

        return False

    def install_widevine(self):
        ''' Wrapper function that calls Widevine installer method depending on architecture '''
        if not self._supports_widevine():
            return False

        if 'x86' in self._arch():
            return self._install_widevine_x86()

        return self._install_widevine_arm()

    def remove_widevine(self):
        """Removes Widevine CDM"""
        widevinecdm = self._widevine_path()
        if widevinecdm and xbmcvfs.exists(widevinecdm):
            log('Remove Widevine CDM at {path}', path=widevinecdm)
            xbmcvfs.delete(widevinecdm)
            xbmcgui.Dialog().notification(localize(30037), localize(30052))  # Success! Widevine successfully removed.
            return True
        xbmcgui.Dialog().notification(localize(30004), localize(30053))  # Error. Widevine CDM not found.
        return False

    @staticmethod
    def _first_run():
        """Check if this add-on version is running for the first time"""

        # Get versions
        settings_version = ADDON.getSetting('version')
        if settings_version == '':
            settings_version = '0.3.4'  # settings_version didn't exist in version 0.3.4 and older
        addon_version = ADDON.getAddonInfo('version')

        # Compare versions
        if LooseVersion(addon_version) > LooseVersion(settings_version):
            # New version found, save addon_version to settings
            ADDON.setSetting('version', addon_version)
            log('inputstreamhelper version {version} is running for the first time', version=addon_version)
            return True
        return False

    def _update_widevine(self):
        """Prompts user to upgrade Widevine CDM when a newer version is available."""
        last_update = ADDON.getSetting('last_update')
        if last_update and not self._first_run():
            last_update_dt = datetime.fromtimestamp(float(ADDON.getSetting('last_update')))
            if last_update_dt + timedelta(days=config.WIDEVINE_UPDATE_INTERVAL_DAYS) >= datetime.utcnow():
                log('Widevine update check was made on {date}', date=last_update_dt.isoformat())
                return

        wv_config = self._load_widevine_config()
        latest_version = self._latest_widevine_version()
        if 'x86' in self._arch():
            component = 'Widevine CDM'
            current_version = wv_config['version']
        else:
            component = 'Chrome OS'
            current_version = self._select_best_chromeos_image(wv_config)['version']
        log('Latest {component} version is {version}', component=component, version=latest_version)
        log('Current {component} version installed is {version}', component=component, version=current_version)

        if LooseVersion(latest_version) > LooseVersion(current_version):
            log('There is an update available for {component}', component=component)
            if xbmcgui.Dialog().yesno(localize(30040), localize(30033), yeslabel=localize(30034), nolabel=localize(30028)):
                self.install_widevine()
            else:
                log('User declined to update {component}.', component=component)
        else:
            log('User is on the latest available {component} version.', component=component)

    def _widevine_eula(self):
        """Displays the Widevine EULA and prompts user to accept it."""
        if os.path.exists(os.path.join(self._ia_cdm_path(), config.WIDEVINE_LICENSE_FILE)):
            license_file = os.path.join(self._ia_cdm_path(), config.WIDEVINE_LICENSE_FILE)
            with open(license_file, 'r') as f:
                eula = f.read().strip().replace('\n', ' ')
        else:  # grab the license from the x86 files
            log('Acquiring Widevine EULA from x86 files.')
            url = config.WIDEVINE_DOWNLOAD_URL.format(version=self._latest_widevine_version(eula=True), os='mac', arch='x64')
            downloaded = self._http_download(url, message=localize(30025))  # Acquiring EULA
            if not downloaded:
                return False

            with zipfile.ZipFile(self._download_path) as z:
                with z.open(config.WIDEVINE_LICENSE_FILE) as f:
                    eula = f.read().decode().strip().replace('\n', ' ')

        return xbmcgui.Dialog().yesno(localize(30026), eula, yeslabel=localize(30027), nolabel=localize(30028))  # Widevine CDM EULA

    def _extract_widevine_from_img(self):
        ''' Extract the Widevine CDM binary from the mounted Chrome OS image '''
        for root, dirs, files in os.walk(str(self._mnt_path())):  # pylint: disable=unused-variable
            if 'libwidevinecdm.so' not in files:
                continue
            cdm_path = os.path.join(root, 'libwidevinecdm.so')
            log('Found libwidevinecdm.so in {path}', path=cdm_path)
            shutil.copyfile(cdm_path, os.path.join(self._ia_cdm_path(), 'libwidevinecdm.so'))
            return True

        log('Failed to find Widevine CDM binary in Chrome OS image.')
        return False

    def _missing_widevine_libs(self):
        """Parses ldd output of libwidevinecdm.so and displays dialog if any depending libraries are missing."""
        if system_os() != 'Linux':  # this should only be needed for linux
            return None

        if self._cmd_exists('ldd'):
            if not os.access(self._widevine_path(), os.X_OK):
                log('Changing {path} permissions to 744.', path=self._widevine_path())
                os.chmod(self._widevine_path(), 0o744)

            missing_libs = []
            cmd = ['ldd', self._widevine_path()]
            output = self._run_cmd(cmd, sudo=False)
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

        if self._arch() == 'arm64' and (struct.calcsize('P') * 8) == 64:
            log('ARM64 ldd check failed. User needs 32-bit userspace.')
            xbmcgui.Dialog().ok(localize(30004), localize(30039))  # Widevine not available on ARM64

        log('Failed to check for missing Widevine libraries.')
        return None

    def _check_widevine(self):
        """Checks that all Widevine components are installed and available."""
        if system_os() == 'Android':  # no checks needed for Android
            return True

        if not os.path.exists(self._widevine_config_path()):
            log('Widevine or recovery config is missing. Reinstall is required.')
            xbmcgui.Dialog().ok(localize(30001), localize(30031))  # An update of Widevine is required
            return self.install_widevine()

        if 'x86' in self._arch():  # check that widevine arch matches system arch
            wv_config = self._load_widevine_config()
            if config.WIDEVINE_ARCH_MAP_X86[self._arch()] != wv_config['arch']:
                log('Widevine/system arch mismatch. Reinstall is required.')
                xbmcgui.Dialog().ok(localize(30001), localize(30031))  # An update of Widevine is required
                return self.install_widevine()

        if self._missing_widevine_libs():
            xbmcgui.Dialog().ok(localize(30004), localize(30032, libs=', '.join(self._missing_widevine_libs())))  # Missing libraries
            return False

        self._update_widevine()
        return True

    def _unzip(self, unzip_dir, file_to_unzip=None):
        ''' Unzip files to specified path '''
        ret = False

        zip_obj = zipfile.ZipFile(self._download_path)
        for filename in zip_obj.namelist():
            if file_to_unzip and filename != file_to_unzip:
                continue

            # Detect and remove (dangling) symlinks before extraction
            fullname = os.path.join(unzip_dir, filename)
            if os.path.islink(fullname):
                log('Remove (dangling) symlink at {symlink}', symlink=fullname)
                os.unlink(fullname)

            zip_obj.extract(filename, unzip_dir)
            ret = True

        return ret

    def _unmount(self):
        ''' Unmount mountpoint if mounted '''
        while os.path.ismount(self._mnt_path()):
            log('Unmount {mountpoint}', mountpoint=self._mnt_path())
            umount_output = self._run_cmd(['umount', self._mnt_path()], sudo=True)
            if not umount_output['success']:
                break

    def _cleanup(self):
        ''' Clean up function after Widevine CDM installation '''
        self._unmount()
        if self._attached_loop_dev:
            cmd = ['losetup', '-d', self._loop_dev]
            unattach_output = self._run_cmd(cmd, sudo=True)
            if unattach_output['success']:
                self._loop_dev = False
        if self._modprobe_loop:
            xbmcgui.Dialog().notification(localize(30035), localize(30036))  # Unload by hand in CLI
        if not self._has_widevine():
            shutil.rmtree(self._ia_cdm_path())

        shutil.rmtree(self._temp_path())
        return True

    def _supports_hls(self):
        """Return if HLS support is available in inputstream.adaptive."""
        if LooseVersion(self._inputstream_version()) >= LooseVersion(config.HLS_MINIMUM_IA_VERSION):
            return True

        log('HLS is unsupported on {addon} version {version}', addon=self.inputstream_addon, version=self._inputstream_version())
        return False

    def _check_drm(self):
        """Main function for ensuring that specified DRM system is installed and available."""
        if not self.drm or self.inputstream_addon != 'inputstream.adaptive':
            return True

        if self.drm != 'widevine':
            return True

        if self._has_widevine():
            return self._check_widevine()

        if xbmcgui.Dialog().yesno(localize(30041), localize(30002), yeslabel=localize(30038), nolabel=localize(30028)):  # Widevine required
            return self.install_widevine()

        return False

    def _install_inputstream(self):
        """Install inputstream addon."""
        try:
            # See if there's an installed repo that has it
            xbmc.executebuiltin('InstallAddon({})'.format(self.inputstream_addon), wait=True)

            # Check if InputStream add-on exists!
            xbmcaddon.Addon('{}'.format(self.inputstream_addon))

            log('inputstream addon installed from repo')
            return True
        except RuntimeError:
            log('inputstream addon not installed')
            return False

    def check_inputstream(self):
        """Main function. Ensures that all components are available for InputStream add-on playback."""
        if self._helper_disabled():  # blindly return True if helper has been disabled
            return True
        if self.drm == 'widevine' and not self._supports_widevine():
            return False
        if not self._has_inputstream():
            # Try to install InputStream add-on
            if not self._install_inputstream():
                xbmcgui.Dialog().ok(localize(30004), localize(30008, addon=self.inputstream_addon))  # inputstream is missing on system
                return False
        elif not self._inputstream_enabled():
            ok = xbmcgui.Dialog().yesno(localize(30001), localize(30009, addon=self.inputstream_addon))  # inputstream is disabled
            if ok:
                self._enable_inputstream()
            return False
        log('{addon} {version} is installed and enabled.', addon=self.inputstream_addon, version=self._inputstream_version())

        if self.protocol == 'hls' and not self._supports_hls():
            xbmcgui.Dialog().ok(localize(30004),  # HLS Minimum version is needed
                                localize(30017, addon=self.inputstream_addon, version=config.HLS_MINIMUM_IA_VERSION))
            return False

        return self._check_drm()

    @staticmethod
    def _get_global_setting(setting):
        json_result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": {"setting": "%s"}, "id": 1}' % setting)
        return json.loads(json_result)['result']['value']

    def _get_proxies(self):
        usehttpproxy = self._get_global_setting('network.usehttpproxy')
        if usehttpproxy is False:
            return None

        httpproxytype = self._get_global_setting('network.httpproxytype')

        socks_supported = has_socks()
        if httpproxytype != 0 and not socks_supported:
            # Only open the dialog the first time (to avoid multiple popups)
            if socks_supported is None:
                xbmcgui.Dialog().ok('', localize(30042))  # Requires PySocks
            return None

        proxy_types = ['http', 'socks4', 'socks4a', 'socks5', 'socks5h']
        if 0 <= httpproxytype <= 5:
            httpproxyscheme = proxy_types[httpproxytype]
        else:
            httpproxyscheme = 'http'

        httpproxyserver = self._get_global_setting('network.httpproxyserver')
        httpproxyport = self._get_global_setting('network.httpproxyport')
        httpproxyusername = self._get_global_setting('network.httpproxyusername')
        httpproxypassword = self._get_global_setting('network.httpproxypassword')

        if httpproxyserver and httpproxyport and httpproxyusername and httpproxypassword:
            proxy_address = '%s://%s:%s@%s:%s' % (httpproxyscheme, httpproxyusername, httpproxypassword, httpproxyserver, httpproxyport)
        elif httpproxyserver and httpproxyport and httpproxyusername:
            proxy_address = '%s://%s@%s:%s' % (httpproxyscheme, httpproxyusername, httpproxyserver, httpproxyport)
        elif httpproxyserver and httpproxyport:
            proxy_address = '%s://%s:%s' % (httpproxyscheme, httpproxyserver, httpproxyport)
        elif httpproxyserver:
            proxy_address = '%s://%s' % (httpproxyscheme, httpproxyserver)
        else:
            return None

        return dict(http=proxy_address, https=proxy_address)

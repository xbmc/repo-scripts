import os
import platform
import zipfile
import json
import time
import subprocess
import shutil
from distutils.version import LooseVersion
from datetime import datetime, timedelta

import requests

import config

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon('script.module.inputstreamhelper')
ADDON_PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))
LANGUAGE = ADDON.getLocalizedString


class Helper(object):
    def __init__(self, protocol, drm=None):
        self._log('Platform information: {0}'.format(platform.uname()))

        self._url = None
        self._download_path = None
        self._loop_dev = None
        self._attached_loop_dev = False
        self._mounted = False

        self.protocol = protocol
        self.drm = drm

        if self.protocol not in config.INPUTSTREAM_PROTOCOLS:
            raise self.InputStreamException('UnsupportedProtocol')
        else:
            self._inputstream_addon = config.INPUTSTREAM_PROTOCOLS[self.protocol]

        if self.drm:
            if self.drm not in config.DRM_SCHEMES:
                raise self.InputStreamException('UnsupportedDRMScheme')
            else:
                self.drm = config.DRM_SCHEMES[drm]

    def __repr__(self):
        return 'Helper({0}, drm={1})'.format(self.protocol, self.drm)

    class InputStreamException(Exception):
        pass

    @staticmethod
    def sizeof_fmt(num, suffix='B'):
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

    @classmethod
    def _diskspace(cls):
        """Return the free disk space available (in bytes) in cdm_path."""
        statvfs = os.statvfs(cls._addon_cdm_path())
        return statvfs.f_frsize * statvfs.f_bavail

    @classmethod
    def _temp_path(cls):
        temp_path = os.path.join(ADDON_PROFILE, 'tmp')
        if not xbmcvfs.exists(temp_path):
            xbmcvfs.mkdir(temp_path)

        return temp_path

    @classmethod
    def _mnt_path(cls):
        mnt_path = os.path.join(cls._temp_path(), 'mnt')
        if not xbmcvfs.exists(mnt_path):
            xbmcvfs.mkdir(mnt_path)

        return mnt_path

    @classmethod
    def _addon_cdm_path(cls):
        cdm_path = os.path.join(ADDON_PROFILE, 'cdm')
        if not xbmcvfs.exists(cdm_path):
            xbmcvfs.mkdir(cdm_path)

        return cdm_path

    @classmethod
    def _ia_cdm_path(cls):
        """Return the specified CDM path for inputstream.adaptive."""
        addon = xbmcaddon.Addon('inputstream.adaptive')
        cdm_path = xbmc.translatePath(addon.getSetting('DECRYPTERPATH'))
        if not xbmcvfs.exists(cdm_path):
            xbmcvfs.mkdir(cdm_path)

        return cdm_path

    @classmethod
    def _widevine_config_path(cls):
        return os.path.join(cls._addon_cdm_path(), config.WIDEVINE_CONFIG_NAME)

    @classmethod
    def _load_widevine_config(cls):
        with open(cls._widevine_config_path(), 'r') as config_file:
            return json.loads(config_file.read())

    @classmethod
    def _widevine_path(cls):
        for filename in os.listdir(cls._ia_cdm_path()):
            if 'widevine' in filename and filename.endswith(config.CDM_EXTENSIONS):
                return os.path.join(cls._ia_cdm_path(), filename)

        return False

    @classmethod
    def _kodi_version(cls):
        version = xbmc.getInfoLabel('System.BuildVersion')
        return version.split(' ')[0]

    @classmethod
    def _arch(cls):
        """Map together and return the system architecture."""
        arch = platform.machine()
        if arch == 'AMD64':
            arch_bit = platform.architecture()[0]
            if arch_bit == '32bit':
                arch = 'x86'
            else:
                arch = 'x86_64'
        elif 'armv' in arch:
            arch = 'armv' + arch.split('v')[1][:-1]
        if arch in config.X86_MAP:
            return config.X86_MAP[arch]
        elif arch in config.ARM_MAP:
            return config.ARM_MAP[arch]

        return arch

    @classmethod
    def _os(cls):
        if xbmc.getCondVisibility('system.platform.android'):
            return 'Android'

        return platform.system()

    def _inputstream_version(self):
        addon = xbmcaddon.Addon(self._inputstream_addon)
        return addon.getAddonInfo('version')

    def _log(self, string):
        """InputStream Helper log method."""
        logging_prefix = '[{0}-{1}]'.format(ADDON.getAddonInfo('id'), ADDON.getAddonInfo('version'))
        msg = '{0}: {1}'.format(logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def _parse_chromeos_offset(self, bin_path):
        """Calculate the Chrome OS losetup start offset using fdisk/parted."""
        if self._cmd_exists('fdisk'):
            cmd = ['fdisk', bin_path, '-l']
        else:  # parted
            cmd = ['parted', '-s', bin_path, 'unit s print']
        self._log('losetup calculation cmd: {0}'.format(cmd))

        output = subprocess.check_output(cmd)
        self._log('losetup calculation output: \n{0}'.format(output))
        for line in output.splitlines():
            partition_data = line.split()
            if partition_data:
                if partition_data[0] == '3' or '.bin3' in partition_data[0]:
                    offset = int(partition_data[1].replace('s', ''))
                    return str(offset * config.CHROMEOS_BLOCK_SIZE)

        self._log('Failed to calculate losetup offset.')
        return False

    def _run_cmd(self, cmd, sudo=False, ask=True):
        """Run subprocess command and return if it succeeds as a bool."""
        dialog = xbmcgui.Dialog()
        if ask and os.getuid() != 0 and not dialog.yesno(LANGUAGE(30001), LANGUAGE(30030), yeslabel=LANGUAGE(30029),
                                                         nolabel=LANGUAGE(30028)):
            self._log('User refused to give sudo permissions.')
            return cmd
        if sudo and os.getuid() != 0 and self._cmd_exists('sudo'):
            cmd.insert(0, 'sudo')

        try:
            subprocess.check_output(cmd)
            self._log('{0} cmd executed successfully.'.format(cmd))
            success = True
        except subprocess.CalledProcessError, error:
            self._log('cmd failed with output: {0}'.format(error.output))
            success = False
        if 'sudo' in cmd:
            subprocess.call(['sudo', '-k'])  # reset timestamp

        return success

    def _set_loop_dev(self):
        """Set an unused loop device that's available for use."""
        cmd = ['losetup', '-f']
        self._loop_dev = subprocess.check_output(cmd).strip()
        self._log('Found free loop device: {0}'.format(self._loop_dev))
        return True

    def _losetup(self, bin_path):
        """Setup Chrome OS loop device."""
        cmd = ['losetup', self._loop_dev, bin_path, '-o', self._parse_chromeos_offset(bin_path)]
        success = self._run_cmd(cmd, sudo=True, ask=True)
        if success:
            self._attached_loop_dev = True
            return True
        else:
            return False

    def _mnt_loop_dev(self):
        """Mount loop device to self._mnt_path()"""
        cmd = ['mount', '-t', 'ext2', self._loop_dev, '-o', 'ro', self._mnt_path()]
        success = self._run_cmd(cmd, sudo=True, ask=False)
        if success:
            self._mounted = True
            return True
        else:
            return False

    def _has_widevine(self):
        """Checks if Widevine CDM is installed on system."""
        if self._os() == 'Android':  # widevine is built in on android
            return True
        else:
            if self._widevine_path():
                self._log('Found Widevine binary at {0}'.format(self._widevine_path()))
                return True
            else:
                self._log('Widevine is not installed.')
                return False

    def _json_rpc_request(self, payload):
        """Kodi JSON-RPC request. Return the response in a dictionary."""
        self._log('jsonrpc payload: {0}'.format(payload))
        response = xbmc.executeJSONRPC(json.dumps(payload))
        self._log('jsonrpc response: {0}'.format(response))

        return json.loads(response)

    def _http_request(self, download=False, message=None):
        """Makes HTTP request and displays a progress dialog on download."""
        self._log('Request URL: {0}'.format(self._url))
        filename = self._url.split('/')[-1]
        dialog = xbmcgui.Dialog()

        try:
            req = requests.get(self._url, stream=download)
            self._log('Response code: {0}'.format(req.status_code))
            if not download:
                self._log('Response: {0}'.format(req.content))
            req.raise_for_status()
        except requests.exceptions.HTTPError:
            dialog.ok(LANGUAGE(30004), LANGUAGE(30013).format(filename))
            return False

        if download:
            if not message:  # display "downloading [filename]"
                message = LANGUAGE(30015).format(filename)
            self._download_path = os.path.join(self._temp_path(), filename)
            total_length = float(req.headers.get('content-length'))
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(LANGUAGE(30014), message)

            with open(self._download_path, 'wb') as f:
                dl = 0
                for chunk in req.iter_content(chunk_size=1024):
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
        else:
            return req.content

    def _has_inputstream(self):
        """Checks if selected InputStream add-on is installed."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': self._inputstream_addon
            }
        }
        data = self._json_rpc_request(payload)
        if 'error' in data:
            return False
        else:
            return True

    def _inputstream_enabled(self):
        """Returns whether selected InputStream add-on is enabled.."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': self._inputstream_addon,
                'properties': ['enabled']
            }
        }
        data = self._json_rpc_request(payload)
        return data['result']['addon']['enabled']

    def _enable_inputstream(self):
        """Enable selected InputStream add-on."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.SetAddonEnabled',
            'params': {
                'addonid': self._inputstream_addon,
                'enabled': True
            }
        }
        data = self._json_rpc_request(payload)
        if 'error' in data:
            return False
        else:
            return True

    def _supports_widevine(self):
        """Check if Widevine is supported on the architecture/operating system/Kodi version."""
        dialog = xbmcgui.Dialog()
        if self._arch() not in config.WIDEVINE_SUPPORTED_ARCHS:
            self._log('Unsupported Widevine architecture found: {0}'.format(self._arch()))
            dialog.ok(LANGUAGE(30004), LANGUAGE(30007))
            return False
        if self._os() not in config.WIDEVINE_SUPPORTED_OS:
            self._log('Unsupported Widevine OS found: {0}'.format(self._os()))
            dialog.ok(LANGUAGE(30004), LANGUAGE(30011).format(self._os()))
            return False
        if LooseVersion(config.WIDEVINE_MINIMUM_KODI_VERSION[self._os()]) > LooseVersion(self._kodi_version()):
            self._log('Unsupported Kodi version for Widevine: {0}'.format(self._kodi_version()))
            dialog.ok(LANGUAGE(30004), LANGUAGE(30010).format(config.WIDEVINE_MINIMUM_KODI_VERSION[self._os()]))
            return False
        if 'WindowsApps' in xbmc.translatePath('special://xbmcbin/'):  # uwp is not supported
            self._log('Unsupported UWP Kodi version detected.')
            dialog.ok(LANGUAGE(30004), LANGUAGE(30012))
            return False

        return True

    def _latest_widevine_version(self, eula=False):
        """Return the latest available version of Widevine CDM/Chrome OS."""
        datetime_obj = datetime.utcnow()
        ADDON.setSetting('last_update', str(time.mktime(datetime_obj.timetuple())))
        if 'x86' in self._arch() or eula:
            if LooseVersion(self._kodi_version()) < LooseVersion('18.0'):
                return config.WIDEVINE_LEGACY_VERSION
            else:
                self._url = config.WIDEVINE_CURRENT_VERSION_URL
                return self._http_request()
        else:
            return [x for x in self._chromeos_config() if config.CHROMEOS_ARM_HWID in x['hwidmatch']][0]['version']

    def _chromeos_config(self):
        """Parse the Chrome OS recovery configuration and put it in a dictionary."""
        devices = []
        if LooseVersion(self._kodi_version()) < LooseVersion('18.0'):
            self._url = config.CHROMEOS_RECOVERY_URL_LEGACY
        else:
            self._url = config.CHROMEOS_RECOVERY_URL
        conf = [x for x in self._http_request().split('\n\n') if 'hwidmatch=' in x]
        for device in conf:
            device_dict = {}
            for device_info in device.splitlines():
                key_value = device_info.split('=')
                key = key_value[0]
                if len(key_value) > 1:  # some keys have empty values
                    value = key_value[1]
                    device_dict[key] = value
            devices.append(device_dict)

        self._log('chromeos devices: \n{0}'.format(devices))
        return devices

    def _install_widevine_x86(self):
        """Install Widevine CDM on x86 based architectures."""
        dialog = xbmcgui.Dialog()
        cdm_version = self._latest_widevine_version()
        cdm_os = config.WIDEVINE_OS_MAP[self._os()]
        cdm_arch = config.WIDEVINE_ARCH_MAP_X86[self._arch()]
        self._url = config.WIDEVINE_DOWNLOAD_URL.format(cdm_version, cdm_os, cdm_arch)

        downloaded = self._http_request(download=True)
        if downloaded:
            busy_dialog = xbmcgui.DialogBusy()
            busy_dialog.create()
            self._unzip(self._addon_cdm_path())
            if self._widevine_eula():
                self._install_cdm()
                self._cleanup()
            else:
                self._cleanup()
                return False

            if self._has_widevine():
                if os.path.lexists(self._widevine_config_path()):
                    os.remove(self._widevine_config_path())
                os.rename(os.path.join(self._addon_cdm_path(), config.WIDEVINE_MANIFEST_FILE),
                          self._widevine_config_path())
                dialog.ok(LANGUAGE(30001), LANGUAGE(30003))
                busy_dialog.close()
                return self._check_widevine()
            else:
                busy_dialog.close()
                dialog.ok(LANGUAGE(30004), LANGUAGE(30005))

        return False

    def _install_widevine_arm(self):
        """Install Widevine CDM on ARM-based architectures."""
        cos_config = self._chromeos_config()
        device = [x for x in cos_config if config.CHROMEOS_ARM_HWID in x['hwidmatch']][0]
        required_diskspace = int(device['filesize']) + int(device['zipfilesize'])
        dialog = xbmcgui.Dialog()
        if dialog.yesno(LANGUAGE(30001),
                        LANGUAGE(30006).format(self.sizeof_fmt(required_diskspace))) and self._widevine_eula():
            if self._os() != 'Linux':
                dialog.ok(LANGUAGE(30004), LANGUAGE(30019).format(self._os()))
                return False
            if required_diskspace >= self._diskspace():
                dialog.ok(LANGUAGE(30004),
                          LANGUAGE(30018).format(self.sizeof_fmt(required_diskspace)))
                return False
            if not self._cmd_exists('fdisk') and not self._cmd_exists('parted'):
                dialog.ok(LANGUAGE(30004), LANGUAGE(30020).format('fdisk', 'parted'))
                return False
            if not self._cmd_exists('mount'):
                dialog.ok(LANGUAGE(30004), LANGUAGE(30021).format('mount'))
                return False
            if not self._cmd_exists('losetup'):
                dialog.ok(LANGUAGE(30004), LANGUAGE(30021).format('losetup'))
                return False

            self._url = device['url']
            downloaded = self._http_request(download=True, message=LANGUAGE(30022))
            if downloaded:
                dialog.ok(LANGUAGE(30023), LANGUAGE(30024))
                busy_dialog = xbmcgui.DialogBusy()
                busy_dialog.create()
                bin_filename = self._url.split('/')[-1].replace('.zip', '')
                bin_path = os.path.join(self._temp_path(), bin_filename)

                success = [
                    self._unzip(self._temp_path(), bin_filename),
                    self._set_loop_dev(), self._losetup(bin_path),
                    self._mnt_loop_dev()
                ]
                if all(success):
                    self._extract_widevine_from_img()
                    self._install_cdm()
                    self._cleanup()
                    if self._has_widevine():
                        with open(self._widevine_config_path(), 'w') as config_file:
                            config_file.write(json.dumps(cos_config, indent=4))
                        dialog.ok(LANGUAGE(30001), LANGUAGE(30003))
                        busy_dialog.close()
                        return self._check_widevine()
                    else:
                        busy_dialog.close()
                        dialog.ok(LANGUAGE(30004), LANGUAGE(30005))
                else:
                    self._cleanup()
                    busy_dialog.close()
                    dialog.ok(LANGUAGE(30004), LANGUAGE(30005))

        return False

    def _install_widevine(self):
        """Simple wrap function to call the right Widevine installer method depending on architecture."""
        if 'x86' in self._arch():
            return self._install_widevine_x86()
        else:
            return self._install_widevine_arm()

    def _update_widevine(self):
        """Prompt user to upgrade Widevine CDM when a newer version is available."""
        utcnow = datetime.utcnow()
        last_update = ADDON.getSetting('last_update')
        if last_update:
            last_update_dt = datetime.fromtimestamp(float(ADDON.getSetting('last_update')))
            if last_update_dt + timedelta(days=config.WIDEVINE_UPDATE_INTERVAL_DAYS) >= utcnow:
                self._log('Widevine update check was made on {0}'.format(last_update_dt.isoformat()))
                return

        wv_config = self._load_widevine_config()
        latest_version = self._latest_widevine_version()
        if 'x86' in self._arch():
            component = 'Widevine CDM'
            current_version = wv_config['version']
        else:
            component = 'Chrome OS'
            current_version = [x for x in wv_config if config.CHROMEOS_ARM_HWID in x['hwidmatch']][0]['version']
        self._log('Latest {0} version is {1}'.format(component, latest_version))
        self._log('Current {0} version installed is {1}'.format(component, current_version))
        ADDON.setSetting('last_update', str(time.mktime(utcnow.timetuple())))

        if LooseVersion(latest_version) > LooseVersion(current_version):
            self._log('There is an update available for {0}'.format(component))
            dialog = xbmcgui.Dialog()
            if dialog.yesno(LANGUAGE(30001), LANGUAGE(30033), yeslabel=LANGUAGE(30034), nolabel=LANGUAGE(30028)):
                self._install_widevine()
            else:
                self._log('User declined to update {0}.'.format(component))
        else:
            self._log('User is on the latest available {0} version.'.format(component))

    def _widevine_eula(self):
        """Display the Widevine EULA and prompt user to accept it."""
        if os.path.exists(os.path.join(self._addon_cdm_path(), config.WIDEVINE_LICENSE_FILE)):
            license_file = os.path.join(self._addon_cdm_path(), config.WIDEVINE_LICENSE_FILE)
            with open(license_file, 'r') as f:
                eula = f.read().strip().replace('\n', ' ')
        else:  # grab the license from the x86 files
            self._log('Acquiring Widevine EULA from x86 files.')
            self._url = config.WIDEVINE_DOWNLOAD_URL.format(self._latest_widevine_version(eula=True), 'mac', 'x64')
            downloaded = self._http_request(download=True, message=LANGUAGE(30025))
            if downloaded:
                with zipfile.ZipFile(self._download_path) as z:
                    with z.open(config.WIDEVINE_LICENSE_FILE) as f:
                        eula = f.read().strip().replace('\n', ' ')
            else:
                return False

        dialog = xbmcgui.Dialog()
        return dialog.yesno(LANGUAGE(30026), eula, yeslabel=LANGUAGE(30027), nolabel=LANGUAGE(30028))

    def _extract_widevine_from_img(self):
        """Extract the Widevine CDM binary from the mounted Chrome OS image."""
        for root, dirs, files in os.walk(self._mnt_path()):
            for filename in files:
                if filename == 'libwidevinecdm.so':
                    shutil.copyfile(os.path.join(root, filename), os.path.join(self._addon_cdm_path(), filename))
                    return True

        self._log('Failed to find Widevine CDM binary in Chrome OS image.')
        return False

    def _missing_widevine_libs(self):
        """Parse ldd output of libwidevinecdm.so and display dialog if any depending libraries are missing."""
        if self._os() != 'Linux':  # this should only be needed for linux
            return None

        if self._cmd_exists('ldd'):
            missing_libs = []
            cmd = ['ldd', self._widevine_path()]
            output = subprocess.check_output(cmd)
            self._log('ldd output: \n{0}'.format(output))
            for line in output.splitlines():
                if '=>' not in line:
                    continue
                lib_path = line.strip().split('=>')
                lib = lib_path[0].strip()
                path = lib_path[1].strip()
                if path == 'not found':
                    missing_libs.append(lib)

            if not missing_libs:
                self._log('There are no missing Widevine libraries! :-)')
                return None
            else:
                self._log('Widevine is missing the following libraries: {0}'.format(missing_libs))
                return missing_libs
        else:
            self._log('ldd is not available - unable to check for missing widevine libs')
            return None

    def _check_widevine(self):
        """Check that all Widevine components are installed and available."""
        if self._os() == 'Android':  # no checks needed for Android
            return True

        dialog = xbmcgui.Dialog()
        if not os.path.exists(self._widevine_config_path()):
            self._log('Widevine config is missing. Reinstall is required.')
            dialog.ok(LANGUAGE(30001), LANGUAGE(30031))
            return self._install_widevine()

        if 'x86' in self._arch():  # check that widevine arch matches system arch
            wv_config = self._load_widevine_config()
            if config.WIDEVINE_ARCH_MAP_X86[self._arch()] != wv_config['arch']:
                self._log('Widevine arch/system arch mismatch. Reinstall is required.')
                dialog.ok(LANGUAGE(30001), LANGUAGE(30031))
                return self._install_widevine()
        if self._missing_widevine_libs():
            dialog.ok(LANGUAGE(30004), LANGUAGE(30032).format(', '.join(self._missing_widevine_libs())))
            return False

        self._update_widevine()

        return True

    def _install_cdm(self):
        """Loop through local cdm folder and symlink/copy binaries to inputstream cdm_path."""
        for cdm_file in os.listdir(self._addon_cdm_path()):
            if cdm_file.endswith(config.CDM_EXTENSIONS):
                self._log('[install_cdm] found file: {0}'.format(cdm_file))
                cdm_path_addon = os.path.join(self._addon_cdm_path(), cdm_file)
                cdm_path_inputstream = os.path.join(self._ia_cdm_path(), cdm_file)
                if self._os() == 'Windows':  # copy on windows
                    shutil.copyfile(cdm_path_addon, cdm_path_inputstream)
                else:
                    if os.path.lexists(cdm_path_inputstream):
                        os.remove(cdm_path_inputstream)  # it's ok to overwrite
                    os.symlink(cdm_path_addon, cdm_path_inputstream)

        return True

    def _unzip(self, unzip_dir, file_to_unzip=None):
        """Unzip files to specified path."""
        zip_obj = zipfile.ZipFile(self._download_path)
        if file_to_unzip:
            for filename in zip_obj.namelist():
                if filename == file_to_unzip:
                    zip_obj.extract(filename, unzip_dir)
                    return True
            return False
        else:  # extract all files
            zip_obj.extractall(unzip_dir)
            return True

    def _cleanup(self):
        """Clean up after Widevine DRM installation."""
        if self._mounted:
            cmd = ['umount', self._mnt_path()]
            unmount_success = self._run_cmd(cmd, sudo=True, ask=False)
            if unmount_success:
                self._mounted = False
        if self._attached_loop_dev:
            cmd = ['losetup', '-d', self._loop_dev]
            unattach_success = self._run_cmd(cmd, sudo=True, ask=False)
            if unattach_success:
                self._loop_dev = False

        shutil.rmtree(self._temp_path())
        return True

    def _supports_hls(self):
        """Return if HLS support is available in inputstream.adaptive."""
        if LooseVersion(self._inputstream_version()) >= LooseVersion(config.HLS_MINIMUM_IA_VERSION):
            return True
        else:
            self._log(
                'HLS is unsupported on {0} version {1}'.format(self._inputstream_addon, self._inputstream_version()))
            dialog = xbmcgui.Dialog()
            dialog.ok(LANGUAGE(30004),
                      LANGUAGE(30017).format(self._inputstream_addon, config.HLS_MINIMUM_IA_VERSION))
            return False

    def _check_drm(self):
        """Main function for ensuring that specified DRM system is installed and available."""
        if not self.drm or not self._inputstream_addon == 'inputstream.adaptive':
            return True

        if self.drm == 'widevine':
            if not self._supports_widevine():
                return False
            if not self._has_widevine():
                dialog = xbmcgui.Dialog()
                if dialog.yesno(LANGUAGE(30001), LANGUAGE(30002)):
                    return self._install_widevine()
                else:
                    return False

            return self._check_widevine()

        return True

    def check_inputstream(self):
        """Main function. Ensures that all components are available for InputStream add-on playback."""
        dialog = xbmcgui.Dialog()
        if not self._has_inputstream():
            self._log('{0} is not installed.'.format(self._inputstream_addon))
            dialog.ok(LANGUAGE(30004), LANGUAGE(30008).format(self._inputstream_addon))
            return False
        elif not self._inputstream_enabled():
            self._log('{0} is not enabled.'.format(self._inputstream_addon))
            ok = dialog.yesno(LANGUAGE(30001), LANGUAGE(30009).format(self._inputstream_addon, self._inputstream_addon))
            if ok:
                self._enable_inputstream()
            else:
                return False
        if self.protocol == 'hls' and not self._supports_hls():
            return False

        self._log('{0} is installed and enabled.'.format(self._inputstream_addon))
        return self._check_drm()

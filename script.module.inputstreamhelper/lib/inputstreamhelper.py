import os
import platform
import zipfile
import json
import subprocess
import shutil
from distutils.version import LooseVersion

import requests

import config
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


class Helper(object):
    _addon = xbmcaddon.Addon('script.module.inputstreamhelper')
    _addon_profile = xbmc.translatePath(_addon.getAddonInfo('profile'))
    _language = _addon.getLocalizedString

    def __init__(self, protocol, drm=None):
        self._os = platform.system()
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
        statvfs = os.statvfs(cls._cdm_path())
        return statvfs.f_frsize * statvfs.f_bavail

    @classmethod
    def _temp_path(cls):
        temp_path = os.path.join(cls._addon_profile, 'tmp')
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
    def _cdm_path(cls):
        cdm_path = os.path.join(cls._addon_profile, 'cdm')
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
    def _widevine_manifest_path(cls):
        return os.path.join(cls._ia_cdm_path(), config.WIDEVINE_MANIFEST_FILE)

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
            elif arch_bit == '64bit':
                arch = 'x86_64'
        if arch in config.X86_MAP:
            return config.X86_MAP[arch]
        elif 'armv' in arch:
            arm_arch = 'armv' + arch.split('v')[1][:-1]
            return arm_arch

        return arch

    def _inputstream_version(self):
        addon = xbmcaddon.Addon(self._inputstream_addon)
        return addon.getAddonInfo('version')

    def _log(self, string):
        """InputStream Helper log method."""
        logging_prefix = '[{0}-{1}]'.format(self._addon.getAddonInfo('id'), self._addon.getAddonInfo('version'))
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
        self._log('losetup calculation output: {0}'.format(output))
        for line in output.splitlines():
            partition_data = line.split()
            if partition_data:
                if partition_data[0] == '3' or '.bin3' in partition_data[0]:
                    offset = int(partition_data[1].replace('s', ''))
                    return str(offset * config.CHROMEOS_BLOCK_SIZE)

        self._log('Failed to calculate losetup offset.')
        return False

    def _run_cmd(self, cmd, sudo=False, ask=True):
        dialog = xbmcgui.Dialog()
        if ask and os.getuid() != 0 and not dialog.yesno(self._language(30001), self._language(30030), yeslabel=self._language(30029), nolabel=self._language(30028)):
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

    def _has_widevine_cdm(self):
        """Checks if Widevine CDM is installed on system."""
        if xbmc.getCondVisibility('system.platform.android'):  # widevine is built in on android
            return True
        else:
            for filename in os.listdir(self._ia_cdm_path()):
                if 'widevine' in filename and filename.endswith(config.CDM_EXTENSIONS):
                    self._log('Found Widevine binary at {0}'.format(os.path.join(self._ia_cdm_path(), filename)))
                    return True

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
            dialog.ok(self._language(30004), self._language(30013).format(filename))
            return False

        if download:
            if not message:  # display "downloading [filename]"
                message = self._language(30015).format(filename)
            self._download_path = os.path.join(self._temp_path(), filename)
            total_length = float(req.headers.get('content-length'))
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(self._language(30014), message)

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
        if xbmc.getCondVisibility('system.platform.android'):
            min_version = config.WIDEVINE_ANDROID_MINIMUM_KODI_VERSION
        else:
            min_version = config.WIDEVINE_MINIMUM_KODI_VERSION

        if self._arch() not in config.WIDEVINE_SUPPORTED_ARCHS:
            self._log('Unsupported Widevine architecture found: {0}'.format(self._arch()))
            dialog.ok(self._language(30004), self._language(30007))
            return False
        if self._os not in config.WIDEVINE_SUPPORTED_OS:
            self._log('Unsupported Widevine OS found: {0}'.format(self._os))
            dialog.ok(self._language(30004), self._language(30011).format(self._os))
            return False
        if LooseVersion(min_version) > LooseVersion(self._kodi_version()):
            self._log('Unsupported Kodi version for Widevine: {0}'.format(self._kodi_version()))
            dialog.ok(self._language(30004), self._language(30010).format(min_version))
            return False
        if 'WindowsApps' in xbmc.translatePath('special://xbmcbin/'):  # uwp is not supported
            self._log('Unsupported UWP Kodi version detected.')
            dialog.ok(self._language(30004), self._language(30012))
            return False

        return True

    def _current_widevine_cdm_version(self):
        """Return the latest available version of Widevine CDM."""
        self._url = config.WIDEVINE_CURRENT_VERSION_URL
        return self._http_request()

    def _parse_chromeos_recovery_conf(self):
        """Parse the Chrome OS recovery configuration and put it in a dictionary."""
        devices = []
        self._url = config.CHROMEOS_RECOVERY_CONF
        conf = [x for x in self._http_request().split('\n\n') if 'name=' in x]
        for device in conf:
            device_dict = {}
            for device_info in device.splitlines():
                key_value = device_info.split('=')
                key = key_value[0]
                if len(key_value) > 1:  # some keys have empty values
                    value = key_value[1]
                    device_dict[key] = value
            devices.append(device_dict)

        self._log('chromeos devices: {0}'.format(devices))
        return devices

    def _install_widevine_cdm_x86(self):
        """Install Widevine CDM on x86 based architectures."""
        dialog = xbmcgui.Dialog()
        if dialog.yesno(self._language(30001), self._language(30002)):
            cdm_version = self._current_widevine_cdm_version()
            cdm_os = config.WIDEVINE_OS_MAP[self._os]
            cdm_arch = config.WIDEVINE_ARCH_MAP_X86[self._arch()]
            self._url = config.WIDEVINE_DOWNLOAD_URL.format(cdm_version, cdm_os, cdm_arch)

            downloaded = self._http_request(download=True)
            if downloaded:
                busy_dialog = xbmcgui.DialogBusy()
                busy_dialog.create()
                self._unzip(self._cdm_path())
                if self._widevine_eula():
                    self._install_cdm()
                    self._cleanup()
                else:
                    self._cleanup()
                    return False

                if self._has_widevine_cdm():
                    dialog.ok(self._language(30001), self._language(30003))
                    busy_dialog.close()
                    return True
                else:
                    busy_dialog.close()
                    dialog.ok(self._language(30004), self._language(30005))

        return False

    def _install_widevine_cdm_arm(self):
        """Install Widevine CDM on ARM-based architectures."""
        arm_device = [x for x in self._parse_chromeos_recovery_conf() if config.CHROMEOS_ARM_HWID in x['hwidmatch']][0]
        required_diskspace = int(arm_device['filesize']) + int(arm_device['zipfilesize'])
        dialog = xbmcgui.Dialog()
        if dialog.yesno(self._language(30001), self._language(30002)) and dialog.yesno(self._language(30001), self._language(30006).format(self.sizeof_fmt(required_diskspace))) and self._widevine_eula():
            if self._os != 'Linux':
                dialog.ok(self._language(30004), self._language(30019).format(self._os))
                return False
            if required_diskspace >= self._diskspace():
                dialog.ok(self._language(30004),
                          self._language(30018).format(self.sizeof_fmt(required_diskspace)))
                return False
            if not self._cmd_exists('fdisk') and not self._cmd_exists('parted'):
                dialog.ok(self._language(30004), self._language(30020).format('fdisk', 'parted'))
                return False
            if not self._cmd_exists('mount'):
                dialog.ok(self._language(30004), self._language(30021).format('mount'))
                return False
            if not self._cmd_exists('losetup'):
                dialog.ok(self._language(30004), self._language(30021).format('losetup'))
                return False

            self._url = arm_device['url']
            downloaded = self._http_request(download=True, message=self._language(30022))
            if downloaded:
                dialog.ok(self._language(30023), self._language(30024))
                busy_dialog = xbmcgui.DialogBusy()
                busy_dialog.create()

                bin_filename = self._url.split('/')[-1].replace('.zip', '')
                bin_path = os.path.join(self._temp_path(), bin_filename)
                if not self._unzip(self._temp_path(), bin_filename) or not self._set_loop_dev() or not self._losetup(bin_path) or not self._mnt_loop_dev():
                    self._cleanup()
                    busy_dialog.close()
                    dialog.ok(self._language(30004), self._language(30005))
                else:
                    self._extract_widevine_cdm_from_img()
                    self._install_cdm()
                    self._cleanup()
                    if self._has_widevine_cdm():
                        dialog.ok(self._language(30001), self._language(30003))
                        busy_dialog.close()
                        return True
                    else:
                        busy_dialog.close()
                        dialog.ok(self._language(30004), self._language(30005))

        return False

    def _widevine_eula(self):
        """Display the Widevine EULA and prompt user to accept it."""
        if os.path.exists(os.path.join(self._cdm_path(), config.WIDEVINE_LICENSE_FILE)):
            license_file = os.path.join(self._cdm_path(), config.WIDEVINE_LICENSE_FILE)
            with open(license_file, 'r') as f:
                eula = f.read().strip().replace('\n', ' ')
        else:  # grab the license from the x86 files
            self._url = config.WIDEVINE_DOWNLOAD_URL.format(self._current_widevine_cdm_version(), 'mac', 'x64')
            downloaded = self._http_request(download=True, message=self._language(30025))
            if downloaded:
                with zipfile.ZipFile(self._download_path) as z:
                    with z.open(config.WIDEVINE_LICENSE_FILE) as f:
                        eula = f.read().strip().replace('\n', ' ')
            else:
                return False

        dialog = xbmcgui.Dialog()
        return dialog.yesno(self._language(30026), eula, yeslabel=self._language(30027), nolabel=self._language(30028))

    def _extract_widevine_cdm_from_img(self):
        """Extract the Widevine CDM binary from the mounted Chrome OS image."""
        for root, dirs, files in os.walk(self._mnt_path()):
            for filename in files:
                if filename == 'libwidevinecdm.so':
                    shutil.copyfile(os.path.join(root, filename), os.path.join(self._cdm_path(), filename))
                    return True

        self._log('Failed to find Widevine CDM binary in Chrome OS image.')
        return False

    def _install_cdm(self):
        """Loop through local cdm folder and symlink/copy binaries to inputstream cdm_path."""
        for cdm_file in os.listdir(self._cdm_path()):
            if cdm_file.endswith(config.CDM_EXTENSIONS):
                self._log('[install_cdm] found file: {0}'.format(cdm_file))
                cdm_path_addon = os.path.join(self._cdm_path(), cdm_file)
                cdm_path_inputstream = os.path.join(self._ia_cdm_path(), cdm_file)
                if self._os == 'Windows':  # copy on windows
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
            self._log('HLS is unsupported on {0} version {1}'.format(self._inputstream_addon, self._inputstream_version()))
            dialog = xbmcgui.Dialog()
            dialog.ok(self._language(30004),
                      self._language(30017).format(self._inputstream_addon, config.HLS_MINIMUM_IA_VERSION))
            return False

    def _check_drm(self):
        """Main function for ensuring that specified DRM system is installed and available."""
        if not self.drm or not self._inputstream_addon == 'inputstream.adaptive':
            return True
        if self.drm == 'widevine':
            if not self._supports_widevine():
                return False
            if not self._has_widevine_cdm():
                if 'x86' in self._arch():
                    return self._install_widevine_cdm_x86()
                else:
                    return self._install_widevine_cdm_arm()
            if 'x86' in self._arch():
                dialog = xbmcgui.Dialog()
                if not os.path.exists(self._widevine_manifest_path()):  # needed to validate arch/version
                    dialog.ok(self._language(30001), self._language(30031))
                    return self._install_widevine_cdm_x86()

                with open(self._widevine_manifest_path(), 'r') as f:
                    widevine_manifest = json.loads(f.read())
                if config.WIDEVINE_ARCH_MAP_X86[self._arch()] != widevine_manifest['arch']:
                    dialog.ok(self._language(30001), self._language(30031))
                    return self._install_widevine_cdm_x86()

        return True

    def check_inputstream(self):
        """Main function. Ensures that all components are available for InputStream add-on playback."""
        dialog = xbmcgui.Dialog()
        if not self._has_inputstream():
            self._log('{0} is not installed.'.format(self._inputstream_addon))
            dialog.ok(self._language(30004), self._language(30008).format(self._inputstream_addon))
            return False
        elif not self._inputstream_enabled():
            self._log('{0} is not enabled.'.format(self._inputstream_addon))
            ok = dialog.yesno(self._language(30001),
                              self._language(30009).format(self._inputstream_addon, self._inputstream_addon))
            if ok:
                self._enable_inputstream()
            else:
                return False
        if self.protocol == 'hls' and not self._supports_hls():
            return False

        self._log('{0} is installed and enabled.'.format(self._inputstream_addon))
        return self._check_drm()

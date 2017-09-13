import os
import platform
import zipfile
import json
from distutils.version import LooseVersion

import requests

import config
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


class Helper(object):
    def __init__(self, protocol, drm=None):
        self._addon = xbmcaddon.Addon('script.module.inputstreamhelper')
        self._logging_prefix = '[%s-%s]' % (self._addon.getAddonInfo('id'), self._addon.getAddonInfo('version'))
        self._language = self._addon.getLocalizedString
        self._arch = self._get_arch(platform.machine())
        self._os = platform.system()
        self._log('Platform information: {0}'.format(platform.uname()))

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

    class InputStreamException(Exception):
        pass

    def _get_arch(self, arch):
        if arch in config.ARCHS:
            return config.ARCHS[arch]
        else:
            return arch

    def _log(self, string):
        msg = '{0}: {1}'.format(self._logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def _cdm_path(self):
        addon = xbmcaddon.Addon('inputstream.adaptive')
        return xbmc.translatePath(addon.getSetting('DECRYPTERPATH'))

    def _kodi_version(self):
        version = xbmc.getInfoLabel('System.BuildVersion')
        return version.split(' ')[0]

    def _inputstream_version(self):
        addon = xbmcaddon.Addon(self._inputstream_addon)
        return addon.getAddonInfo('version')

    def _has_widevine_cdm(self):
        if not xbmcvfs.exists(self._cdm_path()):
            xbmcvfs.mkdir(self._cdm_path())
        if xbmc.getCondVisibility('system.platform.android'):  # widevine is built in on android
            return True
        else:
            for filename in os.listdir(self._cdm_path()):
                if 'widevine' in filename and filename.endswith(config.WIDEVINE_CDM_EXTENSIONS):
                    self._log('Found Widevine binary at {0}'.format(os.path.join(self._cdm_path(), filename)))
                    return True

            self._log('Widevine is not installed.')
            return False

    def _json_rpc_request(self, payload):
        self._log('jsonrpc payload: {0}'.format(payload))
        response = xbmc.executeJSONRPC(json.dumps(payload))
        self._log('jsonrpc response: {0}'.format(response))

        return json.loads(response)

    def _http_request(self, url, download=False, download_path=None):
        busy_dialog = xbmcgui.DialogBusy()
        dialog = xbmcgui.Dialog()
        filename = url.split('/')[-1]
        self._log('Request URL: {0}'.format(url))
        try:
            busy_dialog.create()
            req = requests.get(url, stream=download, verify=False)
            self._log('Response code: {0}'.format(req.status_code))
            if not download:
                self._log('Response: {0}'.format(req.content))
            req.raise_for_status()
        except requests.exceptions.HTTPError:
            busy_dialog.close()
            dialog.ok(self._language(30004), self._language(30013).format(filename))
            return False

        busy_dialog.close()
        if download:
            total_length = float(req.headers.get('content-length'))
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(self._language(30014), self._language(30015).format(filename))

            with open(download_path, 'wb') as f:
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
        if data['result']['addon']['enabled']:
            return True
        else:
            return False

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
        dialog = xbmcgui.Dialog()
        if xbmc.getCondVisibility('system.platform.android'):
            min_version = config.WIDEVINE_ANDROID_MINIMUM_KODI_VERSION
        else:
            min_version = config.WIDEVINE_MINIMUM_KODI_VERSION

        if self._arch not in config.WIDEVINE_SUPPORTED_ARCHS:
            self._log('Unsupported Widevine architecture found: {0}'.format(self._arch))
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

    def _install_widevine_cdm(self):
        dialog = xbmcgui.Dialog()
        if self._arch in config.WIDEVINE_DOWNLOAD_UNAVAILABLE:
            dialog.ok(self._language(30001), self._language(30006))
            return False
        download_path = os.path.join(xbmc.translatePath('special://temp'), 'widevine_cdm.zip')
        cdm_platform = config.WIDEVINE_DOWNLOAD_MAP[self._arch][self._os]
        cdm_source = json.loads(self._http_request(config.WIDEVINE_CDM_SOURCE))['vendors']['gmp-widevinecdm']['platforms']
        cdm_zip_url = cdm_source[cdm_platform]['fileUrl']

        downloaded = self._http_request(cdm_zip_url, download=True, download_path=download_path)
        if downloaded:
            if self._unzip_widevine_cdm(download_path):
                dialog.ok(self._language(30001), self._language(30003))
                return True

        return False

    def _unzip_widevine_cdm(self, zip_path):
        busy_dialog = xbmcgui.DialogBusy()
        zip_obj = zipfile.ZipFile(zip_path)
        busy_dialog.create()
        for filename in zip_obj.namelist():
            if filename.endswith(config.WIDEVINE_CDM_EXTENSIONS):
                self._log('Widevine CDM found in zip: {0}'.format(os.path.join(zip_path, filename)))
                zip_obj.extract(filename, self._cdm_path())
                busy_dialog.close()
                return True

        busy_dialog.close()
        dialog = xbmcgui.Dialog()
        dialog.ok(self._language(30004), self._language(30016))
        self._log('Failed to find Widevine CDM file in {0}'.format(zip_path))
        return False

    def _supports_hls(self):
        if LooseVersion(self._inputstream_version()) >= LooseVersion(config.HLS_MINIMUM_IA_VERSION):
            return True
        else:
            self._log('HLS is not supported on {0} version {1}'.format(self._inputstream_addon, self._inputstream_version()))
            return False

    def _check_for_drm(self):
        """Main function for ensuring that specified DRM system is installed and available."""
        if self.drm:
            if self.drm == 'widevine':
                if not self._supports_widevine():
                    return False
                if not self._has_widevine_cdm():
                    dialog = xbmcgui.Dialog()
                    ok = dialog.yesno(self._language(30001), self._language(30002))
                    if ok:
                        return self._install_widevine_cdm()
                    else:
                        return False

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
        return self._check_for_drm()

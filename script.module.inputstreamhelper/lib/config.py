# -*- coding: utf-8 -*-

INPUTSTREAM_PROTOCOLS = {
    'mpd': 'inputstream.adaptive',
    'ism': 'inputstream.adaptive',
    'hls': 'inputstream.adaptive',
    'rtmp': 'inputstream.rtmp'
}

DRM_SCHEMES = {
    'widevine': 'widevine',
    'com.widevine.alpha': 'widevine'
}

CDM_EXTENSIONS = (
    '.so',
    '.dll',
    '.dylib'
)

ARCH_MAP = {
    'x86_64': 'x86_64',
    'AMD64': 'x86_64',
    'x86': 'x86',
    'i386': 'x86',
    'i686': 'x86',
    'armv7': 'arm',
    'armv8': 'arm',
    'aarch64': 'arm64',
    'aarch64_be': 'arm64'
}

WIDEVINE_SUPPORTED_ARCHS = [
    'x86_64',
    'x86',
    'arm',
    'arm64'
]

WIDEVINE_ARCH_MAP_X86 = {
    'x86_64': 'x64',
    'x86': 'ia32'
}

WIDEVINE_OS_MAP = {
    'Linux': 'linux',
    'Windows': 'win',
    'Darwin': 'mac'
}

WIDEVINE_SUPPORTED_OS = [
    'Android',
    'Linux',
    'Windows',
    'Darwin'
]

WIDEVINE_MINIMUM_KODI_VERSION = {
    'Android': '18.0',
    'Windows': '17.4',
    'Linux': '17.4',
    'Darwin': '17.4'
}

WIDEVINE_CURRENT_VERSION_URL = 'https://dl.google.com/widevine-cdm/current.txt'

WIDEVINE_DOWNLOAD_URL = 'https://dl.google.com/widevine-cdm/{0}-{1}-{2}.zip'

WIDEVINE_LICENSE_FILE = 'LICENSE.txt'

WIDEVINE_MANIFEST_FILE = 'manifest.json'

WIDEVINE_CONFIG_NAME = 'widevine_config.json'

WIDEVINE_UPDATE_INTERVAL_DAYS = 30

WIDEVINE_LEGACY_VERSION = '1.4.8.903'

CHROMEOS_RECOVERY_URL = 'https://dl.google.com/dl/edgedl/chromeos/recovery/recovery.conf'

CHROMEOS_RECOVERY_URL_LEGACY = 'https://gist.githubusercontent.com/emilsvennesson/5e74181c9a833129ad0bb03ccb41d81f/raw/8d162568277caaa31b54f4773e75a20514856825/recovery.conf'

CHROMEOS_ARM_HWID = 'SPRING'

CHROMEOS_BLOCK_SIZE = 512

HLS_MINIMUM_IA_VERSION = '2.0.10'

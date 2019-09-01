# -*- coding: utf-8 -*-
''' Configuration variables for inpustreamhelper '''
from __future__ import absolute_import, division, unicode_literals


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

WIDEVINE_CDM_FILENAME = {
    'Android': None,
    'Linux': 'libwidevinecdm.so',
    'Windows': 'widevinecdm.dll',
    'Darwin': 'libwidevinecdm.dylib'
}

ARCH_MAP = {
    'aarch64': 'arm64',
    'aarch64_be': 'arm64',
    'AMD64': 'x86_64',
    'armv7': 'arm',
    'armv8': 'arm',
    'i386': 'x86',
    'i686': 'x86',
    'x86': 'x86',
    'x86_64': 'x86_64',
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
    'Windows': '18.0',
    'Linux': '18.0',
    'Darwin': '18.0'
}

WIDEVINE_VERSIONS_URL = 'https://dl.google.com/widevine-cdm/versions.txt'

WIDEVINE_DOWNLOAD_URL = 'https://dl.google.com/widevine-cdm/{version}-{os}-{arch}.zip'

WIDEVINE_LICENSE_FILE = 'LICENSE.txt'

WIDEVINE_MANIFEST_FILE = 'manifest.json'

WIDEVINE_CONFIG_NAME = 'widevine_config.json'

WIDEVINE_UPDATE_INTERVAL_DAYS = 14

CHROMEOS_RECOVERY_URL = 'https://dl.google.com/dl/edgedl/chromeos/recovery/recovery.conf'

# Last updated: 2019-08-20 (version 12239.67.0)
CHROMEOS_RECOVERY_ARM_HWIDS = [
    'BOB',
    'WHITETIP',
    'SKATE',
    'SPRING',
    'SNOW',
    'ELM',
    'HANA',
    'BIG',
    'BLAZE',
    'RELM',
    'DUMO',
    'SCARLET',
    'FIEVEL',
    'JAQ',
    'JERRY',
    'MICKEY',
    'MIGHTY',
    'MINNIE',
    'SPEEDY',
    'TIGER',
]

CHROMEOS_BLOCK_SIZE = 512

HLS_MINIMUM_IA_VERSION = '2.0.10'

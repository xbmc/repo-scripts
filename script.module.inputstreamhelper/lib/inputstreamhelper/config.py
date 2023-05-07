# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Configuration variables for inpustreamhelper"""
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

WIDEVINE_ARCH_MAP_REPO = {
    'x86_64': 'x64',
    'x86': 'ia32',
    'arm64': 'arm64'
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

WIDEVINE_CONFIG_NAME = 'manifest.json'

CHROMEOS_RECOVERY_URL = 'https://dl.google.com/dl/edgedl/chromeos/recovery/recovery.json'

# To keep the Chrome OS ARM(64) hardware ID list up to date, the following resources can be used:
# https://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices
# https://chromiumdash.appspot.com/serving-builds?deviceCategory=Chrome%20OS
# Last updated: 2023-03-24
CHROMEOS_RECOVERY_ARM_HWIDS = [
    'BOB',
    'BURNET',
    'COACHZ',
    'COZMO',
    'DAMU',
    'DOJO-EJPG',
    'DRUWL',
    'DUMO',
    'ELM',
    'ESCHE',
    'FENNEL',
    'FENNEL14',
    'HANA',
    'HAYATO-YLRO',
    'HOMESTAR-MBLE',
    'JUNIPER-HVPU',
    'KAKADU-WFIQ',
    'KAPPA',
    'KAPPA-EWFK',
    'KATSU',
    'KENZO-IGRW',
    'KEVIN',
    'KODAMA',
    'KRANE-ZDKS',
    'MAKOMO-UTTX',
    'PICO-EXEM',
    'QUACKINGSTICK',
    'SCARLET',
    'SPHERION',
    'TOMATO-LYVN',
    'WILLOW-TFIY',
    'WORMDINGLER-JQAO',
]

CHROMEOS_RECOVERY_ARM64_HWIDS = [
    'KINGOFTOWN-KDDA',
    'LAZOR',
    'LIMOZEEN',
    'MAGNETON-LCKC',
    'PAZQUEL-HGNV',
    'PAZQUEL-OPNA',
    'POMPOM-MZVS',
    'RUSTY-ZNCE',
    'STEELIX-VZSZ',
    'TENTACOOL-ZLJE',
    'TENTACRUEL-VAFH',
]

MINIMUM_INPUTSTREAM_VERSION_ARM64 = {
    'inputstream.adaptive': '20.3.5',
}

CHROMEOS_BLOCK_SIZE = 512

HLS_MINIMUM_IA_VERSION = '2.0.10'

ISSUE_URL = 'https://github.com/emilsvennesson/script.module.inputstreamhelper/issues'

SHORT_ISSUE_URL = 'https://git.io/JfKJb'

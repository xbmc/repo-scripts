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

X86_MAP = {
    'x86_64': 'x86_64',
    'AMD64': 'x86_64',
    'x86': 'x86',
    'i386': 'x86',
    'i686': 'x86'
}

WIDEVINE_SUPPORTED_ARCHS = [
    'x86_64',
    'x86',
    'armv7',
    'armv8',
    'aarch64',
    'aarch64_be'
]

WIDEVINE_ARCH_MAP_X86 = {
    'x86_64':
        {
            'Linux': 'x64',
            'Windows': 'ia32',
            'Darwin': 'x64'
        },
    'x86':
        {
            'Linux': 'ia32',
            'Windows': 'ia32',
            'Darwin': 'ia32'
        }
}

WIDEVINE_OS_MAP = {
    'Linux': 'linux',
    'Windows': 'win',
    'Darwin': 'mac'
}

WIDEVINE_SUPPORTED_OS = [
    'Linux',
    'Windows',
    'Darwin'
]

WIDEVINE_ANDROID_MINIMUM_KODI_VERSION = '18.0'

WIDEVINE_MINIMUM_KODI_VERSION = '17.4'

WIDEVINE_CURRENT_VERSION_URL = 'https://dl.google.com/widevine-cdm/current.txt'

WIDEVINE_DOWNLOAD_URL = 'https://dl.google.com/widevine-cdm/{0}-{1}-{2}.zip'

WIDEVINE_LICENSE_FILE = 'LICENSE.txt'

CHROMEOS_RECOVERY_CONF = 'https://dl.google.com/dl/edgedl/chromeos/recovery/recovery.conf'

CHROMEOS_ARM_HWID = 'SPRING'

CHROMEOS_BLOCK_SIZE = 512

HLS_MINIMUM_IA_VERSION = '2.0.10'

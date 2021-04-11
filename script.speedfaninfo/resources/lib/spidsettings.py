
from resources.lib.kodisettings import *

SETTINGSLIST = [{'name': 'log_title', 'default': ''},
                {'name': 'log_location', 'default': ''},
                {'name': 'show_compact', 'default': False},
                {'name': 'transparency', 'default': '70'},
                {'name': 'temp_scale', 'default': 'Celcius'},
                {'name': 'update_delay', 'default': 30},
                {'name': 'use_log2', 'default': False},
                {'name': 'log_title2', 'default': ''},
                {'name': 'log_location2', 'default': ''},
                {'name': 'use_log3', 'default': False},
                {'name': 'log_title3', 'default': ''},
                {'name': 'log_location3', 'default': ''},
                {'name': 'read_size', 'default': 256},
                {'name': 'debug', 'default': False}
                ]


def loadSettings():
    settings = {}
    settings['ADDON'] = ADDON
    settings['ADDONNAME'] = ADDONNAME
    settings['ADDONLONGNAME'] = ADDONLONGNAME
    settings['ADDONVERSION'] = ADDONVERSION
    settings['ADDONPATH'] = ADDONPATH
    settings['ADDONDATAPATH'] = ADDONDATAPATH
    settings['ADDONICON'] = ADDONICON
    settings['ADDONLANGUAGE'] = ADDONLANGUAGE
    for item in SETTINGSLIST:
        if isinstance(item['default'], bool):
            getset = getSettingBool
        elif isinstance(item['default'], int):
            getset = getSettingInt
        elif isinstance(item['default'], float):
            getset = getSettingNumber
        else:
            getset = getSettingString
        settings[item['name']] = getset(item['name'], item['default'])
    return settings

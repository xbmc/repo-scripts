
from resources.lib.kodisettings import *

SETTINGSLIST = [{'name': 'version_upgrade', 'default': ''},
                {'name': 'show_cache', 'default': ''},
                {'name': 'tvmaze_user', 'default': ''},
                {'name': 'tvmaze_apikey', 'default': ''},
                {'name': 'add_followed', 'default': False},
                {'name': 'mark_acquired', 'default': True},
                {'name': 'mark_watched', 'default': True},
                {'name': 'mark_on_remove', 'default': True},
                {'name': 'percent_watched', 'default': 85},
                {'name': 'hidemenu', 'default': False},
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

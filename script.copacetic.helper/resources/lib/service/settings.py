# author: realcopacetic

from resources.lib.utilities import (ADDON, ADDON_ID, DIALOG, condition,
                                     json_call, log, window_property)


class SettingsMonitor:
    def __init__(self):
        self.settings = {
            'filelists.showparentdiritems': False,
            'videolibrary.showallitems': False,
            'videolibrary.groupmoviesets': True,
            'videolibrary.flattentvshows': 1,
            'videolibrary.showemptytvshows': False,
            'videolibrary.tvshowsselectfirstunwatcheditem': 2,
            'videolibrary.tvshowsincludeallseasonsandspecials': 3,
            'videolibrary.artworklevel': 2,
            'videolibrary.movieartwhitelist': ['keyart', 'square', 'clearlogo', 'clearlogo-alt', 'clearlogo-billboard'],
            'videolibrary.tvshowartwhitelist': ['keyart', 'square', 'clearlogo', 'clearlogo-alt', 'clearlogo-billboard'],
            'musiclibrary.showallitems': False,
            'musiclibrary.showcompilationartists': False,
            'pictures.generatethumbs': True,
            'musicplayer.visualisation': 'visualization.waveform'
        }
        self.settings_to_change = {}

    def get_default(self, **kwargs):
        self.settings_to_change.clear()
        window_property('Settings_To_Change')
        cats = {
            'general': False,
            'videolibrary': False,
            'musiclibrary': False,
            'pictures': False,
            'musicplayer': False
        }
        for item in list(self.settings.items()):
            window_property(key=item[0])
            category = item[0].split('.')[0]
            json_response = json_call('Settings.GetSettingValue',
                                        params={'setting': item[0]},
                                        parent='get_settings'
                                        )
            try:
                value = json_response['result']['value']

            except KeyError:
                value = 'None'
            if value != item[1]:
                if (
                    (isinstance(value, int) and value == 0) or
                    (isinstance(value, bool) and value == False)
                ):
                    value = '0'
                elif (
                    (isinstance(value, list) and value == []) or
                    (isinstance(value, str) and value == '')
                ):
                    value = 'None'
                cats.update({category: True})
                self.settings_to_change.update({item[0]: item[1]})
                if isinstance(value, list):
                    window_property(key=item[0], set=', '.join(value))
                else:
                    window_property(key=item[0], set=value)
        cat_count = sum(value for value in list(cats.values()))
        item_count = cat_count + len(self.settings_to_change)
        window_property('Settings_To_Change', set=item_count)

    def set_default(self, **kwargs):
        count = 0
        for item in list(self.settings_to_change.items()):
            if condition(f'Skin.HasSetting({item[0]})'):
                json_call('Settings.SetSettingValue',
                                        params={'setting': item[0], 'value': item[1]},
                                        parent='set_settings'
                                        )
                count += 1
        if count == 1:
            string = ADDON.getLocalizedString(32203)
        else:
            string = ADDON.getLocalizedString(32204)
        string = f'{count} ' + string + '.'
        DIALOG.notification(ADDON_ID, string)

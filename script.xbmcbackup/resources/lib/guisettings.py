import json
import xbmc
from . import utils as utils


class GuiSettingsManager:
    filename = 'kodi_settings.json'
    systemSettings = None

    def __init__(self):
        # get all of the current Kodi settings
        json_response = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.GetSettings","params":{"level":"expert"}}'))

        self.systemSettings = json_response['result']['settings']

    def list_addons(self):
        # list all currently installed addons
        addons = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Addons.GetAddons", "params":{"properties":["version","author"]}, "id":2}'))

        return addons['result']['addons']

    def backup(self):
        utils.log('Backing up Kodi settings')

        # return all current settings
        return self.systemSettings

    def restore(self, restoreSettings):
        utils.log('Restoring Kodi settings')

        updateJson = {"jsonrpc": "2.0", "id": 1, "method": "Settings.SetSettingValue", "params": {"setting": "", "value": ""}}

        # create a setting=value dict of the current settings
        settingsDict = {}
        for aSetting in self.systemSettings:
            # ignore action types, no value
            if(aSetting['type'] != 'action'):
                settingsDict[aSetting['id']] = aSetting['value']

        restoreCount = 0
        for aSetting in restoreSettings:
            # Ensure key exists before referencing
            if(aSetting['id'] in settingsDict.values()):
            # only update a setting if its different than the current (action types have no value)
                if(aSetting['type'] != 'action' and settingsDict[aSetting['id']] != aSetting['value']):
                    if(utils.getSettingBool('verbose_logging')):
                        utils.log('%s different than current: %s' % (aSetting['id'], str(aSetting['value'])))

                updateJson['params']['setting'] = aSetting['id']
                updateJson['params']['value'] = aSetting['value']

                xbmc.executeJSONRPC(json.dumps(updateJson))
                restoreCount = restoreCount + 1

        utils.log('Update %d settings' % restoreCount)

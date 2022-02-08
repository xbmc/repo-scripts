import xbmc
import xbmcgui
import json
import os
import sys
from resources.lib import hcdialog
from resources.lib.hcsettings import loadSettings
from resources.lib.xlogger import Logger
from resources.lib.api.harmony import HubControl
try:
    from urllib.parse import unquote_plus as _unquote_plus
except ImportError:
    from urllib import unquote_plus as _unquote_plus


def _upgrade():
    settings = loadSettings()
    if settings['version_upgrade'] != settings['ADDONVERSION']:
        settings['ADDON'].setSetting(
            'version_upgrade', settings['ADDONVERSION'])


class Main:

    def __init__(self):
        self._init_vars()
        self.LW = Logger(preamble='[Harmony Hub Control]',
                         logdebug=self.SETTINGS['debug'])
        self.LW.log(['script version %s started' %
                    self.SETTINGS['ADDONVERSION']], xbmc.LOGINFO)
        self._parse_argv()
        if self.ACTION == 'fromsettings':
            self._mappings_options()
            self.SETTINGS['ADDON'].openSettings()
        elif self.ACTION:
            saved_mappings, json_mappings = self._get_mappings()
            activity, cmds = self._get_mapping_details(
                json_mappings, self.ACTION)
            self._run_activity(activity, cmds)
        else:
            self._pick_activity()
        self.LW.log(['script stopped'], xbmc.LOGINFO)

    def _init_vars(self):
        self.SETTINGS = loadSettings()
        self.DIALOG = xbmcgui.Dialog()
        self.MYHUB = HubControl(
            self.SETTINGS['hub_ip'], thetimeout=self.SETTINGS['timeout'], delay=self.SETTINGS['delay'])

    def _get_mappings(self):
        self.LW.log(['the settings mappings are:', self.SETTINGS['mappings']])
        try:
            json_mappings = json.loads(self.SETTINGS['mappings'])
        except ValueError:
            json_mappings = {}
        saved_mappings = []
        for item in json_mappings:
            mapping_name = json_mappings.get(item, {}).get('match')
            if mapping_name:
                saved_mappings.append(mapping_name)
        saved_mappings.sort()
        self.LW.log(['returning saved mappings of:', saved_mappings,
                    'returning json mappings of:', json_mappings])
        return saved_mappings, json_mappings

    def _get_mapping_details(self, json_mappings, item):
        activity = json_mappings.get(item, {}).get('activity', '')
        if self.SETTINGS['harmonyadvanced']:
            cmds = json_mappings.get(item, {}).get('cmds', '')
        else:
            cmds = ''
        return activity, cmds

    def _mappings_options(self):
        options = [self.SETTINGS['ADDONLANGUAGE'](32300)]
        options.append(self.SETTINGS['ADDONLANGUAGE'](32301))
        options.append(self.SETTINGS['ADDONLANGUAGE'](32302))
        ret = self.DIALOG.select(
            self.SETTINGS['ADDONLANGUAGE'](32200), options)
        self.LW.log(['got back %s from the dialog box' % str(ret)])
        if ret == -1:
            return
        if ret == 0:
            self._option_add()
        elif ret == 1:
            self._option_edit()
        elif ret == 2:
            self._option_edit(dodelete=True)

    def _option_add(self, default_match='', default_activity='', default_cmds=''):
        thematch = self.DIALOG.input(
            self.SETTINGS['ADDONLANGUAGE'](32201), defaultt=default_match)
        if not thematch:
            return
        activity_list = []
        activities, loglines = self.MYHUB.getActivities()
        self.LW.log(loglines)
        for activity_key in activities:
            activity_list.append(activity_key)
        activity_list.sort()
        if activity_list:
            try:
                default_index = activity_list.index(default_activity)
            except ValueError:
                default_index = -1
            ret = self.DIALOG.select(
                self.SETTINGS['ADDONLANGUAGE'](32203), activity_list, 0, default_index)
            if ret == -1:
                return
            else:
                activity = activity_list[ret]
        else:
            activity = self.DIALOG.input(
                self.SETTINGS['ADDONLANGUAGE'](32203), defaultt=default_activity)
        if self.SETTINGS['harmonyadvanced']:
            cmds = self.DIALOG.input(
                self.SETTINGS['ADDONLANGUAGE'](32202), defaultt=default_cmds)
        else:
            cmds = ''
        saved_mappings, json_mappings = self._get_mappings()
        json_mappings[thematch] = {'match': thematch,
                                   'activity': activity, 'cmds': cmds}
        self.SETTINGS['ADDON'].setSetting(
            'mappings', json.dumps(json_mappings))

    def _option_edit(self, dodelete=False):
        saved_mappings, json_mappings = self._get_mappings()
        if not json_mappings:
            self._option_add()
            return
        ret = self.DIALOG.select(
            self.SETTINGS['ADDONLANGUAGE'](32204), saved_mappings)
        if ret == -1:
            return
        if dodelete:
            del json_mappings[saved_mappings[ret]]
            self.SETTINGS['ADDON'].setSetting(
                'mappings', json.dumps(json_mappings))
        else:
            thematch = json_mappings.get(
                saved_mappings[ret], {}).get('match', '')
            activity = json_mappings.get(
                saved_mappings[ret], {}).get('activity', '')
            cmds = json_mappings.get(saved_mappings[ret], {}).get('cmds', '')
            self._option_add(default_match=thematch,
                             default_activity=activity, default_cmds=cmds)

    def _parse_argv(self):
        try:
            self.ACTION = sys.argv[1]
        except IndexError:
            self.ACTION = ''

    def _pick_activity(self):
        saved_mappings, json_mappings = self._get_mappings()
        dialog_return, loglines = hcdialog.Dialog().start(self.SETTINGS, title=self.SETTINGS['ADDONLANGUAGE'](32205),
                                                          buttons=saved_mappings)
        self.LW.log(loglines)
        if dialog_return is None:
            return
        activity, cmds = self._get_mapping_details(
            json_mappings, saved_mappings[dialog_return])
        self._run_activity(activity, cmds)

    def _run_activity(self, activity, cmds):
        if self.SETTINGS['hub_ip']:
            self.LW.log(['the activity to run is: %s' % activity])
            if activity:
                result, loglines = self.MYHUB.startActivity(activity)
                self.LW.log(loglines)
                self.LW.log(['the result from the hub was:', result])
            else:
                self.LW.log(['no activity to run'])
            self.LW.log(['the extra commands to run are: %s' % cmds])
            if cmds:
                result, loglines = self.MYHUB.runCommands(cmds)
                self.LW.log(loglines)
                self.LW.log(['the result from the hub was:', result])
            else:
                self.LW.log(['no extra commands to run'])
        else:
            self.LW.log(['no hub IP address in settings'], xbmc.LOGWARNING)

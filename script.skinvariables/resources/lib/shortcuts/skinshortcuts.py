# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import re
import xbmc
import xbmcgui
import jurialmunkey.futils
import xml.etree.ElementTree as ET
from json import loads
from jurialmunkey.futils import get_files_in_folder, load_filecontent, write_file
from resources.lib.kodiutils import get_localized

ADDONDATA = 'special://profile/addon_data/script.skinvariables/'
TAB = '    '
DATA_FOLDER = 'special://profile/addon_data/script.skinshortcuts/'
SKIN_FOLDER = 'special://skin/shortcuts/'


class FileUtils(jurialmunkey.futils.FileUtils):
    addondata = ADDONDATA   # Override module addon_data with plugin addon_data


FILEUTILS = FileUtils()
delete_file = FILEUTILS.delete_file


get_infolabel = xbmc.getInfoLabel


class SkinShortcutsMethodsJSON():
    pass


class SkinShortcutsMethodsXML():
    def write_shortcut(self, name):
        shortcuts_content = []
        for shortcut in self.meta[name]:
            shortcut_content = '\n'.join([f'{TAB}{TAB}<{tag_name}>{tag_text}</{tag_name}>' for tag_name, tag_text in shortcut.items()])
            shortcut_content = f'{TAB}<shortcut>\n{shortcut_content}\n{TAB}</shortcut>'
            shortcut_content = shortcut_content.replace('&', '&amp;')
            shortcuts_content.append(shortcut_content)
        shortcuts_content = '\n'.join(shortcuts_content)
        content = f'<shortcuts>\n{shortcuts_content}\n</shortcuts>'
        filepath = f'{DATA_FOLDER}{self.skin}-{name}.DATA.xml'
        write_file(filepath=filepath, content=content)
        delete_file(folder=DATA_FOLDER, filename=f'{self.skin}.hash', join_addon_data=False)

    def mod_skinshortcut(self):
        name = self.get_menu_name(self.params.get('name'), heading=get_localized(32016))
        if not name:
            return
        if name[-2:-1] == '-':
            name = name[:-2] + '.' + name[-1:]
        xbmc.executebuiltin(f'RunScript(script.skinshortcuts,type=manage&group={name})')
        return name

    def del_skinshortcut(self):
        name = self.get_menu_name(self.params.get('name'), heading=get_localized(32017))
        if not name:
            return
        try:
            x = int(self.params.get('index')) - 1
        except (ValueError, TypeError):
            files = [self.get_nice_name(i.get('label')) for i in self.meta[name]]
            x = xbmcgui.Dialog().select(get_localized(117), files)
        if x == -1:
            return
        self.meta[name].pop(x)
        self.write_shortcut(name)
        return name

    def add_skinshortcut(self):
        action = ''

        def _get_infolabel(infolabel):
            if self.params.get('use_listitem'):
                return get_infolabel(infolabel) or ''
            return ''

        if self.params.get('path') or self.params.get('use_listitem'):
            window = self.params.get('window') or 'videos'
            folder = self.params.get('path') or _get_infolabel('Container.ListItem.FolderPath')
            action = f"ActivateWindow({window},{folder},return)"

        item = self.config_id({
            'label': self.params.get('label') or _get_infolabel('Container.ListItem.Label'),
            'label2': self.params.get('label2') or _get_infolabel('Container.ListItem.Label2'),
            'icon': self.params.get('icon') or _get_infolabel('Container.ListItem.Icon'),
            'thumb': self.params.get('thumb') or '',
            'action': action
        })

        name, nice_name = self.choose_menu(get_localized(32021))
        if not name:
            return
        self.meta[name].append(item)
        self.write_shortcut(name)

        xbmcgui.Dialog().ok(get_localized(32020), get_localized(32018).format(item.get('label') or '', nice_name))
        return name

    def imp_skinshortcut(self):
        files = [i for i in get_files_in_folder(DATA_FOLDER, r'.*?-(.*)\.DATA\.xml')]
        if not files:
            xbmcgui.Dialog().ok(get_localized(32019), get_localized(32022))
            return
        x = xbmcgui.Dialog().select(get_localized(32019), files)
        if x == -1:
            return

        name, nice_name = self.choose_menu(get_localized(32023))
        if not name:
            return
        self.meta[name] = self.load_skinshortcut(f'{DATA_FOLDER}{files[x]}')
        self.write_shortcut(name)

        xbmcgui.Dialog().ok(get_localized(32024), get_localized(32025).format(files[x], nice_name))
        return name

    def mov_skinshortcut(self):
        regex = r'(.*)\.DATA\.xml'
        folder = self.params['folder']

        if not xbmcgui.Dialog().yesno(get_localized(32026), get_localized(32027), yeslabel=get_localized(186), nolabel=get_localized(222)):
            return

        for file in get_files_in_folder(folder, regex):
            name = re.search(regex, file).group(1)
            self.meta[name] = self.load_skinshortcut(f'{folder}{file}')
            self.write_shortcut(name)

        xbmcgui.Dialog().ok(get_localized(32019), get_localized(32028).format(folder, self.skin))
        return name


class SkinShortcutsMenu():
    def __init__(self, skin, **kwargs):
        self.skin = skin
        self.params = kwargs
        self.folders = [
            (SKIN_FOLDER, r'(.*)\.DATA\.xml'),
            (DATA_FOLDER, fr'{self.skin}-(.*)\.DATA\.xml')]
        self.meta = self.read_skinshortcuts(self.folders)
        self.config = self.read_config()

    def read_config(self):
        content = load_filecontent('special://skin/shortcuts/skinvariables-skinshortcuts.json')
        if not content:
            return {}
        config = loads(content) or {}
        levels = config.get('mainmenu', {}).get('levels') or [{}]

        mainmenu = self.meta.setdefault('mainmenu', [])
        for i in mainmenu:
            default_id = i.get('defaultID')
            for level in levels:
                affix = level.get('affix') or ''
                level_default_id = f'{default_id}{affix}'
                self.meta.setdefault(level_default_id, [])
                config.setdefault(level_default_id, {k: v for k, v in level.items()})
                if i.get('label') and not i['label'].startswith('$SKIN'):
                    config[level_default_id]['name'] = i['label']

        return config

    @staticmethod
    def load_skinshortcut_file(filename):
        xmlstring = load_filecontent(filename)
        if not xmlstring:
            return []
        return [{i.tag: i.text for i in shortcut} for shortcut in ET.fromstring(xmlstring)]

    def load_skinshortcut(self, filename, configure_ids=True):
        meta = self.load_skinshortcut_file(filename)
        if not configure_ids:
            return meta
        return self.configure_ids(meta)

    def read_skinshortcuts(self, folders):
        meta = {}
        for folder, regex in folders:
            for file in get_files_in_folder(folder, regex):
                name = re.search(regex, file).group(1)
                meta[name] = self.load_skinshortcut(f'{folder}{file}')
        return meta

    def configure_ids(self, meta):
        return [self.config_id(item) for item in meta]

    @staticmethod
    def config_id(item):
        if item.get('defaultID'):
            return item
        label_id = item.get('labelID') or re.sub('[^0-9a-zA-Z]+', '', item.get('label') or '')
        item['defaultID'] = item['labelID'] = label_id.lower()
        return item

    def get_index(self, label):
        if label not in self.config:
            return ''
        if 'index' not in self.config[label]:
            return
        return str(self.config[label]['index'] or '')

    def get_nice_name(self, label):
        prefix, suffix, affix = '', '', ''

        if label in self.config:
            affix = self.config[label].get('affix') or ''
            suffix = self.config[label].get('suffix') or ''
            prefix = self.config[label].get('prefix') or ''
            label = self.config[label].get('name') or label

        if affix and label.endswith(affix):
            label = label[:-len(affix)]

        monitor = xbmc.Monitor()

        while not monitor.abortRequested():
            result = re.search(r'.*\$LOCALIZE\[(.*?)\].*', label)
            if not result:
                break
            try:
                localized = xbmc.getLocalizedString(int(result.group(1))) or ''
            except ValueError:
                localized = ''
            label = label.replace(result.group(0), localized)

        while not monitor.abortRequested():
            result = re.search(r'.*\$INFO\[(.*?)\].*', label)
            if not result:
                break
            localized = get_infolabel(result.group(1)) or ''
            label = label.replace(result.group(0), localized)

        try:
            label = xbmc.getLocalizedString(int(label)) or label
        except ValueError:
            pass

        label = f'{prefix}{label}{suffix}'

        return label

    def choose_menu(self, header, names=None):
        names = names if names else self.meta.keys()
        regex = self.params.get('label_regex')
        files = [(self.get_nice_name(i), i, self.get_index(i), ) for i in names if not regex or re.search(regex, self.get_nice_name(i))]
        files = sorted(files, key=lambda a: f'{a[2] or ""}{a[0]}')
        x = xbmcgui.Dialog().select(header, [i[0] for i in files])
        if x == -1:
            return (None, '')
        choice = [i for i in files][x]
        return (choice[1], choice[0])

    def get_menu_name(self, name=None, heading=get_localized(32029)):
        if not name:
            return
        name = [i[4:] if i.startswith('num-') else i for i in name.split('||')]
        menu = [k for k in self.meta.keys() if any(re.match(i, k) for i in name)]
        if len(menu) == 1:
            return menu[0]
        if len(menu) > 1:
            return self.choose_menu(heading, menu)[0]
        return self.choose_menu(heading)[0]

    def run(self, action):
        route = getattr(self, action)

        try:
            success = route()
        except KeyError:
            success = False

        if not success:
            return

        if self.params.get('executebuiltin'):
            xbmc.executebuiltin(self.params['executebuiltin'])


class SkinShortcutsXML(SkinShortcutsMenu, SkinShortcutsMethodsXML):
    pass


class SkinShortcutsJSON(SkinShortcutsMenu, SkinShortcutsMethodsJSON):
    pass


def get_skinshortcuts_menu(route, mode='xml', **kwargs):
    factory = {
        'xml': SkinShortcutsXML,
        'json': SkinShortcutsJSON
    }
    factory[mode](**kwargs).run(route)

import xbmc
import xbmcgui
from resources.lib.kodiutils import get_localized


LISTITEM_VALUE_PAIRS = (('label', 'Label'), ('icon', 'Icon'), ('path', 'FolderPath'))
DEFAULT_MODES = ('submenu', 'widgets')


def get_target_from_window():
    if xbmc.getCondVisibility('Window.IsVisible(MyVideoNav.xml)'):
        return 'videos'
    if xbmc.getCondVisibility('Window.IsVisible(MyMusicNav.xml)'):
        return 'music'
    if xbmc.getCondVisibility('Window.IsVisible(MyPics.xml)'):
        return 'pictures'
    if xbmc.getCondVisibility('Window.IsVisible(MyPrograms.xml)'):
        return 'programs'
    if xbmc.getCondVisibility('Window.IsVisible(MyPVRGuide.xml)'):
        return 'tvguide'
    if xbmc.getCondVisibility('Window.IsVisible(MyPVRChannels.xml)'):
        return 'tvchannels'


def get_item_from_listitem(item=None, value_pairs=None, listitem='Container.ListItem'):
    item = item or {}
    value_pairs = value_pairs or LISTITEM_VALUE_PAIRS
    return {k: xbmc.getInfoLabel(f'{listitem}.{v}') or item.get(k) or '' for k, v in value_pairs}


class MenuNode():
    def __init__(self, skin, menufiles=None, levels=1):
        self.skin = skin
        self.menufiles = menufiles or []
        self.levels = int(levels)

    def select_menu(self):
        if not self.menufiles:
            return
        x = xbmcgui.Dialog().select(get_localized(32069), self.menufiles)
        if x == -1:
            return
        return self.menufiles[x]

    def get_menu(self):
        self._menu = self.select_menu()
        return self._menu

    @property
    def menu(self):
        try:
            return self._menu
        except AttributeError:
            return self.get_menu()

    def select_node(self, mode, guid, level=0):
        from resources.lib.shortcuts.node import ListGetShortcutsNode
        lgsn = ListGetShortcutsNode(-1, '')
        lgsn.get_directory(menu=self.menu, skin=self.skin, item=None, mode=mode, guid=guid, func='node')
        if lgsn.menunode is None:
            return
        choices = [f'{get_localized(32071)}...']
        if level < self.levels:  # Only add the options to traverse submenu/widgets if we're not deeper than our max level
            from jurialmunkey.parser import parse_localize
            choices = [parse_localize(i.get('label') or '') for i in lgsn.menunode] + choices
        x = xbmcgui.Dialog().select(get_localized(32069), choices)
        if x == -1:
            return
        if choices[x] == f'{get_localized(32071)}...':
            return lgsn
        y = xbmcgui.Dialog().select(get_localized(32070), DEFAULT_MODES)
        if y == -1:
            return self.select_node(mode, guid, level)  # Go back to previous level
        return self.select_node(DEFAULT_MODES[y], lgsn.menunode[x].get('guid'), level=level + 1)  # Go up to next level

    def set_item_to_node(self, item):
        lgsn = self.select_node('submenu', None)
        if not lgsn:
            return
        lgsn.menunode.append(item)
        lgsn.write_meta_to_file()
        lgsn.do_refresh()


def set_listitem_to_menunode(set_listitem_to_menunode, skin, label=None, icon=None, path=None, target=None, use_listitem=True):
    if not set_listitem_to_menunode or not skin:
        return
    item = {'label': label, 'icon': icon, 'path': path, 'target': target}

    if use_listitem:
        item = get_item_from_listitem(item)
        item['target'] = get_target_from_window() or target or 'videos'

    if not item['path']:
        xbmcgui.Dialog().ok(heading=get_localized(32068), message=get_localized(32067))
        return

    MenuNode(skin, menufiles=set_listitem_to_menunode.split('||')).set_item_to_node(item)


def set_shortcut(set_shortcut, use_rawpath=False):
    import xbmc
    from jurialmunkey.parser import boolean
    from jurialmunkey.window import WindowProperty
    from resources.lib.shortcuts.browser import GetDirectoryBrowser

    with WindowProperty(('IsSkinShortcut', 'True')):
        item = GetDirectoryBrowser(use_rawpath=boolean(use_rawpath)).get_directory()

    if not item:
        return

    item = {f'{set_shortcut}.{k}': v for k, v in item.items()}

    for k, v in item.items():
        if not isinstance(v, str):
            continue
        xbmc.executebuiltin(f'Skin.SetString({k},{v})')


def copy_menufolder(copy_menufolder, skin):
    from resources.lib.shortcuts.futils import read_meta_from_file, get_files_in_folder

    files = get_files_in_folder(copy_menufolder, r'.*\.json')
    if not files:
        xbmcgui.Dialog().ok(get_localized(32076), f'copy_menufolder={copy_menufolder}\nskin={skin}')
        return

    msg = get_localized(32072).format(
        filename=get_localized(32073).format(skin=skin),
        content=get_localized(32074).format(folder=copy_menufolder))
    msg = f'{msg}\n{get_localized(32043)}'

    x = xbmcgui.Dialog().yesno(get_localized(32075), msg)

    if not x or x == -1:
        return

    from resources.lib.shortcuts.node import assign_guid
    from resources.lib.shortcuts.futils import write_meta_to_file

    files = ((read_meta_from_file(f'{copy_menufolder}{f}'), f) for f in files if f)
    for meta, file in files:
        if not meta or not file:
            continue
        write_meta_to_file(
            assign_guid(meta),
            folder=skin,
            filename=file,
            fileprop=f'{skin}-{file}',
            reload=True)


def copy_menufile(copy_menufile, filename, skin):
    from resources.lib.shortcuts.futils import read_meta_from_file, write_meta_to_file, FILE_PREFIX
    if not copy_menufile or not filename or not skin:
        raise ValueError(f'copy_menufile details missing\ncopy_menufile={copy_menufile}\nfilename={filename}\nskin={skin}')
        return
    filename = f'{FILE_PREFIX}{filename}.json'
    meta = read_meta_from_file(copy_menufile)
    if meta is None:
        raise ValueError(f'copy_menufile content missing\ncopy_menufile={copy_menufile}\nfilename={filename}\nskin={skin}')
        return
    x = xbmcgui.Dialog().yesno(get_localized(32075), f'{get_localized(32072).format(filename=filename, content=copy_menufile)}\n{get_localized(32043)}')
    if not x or x == -1:
        return
    from resources.lib.shortcuts.node import assign_guid
    write_meta_to_file(assign_guid(meta), folder=skin, filename=filename, fileprop=f'{skin}-{filename}', reload=True)

# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmcgui import ListItem, Dialog, INPUT_NUMERIC
from jurialmunkey.litems import Container
from resources.lib.kodiutils import get_localized
import jurialmunkey.futils as jmfutils


BASEPLUGIN = 'plugin://script.skinvariables/'
BASEFOLDER = 'special://profile/addon_data/script.skinvariables/logins/'
USERS_FILE = 'skinusers.json'


class FileUtils(jmfutils.FileUtils):
    addondata = BASEFOLDER   # Override module addon_data with plugin addon_data


class ListAddSkinUser(Container):
    def get_directory(self, skinid, **kwargs):
        import re
        import random
        from jurialmunkey.futils import load_filecontent
        from resources.lib.shortcuts.futils import reload_shortcut_dir
        from json import loads
        filepath = f'{BASEFOLDER}/{skinid}/{USERS_FILE}'
        file = load_filecontent(filepath)
        meta = loads(file) if file else []

        name = Dialog().input(get_localized(32054))
        if not name:
            return

        slug = re.sub('[^0-9a-zA-Z]+', '', name)
        if not slug:
            slug = f'{random.randrange(16**8):08x}'  # Assign a random 32bit hex value if no valid slug name
        slug = f'user-{slug}'  # Avoid Kodi trying to localize slugs which are only numbers by adding alpha prefix

        icon = ''

        def _get_code():
            if not Dialog().yesno(get_localized(32055), get_localized(32056)):
                return
            code = Dialog().input(get_localized(32057), type=INPUT_NUMERIC)
            if not code:
                return
            if not Dialog().input(get_localized(32058), type=INPUT_NUMERIC) == code:
                return _get_code()
            return str(code)

        code = _get_code()

        item = {
            'name': name,
            'slug': slug,
            'icon': icon,
            'code': code
        }

        meta.append(item)
        FileUtils().dumps_to_file(meta, folder=skinid, filename=USERS_FILE, indent=4)
        reload_shortcut_dir()


class ListGetSkinUser(Container):
    def get_directory(self, skinid, folder, slug=None, allow_new=False, func=None, **kwargs):
        import xbmc
        from jurialmunkey.parser import boolean
        from jurialmunkey.futils import load_filecontent, write_skinfile
        from resources.lib.shortcuts.futils import reload_shortcut_dir
        from json import loads

        filepath = f'{BASEFOLDER}/{skinid}/{USERS_FILE}'
        file = load_filecontent(filepath)
        meta = loads(file) if file else []

        def _login_user():
            if slug == 'default':
                user = _get_default_user()
            else:
                user = next(i for i in meta if slug == i.get('slug'))

            if user.get('code') and str(user.get('code')) != str(Dialog().input(get_localized(32057), type=INPUT_NUMERIC)):
                Dialog().ok(get_localized(32063), get_localized(32060))
                return

            xbmc.executebuiltin('SetProperty(SkinVariables.SkinUser.LoggingIn,True,Home)')

            filename = 'script-skinvariables-skinusers.xml'
            content = load_filecontent(f'special://skin/shortcuts/skinvariables-skinusers.xmltemplate')
            content = content.format(slug=slug if slug != 'default' else '', **kwargs)
            write_skinfile(folders=[folder], filename=filename, content=content)

            import datetime
            last = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            executebuiltin = xbmc.getInfoLabel('Skin.String(SkinVariables.SkinUser.ExecuteBuiltIn)')
            xbmc.executebuiltin(f'Skin.SetString(SkinVariables.SkinUser.Name,{user.get("name")})')
            xbmc.executebuiltin(f'Skin.SetString(SkinVariables.SkinUser.Icon,{user.get("icon", "")})')
            xbmc.executebuiltin(f'Skin.SetString(SkinVariables.SkinUser,{slug})' if slug != 'default' else 'Skin.Reset(SkinVariables.SkinUser)')
            xbmc.executebuiltin(f'Skin.SetString(SkinVariables.SkinUser.{slug}.LastLogin,{last})')
            xbmc.executebuiltin('SetProperty(SkinVariables.SkinUserLogin,True,Home)')
            xbmc.executebuiltin(executebuiltin or 'ReloadSkin()')

        def _get_default_user():
            return {'name': get_localized(32061), 'slug': 'default'}

        def _make_item(i):
            name = i.get('name') or ''
            slug = i.get('slug') or ''

            if not name:
                return

            icon = i.get('icon') or ''
            code = i.get('code') or ''
            menu = boolean(i.get('menu', True))
            path = f'{BASEPLUGIN}?info=get_skin_user&skinid={skinid}&slug={slug}'
            path = f'{path}&folder={folder}' if folder else path
            last = xbmc.getInfoLabel(f'Skin.String(SkinVariables.SkinUser.{slug}.LastLogin)') or get_localized(32062)

            li = ListItem(label=name, label2=last, path=path)
            li.setProperty('last', last)
            li.setProperty('slug', slug)
            li.setProperty('code', code) if code else None
            li.setArt({'thumb': icon, 'icon': icon}) if icon else None

            def _get_contentmenuitems():
                if not menu:
                    return []
                if slug == 'default':
                    return [_get_contextmenu_item_toggle_default_user()]
                return [
                    ('Rename', f'RunPlugin({path}&func=rename)'),
                    ('Delete', f'RunPlugin({path}&func=delete)')]

            li.addContextMenuItems(_get_contentmenuitems())

            return (path, li, False)

        def _get_contextmenu_item_toggle_default_user():
            path = f'{BASEPLUGIN}?info=get_skin_user&skinid={skinid}&slug=default'
            path = f'{path}&folder={folder}' if folder else path
            path = f'RunPlugin({path}&func=toggle)'
            if xbmc.getCondVisibility('Skin.HasSetting(SkinVariables.SkinUsers.DisableDefaultUser)'):
                return (get_localized(32097), path)
            return (get_localized(32098), path)

        def _join_item():
            if not boolean(allow_new):
                return []
            name = f'{get_localized(32096)}...'
            path = f'{BASEPLUGIN}?info=add_skin_user&skinid={skinid}'
            path = f'{path}&folder={folder}' if folder else path
            li = ListItem(label=name, path=path)
            li.addContextMenuItems([_get_contextmenu_item_toggle_default_user()])
            return [(path, li, False)]

        def _open_directory():
            items = []
            if xbmc.getCondVisibility('!Skin.HasSetting(SkinVariables.SkinUsers.DisableDefaultUser)'):
                items += [_make_item(_get_default_user())]
            items += [j for j in (_make_item(i) for i in meta) if j] + _join_item()
            plugin_category = ''
            container_content = ''
            self.add_items(items, container_content=container_content, plugin_category=plugin_category)

        def _toggle_default_user():
            xbmc.executebuiltin('Skin.ToggleSetting(SkinVariables.SkinUsers.DisableDefaultUser)')
            reload_shortcut_dir()

        def _delete_user():
            x, user = next((x, i) for x, i in enumerate(meta) if slug == i.get('slug'))

            if user.get('code') and str(user.get('code')) != str(Dialog().input(get_localized(32057), type=INPUT_NUMERIC)):
                Dialog().ok(get_localized(32063), get_localized(32060))
                return
            if not Dialog().yesno(get_localized(32064), f'{get_localized(32065).format(user["name"])}\n{get_localized(32043)}'):
                return

            del meta[x]
            FileUtils().dumps_to_file(meta, folder=skinid, filename=USERS_FILE, indent=4)
            reload_shortcut_dir()

        def _rename_user():
            x, user = next((x, i) for x, i in enumerate(meta) if slug == i.get('slug'))

            if user.get('code') and str(user.get('code')) != str(Dialog().input(get_localized(32057), type=INPUT_NUMERIC)):
                Dialog().ok(get_localized(32063), get_localized(32060))
                return
            user['name'] = Dialog().input(get_localized(32066), defaultt=user.get('name', ''))
            if not user['name']:
                return
            meta[x] = user
            FileUtils().dumps_to_file(meta, folder=skinid, filename=USERS_FILE, indent=4)
            reload_shortcut_dir()

        if not slug:
            _open_directory()
            return

        route = {
            'toggle': _toggle_default_user,
            'delete': _delete_user,
            'rename': _rename_user
        }
        route.get(func, _login_user)()

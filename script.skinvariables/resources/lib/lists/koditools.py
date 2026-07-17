# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from jurialmunkey.window import set_to_windowprop, clear_windowprops, get_property
from jurialmunkey.litems import ContainerDirectory


KEYS_PROP = 'PropertiesList'


def store_windowprops(values, window_prop, window_id=None):
    set_to_windowprop(f'{"||".join(values)}', KEYS_PROP, window_prop, window_id)


def store_windowprops_counter(stop, window_prop, window_id=None):
    store_windowprops([str(x) for x in range(0, stop)], window_prop, window_id)


def clear_windowprops_decorator(func):
    def wrapper(*args, **kwargs):
        clear_windowprops(window_prop=kwargs.get('window_prop'), window_id=kwargs.get('window_id'), keys_prop=KEYS_PROP)
        return func(*args, **kwargs)
    return wrapper


class ListGetRefreshCounter(ContainerDirectory):

    @clear_windowprops_decorator
    def get_directory(self, uid, window_prop=None, window_id=None, **kwargs):

        affix = 'SkinVariables'
        value = int(get_property(uid, prefix=affix) or 0) + 1
        get_property(uid, prefix=affix, set_property=str(value))

        label = f'{value}'
        items = [self.get_list_item(label)]
        set_to_windowprop(label, 0, window_prop, window_id)

        self.add_items(items)


class ListGetNumberSum(ContainerDirectory):

    @clear_windowprops_decorator
    def get_directory(self, expression, window_prop=None, window_id=None, **kwargs):

        values = [0]
        values += [int(i) for i in expression.split() if i]

        label = f'{sum(values)}'
        items = [self.get_list_item(label)]
        set_to_windowprop(label, 0, window_prop, window_id)

        self.add_items(items)


class ListRunExecuteBuiltin(ContainerDirectory):
    def get_directory(self, paths, **kwargs):
        from resources.lib.method import run_executebuiltin

        for path in paths:
            run_executebuiltin(path, use_rules=True, **kwargs)

        items = [self.get_list_item('None')]  # Add a blank item to keep container alive

        self.add_items(items)


class ListGetJSONRPC(ContainerDirectory):

    @clear_windowprops_decorator
    def get_directory(self, info, method, window_prop=None, window_id=None, **kwargs):
        from jurialmunkey.jsnrpc import get_jsonrpc
        result = get_jsonrpc(method, kwargs) or {}
        result = result.get("result")
        if not result:
            return

        items = [self.get_list_item(method)]

        li = items[0][1]
        keys = []
        for k, v in result.items():
            li.setProperty(str(k), str(v))
            set_to_windowprop(v, k, window_prop, window_id)
            keys.append(k)

        store_windowprops(keys, window_prop, window_id)
        self.add_items(items)

        return result


class ListGetARGBColors(ContainerDirectory):

    @clear_windowprops_decorator
    def get_directory(self, colorhex=None, window_prop=None, window_id=None, slider_window_id=None, **kwargs):
        if not colorhex:
            return

        from xbmcgui import Window

        start_positions = {'alpha': 0, 'red': 2, 'green': 4, 'blue': 6}

        def get_argb_int(hx):
            return int(hx, 16)

        def get_argb_percent(ix):
            return int((ix / 255) * 100)

        def get_argb_hex(colorhex, color):
            a = start_positions[color]
            b = a + 2
            return colorhex[a:b]

        items = []
        infoproperties = {}
        for color in start_positions.keys():
            hx = get_argb_hex(colorhex, color)
            ix = get_argb_int(hx)
            pc = get_argb_percent(ix)
            infoproperties[f'{color}.hex'] = hx
            infoproperties[f'{color}.int'] = ix
            infoproperties[f'{color}.pct'] = pc
            if not slider_window_id:
                continue
            if not kwargs.get(f'slider_{color}_id'):
                continue
            try:
                win = Window(int(slider_window_id))
                con = win.getControl(int(kwargs[f'slider_{color}_id']))
                con.setPercent(pc)
            except Exception:
                pass

        item = self.get_list_item(colorhex)
        item[1].setProperties(infoproperties)
        items.append(item)

        keys = []
        for key, value in infoproperties.items():
            set_to_windowprop(value, key, window_prop, window_id)
            keys.append(key)

        store_windowprops(keys, window_prop, window_id)
        self.add_items(items)


class ListGetSplitString(ContainerDirectory):

    @clear_windowprops_decorator
    def get_directory(self, values=None, infolabel=None, separator='|', window_prop=None, window_id=None, **kwargs):
        from xbmc import getInfoLabel as get_infolabel
        values = get_infolabel(infolabel) if infolabel else values

        if not values:
            return

        x = 0
        items = []
        for i in values.split(separator):
            if not i:
                continue
            label = f'{i}'
            items.append(self.get_list_item(label))
            set_to_windowprop(label, x, window_prop, window_id)
            x += 1

        store_windowprops_counter(x, window_prop, window_id)
        self.add_items(items)


class ListGetEncodedString(ContainerDirectory):

    @clear_windowprops_decorator
    def get_directory(self, paths=None, window_prop=None, window_id=None, **kwargs):
        from urllib.parse import quote_plus

        if not paths:
            return

        items = []
        for x, i in enumerate(paths):
            label = quote_plus(i)
            items.append(self.get_list_item(label))
            set_to_windowprop(label, x, window_prop, window_id)

        store_windowprops_counter(x + 1, window_prop, window_id)
        self.add_items(items)


class ListGetFileExists(ContainerDirectory):

    @clear_windowprops_decorator
    def get_directory(self, paths, window_prop=None, window_id=None, **kwargs):
        import xbmcvfs

        if not paths:
            return

        items = []
        for x, i in enumerate(paths):
            label = i
            path = i if xbmcvfs.exists(i) else ''
            items.append(self.get_list_item(label))
            set_to_windowprop(path, x, window_prop, window_id)

        store_windowprops_counter(x + 1, window_prop, window_id)
        self.add_items(items)


class ListGetDottedProperties(ContainerDirectory):
    def get_directory(
            self, source='Container.ListItem', string='', infoproperties='', label='', thumb=None, fanart=None,
            separator='/', xmax='10', ymax=None, no_label_dupes=False,
            **kwargs
    ):
        import xbmc

        """

        $INFO[Container(ID).ListItem.Property(movies.X.item.cast.Y.name)]
        $INFO[Container(ID).ListItem.Property(movies.X.item.cast.Y.role)]
        $INFO[Container(ID).ListItem.Property(movies.X.item.cast.Y.thumbnail)]

        source=Container(ID).ListItem
        string=movies.{x}.item.cast.{y}.

        label=name
        thumb=thumbnail
        infoproperties=name|role|thumbnail

        plugin://script.skinvariables/?info=get_dotted_properties&source=Container(ID).ListItem&string=movies.{x}.item.cast.{y}.
        &infoproperties=name/role/thumbnail&label=name&thumb=thumbnail&xmax=10&ymax=10


        """

        if not source or not string or not xmax:
            return

        _fstr = f'{source}.Property({string}{{k}})'

        infoproperties = infoproperties.split(separator) or ['']

        xmax = int(xmax or 1)
        ymax = int(ymax or 0)
        ymax = ymax or 1

        items = []
        added_items = []
        for x in range(0, xmax):
            for y in range(0, ymax):

                i_label = ''
                i_infoproperties = {}
                i_art = {}

                for k in infoproperties:

                    v = xbmc.getInfoLabel(_fstr.format(x=x, y=y, k=k))
                    if not v:
                        continue

                    i_infoproperties[k] = v

                    if k == label:
                        i_label = v
                    if k == thumb:
                        i_art['thumb'] = i_art['icon'] = v
                    if k == fanart:
                        i_art['fanart'] = v

                if not i_infoproperties:
                    continue

                if no_label_dupes and i_label in added_items:
                    continue

                added_items.append(i_label)

                i_infoproperties['xpos'] = f'{x}'
                i_infoproperties['ypos'] = f'{y}'

                item = self.get_list_item(i_label)
                item[1].setProperties(i_infoproperties)
                item[1].setArt(i_art)
                items.append(item)

        self.add_items(items)


class ListGetSelectedItem(ContainerDirectory):
    def get_directory(
            self, container, infolabels='', artwork='', separator='/', listitem='ListItem(0)',
            window_prop=None, window_id=None, **kwargs
    ):
        import xbmc

        if not container:
            return

        _fstr = f'Container({container}).{listitem}.{{}}'
        _label = xbmc.getInfoLabel(_fstr.format('Label'))

        _infoproperties = {}
        for i in infolabels.split(separator):
            _infoproperties[i] = xbmc.getInfoLabel(_fstr.format(i))

        _artwork = {}
        for i in artwork.split(separator):
            _artwork[i] = xbmc.getInfoLabel(_fstr.format(f'Art({i})'))

        item = self.get_list_item(_label)
        item[1].setProperties(_infoproperties)
        item[1].setArt(_artwork)

        self.add_items([item])

        if not window_prop:
            return

        window_id = f',{window_id}' if window_id else ''

        for k, v in _infoproperties.items():
            window_prop_name = f'{window_prop}.{k}'
            xbmc.executebuiltin(f'SetProperty({window_prop_name},{v}{window_id})')

        for k, v in _artwork.items():
            window_prop_name = f'{window_prop}.{k}'
            xbmc.executebuiltin(f'SetProperty({window_prop_name},{v}{window_id})')

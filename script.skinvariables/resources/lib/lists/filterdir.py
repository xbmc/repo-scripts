# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmcgui import ListItem, Dialog
from infotagger.listitem import ListItemInfoTag
from jurialmunkey.litems import ContainerDirectory, INFOLABEL_MAP
from jurialmunkey.window import set_to_windowprop, WindowProperty
from resources.lib.kodiutils import kodi_log, get_localized
from resources.lib.filters import get_filters, is_excluded
import jurialmunkey.thread as jurialmunkey_thread


class ParallelThread(jurialmunkey_thread.ParallelThread):
    thread_max = 50

    @staticmethod
    def kodi_log(msg, level=0):
        kodi_log(msg, level)


DIRECTORY_PROPERTIES_BASIC = ["title", "art", "file", "fanart"]

DIRECTORY_PROPERTIES_VIDEO = [
    "genre", "year", "rating", "playcount", "director", "trailer", "tagline", "plot", "plotoutline", "originaltitle", "lastplayed", "writer",
    "studio", "mpaa", "country", "premiered", "runtime", "set", "streamdetails", "top250", "votes", "firstaired", "season", "episode", "showtitle",
    "tvshowid", "setid", "sorttitle", "thumbnail", "uniqueid", "dateadded", "resume", "customproperties"]

DIRECTORY_PROPERTIES_MUSIC = [
    "artist", "albumartist", "genre", "year", "rating", "album", "track", "duration", "lastplayed", "studio", "mpaa",
    "disc", "description", "theme", "mood", "style", "albumlabel", "sorttitle", "uniqueid", "dateadded", "customproperties",
    "totaldiscs", "disctitle", "releasedate", "originaldate", "bpm", "bitrate", "samplerate", "channels"]

SORTBY_METHODS = [
    "none", "title", "genre", "year", "rating", "playcount", "director", "trailer", "tagline", "plot", "originaltitle", "lastplayed", "writer",
    "studio", "mpaa", "country", "premiered", "top250", "votes", "tvshowtitle", "custom"]

STANDARD_OPERATORS = (
    ('contains', 21400),
    ('lt', 32036),
    ('le', 32037),
    ('eq', 32038),
    ('ne', 32039),
    ('ge', 32040),
    ('gt', 32041))


INFOPROPERTY_MAP = {
    "disctitle": "disctitle",
    "releasedate": "releasedate",
    "originaldate": "originaldate",
    "bpm": "bpm",
    "bitrate": "bitrate",
    "samplerate": "samplerate",
    "channels": "channels",
    "totaldiscs": "totaldiscs",
    "disc": "disc",
    "description": "description",
    "theme": "theme",
    "mood": "mood",
    "style": "style",
    "albumlabel": "albumlabel",
    "tvshowid": "tvshow.dbid",
    "setid": "set.dbid",
    "songvideourl": "songvideourl",
}


def update_global_property_versions():
    """ Add additional properties from newer versions of JSON RPC """

    from jurialmunkey.jsnrpc import get_jsonrpc

    response = get_jsonrpc("JSONRPC.Version")
    version = (
        response['result']['version']['major'],
        response['result']['version']['minor'],
        response['result']['version']['patch'],
    )

    if version >= (13, 3, 0):
        DIRECTORY_PROPERTIES_MUSIC.append('songvideourl')  # Added in 13.3.0 of JSON RPC


class MetaItemJSONRPC():
    def __init__(self, meta, dbtype='video'):
        self.meta = meta or {}
        self.dbtype = dbtype

    @property
    def label(self):
        if self.meta.get('title'):
            return self.meta['title']
        if self.meta.get('label'):
            return self.meta['label']
        return ''

    @property
    def path(self):
        if self.meta.get('file'):
            return self.meta['file']
        return ''

    @property
    def mediatype(self):
        mediatype = self.meta.get('type') or ''
        if mediatype in ['unknown', '']:
            return self.dbtype
        return mediatype

    @property
    def infolabels(self):
        return {INFOLABEL_MAP[k]: v for k, v in self.meta.items() if v and k in INFOLABEL_MAP and v != -1}

    @property
    def infoproperties(self):
        infoproperties = {INFOPROPERTY_MAP[k]: str(v) for k, v in self.meta.items() if v and k in INFOPROPERTY_MAP and v != -1}
        infoproperties.update({k: str(v) for k, v in (self.meta.get('customproperties') or {}).items()})
        infoproperties.update(self.resume)
        return infoproperties

    @property
    def resume(self):
        resume = self.meta.get('resume') or {}
        infoproperties = {}
        if resume.get('total'):
            infoproperties['resumetime'] = resume.get('position') or 0
            infoproperties['totaltime'] = resume.get('total')
            infoproperties['percentplayed'] = int(infoproperties['resumetime'] / infoproperties['totaltime'] * 100)
        return infoproperties

    @property
    def uniqueids(self):
        return self.meta.get('uniqueid') or {}

    @property
    def streamdetails(self):
        return self.meta.get('streamdetails') or {}

    @property
    def artwork(self):
        artwork = self.meta.get('art') or {}
        remap = (
            ('thumb', 'thumb'),
            ('fanart', 'fanart'))
        for a, k in remap:
            if self.meta.get(k) and not artwork.get(a):
                artwork[a] = self.meta[k]

        return artwork

    @property
    def filetype(self):
        return self.meta.get('filetype')


class ListItemJSONRPC():
    def __init__(self, meta, library='video', dbtype='video'):
        self.meta = MetaItemJSONRPC(meta, dbtype)
        self.is_folder = True
        self.library = library or 'video'
        self.infolabels = self.meta.infolabels
        self.infoproperties = self.meta.infoproperties
        self.uniqueids = self.meta.uniqueids
        self.streamdetails = self.meta.streamdetails
        self.artwork = self.meta.artwork
        self.filetype = self.meta.filetype
        self.mediatype = self.meta.mediatype
        self.path = self.meta.path
        self.label = self.meta.label
        self.label2 = ''

    @property
    def mediatype(self):
        return self._mediatype

    @mediatype.setter
    def mediatype(self, value: str):
        self._mediatype = value
        self.infolabels['mediatype'] = value

    @property
    def infolabels(self):
        return self._infolabels

    @infolabels.setter
    def infolabels(self, value):
        self._infolabels = value
        self.fix_music_infolabels()

    def fix_music_infolabels(self):
        # Fix some incompatible type returns from JSON RPC to info_tag in music library
        if self.library != 'music':
            return
        for a in ('artist', 'albumartist', 'album'):
            if not isinstance(self.infolabels.get(a), list):
                continue
            self.infolabels[a] = ' / '.join(self.infolabels[a])

    @property
    def artwork(self):
        return self._artwork

    @artwork.setter
    def artwork(self, value):
        self._artwork = value

        def _map_artwork(key: str, names: tuple):
            if self._artwork.get(key):
                return self._artwork[key]
            for a in names:
                if self._artwork.get(a):
                    return self._artwork[a]
            return ''

        if self.library == 'music':
            parents = ('album', 'albumartist', 'artist')
            for k in ('thumb', 'fanart', 'clearlogo'):
                self._artwork[k] = _map_artwork(k, (f'{parent}.{k}' for parent in parents))

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value
        self.is_folder = True

        if self.filetype == 'file':
            self.is_folder = False
            self.infoproperties['isPlayable'] = 'true'
            return

        if '://' in self._path:
            return

        if self.mediatype == 'tvshow' and self.infolabels.get('dbid'):
            self._path = f'videodb://tvshows/titles/{self.infolabels["dbid"]}/'
            return

        if self.mediatype == 'season' and self.infolabels.get('tvshow.dbid'):
            self._path = f'videodb://tvshows/titles/{self.infoproperties["tvshow.dbid"]}/{self.infolabels["season"]}/'
            return

    @property
    def listitem(self):
        self._listitem = ListItem(label=self.label, label2=self.label2, path=self.path, offscreen=True)
        self._listitem.setLabel2(self.label2)
        self._listitem.setArt(self.artwork)

        self._info_tag = ListItemInfoTag(self._listitem, self.library)
        self._info_tag.set_info(self.infolabels)
        if self.library == 'video':
            self._info_tag.set_unique_ids(self.uniqueids)
            self._info_tag.set_stream_details(self.streamdetails)
            self._info_tag.set_resume_point(self.infoproperties, resume_key='resumetime', total_key='totaltime')

        self._listitem.setProperties(self.infoproperties)
        return self._listitem


class ListGetFilterFiles(ContainerDirectory):
    def get_directory(self, filepath=None, **kwargs):
        from resources.lib.shortcuts.futils import get_files_in_folder

        basepath = 'plugin://script.skinvariables/'
        filepath = filepath or 'special://profile/addon_data/script.skinvariables/nodes/dynamic/'

        def _make_item(i):
            editpath = f'{basepath}?info=set_filter_dir&filepath=special://profile/addon_data/script.skinvariables/nodes/dynamic/{i}'
            itempath = f'{basepath}?info=get_params_file&path=special://profile/addon_data/script.skinvariables/nodes/dynamic/{i}'
            li = ListItem(label=f'{i}', path=itempath)
            li.addContextMenuItems([(get_localized(32094), f'RunPlugin({editpath})')])
            return (itempath, li, True)

        def _add_new_item():
            path = f'{basepath}?info=set_filter_dir'
            return (path, ListItem(label=f'{get_localized(32095)}...', path=path), True)

        files = get_files_in_folder(filepath, r'.*\.json')
        items = [_make_item(i) for i in files if i] + [_add_new_item()]

        plugin_category = ''
        container_content = ''
        self.add_items(items, container_content=container_content, plugin_category=plugin_category)


class MetaFilterDir():
    def __init__(self, library='video', filepath=None):
        self.library = library
        self.filepath = filepath

    @property
    def meta(self):
        try:
            return self._meta
        except AttributeError:
            self._meta = self.get_files_meta()
            return self._meta

    def get_blank_meta(self):
        return {
            'info': 'get_filter_dir',
            'library': self.library,
            'paths': [],
            'names': []
        }

    def get_files_meta(self):
        if not self.filepath:
            return self.get_blank_meta()
        from resources.lib.shortcuts.futils import read_meta_from_file
        return read_meta_from_file(self.filepath) or self.get_blank_meta()

    @staticmethod
    def get_new_path():
        from resources.lib.shortcuts.browser import GetDirectoryBrowser
        with WindowProperty(('IsSkinShortcut', 'True')):
            directory_browser = GetDirectoryBrowser(use_rawpath=True)
            item = directory_browser.get_directory(path='library://video/')  # TODO: Add some choice of library
            name = directory_browser.heading_str
        try:
            path, target = item['path'], item['target']
        except (TypeError, KeyError):
            return (None, None)
        if not target:  # TODO: Add some validation we have correct library
            pass
        return (path, name)

    @staticmethod
    def get_new_method(heading, customheading, methods=SORTBY_METHODS):
        x = Dialog().select(heading, methods)
        if x == -1:
            return None
        v = methods[x]
        if v == 'custom':
            return Dialog().input(heading=customheading)
        if v == 'none':
            return ''
        return v

    def get_new_suffix(self, prefix):
        import random
        existing_filter_suffix = [k.replace(f'{prefix}_key__', '') for k in self.meta.keys() if k.startswith(f'{prefix}_key__')]  # Suffix prefixed by double underscore

        def get_suffix():
            suffix = f'{random.randrange(16**8):08x}'
            if suffix not in existing_filter_suffix:
                return f'_{suffix}'  # Suffix prefixed by double underscore but one will be added when joining so only add one now
            return get_suffix()

        return get_suffix()

    def toggle_randomise(self):
        from jurialmunkey.parser import boolean
        if boolean(self.meta.get('randomise', False)):
            del self.meta['randomise']
            return
        self.meta['randomise'] = 'true'

    def toggle_fallback(self):
        from jurialmunkey.parser import boolean
        if boolean(self.meta.get('fallback', False)):
            del self.meta['fallback']
            return
        self.meta['fallback'] = 'true'

    def del_path(self, value):
        x = next(x for x, i in enumerate(self.meta['paths']) if i == value)
        del self.meta['paths'][x]
        del self.meta['names'][x]

    def rename_path(self, x):
        name = Dialog().input(heading=get_localized(551), defaultt=self.meta['names'][x])
        if not name:
            return
        self.meta['names'][x] = name

    def add_new_path(self):
        path, name = self.get_new_path()
        if path is None:
            return self.meta['paths']
        name = Dialog().input(heading=get_localized(551), defaultt=name)
        self.meta['paths'].append(path)
        self.meta['names'].append(name)
        if Dialog().yesno(get_localized(32030), get_localized(32031)):
            return self.add_new_path()
        return self.meta['paths']

    def add_new_sort_how(self):
        self.meta['sort_how'] = 'desc' if Dialog().yesno(
            get_localized(580),  # Sort direction
            '',
            yeslabel=get_localized(585),  # Descending
            nolabel=get_localized(584)  # Ascending
        ) else 'asc'

    def add_new_sort_by(self):
        sort_by = self.get_new_method(
            get_localized(32032).format(get_localized(32033)),
            get_localized(32034).format(get_localized(32033))
        )
        if sort_by is None:
            return
        self.meta['sort_by'] = sort_by

    def add_new_sort(self):
        self.add_new_sort_by()
        if not self.meta['sort_by']:
            return
        self.add_new_sort_how()

    def del_filter(self, prefix='filter', suffix='', keys=('key', 'value', 'operator')):
        key_names = ['_'.join(filter(None, [prefix, k, suffix])) for k in keys]
        for k in key_names:
            try:
                del self.meta[k]
            except KeyError:
                pass

    def add_new_filter_operator(self, prefix='filter', suffix=''):
        choices = [(k, get_localized(v)) for k, v in STANDARD_OPERATORS]
        x = Dialog().select('[CAPITALIZE]{}[/CAPITALIZE] operator'.format(prefix), [i for _, i in choices])
        if x == -1:
            return
        filter_operator = choices[x][0]
        k = '_'.join(filter(None, [prefix, 'operator', suffix]))
        self.meta[k] = filter_operator
        return filter_operator

    def add_new_filter_key(self, prefix='filter', suffix=''):
        filter_key = self.get_new_method(
            get_localized(32032).format(prefix),
            get_localized(32034).format(prefix)
        )
        if filter_key is None:
            return
        if filter_key == '':
            self.del_filter(prefix, suffix)
            return
        k = '_'.join(filter(None, [prefix, 'key', suffix]))
        self.meta[k] = filter_key
        return filter_key

    def add_new_filter_value(self, prefix='filter', suffix=''):
        k = '_'.join(filter(None, [prefix, 'key', suffix]))
        if not self.meta.get(k):
            self.del_filter(prefix, suffix)
            return
        filter_value = Dialog().input(heading=get_localized(32035).format(prefix))
        if not filter_value:
            self.del_filter(prefix, suffix)
            return
        k = '_'.join(filter(None, [prefix, 'value', suffix]))
        self.meta[k] = filter_value
        return filter_value

    def add_new_filter(self, prefix='filter', suffix=''):
        if not self.add_new_filter_key(prefix, suffix):
            return
        self.add_new_filter_operator(prefix, suffix)
        self.add_new_filter_value(prefix, suffix)

    def write_meta(self, filename=None):
        from resources.lib.shortcuts.futils import FILEUTILS, validify_filename
        filename = filename or Dialog().input(heading=get_localized(551))
        filename = validify_filename(filename)
        if not filename:  # TODO: Ask user if they are sure they dont want to make the file.
            return
        filename = f'{filename}.json'
        FILEUTILS.dumps_to_file(self.meta, folder='dynamic', filename=filename, indent=4)  # TODO: Make sure we dont overwrite?
        return filename

    def delete_meta(self):
        if not self.filepath:
            return
        import xbmcvfs
        xbmcvfs.delete(self.filepath)

    def save_meta(self):
        if not self.filepath:
            return
        import xbmcvfs
        from json import dump
        with xbmcvfs.File(self.filepath, 'w') as file:
            dump(self.meta, file, indent=4)


class ListSetFilterDir(ContainerDirectory):
    def get_directory(self, library='video', filename=None, filepath=None, **kwargs):
        meta_filter_dir = MetaFilterDir(library=library, filepath=filepath)

        def get_new():
            meta_filter_dir.add_new_path()
            meta_filter_dir.add_new_sort()
            meta_filter_dir.add_new_filter('filter')
            meta_filter_dir.add_new_filter('exclude')
            meta_filter_dir.write_meta(filename)
            ListGetFilterFiles(self.handle, '').get_directory()

        def get_path_name_pair(x, i):
            names = meta_filter_dir.meta.setdefault('names', [])
            if x >= len(names):
                names.append('')
            return (f'path = {i}', f'name = {names[x]}')

        def do_edit():
            options = [a for j in (get_path_name_pair(x, i) for x, i in enumerate(meta_filter_dir.meta['paths'])) for a in j]
            options += [f'{k} = {v}' for k, v in meta_filter_dir.meta.items() if k not in ('paths', 'info', 'library', 'names')]
            options += ['randomise = false'] if 'randomise' not in meta_filter_dir.meta.keys() else []
            options += ['fallback = false'] if 'fallback' not in meta_filter_dir.meta.keys() else []
            options += ['add sort'] if 'sort_by' not in meta_filter_dir.meta.keys() else []
            options += ['add filter', 'add exclude', 'add path', 'rename', 'delete', 'save']

            x = Dialog().select(get_localized(21435), options)
            if x == -1:
                meta_filter_dir.save_meta() if Dialog().yesno(get_localized(32044), get_localized(32045)) == 1 else None
                return

            choice_k, choice_s, choice_v = options[x].partition(' = ')

            if choice_k == 'save':
                meta_filter_dir.save_meta()
                return

            if choice_k == 'rename':
                filename = meta_filter_dir.write_meta()
                if filename:
                    import xbmc
                    meta_filter_dir.delete_meta()  # Delete the old file
                    xbmc.executebuiltin('Container.Refresh')  # Refresh container to see changes
                    return
                return do_edit()  # If user didn't enter a valid filename we just go back to menu

            if choice_k == 'delete':
                if Dialog().yesno(get_localized(117), get_localized(32043)) == 1:
                    import xbmc
                    meta_filter_dir.delete_meta()
                    xbmc.executebuiltin('Container.Refresh')
                    return
                return do_edit()

            if choice_k == 'sort_by':
                meta_filter_dir.add_new_sort_by()
                return do_edit()

            if choice_k == 'sort_how':
                meta_filter_dir.add_new_sort_how()
                return do_edit()

            if choice_k == 'path':
                meta_filter_dir.del_path(value=choice_v) if Dialog().yesno(get_localized(32042), '\n'.join([choice_v, get_localized(32043)])) == 1 else None
                return do_edit()

            if choice_k == 'name':
                meta_filter_dir.rename_path(x=((x - 1) // 2))
                return do_edit()

            if choice_k == 'randomise':
                meta_filter_dir.toggle_randomise()
                return do_edit()

            if choice_k == 'fallback':
                meta_filter_dir.toggle_fallback()
                return do_edit()

            if choice_k == 'add path':
                meta_filter_dir.add_new_path()
                return do_edit()

            if choice_k == 'add sort':
                meta_filter_dir.add_new_sort()
                return do_edit()

            if choice_k == 'add filter':
                suffix = meta_filter_dir.get_new_suffix('filter')
                meta_filter_dir.add_new_filter('filter', suffix)
                return do_edit()

            if choice_k == 'add exclude':
                suffix = meta_filter_dir.get_new_suffix('exclude')
                meta_filter_dir.add_new_filter('exclude', suffix)
                return do_edit()

            if '_key' in choice_k:
                prefix, sep, suffix = choice_k.partition('_key')
                suffix = suffix[1:] if suffix else suffix  # Remove additional underscore on suffix
                meta_filter_dir.add_new_filter_key(prefix, suffix)
                return do_edit()

            if '_value' in choice_k:
                prefix, sep, suffix = choice_k.partition('_value')
                suffix = suffix[1:] if suffix else suffix  # Remove additional underscore on suffix
                meta_filter_dir.add_new_filter_value(prefix, suffix)
                return do_edit()

            if '_operator' in choice_k:
                prefix, sep, suffix = choice_k.partition('_operator')
                suffix = suffix[1:] if suffix else suffix  # Remove additional underscore on suffix
                meta_filter_dir.add_new_filter_operator(prefix, suffix)
                return do_edit()

            return do_edit()

        get_new() if not filepath else do_edit()


class ListGetFilterDir(ContainerDirectory):
    def get_directory(
            self, paths=None, library=None, no_label_dupes=False, dbtype=None,
            sort_by=None, sort_how=None, randomise=False, randomise_prop=None, randomise_time=None, fallback=False, names=None,
            window_prop=None, window_id=None,
            **kwargs
    ):
        if not paths:
            return

        from jurialmunkey.jsnrpc import get_directory
        from jurialmunkey.parser import boolean

        update_global_property_versions()  # Add in any properties added in later JSON-RPC versions

        mediatypes = {}
        added_items = []
        all_filters = get_filters(**kwargs)
        all_statistics_filters = get_filters(filter_prefix='stats_', **kwargs)
        directory_properties = DIRECTORY_PROPERTIES_BASIC
        directory_properties += {
            'video': DIRECTORY_PROPERTIES_VIDEO,
            'music': DIRECTORY_PROPERTIES_MUSIC}.get(library) or []

        statistics = {}

        def _make_item(i, path_name=None):
            if not i:
                return

            listitem_jsonrpc = ListItemJSONRPC(i, library=library, dbtype=dbtype)
            listitem_jsonrpc.infolabels['title'] = listitem_jsonrpc.label
            listitem_jsonrpc.infoproperties['widget'] = path_name or listitem_jsonrpc.infoproperties.get('widget') or ''

            for fname, filters in all_filters.items():
                if is_excluded({'infolabels': listitem_jsonrpc.infolabels, 'infoproperties': listitem_jsonrpc.infoproperties}, **filters):
                    return

            for fname, filters in all_statistics_filters.items():
                if not is_excluded({'infolabels': listitem_jsonrpc.infolabels, 'infoproperties': listitem_jsonrpc.infoproperties}, **filters):
                    statistics.setdefault(fname, 0)
                    statistics[fname] += 1

            if listitem_jsonrpc.mediatype:
                mediatypes[listitem_jsonrpc.mediatype] = mediatypes.get(listitem_jsonrpc.mediatype, 0) + 1

            return listitem_jsonrpc

        def _is_not_dupe(i):
            if not no_label_dupes:
                return i
            label = i.infolabels['title']
            if label in added_items:
                return
            added_items.append(label)
            return i

        def _get_sorting(i):
            v = i.infolabels.get(sort_by) or i.infoproperties.get(sort_by) or ''
            try:
                v = float(v)
                x = 2  # We want high numbers (e.g. rating/year) before empty values when sorting in descending order (reversed)
            except ValueError:
                v = str(v)
                x = 1
            except TypeError:
                v = ''
                x = 0  # We want empty values to come last when sorting in descending order (reversed)
            return (x, v)  # Sorted will sort by first value in tuple, then second order afterwards

        def _get_indexed_path(x=0):
            seed_paths = [paths.pop(x)]
            try:
                seed_names = [names.pop(x)]
            except (IndexError, TypeError):
                seed_names = None
            return (seed_paths, seed_names)

        def _get_stored_random_path():
            # Dont randomise if only one path to choose
            total_x = len(paths)
            if total_x == 1:
                return 0

            # Dont check randomise prop if none selected
            if not randomise_prop:
                return

            prefix = 'SkinVariables.RandomisationTimer'

            # Default to ten minute refresh time if nont selected
            time_limit = int(randomise_time or 600)

            # Check expiry of previous stored value
            from jurialmunkey.window import get_property
            from jurialmunkey.tmdate import get_timestamp, set_timestamp
            expiry = get_property(f'{randomise_prop}.expiry', prefix=prefix)

            # Get a new random seed value if expired (and make sure we dont get previous value again)
            if not get_timestamp(expiry, set_int=True):
                import random
                previous_x = get_property(f'{randomise_prop}', prefix=prefix)
                previous_x = int(previous_x) if previous_x else -1
                x = random.choice([x for x in range(len(paths)) if x != previous_x])
                get_property(f'{randomise_prop}.expiry', set_property=f'{set_timestamp(time_limit, set_int=True)}', prefix=prefix)
                get_property(f'{randomise_prop}', set_property=f'{x}', prefix=prefix)
                return x

            return int(get_property(f'{randomise_prop}', prefix=prefix))

        def _get_random_path():
            import random
            x = _get_stored_random_path()
            x = random.choice(range(len(paths))) if x is None else x
            return _get_indexed_path(x)

        def _get_paths_names_tuple():
            if not paths or len(paths) < 1:
                return (None, None)
            if boolean(randomise):
                return _get_random_path()
            if boolean(fallback):
                return _get_indexed_path(0)
            return (paths, names)

        def _get_items_from_paths():
            items = []
            seed_paths, seed_names = _get_paths_names_tuple()

            for x, path in enumerate(seed_paths):
                try:
                    path_name = seed_names[x]
                except (IndexError, TypeError):
                    path_name = ''
                directory = get_directory(path, directory_properties)
                with ParallelThread(directory, _make_item, path_name) as pt:
                    item_queue = pt.queue
                items += [i for i in item_queue if i and (not no_label_dupes or _is_not_dupe(i))]

            if not items and len(paths) > 0:
                if boolean(randomise) or boolean(fallback):
                    return _get_items_from_paths()

            return items

        items = _get_items_from_paths()

        items = sorted(items, key=_get_sorting, reverse=sort_how == 'desc') if sort_by else items
        items = [(i.path, i.listitem, i.is_folder, ) for i in items if i]

        plugin_category = ''
        container_content = f'{max(mediatypes, key=lambda key: mediatypes[key])}s' if mediatypes else ''
        self.add_items(items, container_content=container_content, plugin_category=plugin_category)

        if not statistics:
            return

        window_prop = window_prop or 'Statistics'

        for k, v in statistics.items():
            set_to_windowprop(v, k, window_prop, window_id)


class ListGetContainerLabels(ContainerDirectory):
    def get_directory(
            self, containers, infolabel, numitems=None, thumb=None, label2=None, separator=' / ',
            filter_value=None, filter_operator=None, exclude_value=None, exclude_operator=None,
            window_prop=None, window_id=None, contextmenu=None,
            **kwargs):
        import xbmc
        from resources.lib.method import get_paramstring_tuplepairs

        filters = {
            'filter_key': 'title',
            'filter_value': filter_value,
            'filter_operator': filter_operator,
            'exclude_key': 'title',
            'exclude_value': exclude_value,
            'exclude_operator': exclude_operator,
        }

        added_items = []
        contextmenu = get_paramstring_tuplepairs(contextmenu)

        def _make_item(title, image, label):
            if (title, image, label, ) in added_items:
                return

            if is_excluded({'infolabels': {'title': title}}, **filters):
                return

            listitem = ListItem(label=title, label2=label or '', path='', offscreen=True)
            listitem.setArt({'icon': image or '', 'thumb': image or ''})
            listitem.addContextMenuItems([
                (k.format(label=title, thumb=image, label2=label), v.format(label=title, thumb=image, label2=label))
                for k, v in contextmenu])

            item = ('', listitem, True, )

            added_items.append((title, image, label, ))
            return item

        items = []
        for container in containers.split():
            numitems = int(xbmc.getInfoLabel(f'Container({container}).NumItems') or 0)
            if not numitems:
                continue
            for x in range(numitems):
                image = xbmc.getInfoLabel(f'Container({container}).ListItemAbsolute({x}).{thumb}') if thumb else ''
                label = xbmc.getInfoLabel(f'Container({container}).ListItemAbsolute({x}).{label2}') if label2 else ''
                for il in infolabel.split():
                    titles = xbmc.getInfoLabel(f'Container({container}).ListItemAbsolute({x}).{il}')
                    if not titles:
                        continue
                    for title in titles.split(separator):
                        item = _make_item(title, image, label)
                        if not item:
                            continue
                        items.append(item)

        self.add_items(items)

        if not window_prop or not added_items:
            return

        for x, i in enumerate(added_items):
            set_to_windowprop(i, x, window_prop, window_id)

        xbmc.executebuiltin(f'SetProperty({window_prop},{" / ".join([i[0] for i in added_items])}{f",{window_id}" if window_id else ""})')

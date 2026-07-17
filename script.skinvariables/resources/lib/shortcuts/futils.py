import jurialmunkey.futils as jmfutils


BASE_PROPERTY = 'SkinVariables.ShortcutsNode'
ADDON_DATA = 'special://profile/addon_data/script.skinvariables/nodes/'
RELOAD_PROPERTY = f'{BASE_PROPERTY}.Reload'
FILE_PREFIX = 'skinvariables-shortcut-'


validify_filename = jmfutils.validify_filename


class FileUtils(jmfutils.FileUtils):
    addondata = ADDON_DATA   # Override module addon_data with plugin addon_data


FILEUTILS = FileUtils()


def get_files_in_folder(folder, regex):
    import re
    import xbmcvfs
    return [x for x in xbmcvfs.listdir(folder)[1] if re.match(regex, x)]


def dumps_log_to_file(meta, folder='logging', filename='logging.json', indent=4):
    FILEUTILS.dumps_to_file(meta, folder=folder, filename=filename, indent=indent)


def reload_shortcut_dir():
    import xbmc
    import time
    xbmc.executebuiltin(f'SetProperty({RELOAD_PROPERTY},{time.time()},Home)')


def write_meta_to_file(meta, folder, filename, indent=4, fileprop=None, reload=True):
    FILEUTILS.dumps_to_file(meta, folder=folder, filename=filename, indent=indent)
    write_meta_to_prop(meta, fileprop) if fileprop else None
    reload_shortcut_dir() if reload else None


def write_meta_to_prop(meta, fileprop):
    from xbmcgui import Window
    Window(10000).setProperty(f'{BASE_PROPERTY}.{fileprop}', jmfutils.json_dumps(meta) if meta else '')


def read_meta_from_file(filepath):
    meta = jmfutils.load_filecontent(filepath)
    return jmfutils.json_loads(meta) if meta else None


def read_meta_from_prop(fileprop):
    from xbmcgui import Window
    meta = Window(10000).getProperty(f'{BASE_PROPERTY}.{fileprop}')
    return jmfutils.json_loads(meta) if meta else None

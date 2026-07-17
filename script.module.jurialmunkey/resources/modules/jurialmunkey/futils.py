# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import xbmc
import xbmcvfs

ADDONDATA = 'special://profile/addon_data/script.module.jurialmunkey/'
ALPHANUM_CHARS = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
INVALID_FILECHARS = "\\/\"\'<>:|?*"


class FileUtils():
    addondata = ADDONDATA

    def get_write_path(self, folder, join_addon_data=True, make_dir=True):
        if join_addon_data:
            folder = f'{self.addondata}{folder}/'
        main_dir = xbmcvfs.validatePath(xbmcvfs.translatePath(folder))
        if make_dir and not xbmcvfs.exists(main_dir):
            try:  # Try makedir to avoid race conditions
                xbmcvfs.mkdirs(main_dir)
            except FileExistsError:
                pass
        return main_dir

    def get_file_path(self, folder, filename, join_addon_data=True, make_dir=True):
        return validate_join(self.get_write_path(folder, join_addon_data, make_dir), filename)

    def dumps_to_file(self, data, folder, filename, indent=2, join_addon_data=True):
        from json import dump
        path = self.get_file_path(folder, filename, join_addon_data)
        with xbmcvfs.File(path, 'w') as file:
            dump(data, file, indent=indent)
        return path

    def delete_file(self, folder, filename, join_addon_data=True):
        xbmcvfs.delete(self.get_file_path(folder, filename, join_addon_data, make_dir=False))

    def delete_folder(self, folder, join_addon_data=True, force=False, check_exists=False):
        path = self.get_write_path(folder, join_addon_data, make_dir=False)
        if check_exists and not xbmcvfs.exists(path):
            return
        xbmcvfs.rmdir(path, force=force)


def json_loads(obj):
    import json

    def json_int_keys(ordered_pairs):
        result = {}
        for key, value in ordered_pairs:
            try:
                key = int(key)
            except ValueError:
                pass
            result[key] = value
        return result
    try:
        return json.loads(obj, object_pairs_hook=json_int_keys)
    except json.JSONDecodeError:
        return


def json_dumps(obj, separators=(',', ':')):
    from json import dumps
    return dumps(obj, separators=separators)


def validate_join(folder, filename):
    path = '/'.join([folder, filename])
    return xbmcvfs.validatePath(xbmcvfs.translatePath(path))


def validify_filename(filename, alphanum=False):
    import unicodedata
    filename = unicodedata.normalize('NFD', filename)
    filename = u''.join([c for c in filename if (not alphanum or c in ALPHANUM_CHARS) and c not in INVALID_FILECHARS])
    return filename.strip('.')


def get_filecache_name(cache_name, alphanum=False):
    cache_name = cache_name or ''
    cache_name = cache_name.replace('\\', '_').replace('/', '_').replace('.', '_').replace('?', '_').replace('&', '_').replace('=', '_').replace('__', '_')
    return validify_filename(cache_name, alphanum=alphanum).rstrip('_')


def make_hash(content):
    import hashlib
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def check_hash(hashname, hashvalue=None):
    last_version = xbmc.getInfoLabel('Skin.String({})'.format(hashname))
    if not last_version:
        return hashvalue
    if hashvalue != last_version:
        return hashvalue


def load_filecontent(filename=None):
    try:
        vfs_file = xbmcvfs.File(filename)
        content = vfs_file.read()
    finally:
        vfs_file.close()
    return content


def write_file(filepath=None, content=None):
    if not filepath:
        return
    f = xbmcvfs.File(filepath, 'w')
    f.write(content)
    f.close()


def write_skinfile(filename=None, folders=None, content=None, hashvalue=None, hashname=None, checksum=None):
    if not filename or not folders or not content:
        return

    for folder in folders:
        write_file(filepath='special://skin/{}/{}'.format(folder, filename), content=content)

    if hashvalue and hashname:
        xbmc.executebuiltin('Skin.SetString({},{})'.format(hashname, hashvalue))

    if checksum:
        xbmc.executebuiltin('Skin.SetString({},{})'.format(checksum, make_hash(content)))


def get_files_in_folder(folder, regex):
    import re
    return [x for x in xbmcvfs.listdir(folder)[1] if re.match(regex, x)]


def read_file(filepath):
    content = ''
    with xbmcvfs.File(filepath) as vfs_file:
        content = vfs_file.read()
    return content

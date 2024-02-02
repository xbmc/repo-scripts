
from __future__ import division
from __future__ import with_statement
from __future__ import absolute_import
import os
import struct

import xbmcvfs, xbmc

from resources.lib.utilities import log


def get_file_data(file_original_path):
    item = {u"temp": False, u"rar": False, u"file_original_path": file_original_path}


    if file_original_path.find(u"http") > -1:
        orig_path = xbmc.getInfoLabel(u'Window(10000).Property(videoinfo.current_path)')
        orig_size = xbmc.getInfoLabel(u'Window(10000).Property(videoinfo.current_size)')
        orig_oshash = xbmc.getInfoLabel(u'Window(10000).Property(videoinfo.current_oshash)')
        if orig_path:
            orig_path = unicode(orig_path)
            item[u"basename"] = os.path.basename(orig_path)
            item[u"file_original_path"] = orig_path
        if orig_size:
            item[u"file_size"] = int(orig_size)
        if orig_oshash:
            item[u"moviehash"] = orig_oshash

        if any((orig_path, orig_size, orig_oshash)):
            return item

        item[u"temp"] = True

    elif file_original_path.find(u"rar://") > -1:
        item[u"rar"] = True
        item[u"file_original_path"] = os.path.dirname(file_original_path[6:])

    elif file_original_path.find(u"stack://") > -1:
        stack_path = file_original_path.split(u" , ")
        item[u"file_original_path"] = stack_path[0][8:]

    if not item[u"temp"]:
        item[u"basename"]=os.path.basename(file_original_path[6:])
        item[u"file_size"], item[u"moviehash"] = hash_file(item[u"file_original_path"], item[u"rar"])
    #else:
    #    item["basename"]=os.path.basename(file_original_path[6:])
    return item


def hash_file(file_path, rar):
    if rar:
        return hash_rar(file_path)

    log(__name__, u"Hash Standard file")
    long_long_format = u"q"  # long long
    byte_size = struct.calcsize(long_long_format)
        
    try:
        f = xbmcvfs.File(file_path)
        file_size = f.size()
        hash_ = file_size

        if file_size < 65536 * 2:
            return u"SizeError"

        buffer = f.readBytes(65536)
        f.seek(max(0, file_size - 65536), 0)
        buffer += f.readBytes(65536)
    finally:
        f.close()


    for x in xrange(int(65536 / byte_size) * 2):
        size = x * byte_size
        (l_value,) = struct.unpack(long_long_format, buffer[size:size + byte_size])
        hash_ += l_value
        hash_ = hash_ & 0xFFFFFFFFFFFFFFFF

    return_hash = u"%016x" % hash_
    return file_size, return_hash


def hash_rar(first_rar_file):
    log(__name__, u"Hash Rar file")
    f = xbmcvfs.File(first_rar_file)
    a = f.readBytes(4)
    if a != u"Rar!":
        raise Exception(u"ERROR: This is not rar file.")
    seek = 0
    for i in xrange(4):
        f.seek(max(0, seek), 0)
        a = f.readBytes(100)
        type_, flag, size = struct.unpack(u"<BHH", a[2:2 + 5])
        if 0x74 == type_:
            if 0x30 != struct.unpack(u"<B", a[25:25 + 1])[0]:
                raise Exception(u"Bad compression method! Work only for 'store'.")
            s_divide_body_start = seek + size
            s_divide_body, s_unpack_size = struct.unpack(u"<II", a[7:7 + 2 * 4])
            if flag & 0x0100:
                s_unpack_size = (struct.unpack(u"<I", a[36:36 + 4])[0] << 32) + s_unpack_size
                log(__name__, u"Hash untested for files bigger that 2gb. May work or may generate bad hash.")
            last_rar_file = get_last_split(first_rar_file, (s_unpack_size - 1) / s_divide_body)
            hash_ = add_file_hash(first_rar_file, s_unpack_size, s_divide_body_start)
            hash_ = add_file_hash(last_rar_file, hash_, (s_unpack_size % s_divide_body) + s_divide_body_start - 65536)
            f.close()
            return s_unpack_size, u"%016x" % hash_
        seek += size
    raise Exception(u"ERROR: Not Body part in rar file.")


def get_last_split(first_rar_file, x):
    if first_rar_file[-3:] == u"001":
        return first_rar_file[:-3] + (u"%03d" % (x + 1))
    if first_rar_file[-11:-6] == u".part":
        return first_rar_file[0:-6] + (u"%02d" % (x + 1)) + first_rar_file[-4:]
    if first_rar_file[-10:-5] == u".part":
        return first_rar_file[0:-5] + (u"%1d" % (x + 1)) + first_rar_file[-4:]
    return first_rar_file[0:-2] + (u"%02d" % (x - 1))


def add_file_hash(name, hash_, seek):
    f = xbmcvfs.File(name)
    f.seek(max(0, seek), 0)
    for i in xrange(8192):
        hash_ += struct.unpack(u"<q", f.readBytes(8))[0]
        hash_ = hash_ & 0xffffffffffffffff
    f.close()
    return hash_

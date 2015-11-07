import sys
import struct
import urllib2
import urlparse
import cookielib
from os import path
from httplib import HTTPConnection

import xbmc
import xbmcvfs


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg)).encode('utf-8'), level=xbmc.LOGDEBUG)


def notify(script_name, language, string_id):
    xbmc.executebuiltin((u'Notification(%s,%s)' % (script_name, language(string_id))).encode('utf-8'))


def get_params(params_str=""):
    params_str = params_str or sys.argv[2]
    return dict(urlparse.parse_qsl(params_str.lstrip('?')))


def get_video_path(xbmc_path=''):
    xbmc_path = xbmc_path or urlparse.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))
    if xbmc_path.startswith('rar://'):
        return path.dirname(xbmc_path.replace('rar://', ''))
    elif xbmc_path.startswith('stack://'):
        return xbmc_path.split(" , ")[0].replace('stack://', '')

    return xbmc_path


def get_languages_dict(languages_param):
    langs = {}
    for lang in languages_param.split(','):
        if lang == "Portuguese (Brazil)":
            langs["pob"] = lang
        elif lang == "Greek":
            langs["ell"] = lang
        else:
            langs[xbmc.convertLanguage(lang, xbmc.ISO_639_2)] = lang
    return langs


class HTTP10Connection(HTTPConnection):
    _http_vsn = 10
    _http_vsn_str = "HTTP/1.0"


class HTTP10Handler(urllib2.HTTPHandler):
    def http_open(self, req):
        return self.do_open(HTTP10Connection, req)


def get_session(proxies=None, cookies=True, http_10=False):
    handlers = []
    if proxies:
        handlers.append(urllib2.ProxyHandler(proxies))
    if cookies:
        cj = cookielib.CookieJar()
        handlers.append(urllib2.HTTPCookieProcessor(cj))
    if http_10:
        handlers.append(HTTP10Handler)
    return urllib2.build_opener(*handlers)


def __get_last_split(firs_rar_file, x):
    if firs_rar_file[-3:] == '001':
        return firs_rar_file[:-3] + ('%03d' % (x + 1))
    if firs_rar_file[-11:-6] == '.part':
        return firs_rar_file[0:-6] + ('%02d' % (x + 1)) + firs_rar_file[-4:]
    if firs_rar_file[-10:-5] == '.part':
        return firs_rar_file[0:-5] + ('%1d' % (x + 1)) + firs_rar_file[-4:]
    return firs_rar_file[0:-2] + ('%02d' % (x - 1))


def __add_file_hash(name, file_hash, seek):
    f = xbmcvfs.File(name)
    f.seek(max(0, seek), 0)
    for i in range(8192):
        file_hash += struct.unpack('<q', f.read(8))[0]
        file_hash &= 0xffffffffffffffff
    f.close()
    return file_hash


def __movie_size_and_hash_rar(firs_rar_file):
    log('utils.movie_size_and_hash', 'Hashing Rar file...')
    f = xbmcvfs.File(firs_rar_file)
    a = f.read(4)
    if a != 'Rar!':
        log('utils.movie_size_and_hash', 'ERROR: This is not rar file (%s).' % path.basename(firs_rar_file))
        raise Exception('ERROR: This is not rar file.')
    seek = 0
    for i in range(4):
        f.seek(max(0, seek), 0)
        a = f.read(100)
        tipe, flag, size = struct.unpack('<BHH', a[2:2 + 5])
        if 0x74 == tipe:
            if 0x30 != struct.unpack('<B', a[25:25 + 1])[0]:
                log('utils.movie_size_and_hash', 'Bad compression method! Work only for "store".')
                raise Exception('Bad compression method! Work only for "store".')
            s_partiize_body_start = seek + size
            s_partiize_body, s_unpack_size = struct.unpack('<II', a[7:7 + 2 * 4])
            if flag & 0x0100:
                s_unpack_size += (struct.unpack('<I', a[36:36 + 4])[0] << 32)
                log('utils.movie_size_and_hash',
                    'WARNING: Hash untested for files biger that 2gb. May work or may generate bad hash.')
            last_rar_file = __get_last_split(firs_rar_file, (s_unpack_size - 1) / s_partiize_body)
            file_hash = __add_file_hash(firs_rar_file, s_unpack_size, s_partiize_body_start)
            file_hash = __add_file_hash(
                last_rar_file, file_hash, (s_unpack_size % s_partiize_body) + s_partiize_body_start - 65536
            )
            f.close()
            return s_unpack_size, "%016x" % file_hash
        seek += size
    log('utils.movie_size_and_hash', 'ERROR: Not Body part in rar file.')
    raise Exception('ERROR: Not Body part in rar file.')


def movie_size_and_hash(file_path):
    file_ext = path.splitext(file_path)[1]
    if file_ext == '.rar' or file_ext == '.001':
        return __movie_size_and_hash_rar(file_path)

    longlong_format = '<q'  # little-endian long long
    byte_size = struct.calcsize(longlong_format)

    f = xbmcvfs.File(file_path)
    file_size = f.size()
    movie_hash = file_size

    if file_size < 65536 * 2:
        f.close()
        log('utils.movie_size_and_hash', "ERROR: SizeError (%d)." % file_size)
        raise Exception("SizeError")

    for x in range(65536 / byte_size):
        buff = f.read(byte_size)
        (l_value,) = struct.unpack(longlong_format, buff)
        movie_hash += l_value
        movie_hash &= 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

    f.seek(max(0, file_size - 65536), 0)
    for x in range(65536 / byte_size):
        buff = f.read(byte_size)
        (l_value,) = struct.unpack(longlong_format, buff)
        movie_hash += l_value
        movie_hash &= 0xFFFFFFFFFFFFFFFF
    returned_movie_hash = "%016x" % movie_hash
    f.close()

    return file_size, returned_movie_hash

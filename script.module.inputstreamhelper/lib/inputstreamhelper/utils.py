# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements various Helper functions"""

from __future__ import absolute_import, division, unicode_literals

import os
import re
import struct
from functools import total_ordering
from socket import timeout
from ssl import SSLError
from time import time
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config
from .kodiutils import (bg_progress_dialog, copy, delete, exists, get_setting,
                        localize, log, mkdirs, progress_dialog, set_setting,
                        stat_file, translate_path, yesno_dialog)
from .unicodes import compat_path, from_unicode, to_unicode


@total_ordering
class Version(NamedTuple):
    """Minimal version class used for parse_version. Should be enough for our purpose."""
    major: int = 0
    minor: int = 0
    micro: int = 0
    nano: int = 0

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.micro}.{self.nano}"

    def __lt__(self, other):
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.micro != other.micro:
            return self.micro < other.micro

        return self.nano < other.nano

    def __eq__(self, other):
        return all((self.major == other.major, self.minor == other.minor, self.micro == other.micro, self.nano == other.nano))


def temp_path():
    """Return temporary path, usually ~/.kodi/userdata/addon_data/script.module.inputstreamhelper/temp/"""
    tmp_path = translate_path(os.path.join(get_setting('temp_path', 'special://masterprofile/addon_data/script.module.inputstreamhelper'), 'temp', ''))
    if not exists(tmp_path):
        mkdirs(tmp_path)

    return tmp_path


def update_temp_path(new_temp_path):
    """"Updates temp_path and merges files."""
    old_temp_path = temp_path()

    set_setting('temp_path', new_temp_path)
    if old_temp_path != temp_path():
        from shutil import move
        move(old_temp_path, temp_path())


def download_path(url):
    """Choose download target directory based on url."""
    filename = url.split('/')[-1]

    return os.path.join(temp_path(), filename)


def _http_request(url, headers=None, time_out=10):
    """Perform an HTTP request and return request"""
    log(0, 'Request URL: {url}', url=url)

    try:
        if headers:
            request = Request(url, headers=headers)
        else:
            request = Request(url)
        req = urlopen(request, timeout=time_out)
        log(0, 'Response code: {code}', code=req.getcode())
        if 400 <= req.getcode() < 600:
            raise HTTPError('HTTP {} Error for url: {}'.format(req.getcode(), url), response=req)
    except (HTTPError, URLError) as err:
        log(2, 'Download failed with error {}'.format(err))
        if yesno_dialog(localize(30004), '{line1}\n{line2}'.format(line1=localize(30063), line2=localize(30065))):  # Internet down, try again?
            return _http_request(url, headers, time_out)
        return None

    return req


def http_get(url):
    """Perform an HTTP GET request and return content"""
    req = _http_request(url)
    if req is None:
        return None

    content = req.read()
    # NOTE: Do not log reponse (as could be large)
    # log(0, 'Response: {response}', response=content)
    return content.decode("utf-8")


def http_head(url):
    """Perform an HTTP HEAD request and return status code"""
    req = Request(url)
    req.get_method = lambda: 'HEAD'
    try:
        resp = urlopen(req)
        return resp.getcode()
    except HTTPError as exc:
        return exc.getcode()


def http_download(url, message=None, checksum=None, hash_alg='sha1', dl_size=None, background=False):  # pylint: disable=too-many-statements
    """Makes HTTP request and displays a progress dialog on download."""
    if checksum:
        from hashlib import md5, sha1
        if hash_alg == 'sha1':
            calc_checksum = sha1()
        elif hash_alg == 'md5':
            calc_checksum = md5()
        else:
            log(4, 'Invalid hash algorithm specified: {}'.format(hash_alg))
            checksum = None

    req = _http_request(url)
    if req is None:
        return None

    dl_path = download_path(url)
    filename = os.path.basename(dl_path)
    if not message:  # display "downloading [filename]"
        message = localize(30015, filename=filename)  # Downloading file

    total_length = int(req.info().get('content-length'))
    if dl_size and dl_size != total_length:
        log(2, 'The given file size does not match the request!')
        dl_size = total_length  # Otherwise size check at end would fail even if dl succeeded

    if background:
        progress = bg_progress_dialog()
    else:
        progress = progress_dialog()
    progress.create(localize(30014), message=message)  # Download in progress

    starttime = time()
    chunk_size = 32 * 1024
    with open(compat_path(dl_path), 'wb') as image:
        size = 0
        while size < total_length:
            try:
                chunk = req.read(chunk_size)
            except (timeout, SSLError):
                req.close()
                if not yesno_dialog(localize(30004), '{line1}\n{line2}'.format(line1=localize(30064),
                                                                               line2=localize(30065))):  # Could not finish dl. Try again?
                    progress.close()
                    return False

                headers = {'Range': 'bytes={}-{}'.format(size, total_length)}
                req = _http_request(url, headers=headers)
                if req is None:
                    return None
                continue

            image.write(chunk)
            if checksum:
                calc_checksum.update(chunk)
            size += len(chunk)
            percent = int(round(size * 100 / total_length))
            if not background and progress.iscanceled():
                progress.close()
                req.close()
                return False
            if time() - starttime > 5:
                time_left = int(round((total_length - size) * (time() - starttime) / size))
                prog_message = '{line1}\n{line2}'.format(
                    line1=message,
                    line2=localize(30058, mins=time_left // 60, secs=time_left % 60))  # Time remaining
            else:
                prog_message = message

            progress.update(percent, prog_message)

    progress.close()
    req.close()

    checksum_ok = (not checksum or calc_checksum.hexdigest() == checksum)
    size_ok = (not dl_size or stat_file(dl_path).st_size() == dl_size)

    if not all((checksum_ok, size_ok)):
        free_space = sizeof_fmt(diskspace())
        log(4, 'Something may be wrong with the downloaded file.')
        if not checksum_ok:
            log(4, 'Provided checksum: {}\nCalculated checksum: {}'.format(checksum, calc_checksum.hexdigest()))
        if not size_ok:
            free_space = sizeof_fmt(diskspace())
            log(4, 'Expected filesize: {}\nReal filesize: {}\nRemaining diskspace: {}'.format(dl_size, stat_file(dl_path).st_size(), free_space))

        if yesno_dialog(localize(30003), localize(30070, filename=filename)):  # file maybe broken. Continue anyway?
            log(4, 'Continuing despite possibly corrupt file!')
        else:
            return False

    return dl_path


def unzip(source, destination, file_to_unzip=None, result=[]):  # pylint: disable=dangerous-default-value
    """Unzip files to specified path"""

    if not exists(destination):
        mkdirs(destination)

    from zipfile import ZipFile
    with ZipFile(compat_path(source)) as zip_obj:
        for filename in zip_obj.namelist():
            if file_to_unzip and filename != file_to_unzip:
                continue

            # Detect and remove (dangling) symlinks before extraction
            fullname = os.path.join(destination, filename)
            if os.path.islink(compat_path(fullname)):
                log(3, 'Remove (dangling) symlink at {symlink}', symlink=fullname)
                delete(fullname)

            zip_obj.extract(filename, compat_path(destination))
            result.append(True)  # Pass by reference for Thread

    return bool(result)


def system_os():
    """Get system platform, and remember this information"""

    if hasattr(system_os, 'cached'):
        return getattr(system_os, 'cached')

    from xbmc import getCondVisibility
    if getCondVisibility('system.platform.android'):
        sys_name = 'Android'
    else:
        from platform import system
        sys_name = system()

    system_os.cached = sys_name
    return sys_name


def diskspace():
    """Return the free disk space available (in bytes) in temp_path."""
    statvfs = os.statvfs(compat_path(temp_path()))
    return statvfs.f_frsize * statvfs.f_bavail


def cmd_exists(cmd):
    """Check whether cmd exists on system."""
    # https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
    import subprocess
    return subprocess.call(['type ' + cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0


def run_cmd(cmd, sudo=False, shell=False):
    """Run subprocess command and return if it succeeds as a bool"""
    import subprocess
    env = os.environ.copy()
    env['LANG'] = 'C'
    output = ''
    success = False
    if sudo and os.getuid() != 0 and cmd_exists('sudo'):
        cmd.insert(0, 'sudo')

    try:
        output = to_unicode(subprocess.check_output(cmd, shell=shell, stderr=subprocess.STDOUT, env=env))
    except subprocess.CalledProcessError as error:
        output = to_unicode(error.output)
        log(4, '{cmd} cmd failed.', cmd=cmd)
    except OSError as error:
        log(4, '{cmd} cmd doesn\'t exist. {error}', cmd=cmd, error=error)
    else:
        success = True
        log(0, '{cmd} cmd executed successfully.', cmd=cmd)

    if output.rstrip():
        log(0, '{cmd} cmd output:\n{output}', cmd=cmd, output=output)
    if from_unicode('sudo') in cmd:
        subprocess.call(['sudo', '-k'])  # reset timestamp

    return {
        'output': output,
        'success': success
    }


def sizeof_fmt(num, suffix='B'):
    """Return size of file in a human readable string."""
    # https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def arch():
    """Map together, cache and return the system architecture"""

    if hasattr(arch, 'cached'):
        return getattr(arch, 'cached')

    from platform import architecture, machine
    sys_arch = machine()
    if sys_arch == 'AMD64':
        sys_arch_bit = architecture()[0]
        if sys_arch_bit == '32bit':
            sys_arch = 'x86'  # else, sys_arch = AMD64

    elif 'armv' in sys_arch:
        arm_version = re.search(r'\d+', sys_arch.split('v')[1])
        if arm_version:
            sys_arch = 'armv' + arm_version.group()

    if sys_arch in config.ARCH_MAP:
        sys_arch = config.ARCH_MAP[sys_arch]

    log(0, 'Found system architecture {arch}', arch=sys_arch)

    arch.cached = sys_arch
    return sys_arch


def userspace64():
    """To check if userspace is 64bit or 32bit"""
    return struct.calcsize('P') * 8 == 64


def hardlink(src, dest):
    """Hardlink a file when possible, copy when needed"""
    if exists(dest):
        delete(dest)

    try:
        from os import link
        link(compat_path(src), compat_path(dest))
    except (AttributeError, OSError, ImportError):
        return copy(src, dest)
    log(2, "Hardlink file '{src}' to '{dest}'.", src=src, dest=dest)
    return True


def remove_tree(path):
    """Remove an entire directory tree"""
    from shutil import rmtree
    rmtree(compat_path(path))


def parse_version(vstring):
    """Parse a version string and return a comparable version object, properly handling non-numeric prefixes."""
    vstring = vstring.strip('v').lower()
    parts = re.split(r'\.', vstring)  # split on periods first

    vnums = []
    for part in parts:
        # extract numeric part, ignoring non-numeric prefixes
        numeric_part = re.search(r'\d+', part)
        if numeric_part:
            vnums.append(int(numeric_part.group()))
        else:
            vnums.append(0)  # default to 0 if no numeric part found

    # ensure the version tuple always has 4 components
    vnums = (vnums + [0] * 4)[:4]

    return Version(*vnums)

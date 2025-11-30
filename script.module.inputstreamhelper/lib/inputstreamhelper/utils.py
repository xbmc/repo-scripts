# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements various Helper functions"""

import os
import re
import struct
from functools import total_ordering
from socket import timeout
from ssl import SSLError
from time import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config
from .kodiutils import (bg_progress_dialog, copy, delete, exists, get_setting,
                        localize, log, mkdirs, progress_dialog, set_setting,
                        stat_file, translate_path, yesno_dialog)
from .unicodes import compat_path, from_unicode, to_unicode


@total_ordering
class Version:
    """Implements Version"""
    def __init__(self, *components):
        self.components = list(components)

    def __str__(self):
        return '.'.join(map(str, self.components))

    def __lt__(self, other):
        # extended comparison that accounts for different lengths by padding with zeros
        max_length = max(len(self.components), len(other.components))
        # extend both lists with zeros up to the maximum length
        extended_self = self.components + [0] * (max_length - len(self.components))
        extended_other = other.components + [0] * (max_length - len(other.components))

        for self_comp, other_comp in zip(extended_self, extended_other):
            if self_comp < other_comp:
                return True
            if self_comp > other_comp:
                return False
        return False  # return False if all comparisons are equal

    def __eq__(self, other):
        # Uses the same logic for equality
        return not self < other and not other < self


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


def _http_request(url, data=None, headers=None, time_out=10):
    """Perform an HTTP request and return response"""
    log(0, 'Request URL: {url}', url=url)

    try:
        request = Request(url)
        if headers:
            request.headers = headers
        if data:
            request.data = data
        response = urlopen(request, timeout=time_out)  # pylint: disable=consider-using-with
        log(0, 'Response code: {code}', code=response.getcode())
        if 400 <= response.getcode() < 600:
            raise HTTPError
    except (HTTPError, URLError) as err:
        log(2, 'Download failed with error {}'.format(err))
        if yesno_dialog(localize(30004), '{line1}\n{line2}'.format(line1=localize(30063), line2=localize(30065))):  # Internet down, try again?
            return _http_request(url, headers, time_out)
        return None
    return response


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
        with urlopen(req) as response:
            return response.getcode()
    except HTTPError as exc:
        return exc.getcode()


def http_post(url, data, headers):
    """Perform an HTTP POST request and return content"""
    resp = _http_request(url, data, headers)
    if resp is None:
        return None

    content = resp.read()
    # NOTE: Do not log reponse (as could be large)
    # log(0, 'Response: {response}', response=content)
    return content.decode("utf-8")


def http_download(url, message=None, checksum=None, hash_alg='sha1', dl_size=None, background=False):  # pylint: disable=too-many-positional-arguments, too-many-statements
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

    from shutil import copyfileobj
    from zipfile import ZipFile
    with ZipFile(compat_path(source)) as zip_obj:
        for filename in zip_obj.namelist():
            if file_to_unzip:
                # normalize to list
                if isinstance(file_to_unzip, str):
                    files = [file_to_unzip]
                else:
                    files = list(file_to_unzip)

                if os.path.basename(filename) not in files:
                    continue

            # Detect and remove (dangling) symlinks before extraction
            fullname = os.path.join(destination, filename)
            if os.path.islink(compat_path(fullname)):
                log(3, 'Remove (dangling) symlink at {symlink}', symlink=fullname)
                delete(fullname)

            source = zip_obj.open(filename)
            target = open(os.path.join(compat_path(destination), os.path.basename(filename)), 'wb')
            with source, target:
                copyfileobj(source, target)

            result.append(True)  # Pass by reference for Thread

    return bool(result)


def system_os():
    """Get system platform, and remember this information"""

    if hasattr(system_os, 'cached'):
        return getattr(system_os, 'cached')

    from xbmc import getCondVisibility
    if getCondVisibility('system.platform.android'):
        sys_name = 'Android'
    elif getCondVisibility('system.platform.webos'):
        sys_name = 'webOS'
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


def elfbinary64(path):
    """To check if an ELF binary is 64bit or 32bit"""
    with open(path, 'rb') as f:
        f.seek(4)          # skip 0x7F 'E' 'L' 'F'
        b = f.read(1)
        if b == b'\x01':
            return False
        if b == b'\x02':
            return True
        raise ValueError('Not a valid ELF class')


def hardlink(src, dest):
    """Hardlink a file when possible, copy when needed"""
    if exists(dest):
        delete(dest)

    try:
        from os import link
        link(compat_path(src), compat_path(dest))
    except (AttributeError, OSError, ImportError):
        return copy(src, dest)
    log(0, "Hardlink file '{src}' to '{dest}'.", src=src, dest=dest)
    return True


def remove_tree(path):
    """Remove an entire directory tree"""
    from shutil import rmtree
    if exists(path):
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

    return Version(*vnums)

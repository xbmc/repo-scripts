# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import ast
import hashlib
import json
import os
import traceback

import xbmcvfs

from .common import log
from .common import read_file
from .common import write_file
from .constants import HASH_FILE


def generate_file_hash(filename):
    if not os.path.isfile(filename):
        return None

    md5 = hashlib.md5()
    block_size = 128 * md5.block_size
    try:
        # don't use read_file(), so we can read and update the hexdigest in digestable block sizes
        # improvement for large files
        with open(filename, 'rb') as file_handle:
            while True:
                buffer = file_handle.read(block_size)
                if not buffer:
                    break
                md5.update(buffer)

        return md5.hexdigest()
    except:
        log(traceback.print_exc())
        log("Unable to generate hash for %s" % filename)
        raise


def read_hashes(hash_file=None):
    if not hash_file:
        hash_file = HASH_FILE

    payload = []
    if xbmcvfs.exists(hash_file):
        # The properties file exists, load from it

        raw_hashes = read_file(hash_file)

        try:
            payload = json.loads(raw_hashes)
        except json.decoder.JSONDecodeError:
            payload = ast.literal_eval(raw_hashes)
        except:
            payload = []

    return payload


def write_hashes(data):
    try:
        payload = json.dumps(data, indent=4)
        write_file(HASH_FILE, payload)
    except:
        log(traceback.print_exc())
        log('Failed to write hashes to %s' % HASH_FILE)

# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements ARM specific widevine functions for Lacros image"""

import os
import json
from ctypes.util import find_library

from .repo import cdm_from_repo
from .. import config
from ..kodiutils import exists, localize, log, mkdirs, open_file, progress_dialog
from ..utils import http_download, http_get, system_os, userspace64
from ..unsquash import SquashFs


def cdm_from_lacros():
    """Whether the Widevine CDM can/should be extracted from a lacros image"""
    return not cdm_from_repo() and bool(find_library("zstd"))  # The lacros images are compressed with zstd


def latest_lacros():
    """Finds the version of the latest stable lacros image"""
    latest = json.loads(http_get(config.LACROS_LATEST))[0]["version"]
    log(0, f"latest lacros image version is {latest}")
    return latest


def extract_widevine_lacros(dl_path, backup_path, img_version):
    """Extract Widevine from the given Lacros image"""
    progress = progress_dialog()
    progress.create(heading=localize(30043), message=localize(30044))  # Extracting Widevine CDM, prepping image

    fnames = (config.WIDEVINE_CDM_FILENAME[system_os()], config.WIDEVINE_MANIFEST_FILE, "LICENSE")  # Here it's not LICENSE.txt, as defined in the config.py
    bpath = os.path.join(backup_path, img_version)
    if not exists(bpath):
        mkdirs(bpath)

    try:
        with SquashFs(dl_path) as sfs:
            for num, fname in enumerate(fnames):
                sfs.extract_file(fname, bpath)
                progress.update(int(90 / len(fnames) * (num + 1)), localize(30048))  # Extracting from image

    except (IOError, FileNotFoundError) as err:
        log(4, "SquashFs raised an error")
        log(4, err)
        return False


    with open_file(os.path.join(bpath, config.WIDEVINE_MANIFEST_FILE), "r") as manifest_file:
        manifest_json = json.load(manifest_file)

    manifest_json.update({"img_version": img_version})

    with open_file(os.path.join(bpath, config.WIDEVINE_MANIFEST_FILE), "w") as manifest_file:
        json.dump(manifest_json, manifest_file, indent=2)

    log(0, f"Successfully extracted all files from lacros image {os.path.basename(dl_path)}")
    return progress


def install_widevine_arm_lacros(backup_path, img_version=None):
    """Installs Widevine CDM extracted from a Chrome browser SquashFS image on ARM-based architectures."""

    if not img_version:
        img_version = latest_lacros()

    url = config.LACROS_DOWNLOAD_URL.format(version=img_version, arch=("arm64" if userspace64() else "arm"))

    dl_path = http_download(url, message=localize(30072))

    if dl_path:
        progress = extract_widevine_lacros(dl_path, backup_path, img_version)
        if progress:
            return (progress, img_version)

    return False

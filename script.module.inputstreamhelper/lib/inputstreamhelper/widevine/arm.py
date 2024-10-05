# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements ARM specific widevine functions"""

from __future__ import absolute_import, division, unicode_literals
import os
import json

from .. import config
from ..kodiutils import browsesingle, localize, log, ok_dialog, open_file, progress_dialog, yesno_dialog
from ..utils import diskspace, http_download, http_get, parse_version, sizeof_fmt, system_os, update_temp_path, userspace64
from .arm_chromeos import ChromeOSImage
from .arm_lacros import cdm_from_lacros, install_widevine_arm_lacros


def select_best_chromeos_image(devices):
    """Finds the newest and smallest of the ChromeOS images given"""
    log(0, 'Find best ARM image to use from the Chrome OS recovery.json')

    if userspace64():
        arm_bnames = config.CHROMEOS_RECOVERY_ARM64_BNAMES
    else:
        arm_bnames = config.CHROMEOS_RECOVERY_ARM_BNAMES

    best = None
    for device in devices:
        # Select ARM hardware only
        for arm_bname in arm_bnames:
            if arm_bname == device['file'].split('_')[2]:
                device['boardname'] = arm_bname  # add this new entry to avoid extracting it from the filename all the time
                break  # We found an ARM device, rejoice !
        else:
            continue  # Not ARM, skip this device

        # Select the first ARM device
        if best is None:
            best = device
            continue  # Go to the next device

        # Skip identical boardname
        if device['boardname'] == best['boardname']:
            continue

        # Select the newest version
        if parse_version(device['version']) > parse_version(best['version']):
            log(0, '{device[boardname]} ({device[version]}) is newer than {best[boardname]} ({best[version]})',
                device=device,
                best=best)
            best = device

        # Select the smallest image (disk space requirement)
        elif parse_version(device['version']) == parse_version(best['version']):
            if int(device['zipfilesize']) < int(best['zipfilesize']):
                log(0, '{device[boardname]} ({device_size}) is smaller than {best[boardname]} ({best_size})',
                    device=device,
                    device_size=int(device['zipfilesize']),
                    best=best,
                    best_size=int(best['zipfilesize']))
                best = device

    return best


def chromeos_config():
    """Reads the Chrome OS recovery configuration"""
    return json.loads(http_get(config.CHROMEOS_RECOVERY_URL))


def install_widevine_arm_chromeos(backup_path):
    """Installs Widevine CDM extracted from a Chrome OS image on ARM-based architectures."""
    # Select newest and smallest ChromeOS image
    devices = chromeos_config()
    arm_device = select_best_chromeos_image(devices)

    if arm_device is None:
        log(4, 'We could not find an ARM device in the Chrome OS recovery.json')
        ok_dialog(localize(30004), localize(30005))
        return False

    # Estimated required disk space: takes into account an extra 20 MiB buffer
    required_diskspace = 20971520 + int(arm_device['zipfilesize'])
    if yesno_dialog(localize(30001),  # Due to distributing issues, this takes a long time
                    localize(30006, diskspace=sizeof_fmt(required_diskspace))):
        if system_os() != 'Linux':
            ok_dialog(localize(30004), localize(30019, os=system_os()))
            return False

        while required_diskspace >= diskspace():
            if yesno_dialog(localize(30004), localize(30055)):  # Not enough space, alternative path?
                update_temp_path(browsesingle(3, localize(30909), 'files'))  # Temporary path
                continue

            ok_dialog(localize(30004),  # Not enough free disk space
                      localize(30018, diskspace=sizeof_fmt(required_diskspace)))
            return False

        log(2, 'Downloading ChromeOS image for Widevine: {boardname} ({version})'.format(**arm_device))
        url = arm_device['url']

        extracted = dl_extract_widevine_chromeos(url, backup_path, arm_device)
        if extracted:
            recovery_file = os.path.join(backup_path, arm_device['version'], os.path.basename(config.CHROMEOS_RECOVERY_URL))
            with open_file(recovery_file, 'w') as reco_file:  # pylint: disable=unspecified-encoding
                reco_file.write(json.dumps(devices, indent=4))

            return extracted

    return False


def dl_extract_widevine_chromeos(url, backup_path, arm_device=None):
    """Download the ChromeOS image and extract Widevine from it"""
    if arm_device:
        dl_path = http_download(url, message=localize(30022), checksum=arm_device['sha1'], hash_alg='sha1',
                                   dl_size=int(arm_device['zipfilesize']))  # Downloading the recovery image
        image_version = arm_device['version']
    else:
        dl_path = http_download(url, message=localize(30022))
        image_version = os.path.basename(url).split('_')[1]
        # minimal info for config.json, "version" is definitely needed e.g. in load_widevine_config:
        arm_device = {"file": os.path.basename(url), "url": url, "version": image_version}

    if dl_path:
        progress = extract_widevine_chromeos(backup_path, dl_path, image_version)
        if not progress:
            return False

        config_file = os.path.join(backup_path, image_version, 'config.json')
        with open_file(config_file, 'w') as conf_file:
            conf_file.write(json.dumps(arm_device))

        return (progress, image_version)

    return False


def extract_widevine_chromeos(backup_path, image_path, image_version):
    """Extract Widevine from the given ChromeOS image"""
    progress = progress_dialog()
    progress.create(heading=localize(30043), message=localize(30044))  # Extracting Widevine CDM

    extracted = ChromeOSImage(image_path, progress=progress).extract_file(
        filename=config.WIDEVINE_CDM_FILENAME[system_os()],
        extract_path=os.path.join(backup_path, image_version))

    if not extracted:
        log(4, 'Extracting widevine from the zip failed!')
        progress.close()
        return False

    return progress


def install_widevine_arm(backup_path):
    """Wrapper for installing widevine either from Chrome browser image or Chrome OS image"""
    if cdm_from_lacros():
        return install_widevine_arm_lacros(backup_path)

    return install_widevine_arm_chromeos(backup_path)

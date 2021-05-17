#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     08 Dec 2020, (21:07 PM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""

import os
import time
import shutil

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from resources import downloader, extract

__addon__ = xbmcaddon.Addon()
__path__ = __addon__.getAddonInfo('path')
__addonname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__icon__ = __addon__.getAddonInfo('icon')
__ID__ = __addon__.getAddonInfo('id')
__language__ = __addon__.getLocalizedString
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))

ffmpeg_url_template = "https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-{}-static.tar.xz"
md5sum_url_template = "https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-{}-static.tar.xz"


class UnmanicDependencies(object):
    os_arch = None

    def fetch_ffmpeg(self):
        downloaded = False
        # TODO: Remove
        downloaded = True

        # Get URL based on ARCH
        try:
            ffmpeg_url, md5sum_url = self.get_ffmpeg_urls()
        except Exception as e:
            xbmc.log('Unmanic: Error while determining download URLs - {}'.format(str(e)), level=xbmc.LOGERROR)
            return False
        # Create Dialog
        dp = xbmcgui.DialogProgress()
        dp.create("Unmanic: {} ".format(__language__(31010)), __language__(31011))

        # Set the downloads path
        download_directory = os.path.join(__profile__, "downloads")
        archive = os.path.join(download_directory, "ffmpeg-git-amd64-static.tar.xz")
        md5sum = os.path.join(download_directory, "ffmpeg-git-amd64-static.md5")  # Not required any more... CBF!

        # Ensure download directory exists
        if not os.path.exists(download_directory):
            os.makedirs(download_directory)

        # Remove previous download if it exists
        if os.path.exists(archive):
            try:
                os.remove(archive)
            except Exception as e:
                xbmc.log('Unmanic: Error while removing file {} - {}'.format(archive, str(e)), level=xbmc.LOGERROR)

        # Download the file with the created progress dialog
        try:
            xbmc.log("Unmanic: Downloading from url '{}'".format(ffmpeg_url), level=xbmc.LOGDEBUG)
            dp.update(0, __language__(31012))
            downloader.download(ffmpeg_url, archive, dp)
            downloaded = True
        except Exception as e:
            xbmc.log('Unmanic: Exception raised while downloading URL {} - {}'.format(ffmpeg_url, str(e)),
                     level=xbmc.LOGERROR)
            downloaded = False

        # # Download checksum - (Not required any more... CBF!)
        # try:
        #     xbmc.log("Unmanic: Downloading from url '{}'".format(md5sum_url), level=xbmc.LOGDEBUG)
        #     dp.update(0, __language__(31013))
        #     downloader.download(md5sum_url, md5sum, dp)
        # except Exception as e:
        #     xbmc.log('Unmanic: Exception raised while downloading URL {} - {}'.format(md5sum_url, str(e)),
        #              level=xbmc.LOGERROR)
        #     downloaded = False

        extract_tmp_dir = os.path.join(__profile__, "tmp")
        destination_dir = os.path.join(__profile__, "bin")
        if downloaded:
            dp.update(0, __language__(31014))
            time.sleep(2)
            try:
                xbmc.log("Unmanic: Extracting file '{}'".format(archive), level=xbmc.LOGDEBUG)
                extract.extract_all(archive, extract_tmp_dir, dp)
            except Exception as e:
                xbmc.log('Unmanic: Exception raised while extracting archive {} - {}'.format(archive, str(e)),
                         level=xbmc.LOGERROR)

            # Install by stripping the first directory
            dp.update(0, __language__(31011))
            components_to_strip = 1
            time.sleep(2)
            dp.update(33)
            copy_directory = extract_tmp_dir
            for i in range(0, components_to_strip):
                sub_folders = os.listdir(copy_directory)
                copy_directory = os.path.join(copy_directory, sub_folders[i])
            # Make sure the destination directory does not exist
            dp.update(45)
            if os.path.exists(destination_dir):
                shutil.rmtree(destination_dir)
            # Now copy the temp 'copy_directory' to the destination directory
            dp.update(70)
            shutil.copytree(copy_directory, destination_dir)
            # Finally remove the temp directory
            dp.update(90)
            shutil.rmtree(extract_tmp_dir)
            dp.update(100)

            dp.update(100, __language__(31015))
            time.sleep(1)
            dp.close()

    def get_ffmpeg_urls(self):
        arch = self.get_os_arch()
        ffmpeg_url = ffmpeg_url_template.format(arch)
        md5sum_url = md5sum_url_template.format(arch)
        return ffmpeg_url, md5sum_url

    def get_os_arch(self):
        if self.os_arch is None:
            arch = os.uname()[4]
            if arch == 'x86_64':
                self.os_arch = "amd64"
            elif arch == 'x86':
                self.os_arch = "i686"
            elif arch == 'armv6l':
                self.os_arch = "armel"
            elif arch == 'armv7l':
                self.os_arch = "armhf"
            elif arch == 'aarch64':
                self.os_arch = "arm64"
            else:
                raise Exception("Incompatible Architecture")
            xbmc.log("Unmanic: '{}' architecture detected".format(self.os_arch), level=xbmc.LOGDEBUG)
        return self.os_arch

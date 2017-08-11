# -*- coding: utf-8 -*-
"""
    screensaver.atv4
    Copyright (C) 2017 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


    Note: This is a standalone script to update the offline video entries and
    their checksums
"""
import urllib2
import os
import json
import hashlib
import shutil
import sys

applefeed = "http://a1.phobos.apple.com/us/r1000/000/Features/atv/AutumnResources/videos/entries.json"
applelocalfeed = os.path.join("resources", "entries.json")
tmpfolder = "tmpvideos"


def generate_entries_and_checksums():
    try:
        response = urllib2.urlopen(applefeed)
    except:
        print("Failed to open Apple Feed, aborting")
        return

    if response.getcode() == 200:
        html = response.read()
        print("Updating offline local video feed file...")
        with open(applelocalfeed, "w") as f:
            f.write(html)
        print("Offline feed file updated!")

        # generating checksums
        print("Starting checksum generator...")
        if not os.path.exists(tmpfolder): os.mkdir(tmpfolder)
        checksums = {}
        failed = []

        video_feed = json.loads(html)
        for block in video_feed:
            for asset in block["assets"]:
                asset_url = asset["url"]
                print "Processing video %s..." % (asset_url)
                file_name = tmpdownload(asset_url)
                if file_name:
                    with open(os.path.join(tmpfolder, file_name), "rb") as f:
                        checksum = hashlib.md5(f.read()).hexdigest()
                        checksums[file_name] = checksum
                        os.remove(os.path.join(tmpfolder, file_name))
                        print "File processed. Checksum= %s" % (checksum)
                else:
                    failed.append(asset_url)

        shutil.rmtree(tmpfolder)
        print "Updating checksum file"
        with open(os.path.join("resources", "checksums.json"), "w") as f:
            f.write(json.dumps(checksums))
            print "All done"
        print "Failed items: %s" % (str(failed))
    else:
        print("Failed to open Apple Feed - Wrong status code, aborting")


def get_locations():
    try:
        response = urllib2.urlopen(applefeed)
    except:
        print("Failed to open Apple Feed, aborting")
        return

    if response.getcode() == 200:
        locations = []
        html = response.read()
        video_feed = json.loads(html)
        for block in video_feed:
            for asset in block["assets"]:
                if asset["accessibilityLabel"].lower() not in locations:
                    locations.append(asset["accessibilityLabel"].lower())
        print locations

    else:
        print("Failed to open Apple Feed - Wrong status code, aborting")


def tmpdownload(url):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)

    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    with open(os.path.join(tmpfolder, file_name), 'wb') as f:
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                return file_name
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8) * (len(status) + 1)
            print status,

    return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "1":
            generate_entries_and_checksums()
        elif sys.argv[1] == "2":
            get_locations()
    else:
        print("Please specify option.\n 1) update entries and timestamps \n 2) Get locations")

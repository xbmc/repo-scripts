# -*- coding: utf-8 -*-
import ftplib
import glob
import shutil
import sys
import os
import time
import socket
import urllib.error
import urllib.parse
import urllib.request
from math import sin, cos, sqrt, atan2, radians
import xbmc
import xbmcvfs

# Allow for unit testing this file (remember to install kodistubs!)
# This brings this addon's resources, and bossanova808 module stuff into scope
# (when running this module outside Kodi)
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..')
    sys.path.insert(0, '../../../../script.module.bossanova808/resources/lib')

from bossanova808.constants import CWD
from bossanova808.logger import Logger
from resources.lib.store import Store


def _download_to_path(url, dst_path, timeout=15):
    """
    Download from URL to destination path atomically with proper cleanup.

    :param url: URL to download from
    :param dst_path: Destination file path
    :param timeout: Request timeout in seconds
    :raises: urllib.error.URLError, socket.timeout, OSError on failure
    """
    tmp_path = dst_path + ".tmp"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = response.read()
        with open(tmp_path, "wb") as fh:
            fh.write(data)
        os.replace(tmp_path, dst_path)
    except (urllib.error.URLError, socket.timeout, OSError):
        # Clean up any partial file
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


# noinspection PyPep8Naming
def get_distance(point1, point2):
    """
    Given two (lat,long) tuples return the distance between them
    https://stackoverflow.com/questions/57294120/calculating-distance-between-latitude-and-longitude-in-python
    """
    R = 6370
    lat1 = radians(point1[0])
    lon1 = radians(point1[1])
    lat2 = radians(point2[0])
    lon2 = radians(point2[1])

    d_lon = lon2 - lon1
    d_lat = lat2 - lat1

    a = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance


def closest_radar_to_lat_lon(point):
    """
    Given a lat/long tuple, return the closest radar (lat/lon) from our list of radars
    """
    closest_radar = (0, 0, "", "")
    closest_distance = 10000
    for radar in Store.BOM_RADAR_LOCATIONS:
        distance = get_distance(point, (radar[0], radar[1]))
        Logger.debug(f'Point {point}, radar {radar}, distance {distance}')
        if distance < closest_distance:
            Logger.debug(f'Setting closest radar to {radar}')
            closest_radar = radar
            closest_distance = distance

    return closest_radar


def download_background(radar_code, file_name, path):
    """
    Downloads a radar background given a BOM radar code like IDR023 &  an output filename
    :param radar_code: BOM radar code e.g. 'IDR0023'
    :param file_name: File name to download, e.g. 'locations.png' (see special cases below)
    :param path: Path to save the background images
    """

    # Needed due to bug in python 2.7 urllib, doesn't hurt anything else, so leave it in...
    # https://stackoverflow.com/questions/44733710/downloading-second-file-from-ftp-fails
    urllib.request.urlcleanup()

    out_file_name = file_name

    # The legend file doesn't have the radar code in the filename
    if file_name == "IDR.legend.0.png":
        out_file_name = "legend.png"
    else:
        # Append the radar code
        file_name = radar_code + "." + file_name

    # Download the backgrounds only if we don't have them yet
    if not os.path.isfile(os.path.join(path, out_file_name)):
        Logger.debug(f"Downloading missing background image....[{file_name}] as [{out_file_name}]")

        # Try bundled national background first (if available)
        if file_name == 'IDR00004.background.png' and CWD:
            src = os.path.join(CWD, "resources", "IDR00004.background.png")
            if os.path.isfile(src):
                Logger.debug("Copying bundled national radar background")
                try:
                    shutil.copy(src, os.path.join(path, "background.png"))
                    return
                except (OSError, shutil.Error) as e:
                    Logger.warning(f"Local copy of national radar background failed: {e} — will attempt remote fetch")

        # Fallback: fetch from BOM for all backgrounds (FTP first, then HTTP)
        ftp_url = Store.BOM_RADAR_BACKGROUND_FTPSTUB + file_name
        dst = os.path.join(path, out_file_name)

        try:
            _download_to_path(ftp_url, dst)
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            Logger.warning(f"FTP fetch failed for background {ftp_url}: {e} — trying HTTP")
            http_url = Store.BOM_RADAR_HTTPSTUB + os.path.basename(ftp_url)
            try:
                _download_to_path(http_url, dst)
            except (urllib.error.URLError, socket.timeout, OSError) as e2:
                Logger.error(f"Failed to retrieve radar background via FTP and HTTP: {ftp_url} | {http_url}, exception: {e2}")

    else:
        Logger.debug(f"Using cached {out_file_name}")


def prepare_backgrounds(radar_code, path):
    """
    Download backgrounds for given radar
    """

    Logger.debug("Calling prepareBackgrounds on [%s]" % radar_code)

    download_background(radar_code, "IDR.legend.0.png", path)
    download_background(radar_code, "background.png", path)
    # these images don't exist for the national radar, so don't try and get them
    if radar_code != "IDR00004":
        download_background(radar_code, "locations.png", path)
        download_background(radar_code, "range.png", path)
        download_background(radar_code, "topography.png", path)
        download_background(radar_code, "waterways.png", path)


def build_images(radar_code, path, loop_path):
    """
    Builds the radar images given a BOM radar code like IDR023
    The radar images are stored for maximum two hours, backgrounds forever
    (user can purge the radar background in the addon settings if need be, will force a re-download on next refresh)

    :param radar_code: BOM Radar code, e.g. 'IDR023'
    :param path: path to store the radar backgrounds
    :param loop_path: path to store the radar loop images
    """

    # grab the current time as 12 digit 0 padded string
    time_now = format(int(time.time()), '012d')

    Logger.debug("build_images(%s)" % radar_code)
    Logger.debug("Overlay loop path: " + loop_path)
    Logger.debug("Backgrounds path: " + path)

    Logger.info("Deleting any radar overlays older than an hour, that's long enough to see what has passed plus not take too long to loop")
    current_files = glob.glob(loop_path + "/*.png")
    for count, file in enumerate(current_files):
        filetime = os.path.getmtime(file)
        time_ago = time.time() - (1 * 60 * 60)
        if filetime < time_ago:
            os.remove(file)
            Logger.debug("Deleted aged radar image " + str(os.path.basename(file)))

    # rename the currently kept radar backgrounds to prevent Kodi caching from displaying stale images
    current_files = glob.glob(loop_path + "/*.png")
    for file in current_files:
        os.rename(file, os.path.dirname(file) + "/" + time_now + "." + os.path.basename(file)[13:])

    # create the folder for the backgrounds path if it does not yet exist
    if not os.path.exists(path):
        attempts = 0
        success = False
        while not success and (attempts < 20):
            # noinspection PyBroadException
            try:
                os.makedirs(path)
                success = True
                Logger.debug("Successfully created " + path)
            except:
                attempts += 1
                time.sleep(0.1)
        if not success:
            Logger.error("ERROR: Failed to create directory for radar background images!")
            return

    # ...and create the folder for the radar loop if it does not yet exist
    if not os.path.exists(loop_path):
        attempts = 0
        success = False
        while not success and (attempts < 20):
            # noinspection PyBroadException
            try:
                os.makedirs(loop_path)
                success = True
                Logger.debug("Successfully created " + loop_path)
            except:
                attempts += 1
                time.sleep(0.1)
        if not success:
            Logger.error("ERROR: Failed to create directory for loop images!")
            return

    # If for any reason we're missing any background images, this will go get them...
    prepare_backgrounds(radar_code, path)

    # OK so we should have the backgrounds...now it is time get the current radar loop
    # first we retrieve a list of the available files via ftp

    Logger.debug("Download the radar loop")

    # Try up to 3 times, with an exponential pause between each, to connect to BOM FTP
    # (to try and get past _very_ occasional 'too many users' errors)
    last_err = None
    for attempt in range(3):
        try:
            with ftplib.FTP("ftp.bom.gov.au", timeout=15) as ftp:
                ftp.login("anonymous", "anonymous@anonymous.org")
                ftp.cwd("/anon/gen/radar/")
                files = ftp.nlst(f"{radar_code}*")
                files.sort(reverse=True)
                break
        except ftplib.all_errors as e:
            last_err = e
            # 0.5s, 1s, 2s
            time.sleep(0.5 * (2 ** attempt))
    else:
        Logger.error(f"Failed after 3 attempts to connect/list BOM FTP: {last_err}")
        return

    Logger.debug("Download new files, and rename existing files, to avoid Kodi caching issues with the animated radar")
    # OK now we need just the matching radar files...
    # Maximum of 13 files (65 minutes, just over an hour, at 5 minutes each)
    loop_pic_names = []
    for f in files:
        if radar_code in f:
            loop_pic_names.insert(0, f)
            if len(loop_pic_names) > 13:
                Logger.debug("Retrieved names of latest 13 radar images (1 hour), that's enough.")
                break

    # Download the actual images
    # (note existing images have already been renamed above with time_now to prevent caching issues
    #  which is why we can test here with the current time_now to see if we already have the images)
    if loop_pic_names:
        for f in loop_pic_names:
            candidate = os.path.join(loop_path, f"{time_now}.{f}")
            if not os.path.isfile(candidate):
                # ignore the composite gif...
                if f[-3:] == "png":
                    image_to_retrieve = Store.BOM_RADAR_FTPSTUB + f
                    output_file = time_now + "." + f
                    Logger.debug("Retrieving new radar image: " + image_to_retrieve)
                    Logger.debug("Output to file: " + output_file)

                    dst = os.path.join(loop_path, output_file)
                    try:
                        _download_to_path(image_to_retrieve, dst)
                        Logger.debug(f"Successfully downloaded radar image: {f}")
                    except (urllib.error.URLError, socket.timeout, OSError) as e:
                        Logger.error(f"Failed to retrieve radar loop image via FTP: {image_to_retrieve}, exception: {e}")
                        continue

            else:
                Logger.debug("Using cached radar image: " + time_now + "." + f)


###########################################################
# MAIN - for testing outside Kodi

if __name__ == "__main__":

    # Run this with a 'clean' argument to first wipe any test files that exist
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        # noinspection PyBroadException
        try:
            Logger.debug("\n\nCleaning test-outputs folder")
            shutil.rmtree(os.getcwd() + "/test-outputs/")
        except:
            pass

    Logger.debug("\nCurrent files in test-outputs:\n")
    for dir_path, dir_names, filenames in os.walk(os.getcwd() + "/test-outputs/"):
        for name in dir_names:
            Logger.debug(os.path.join(dir_path, name))
        for name in filenames:
            Logger.debug(os.path.join(dir_path, name))

    test_radars = ["IDR023", "IDR00004"]
    for test_radar in test_radars:
        backgrounds_path = os.getcwd() + "/test-outputs/backgrounds/" + test_radar + "/"
        overlay_loop_path = os.getcwd() + "/test-outputs/loop/" + test_radar + "/"

        Logger.debug(f'\nTesting getting radar images from the BOM for {test_radar}\n')
        build_images(test_radar, backgrounds_path, overlay_loop_path)
        Logger.debug(os.listdir(backgrounds_path))
        Logger.debug(os.listdir(overlay_loop_path))

# -*- coding: utf-8 -*-
import ftplib
import glob
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from math import sin, cos, sqrt, atan2, radians
import xbmc

# Allow for unit testing this file
# This brings this addon's resources, and bossanova808 module stuff into scope
# (when running this module outside Kodi)
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..')
    sys.path.insert(0, '../../../../script.module.bossanova808/resources/lib')

from bossanova808.utilities import *
from bossanova808.logger import Logger
from resources.lib.store import Store


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


def dump_all_radar_backgrounds(all_backgrounds_path=None):
    """
    Remove the entire radar backgrounds folder, so that new ones will be pulled on next weather data refresh
    """
    if all_backgrounds_path is None:
        all_backgrounds_path = xbmcvfs.translatePath(
            "special://profile/addon_data/weather.ozweather/radarbackgrounds/")
    if os.path.isdir(all_backgrounds_path):
        shutil.rmtree(all_backgrounds_path)
        # Little pause to make sure this is complete before any refresh...
        time.sleep(0.5)


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

    # No longer do this - as this trips up the BOMs filter
    # New approach - if file is missing, then try get it
    # If it is not missing, don't do anything....but user can purge old/stale files manually in the addon settings

    # # Delete backgrounds older than a week old
    # if os.path.isfile(backgrounds_path + out_file_name) and ADDON.getSetting('BGDownloadToggle'):
    #     file_creation = os.path.getmtime(backgrounds_path + out_file_name)
    #     now = time.time()
    #     week_ago = now - 7 * 60 * 60 * 24  # Number of seconds in a week
    #     # log ("file creation: " + str(file_creation) + " week_ago " + str(week_ago))
    #     if file_creation < week_ago:
    #         log("Backgrounds stale (> one week) - refreshing - " + out_file_name)
    #         os.remove(backgrounds_path + out_file_name)
    #     else:
    #         log("Using cached background - " + out_file_name)

    # Download the backgrounds only if we don't have them yet
    if not os.path.isfile(path + out_file_name):

        Logger.debug("Downloading missing background image....[%s] as [%s]" % (file_name, out_file_name))

        if file_name == 'IDR00004.background.png':
            # Special case: national radar background periodically seems to be missing from BOM ftp?  Use a local copy...
            Logger.debug("Copying local copy of national radar background")
            # No need to do this if we're unit testing outside Kodi
            if CWD:
                shutil.copy(f"{CWD}/resources/IDR00004.background.png", f"{path}/background.png")
        else:
            url_to_get = Store.BOM_RADAR_BACKGROUND_FTPSTUB + file_name

            try:
                radar_image = urllib.request.urlopen(url_to_get)
                with open(path + "/" + out_file_name, "wb") as fh:
                    fh.write(radar_image.read())

            except Exception as e:
                Logger.error(f"Failed to retrieve radar background image: {url_to_get}, exception: {str(e)}")

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
    files = []

    Logger.debug("Log in to BOM FTP")
    attempts = 0
    ftp = None

    # Try up to 3 times, with a seconds pause between each, to connect to BOM FTP
    # (to try and get past very occasional 'too many users' errors)
    while not ftp and attempts < 3:
        # noinspection PyBroadException
        try:
            ftp = ftplib.FTP("ftp.bom.gov.au")
        except:
            attempts += 1
            time.sleep(1)

    if not ftp:
        Logger.error("Failed after 3 attempt to connect to BOM FTP - can't update radar loop")
        return

    ftp.login("anonymous", "anonymous@anonymous.org")
    ftp.cwd("/anon/gen/radar/")

    Logger.debug("Get files list")
    # connected, so let's get the list
    try:
        # BOM FTP still, in 2021, does not support the nicer mdst() operation
        files = ftp.nlst()
        files.sort(reverse=True)
    except ftplib.error_perm as resp:
        if str(resp) == "550 No files found":
            Logger.error("No files in BOM ftp directory!")
        else:
            Logger.error("Something wrong in the ftp bit of radar images")
            Logger.error(str(resp))

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
            if not os.path.isfile(loop_path + time_now + "." + f):
                # ignore the composite gif...
                if f[-3:] == "png":
                    image_to_retrieve = Store.BOM_RADAR_FTPSTUB + f
                    output_file = time_now + "." + f
                    Logger.debug("Retrieving new radar image: " + image_to_retrieve)
                    Logger.debug("Output to file: " + output_file)

                    try:
                        radar_image = urllib.request.urlopen(image_to_retrieve)
                        with open(loop_path + "/" + output_file, "wb") as fh:
                            fh.write(radar_image.read())

                    except Exception as e:
                        Logger.error(f"Failed to retrieve radar image: {image_to_retrieve}, exception: {str(e)}")
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

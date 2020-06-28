# -*- coding: utf-8 -*-

import ftplib
import glob
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib3

# This little bit of code is only for unit testing.
# When this module is run within Kodi, it will use the Kodi log function as usual
# However, when unit testing from the command line, the xbmc* modules will not be importable
# So the exception will be raised and in response we define a local log function that simply
# prints stuff to the command line.
try:
    from .common import log as log
except ImportError:
    print("\nKodi is not available -> probably unit testing")

    def log(message):
        print(message)

# Constants

FTPSTUB = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar/"
HTTPSTUB = "http://www.bom.gov.au/products/radar_transparencies/"


# Downloads a radar background given a BOM radar code like IDR023 & filename
# Converts the image from indexed colour to RGBA colour

def downloadBackground(radarCode, fileName, backgroundsPath):
    # Needed due to bug in python 2.7 urllib
    # https://stackoverflow.com/questions/44733710/downloading-second-file-from-ftp-fails
    urllib.request.urlcleanup()

    outFileName = fileName

    # The legend file doesn't have the radar code in the filename
    if fileName == "IDR.legend.0.png":
        outFileName = "legend.png"
    else:
        # Append the radar code
        fileName = radarCode + "." + fileName

    # Delete backgrounds older than a week old
    if os.path.isfile(backgroundsPath + outFileName):
        fileCreation = os.path.getmtime(backgroundsPath + outFileName)
        now = time.time()
        weekAgo = now - 7 * 60 * 60 * 24  # Number of seconds in a week
        # log ("file creation: " + str(fileCreation) + " weekAgo " + str(weekAgo))
        if fileCreation < weekAgo:
            log("Backgrounds stale (> one week) - refreshing - " + outFileName)
            os.remove(backgroundsPath + outFileName)
        else:
            log("Using cached background - " + outFileName)

    # Download the backgrounds only if we don't have them yet
    if not os.path.isfile(backgroundsPath + outFileName):

        log("Downloading missing background image....[%s] as [%s]" % (fileName, outFileName))

        # Ok get ready to retrieve some images
        imageFileRGB = backgroundsPath + outFileName

        USER_AGENT = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
        headers = urllib3.util.request.make_headers(accept_encoding='gzip, deflate',
                                                    keep_alive=True,
                                                    user_agent=USER_AGENT)

        # Special case for national radar background
        if "background.png" in fileName and '00004' in fileName:
            url_to_get = HTTPSTUB + 'IDE00035.background.png'
        else:
            url_to_get = HTTPSTUB + fileName

        try:
            http = urllib3.PoolManager()
            r = http.request('GET', url_to_get, preload_content=False, headers=headers)
            with open(imageFileRGB, 'wb') as out:
                while True:
                    data = r.read(65536)
                    if not data:
                        break
                    out.write(data)
            r.release_conn()
        except Exception as e:
            log(f'Failed to retrieve {url_to_get}', e)


# Download backgrounds for a radar image
def prepareBackgrounds(radarCode, backgroundsPath):
    log("Calling prepareBackgrounds on [%s]" % radarCode)

    downloadBackground(radarCode, "IDR.legend.0.png", backgroundsPath)
    downloadBackground(radarCode, "background.png", backgroundsPath)
    # these images don't exist for the national radar, so don't try and get them
    if radarCode != "IDR00004":
        downloadBackground(radarCode, "locations.png", backgroundsPath)
        downloadBackground(radarCode, "range.png", backgroundsPath)
        downloadBackground(radarCode, "topography.png", backgroundsPath)
        downloadBackground(radarCode, "waterways.png", backgroundsPath)


# Builds the radar images given a BOM radar code like IDR023
# the radar images are cached for four hours, backgrounds for a week (or always if updateRadarBackgrounds is false)

def buildImages(radarCode, updateRadarBackgrounds, backgroundsPath, overlayLoopPath):

    # grab the current time as as 12 digit 0 padded string
    timeNow = format(int(time.time()), '012d')

    log("buildImages(%s)" % radarCode)
    log("Overlay loop path: " + overlayLoopPath)
    log("Backgrounds path: " + backgroundsPath)

    log("Deleting any radar overlays older than 2 hours (as BOM keeps last two hours, we do too)")
    currentFiles = glob.glob(overlayLoopPath + "/*.png")
    for count, file in enumerate(currentFiles):
        filetime = os.path.getmtime(file)
        twoHoursAgo = time.time() - (2 * 60 * 60)
        if filetime < twoHoursAgo:
            os.remove(file)
            log("Deleted aged radar image " + str(os.path.basename(file)))

    # rename the currently kept radar backgrounds to prevent Kodi caching issues
    currentFiles = glob.glob(overlayLoopPath + "/*.png")
    for file in currentFiles:
        os.rename(file, os.path.dirname(file) + "/" + timeNow + "." + os.path.basename(file)[13:])

    # create the folder for the backgrounds path if it does not yet exist
    if not os.path.exists(backgroundsPath):
        try:
            os.makedirs(backgroundsPath)
            log("Created path for backgrounds at" + backgroundsPath)
        except Exception:
            log("ERROR: Failed to create directory for radar background images!")
            return

    if not os.path.exists(overlayLoopPath):
        attempts = 0
        success = False
        while not success and (attempts < 20):
            try:
                os.makedirs(overlayLoopPath)
                success = True
                log("Successfully created " + overlayLoopPath)
            except Exception:
                attempts += 1
                time.sleep(0.1)
        if not success:
            log("ERROR: Failed to create directory for loop images!")
            return

    # If we don't have any backgrounds, try and get them no matter what...
    if not os.listdir(backgroundsPath):
        updateRadarBackgrounds = True

    # If we need to get background images, go get them....
    if updateRadarBackgrounds:
        prepareBackgrounds(radarCode, backgroundsPath)

    # Ok so we have the backgrounds...now it is time get the loop
    # first we retrieve a list of the available files via ftp
    # ok get ready to retrieve some images

    log("Download the radar loop")
    files = []

    log("Log in to BOM FTP")
    ftp = ftplib.FTP("ftp.bom.gov.au")
    ftp.login("anonymous", "anonymous@anonymous.org")
    ftp.cwd("/anon/gen/radar/")

    log("Get files list")
    # connected, so let's get the list
    try:
        files = ftp.nlst()
    except ftplib.error_perm as resp:
        if str(resp) == "550 No files found":
            log("No files in BOM ftp directory!")
        else:
            log("Something wrong in the ftp bit of radar images")

    log("Download the files...")
    # ok now we need just the matching radar files...
    loopPicNames = []
    for f in files:
        if radarCode in f:
            loopPicNames.append(f)

    # download the actual images, might as well get the longest loop they have
    for f in loopPicNames:
        # don't re-download ones we already have
        if not os.path.isfile(overlayLoopPath + timeNow + "." + f):
            # ignore the composite gif...
            if f[-3:] == "png":
                imageToRetrieve = FTPSTUB + f
                outputFile = timeNow + "." + f
                log("Retrieving new radar image: " + imageToRetrieve)
                log("Output to file: " + outputFile)
                try:
                    radarImage = urllib.request.urlopen(imageToRetrieve)
                    with open(overlayLoopPath + "/" + outputFile, "wb") as fh:
                        fh.write(radarImage.read())

                except Exception as e:
                    log(f"Failed to retrieve radar image: {imageToRetrieve}, exception: {str(e)}")
        else:
            log("Using cached radar image: " + timeNow + "." + f)


###########################################################
# MAIN - for testing outside of Kodi

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        try:
            log("\n\nCleaning test-outputs folder")
            shutil.rmtree(os.getcwd() + "/test-outputs/")
        except Exception as inst:
            pass

    log("\nCurrent files in test-outputs:\n")

    for dirpath, dirnames, filenames in os.walk(os.getcwd() + "/test-outputs/"):
        for name in dirnames:
            log(os.path.join(dirpath, name))
        for name in filenames:
            log(os.path.join(dirpath, name))

    # Test Ascot Vale IDR023
    log("\nTesting getting radar images from the BOM for Ascot Vale - IDR023\n")
    radarCode = "IDR023"
    backgroundsPath = os.getcwd() + "/test-outputs/backgrounds/" + radarCode + "/"
    overlayLoopPath = os.getcwd() + "/test-outputs/loop/" + radarCode + "/"
    buildImages(radarCode, True, backgroundsPath, overlayLoopPath)
    log(os.listdir(backgroundsPath))
    log(os.listdir(overlayLoopPath))

    # Test national radar IDR00004, a special case
    log("\n\n\nTesting getting radar images from the BOM for the National Radar - IDR00004\n")
    radarCode = "IDR00004"
    backgroundsPath = os.getcwd() + "/test-outputs/backgrounds/" + radarCode + "/"
    overlayLoopPath = os.getcwd() + "/test-outputs/loop/" + radarCode + "/"
    buildImages(radarCode, True, backgroundsPath, overlayLoopPath)
    log(os.listdir(backgroundsPath))
    log(os.listdir(overlayLoopPath))

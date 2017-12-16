# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with KODI; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *

import requests
import glob
import os, sys, shutil
import time
import ftplib
import urllib, urllib2

# Constants

FTPSTUB = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar_transparencies/"
HTTPSTUB = "http://www.bom.gov.au/products/radar_transparencies/"

# Downloads a radar background given a BOM radar code like IDR023 & filename
# Converts the image from indexed colour to RGBA colour

def downloadBackground(radarCode, fileName, backgroundsPath):
    
    outFileName = fileName

    #the legend file doesn't have the radar code in the filename
    if fileName == "IDR.legend.0.png":
        outFileName = "legend.png"
    else:
        #append the radar code
        fileName = radarCode + "." + fileName


    # Delete backgrounds older than a week old

    if os.path.isfile( backgroundsPath + outFileName ):
        fileCreation = os.path.getmtime( backgroundsPath + outFileName )
        now = time.time()
        weekAgo = now - 7*60*60*24 # Number of seconds in a week
        #log ("filecreation: " + str(fileCreation) + " weekAgo " + str(weekAgo))
        if fileCreation < weekAgo:
            print("Backgrounds stale (> one week) - refreshing - " + outFileName)
            os.remove(backgroundsPath + outFileName)
        else:
            print("Using cached background - " + outFileName)

    #download the backgrounds only if we don't have them yet
    if not os.path.isfile( backgroundsPath + outFileName ):

        print("Downloading missing background image...." + outFileName)

        #import PIL only if we need it so the add on can be run for data only
        #on platforms without PIL
        #print("Importing PIL as extra features are activated.")
        from PIL import Image
        #ok get ready to retrieve some images
        image = urllib.URLopener()

        #the legend image showing the rain scale
        try:
            imageFileIndexed = backgroundsPath + "idx." + fileName
            imageFileRGB = backgroundsPath + outFileName
            try:
                image.retrieve(FTPSTUB + fileName, imageFileIndexed )
            except:
                print("ftp failed, let's try http instead...")
                try:
                    image.retrieve(HTTPSTUB + fileName, imageFileIndexed )
                except:
                    print("http failed too.. sad face :( ")
                    #jump to the outer exception
                    raise
            #got here, we must have an image
            print("Downloaded background texture...now converting from indexed to RGB - " + fileName)
            im = Image.open( imageFileIndexed )
            rgbimg = im.convert('RGBA')
            rgbimg.save(imageFileRGB, "PNG")
            os.remove(imageFileIndexed)
        
        except Exception as inst:

            print("Error getting " + fileName + " - error: ", inst)

            try:
                #ok so something is wrong with image conversion - probably a PIL issue, so let's just get a minimal BG image
                if "background.png" in fileName:
                    if not '00004' in fileName:
                        image.retrieve(FTPSTUB + fileName, imageFileRGB )
                        print("Got " + filename)
                    else:
                        #national radar loop uses a different BG for some reason...
                        image.retrieve(HTTPSTUB + 'IDE00035.background.png', imageFileRGB )
                        print("Got IDE00035.background.png")
            except Exception as inst2:
                print("No, really, -> Error, couldn't retrieve " + fileName + " - error: ", inst2)


# Download backgrounds for a radar image

def prepareBackgrounds(radarCode, backgroundsPath):

    print("prepareBackgrounds(%s)" % radarCode)

    downloadBackground(radarCode, "IDR.legend.0.png", backgroundsPath)
    downloadBackground(radarCode, "background.png", backgroundsPath)
    #these images don't exist for the national radar, so don't try and get them
    if radarCode != "IDR00004":
        downloadBackground(radarCode, "locations.png", backgroundsPath)
        downloadBackground(radarCode, "range.png", backgroundsPath)
        downloadBackground(radarCode, "topography.png", backgroundsPath)
        downloadBackground(radarCode, "waterways.png", backgroundsPath)


# Builds the radar images given a BOM radar code like IDR023
# the radar images are cached for four hours, backgrounds for a week (or always if updateRadarBackgrounds is false)

def buildImages(radarCode, updateRadarBackgrounds, backgroundsPath, overlayLoopPath):

    # grab the current time as as 12 digit 0 padded string
    timeNow = format(int(time.time()),'012d')

    print("buildImages(%s)" % radarCode)
    print("Overlay loop path: " + overlayLoopPath)
    print("Backgrounds path: " + backgroundsPath)

    # remove any backgrounds older than 

    print("Deleting any radar overlays older than 2 hours")
    currentFiles = glob.glob (overlayLoopPath + "/*.png")
    for count, file in enumerate(currentFiles):
        filetime = os.path.getmtime(file) 
        twoHoursAgo = time.time() - (2 * 60 * 60)
        if filetime < twoHoursAgo:
            print("Deleted " + str(os.path.basename(file)))
            os.remove(file)

    # rename the currently kept radar backgrounds to prevent Kodi caching issues
    currentFiles = glob.glob (overlayLoopPath + "/*.png")
    for file in currentFiles:
        os.rename(file, os.path.dirname(file) + "/" + timeNow + "." + os.path.basename(file)[13:])


    #sys.exit()

    # We need make the directories to store stuff if they don't exist
    # delay hack is here to make sure OS has actually released the handle
    # from the rmtree call above before we try and make the directory

    if not os.path.exists( backgroundsPath ):
        attempts = 0
        success = False
        while not success and (attempts < 20):
            try:
                os.makedirs( backgroundsPath )
                success = True
                print("Successfully created " + backgroundsPath)
            except:
                attempts += 1
                time.sleep(0.1)
        if not success:
            print("ERROR: Failed to create directory for radar background images!")
            return    

    if not os.path.exists( overlayLoopPath ):
        attempts = 0
        success = False
        while not success and (attempts < 20):
            try:
                os.makedirs( overlayLoopPath )
                success = True
                print("Successfully created " + overlayLoopPath)
            except:
                attempts += 1
                time.sleep(0.1)
        if not success:
            print("ERROR: Failed to create directory for loop images!")
            return


    # If we don't have any backgrounds, try and get them no matter what...
    if os.listdir(backgroundsPath) == []:
        updateRadarBackgrounds = True
    
    # If we need to get background images, go get them....
    if updateRadarBackgrounds:
        prepareBackgrounds(radarCode, backgroundsPath)

    # Ok so we have the backgrounds...now it is time get the loop
    # first we retrieve a list of the available files via ftp
    # ok get ready to retrieve some images

    print("Download the radar loop")
    files = []

    print("Log in to BOM FTP")
    ftp = ftplib.FTP("ftp.bom.gov.au")
    ftp.login("anonymous", "anonymous@anonymous.org")
    ftp.cwd("/anon/gen/radar/")

    print("Get files list")
    #connected, so let's get the list
    try:
        files = ftp.nlst()
    except ftplib.error_perm, resp:
        if str(resp) == "550 No files found":
            print("No files in BOM ftp directory!")
        else:
            print("Something wrong in the ftp bit of radar images")

    print("Download the files...")
    #ok now we need just the matching radar files...
    loopPicNames = []
    for f in files:
        if radarCode in f:
            loopPicNames.append(f)

    #download the actual images, might as well get the longest loop they have
    for f in loopPicNames:
        # don't re-download ones we already have
        if not os.path.isfile(overlayLoopPath + timeNow + "." + f):
            #ignore the composite gif...
            if f[-3:] == "png":
                imageToRetrieve = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar/" + f
                outputFile = timeNow + "." + f
                print("Retrieving new radar image: " + imageToRetrieve)
                print("Output to file: " + outputFile)
                try:
                    radarImage = urllib2.urlopen(imageToRetrieve)                    
                    fh = open( overlayLoopPath + "/" + outputFile , "wb")
                    fh.write(radarImage.read())
                    fh.close()
                except Exception as inst:
                    print("Failed to retrieve radar image: " + imageToRetrieve + ", oh well never mind!", inst )
        else:
            print("Using cached radar image: " + timeNow + "." + f)


###########################################################
# MAIN - for testing outside of Kodi

if __name__ == "__main__":

    radarCode = "IDR023"
    backgroundsPath = os.getcwd() + "/test-outputs/backgrounds/" + radarCode + "/"
    overlayLoopPath = os.getcwd() + "/test-outputs/loop/" + radarCode + "/"

    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        try:
            print("\n\nCleaning test-outputs folder")
            shutil.rmtree(os.getcwd() + "/test-outputs/")
        except Exception as inst:
            pass        

    print("\nCurrent files in test-outputs:\n")

    for dirpath, dirnames, filenames in os.walk(os.getcwd() + "/test-outputs/"):
        for name in dirnames:
            print(os.path.join(dirpath, name))
        for name in filenames:
            print(os.path.join(dirpath, name))
 
    print("\nTesting getting radar images from them BOM\n")
    buildImages(radarCode, True, backgroundsPath, overlayLoopPath)

    print(os.listdir(backgroundsPath))
    print(os.listdir(overlayLoopPath))
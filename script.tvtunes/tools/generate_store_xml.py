#
# Things to do before uploading themes
# 1) Make sure all themes are in mp3 format
# 2) Remove all tags etc from the mp3 file
# 3) Generate Replay Gain for each file
#
import os
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom


def isVideoFile(filename):
    if filename.endswith('.mp4'):
        return True
    if filename.endswith('.mkv'):
        return True
    if filename.endswith('.avi'):
        return True
    if filename.endswith('.mov'):
        return True
    return False


# Return a pretty-printed XML string for the Element.
def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    uglyXml = reparsed.toprettyxml(indent="    ")
    text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
    return text_re.sub('>\g<1></', uglyXml)


##################################
# Main of the TvTunes Service
##################################
if __name__ == '__main__':
    print "About to generate tvtunes-store.xml"

    shouldOpenWindows = False

    # Construct the XML handler
    root = ET.Element('tvtunesStore')
    enabledElem = ET.SubElement(root, 'enabled')
    enabledElem.text = "true"
    tvshowsElem = ET.SubElement(root, 'tvshows')
    moviesElem = ET.SubElement(root, 'movies')

    # Now add each tv show into the list
    tvShowIds = []
    if os.path.exists('tvshows'):
        tvShowIds = os.listdir('tvshows')

    print "Number of TV Shows is %d" % len(tvShowIds)
    openWindows = 0

    for tvShowId in tvShowIds:
        # Get the contents of the directory
        themesDir = "%s/%s" % ('tvshows', tvShowId)
        themes = os.listdir(themesDir)
        # Make sure the themes are not empty
        if len(themes) < 1:
            print "No themes in directory: %s" % themesDir
            continue

        # Create an element for this tv show
        tvshowElem = ET.SubElement(tvshowsElem, 'tvshow')
        tvshowElem.attrib['id'] = tvShowId

        # TODO: We could also get the name of the show here if we wanted

        numThemes = 0
        # Add each theme to the element
        for theme in themes:
            fullThemePath = "%s/%s" % (themesDir, theme)
            # Get the size of this theme file
            statinfo = os.stat(fullThemePath)
            fileSize = statinfo.st_size
            # Make sure not too small
            if fileSize < 19460:
                print "Themes file %s/%s is very small" % (themesDir, theme)
                continue

            themeElem = None
            # Add the theme to the list
            if isVideoFile(theme):
                print "Video Theme for %s is %s" % (themesDir, theme)
                themeElem = ET.SubElement(tvshowElem, 'videotheme')
            else:
                numThemes = numThemes + 1
                if not theme.endswith('.mp3'):
                    print "Audio theme %s is not mp3: %s" % (themesDir, theme)
                themeElem = ET.SubElement(tvshowElem, 'audiotheme')
            themeElem.text = theme
            themeElem.attrib['size'] = str(fileSize)

        if numThemes > 1:
            print "TvShow %s has %d themes" % (themesDir, numThemes)
            if shouldOpenWindows and (openWindows < 10):
                windowsDir = "start %s\\%s" % ('tvshows', tvShowId)
                os.system(windowsDir)
                openWindows = openWindows + 1

    # Now add each tv show into the list
    movieIds = []
    if os.path.exists('movies'):
        movieIds = os.listdir('movies')

    print "Number of Movies is %d" % len(movieIds)

    for movieId in movieIds:
        # Get the contents of the directory
        themesDir = "%s/%s" % ('movies', movieId)
        themes = os.listdir(themesDir)
        # Make sure the themes are not empty
        if len(themes) < 1:
            print "No themes in directory: %s" % themesDir
            continue

        # Create an element for this tv show
        movieElem = ET.SubElement(moviesElem, 'movie')
        movieElem.attrib['id'] = movieId

        # TODO: We could also get the name of the show here if we wanted

        numThemes = 0
        # Add each theme to the element
        for theme in themes:
            fullThemePath = "%s/%s" % (themesDir, theme)
            # Get the size of this theme file
            statinfo = os.stat(fullThemePath)
            fileSize = statinfo.st_size
            # Make sure not too small
            if fileSize < 19460:
                print "Themes file %s/%s is very small" % (themesDir, theme)
                continue

            themeElem = None
            # Add the theme to the list
            if isVideoFile(theme):
                if fileSize > 104857600:
                    print "Themes file %s/%s is very large" % (themesDir, theme)
                    continue
                print "Video Theme for %s is %s" % (themesDir, theme)
                themeElem = ET.SubElement(movieElem, 'videotheme')
            else:
                if fileSize > 20971520:
                    print "Themes file %s/%s is very large" % (themesDir, theme)
                    continue
                numThemes = numThemes + 1
                if not theme.endswith('.mp3'):
                    print "Audio theme %s is not mp3: %s" % (themesDir, theme)
                themeElem = ET.SubElement(movieElem, 'audiotheme')
            themeElem.text = theme
            themeElem.attrib['size'] = str(fileSize)

        if numThemes > 1:
            print "Movie %s has %d themes" % (themesDir, numThemes)
            if shouldOpenWindows and (openWindows < 10):
                windowsDir = "start %s\\%s" % ('movies', movieId)
                os.system(windowsDir)
                openWindows = openWindows + 1

    # Now create the file for the Store
    fileContent = prettify(root)

    recordFile = open('tvtunes-store.xml', 'w')
    recordFile.write(fileContent)
    recordFile.close()

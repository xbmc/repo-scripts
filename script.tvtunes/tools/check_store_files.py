# Checks the Theme Library for invalid theme files
import os


# gets all the themes in the library, keyed off of the theme filename
def collectItems(rootDir, userlist, cleanLib=False):
    # Now add each user entry into the list
    mediaIds = []
    if os.path.exists(rootDir):
        mediaIds = os.listdir(rootDir)

    print "Number of %s is %d" % (rootDir, len(mediaIds))

    for mediaId in mediaIds:
        # Get the contents of the directory
        themesDir = "%s/%s" % (rootDir, mediaId)
        themes = os.listdir(themesDir)
        # Make sure the themes are not empty
        if len(themes) < 1:
            print "No themes in directory: %s" % themesDir
            if cleanLib:
                os.rmdir(themesDir)
            continue

        # Add each theme to the element
        for theme in themes:
            fullThemePath = "%s/%s" % (themesDir, theme)
            # Get the size of this theme file
            statinfo = os.stat(fullThemePath)
            fileSize = statinfo.st_size
            # Make sure not too small
            if fileSize < 19460:
                print "Themes file %s/%s is very small" % (themesDir, theme)
                if cleanLib:
                    os.remove(fullThemePath)
                continue

            # Make sure not too small
            if fileSize > 104857600:
                print "Themes file %s/%s is very large" % (themesDir, theme)
                if cleanLib:
                    os.remove(fullThemePath)
                continue

            # Add the theme to the list
            userList = userlist.get(theme, None)
            if userList is None:
                userlist[theme] = []

            userlist[theme].append({'id': mediaId, 'size': fileSize, 'rootDir': rootDir, 'fullPath': fullThemePath})

    return userlist


##################################
# Main of the TvTunes Service
##################################
if __name__ == '__main__':
    print "About to check store files"

    cleanLib = False
    # Add all the themes in the library to a list keyed on the user ID
    userlist = {}
    userlist = collectItems('tvshows', userlist, cleanLib)
    userlist = collectItems('movies', userlist, cleanLib)

    filesToRemove = []
    # Now go through the list checking to ensure there are not multiple themes from
    # the same user that are the same size
    for userId in userlist:
        # get the set of themes uploaded by this user
        themesArray = userlist[userId]
        numEntries = len(themesArray)

        if numEntries > 1:
            for i in range(numEntries - 1):
                includedSrc = False
                size_i = themesArray[i]['size']
                for j in range(i + 1, numEntries):
                    size_j = themesArray[j]['size']
                    if size_i == size_j:
                        if themesArray[i]['fullPath'] not in filesToRemove:
                            print 'Matching size for %s, path = %s' % (userId, themesArray[i]['fullPath'])
                            filesToRemove.append(themesArray[i]['fullPath'])
                        if themesArray[j]['fullPath'] not in filesToRemove:
                            print 'Matching size for %s, path = %s' % (userId, themesArray[j]['fullPath'])
                            filesToRemove.append(themesArray[j]['fullPath'])

    # Now remove the files if required
    if cleanLib and (len(filesToRemove) > 0):
        print "\n\n"
        for remFile in filesToRemove:
            print 'Removing %s' % remFile
            os.remove(remFile)

    print "Total duplicates is %d" % len(filesToRemove)

#
# Moves all the videos into a directory of their own
#
import os


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


if __name__ == '__main__':
    print "About to move videos"

    # Now add each tv show into the list
    tvShowIds = os.listdir('tvshows')

    print "Number of TV Shows is %d" % len(tvShowIds)

    for tvShowId in tvShowIds:
        # Get the contents of the directory
        themesDir = "%s/%s" % ('tvshows', tvShowId)
        themes = os.listdir(themesDir)
        # Make sure the themes are not empty
        if len(themes) < 1:
            print "No themes in directory: %s" % themesDir
            continue

        numThemes = 0
        # Add each theme to the element
        for theme in themes:
            fullThemePath = "%s/%s" % (themesDir, theme)
            # Add the theme to the list
            if isVideoFile(theme):
                print "TV Video Theme for %s is %s" % (themesDir, theme)
                newLocation = "tvshows.videos/%s/%s" % (tvShowId, theme)
                os.renames(fullThemePath, newLocation)

    # Now add each tv show into the list
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

        numThemes = 0
        # Add each theme to the element
        for theme in themes:
            fullThemePath = "%s/%s" % (themesDir, theme)
            # Add the theme to the list
            if isVideoFile(theme):
                print "Movie Video Theme for %s is %s" % (themesDir, theme)
                newLocation = "movies.videos/%s/%s" % (movieId, theme)
                os.renames(fullThemePath, newLocation)

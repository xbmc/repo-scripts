# *  Function: Revolve/PopulateStaticItemsFromHomeProperties

import sys
import xbmc

import baselibrary
import xbmclibrary

FUNCTIONNAME = 'Revolve/PopulateStaticItemsFromHomeProperties'
DEFAULTTARGETWINDOW = '0'
DEFAULTTARGETMASK = 'MyItems%02dOption'
TOTALITEMS = 20

def createGenericName(sourcebase):
    return xbmclibrary.replaceEmptyItemWithHomeProperty(xbmclibrary.getItemFromHomeProperty(sourcebase + '.Title'), sourcebase + '.EpisodeTitle')

def createSongName(sourcebase):
    return xbmclibrary.getItemFromHomeProperty(sourcebase + '.Artist') + ' - ' + xbmclibrary.getItemFromHomeProperty(sourcebase + '.Title')

def createFavouriteName(sourcebase):
    return xbmclibrary.getItemFromHomeProperty(sourcebase + '.name')

def createGenericSubtitle(sourcebase):
    return xbmclibrary.joinItems(
        xbmclibrary.getItemFromHomeProperty(sourcebase + '.ShowTitle'),
        xbmclibrary.getItemFromHomeProperty(sourcebase + '.TVShowTitle'),
        xbmclibrary.getItemFromHomeProperty(sourcebase + '.Studio'),
        xbmclibrary.getItemFromHomeProperty(sourcebase + '.Artist'),
        xbmclibrary.getNumericValue(xbmclibrary.getItemFromHomeProperty(sourcebase + '.Year')),
        xbmclibrary.getNumericValue(xbmclibrary.getItemFromHomeProperty(sourcebase + '.Version')))

def createEpisodeSubtitle(sourcebase):
    seasonNumber = xbmclibrary.replaceEmptyItemWithHomeProperty(xbmclibrary.getItemFromHomeProperty(sourcebase + '.Season'), sourcebase + '.EpisodeSeason')
    episodeNumber = xbmclibrary.replaceEmptyItemWithHomeProperty(xbmclibrary.getItemFromHomeProperty(sourcebase + '.Episode'), sourcebase + '.EpisodeNumber')
    
    return xbmclibrary.joinItems(
        xbmclibrary.getItemFromHomeProperty(sourcebase + '.ShowTitle'),
        xbmclibrary.getItemFromHomeProperty(sourcebase + '.TVShowTitle'),
        xbmclibrary.addPrefixToItem(xbmclibrary.getLocalizedValue(20373) + ' ', xbmclibrary.getNumericValue(seasonNumber)),
        xbmclibrary.addPrefixToItem(xbmclibrary.getLocalizedValue(20359) + ' ', xbmclibrary.getNumericValue(episodeNumber)))

def createSongSubtitle(sourcebase):
    return xbmclibrary.joinItems(
        xbmclibrary.getItemFromHomeProperty(sourcebase + '.Album'),
        xbmclibrary.getNumericValue(xbmclibrary.getItemFromHomeProperty(sourcebase + '.Year')))

def createFavouriteSubtitle(sourcebase):
    return ''

def createGenericThumbnail(sourcebase):
    result = xbmclibrary.getItemFromHomeProperty(sourcebase + '.Art(poster)')
    result = xbmclibrary.replaceEmptyItemWithHomeProperty(result, sourcebase + '.thumb')
    result = xbmclibrary.replaceEmptyItemWithHomeProperty(result, sourcebase + '.Thumb')
    result = xbmclibrary.replaceEmptyItemWithHomeProperty(result, sourcebase + '.Icon')
    return result

def createGenericBackgroundImage(sourcebase):
    result = xbmclibrary.getItemFromHomeProperty(sourcebase + '.Art(Fanart)')
    result = xbmclibrary.replaceEmptyItemWithHomeProperty(result, sourcebase + '.Property(Fanart_image)')
    result = xbmclibrary.replaceEmptyItemWithHomeProperty(result, sourcebase + '.Fanart')
    return result

def createFavouriteBackgroundImage(sourcebase):
    return ''

def createGenericAction(sourcebase):
    result = xbmclibrary.getItemFromHomeProperty(sourcebase + '.Play')
    if result == '':
        result = xbmclibrary.getItemFromHomeProperty(sourcebase + '.LibraryPath')
        if 'videodb' in result.lower():
            result = xbmclibrary.addPrefixAndSuffixToItem('ActivateWindow(videos,', result, ',return)')
        if 'musicdb' in result.lower():
            result = xbmclibrary.addPrefixAndSuffixToItem('ActivateWindow(music,', result, ',return)')
    if result == '':
        result = xbmclibrary.addPrefixAndSuffixToItem('PlayMedia("', xbmclibrary.getItemFromHomeProperty(sourcebase + '.Path'), '")')
    return result

def createFavouriteAction(sourcebase):
    return baselibrary.escapePath(xbmclibrary.getItemFromHomeProperty(sourcebase + '.path'))


def determineNameMethod(sourcemask):
    result = createGenericName    
    if 'song' in sourcemask.lower():
        result = createSongName
    if 'favourite' in sourcemask.lower():
        result = createFavouriteName
    return result

def determineSubtitleMethod(sourcemask):
    result = createGenericSubtitle
    if 'episode' in sourcemask.lower():
        result = createEpisodeSubtitle
    if 'song' in sourcemask.lower():
        result = createSongSubtitle
    if 'favourite' in sourcemask.lower():
        result = createFavouriteSubtitle
    return result
    
def determineThumbnailMethod(sourcemask):
    return createGenericThumbnail
    
def determineBackgroundImageMethod(sourcemask):
    result = createGenericBackgroundImage
    if 'favourite' in sourcemask.lower():
        result = createFavouriteBackgroundImage
    return result
    
def determineActionMethod(sourcemask):
    result = createGenericAction
    if 'favourite' in sourcemask.lower():
        result = createFavouriteAction
    return result
    
def copyProperties(sourcemask, targetmask, targetwindow):
    nameMethod = determineNameMethod(sourcemask)
    subtitleMethod = determineSubtitleMethod(sourcemask)
    thumbnailMethod = determineThumbnailMethod(sourcemask)
    backgroundImageMethod = determineBackgroundImageMethod(sourcemask)
    actionMethod = determineActionMethod(sourcemask)

    for index in range (1, TOTALITEMS + 1):
        sourcebase = sourcemask % (index)
        targetbase = targetmask % (index)

        xbmclibrary.setItemToProperty(targetbase + '.Name', nameMethod(sourcebase), targetwindow)
        xbmclibrary.setItemToProperty(targetbase + '.Subtitle', subtitleMethod(sourcebase), targetwindow)
        xbmclibrary.setItemToProperty(targetbase + '.Thumbnail', thumbnailMethod(sourcebase), targetwindow)
        xbmclibrary.setItemToProperty(targetbase + '.BackgroundImage', backgroundImageMethod(sourcebase), targetwindow)
        xbmclibrary.setItemToProperty(targetbase + '.Action', actionMethod(sourcebase), targetwindow)

def execute(arguments):        
    if len(arguments) > 2:
        sourcemask = arguments[2]
        targetmask = baselibrary.extractArgument(arguments, 3, DEFAULTTARGETMASK)
        targetwindow = baselibrary.extractArgument(arguments, 4, DEFAULTTARGETWINDOW)

        copyProperties(sourcemask, targetmask, targetwindow)
    else:
        xbmclibrary.writeErrorMessage(FUNCTIONNAME, FUNCTIONNAME + ' terminates: Missing argument(s) in call to script.')	

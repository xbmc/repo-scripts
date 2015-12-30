# *  Library: XBMC/Kodi Wrapper

import sys
import xbmc

# Filter Methods

def escapeValue(value):
    if '"' not in value:
        value = '"' + value + '"'
    return value

def getNumericValue(value):
    if value == '0':
        value = ''
    return value
    
def getLocalizedValue(value):
    return xbmc.getLocalizedString(value)

# Recombination Methods    
    
def joinSingleValue(result, value):
    return result + value
    
def joinValues(*values):
    result = ''
    for value in values:
        result = joinSingleValue(result, label)
    return result
    
def joinSingleItem(result, item):
    if (result != '') and (item != ''):
        result = result + joinSingleValue(' | ', item)
    elif result == '':
        result = item
    return result
    
def joinItems(*items):
    result = ''
    for item in items:
        result = joinSingleItem(result, item)
    return result

def addPrefixToItem(prefix, item):
    if item != '':
        item = prefix + item
    return item
    
def addPrefixAndSuffixToItem(prefix, item, suffix):
    if item != '':
        item = prefix + item + suffix
    return item
    
def replaceEmptyItem(item, nextItem):
    if item != '':
        return item
    else:
        return nextItem
    
# Data Read Methods    
    
def getItemFromInfoLabel(infolabel):    
    return xbmc.getInfoLabel(infolabel)
    
def getItemFromProperty(property, window):
    return getItemFromInfoLabel('Window(' + window + ').Property(' + property + ')')

def getItemFromHomeProperty(property):
    return getItemFromProperty(property, 'home')

def getNumericItemFromHomeProperty(property):
    return getNumericValue(getItemFromProperty(property, 'home'))

def getItemFromSkinSetting(skinsetting):
    return getItemFromInfoLabel('Skin.String(' + skinsetting + ')')

def getBooleanItemFromSkinSetting(skinsetting):
    item = getItemFromInfoLabel('Skin.HasSetting(' + skinsetting + ')')
    if item == '':
        item = 'False'
    return item

def replaceEmptyItemWithHomeProperty(item, property):
    if item == '':
        item = getItemFromHomeProperty(property)
    return item

# Data Write Methods    
    
def clearProperty(property, window):
    xbmc.executebuiltin('ClearProperty(' + property + ',' + window + ')')
    
def setItemToProperty(property, item, window):
    if item != '':
        xbmc.executebuiltin('SetProperty(' + property + ',' + escapeValue(item) + ',' + window + ')')        
    else:
        xbmc.executebuiltin('ClearProperty(' + property + ',' + window + ')')
    
def setItemToSkinSetting(skinsetting, item):
    if item != '':
        xbmc.executebuiltin('Skin.SetString(' + skinsetting + ',' + escapeValue(item) + ')')
    else:
        xbmc.executebuiltin('Skin.Reset(' + skinsetting + ')')
    
# Data Copy Methods    
    
def copySkinSettingToProperty(skinsetting, property, window):
    item = getItemFromSkinSetting(skinsetting)
    setItemToProperty(property, item, window)

def copyBooleanSkinSettingToProperty(skinsetting, property, window):
    item = getBooleanItemFromSkinSetting(skinsetting)
    setItemToProperty(property, item, window)

    
# File Methods

def translatePath(filename):
    if filename.startswith('special://'):
        return xbmc.translatePath(filename)
    else:
        return filename

# Log Methods

def writeErrorMessage(source, message):
    if isinstance(message, str):
        message = message.decode("utf-8")
    logmessage = u'%s: %s' % (source, message)
    xbmc.log(msg=logmessage.encode("utf-8"), level=xbmc.LOGNOTICE)

def writeDebugMessage(source, message):
    if isinstance(message, str):
        message = message.decode("utf-8")
    logmessage = u'%s: %s' % (source, message)
    xbmc.log(msg=logmessage.encode("utf-8"), level=xbmc.LOGDEBUG)

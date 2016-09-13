# *  Library: Basic Functions

import sys
import time

# Methods

def extractArgument(arguments, index, defaultvalue):
    if len(arguments) > index:
        value = arguments[index]
    else:
        value = defaultvalue
    return value

def getTimeInMilliseconds():
    return int(round(time.time() * 1000))

def escapePath(path):
    return path.replace('\\\\', '\\').replace('\\', '\\\\\\\\')

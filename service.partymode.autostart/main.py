# -*- coding: utf-8 -*-
import xbmc, xbmcaddon

def handleArg(arg):

    pass

def main():

    xbmcaddon.Addon().openSettings()

if __name__ == '__main__':

    args = None
    if len(sys.argv) > 1:
        args = sys.argv[1:]

    if args:
        handleArg(args[0])
    else:
        main()
import sys
from kodi_six import xbmcgui
import resources.lib.utils as utils
from resources.lib.cronclasses import CustomPathFile
dialog = xbmcgui.Dialog()

# show the disclaimer - do this every time
dialog.ok(utils.getString(30031), "%s\n%s" % (utils.getString(30032), utils.getString(30033)))


def selectPath(contentType):
    path = {'expression': '0 */2 * * *', 'content': contentType}

    # select path to scan
    path['path'] = dialog.browse(0, utils.getString(30023), contentType)

    # create expression
    if(path['path'] != ''):
        path['expression'] = dialog.input(utils.getString(30056), path['expression'])
    else:
        # return nothing if dialog closed
        return None

    return path


def showMainScreen(contentType):
    exitCondition = ""
    customPaths = CustomPathFile(contentType)

    while(exitCondition != -1):
        # load the custom paths
        options = ['Add']

        for aPath in customPaths.getPaths():
            options.append(aPath['path'] + ' - ' + aPath['expression'])

        # show the gui
        exitCondition = dialog.select(utils.getString(30020), options)

        if(exitCondition >= 0):
            if(exitCondition == 0):
                path = selectPath(contentType)

                # could return None if dialog canceled
                if(path is not None):
                    customPaths.addPath(path)
            else:
                # delete?
                if(dialog.yesno(heading=utils.getString(30021), message=utils.getString(30022))):
                    # get the id of the selected item
                    aPath = customPaths.getPaths()[exitCondition - 1]
                    # delete that id
                    customPaths.deletePath(aPath['id'])


def get_params():
    param = {}
    try:
        for i in sys.argv:
            args = i
            if('=' in args):
                if(args.startswith('?')):
                    args = args[1:]  # legacy in case of url params
                splitString = args.split('=')
                param[splitString[0]] = splitString[1]
    except Exception:
        pass

    return param


# send type (video/music) to editor
params = get_params()

showMainScreen(params['type'])

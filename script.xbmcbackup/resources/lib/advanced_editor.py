import json
import xbmcgui
import xbmcvfs
import os.path
from . import utils as utils


class BackupSetManager:
    jsonFile = xbmcvfs.translatePath(utils.data_dir() + "custom_paths.json")
    paths = None

    def __init__(self):
        self.paths = {}

        # try and read in the custom file
        self._readFile()

    def addSet(self, aSet):
        self.paths[aSet['name']] = {'root': aSet['root'], 'dirs': [{"type": "include", "path": aSet['root'], 'recurse': True}]}

        # save the file
        self._writeFile()

    def updateSet(self, name, aSet):
        self.paths[name] = aSet

        # save the file
        self._writeFile()

    def deleteSet(self, index):
        # match the index to a key
        keys = self.getSets()

        # delete this set
        del self.paths[keys[index]]

        # save the file
        self._writeFile()

    def getSets(self):
        # list all current sets by name
        keys = list(self.paths.keys())
        keys.sort()

        return keys

    def getSet(self, index):
        keys = self.getSets()

        # return the set at this index
        return {'name': keys[index], 'set': self.paths[keys[index]]}

    def validateSetName(self, name):
        return (name not in self.getSets())

    def _writeFile(self):
        # create the custom file
        aFile = xbmcvfs.File(self.jsonFile, 'w')
        aFile.write(json.dumps(self.paths))
        aFile.close()

    def _readFile(self):

        if(xbmcvfs.exists(self.jsonFile)):

            # read in the custom file
            aFile = xbmcvfs.File(self.jsonFile)

            # load custom dirs
            self.paths = json.loads(aFile.read())
            aFile.close()
        else:
            # write a blank file
            self._writeFile()


class AdvancedBackupEditor:
    dialog = None

    def __init__(self):
        self.dialog = xbmcgui.Dialog()

    def _cleanPath(self, root, path):
        return path[len(root) - 1:]

    def _validatePath(self, root, path):
        return path.startswith(root)

    def createSet(self):
        backupSet = None

        name = self.dialog.input(utils.getString(30110), defaultt='Backup Set')

        if(name is not None):

            # give a choice to start in home or enter a root path
            enterHome = self.dialog.yesno(utils.getString(30111), message=utils.getString(30112) + " - " + utils.getString(30114) + "\n" + utils.getString(30113) + " - " + utils.getString(30115), nolabel=utils.getString(30112), yeslabel=utils.getString(30113))

            rootFolder = 'special://home'
            if(enterHome):
                rootFolder = self.dialog.input(utils.getString(30116), defaultt=rootFolder)

                # direcotry has to end in slash
                if(rootFolder[:-1] != '/'):
                    rootFolder = rootFolder + '/'

                # check that this path even exists
                if(not xbmcvfs.exists(xbmcvfs.translatePath(rootFolder))):
                    self.dialog.ok(utils.getString(30117), utils.getString(30118), rootFolder)
                    return None
            else:
                # select path to start set
                rootFolder = self.dialog.browse(type=0, heading=utils.getString(30119), shares='files', defaultt=rootFolder)

            backupSet = {'name': name, 'root': rootFolder}

        return backupSet

    def editSet(self, name, backupSet):
        optionSelected = ''
        rootPath = backupSet['root']

        while(optionSelected != -1):
            options = [xbmcgui.ListItem(utils.getString(30120), utils.getString(30143)), xbmcgui.ListItem(utils.getString(30135), utils.getString(30144)), xbmcgui.ListItem(rootPath, utils.getString(30121))]

            for aDir in backupSet['dirs']:
                if(aDir['type'] == 'exclude'):
                    options.append(xbmcgui.ListItem(self._cleanPath(rootPath, aDir['path']), "%s: %s" % (utils.getString(30145), utils.getString(30129))))
                elif(aDir['type'] == 'include'):
                    options.append(xbmcgui.ListItem(self._cleanPath(rootPath, aDir['path']), "%s: %s | %s: %s" % (utils.getString(30145), utils.getString(30134), utils.getString(30146), str(aDir['recurse']))))

            optionSelected = self.dialog.select(utils.getString(30122) + ' ' + name, options, useDetails=True)

            if(optionSelected == 0 or optionSelected == 1):
                # add a folder, will equal root if cancel is hit
                addFolder = self.dialog.browse(type=0, heading=utils.getString(30120), shares='files', defaultt=backupSet['root'])

                if(addFolder.startswith(rootPath)):

                    if(not any(addFolder == aDir['path'] for aDir in backupSet['dirs'])):
                        # cannot add root as an exclusion
                        if(optionSelected == 0 and addFolder != backupSet['root']):
                            backupSet['dirs'].append({"path": addFolder, "type": "exclude"})
                        elif(optionSelected == 1):
                            # can add root as inclusion
                            backupSet['dirs'].append({"path": addFolder, "type": "include", "recurse": True})
                    else:
                        # this path is already part of another include/exclude rule
                        self.dialog.ok(utils.getString(30117), utils.getString(30137), addFolder)
                else:
                    # folder must be under root folder
                    self.dialog.ok(utils.getString(30117), utils.getString(30136), rootPath)
            elif(optionSelected == 2):
                self.dialog.ok(utils.getString(30121), utils.getString(30130), backupSet['root'])
            elif(optionSelected > 2):

                cOptions = ['Delete']
                if(backupSet['dirs'][optionSelected - 3]['type'] == 'include'):
                    cOptions.append(utils.getString(30147))

                contextOption = self.dialog.contextmenu(cOptions)

                if(contextOption == 0):
                    if(self.dialog.yesno(heading=utils.getString(30123), message=utils.getString(30128))):
                        # remove folder
                        del backupSet['dirs'][optionSelected - 3]
                elif(contextOption == 1 and backupSet['dirs'][optionSelected - 3]['type'] == 'include'):
                    # toggle if this folder should be recursive
                    backupSet['dirs'][optionSelected - 3]['recurse'] = not backupSet['dirs'][optionSelected - 3]['recurse']

        return backupSet

    def showMainScreen(self):
        exitCondition = ""
        customPaths = BackupSetManager()

        # show this every time
        self.dialog.ok(utils.getString(30036), utils.getString(30037))

        while(exitCondition != -1):
            # load the custom paths
            listItem = xbmcgui.ListItem(utils.getString(30126), '')
            listItem.setArt({'icon': os.path.join(utils.addon_dir(), 'resources', 'images', 'plus-icon.png')})
            options = [listItem]

            for index in range(0, len(customPaths.getSets())):
                aSet = customPaths.getSet(index)

                listItem = xbmcgui.ListItem(aSet['name'], utils.getString(30121) + ': ' + aSet['set']['root'])
                listItem.setArt({'icon': os.path.join(utils.addon_dir(), 'resources', 'images', 'folder-icon.png')})
                options.append(listItem)

            # show the gui
            exitCondition = self.dialog.select(utils.getString(30125), options, useDetails=True)

            if(exitCondition >= 0):
                if(exitCondition == 0):
                    newSet = self.createSet()

                    # check that the name is unique
                    if(customPaths.validateSetName(newSet['name'])):
                        customPaths.addSet(newSet)
                    else:
                        self.dialog.ok(utils.getString(30117), utils.getString(30138), newSet['name'])
                else:
                    # bring up a context menu
                    menuOption = self.dialog.contextmenu([utils.getString(30122), utils.getString(30123)])

                    if(menuOption == 0):
                        # get the set
                        aSet = customPaths.getSet(exitCondition - 1)

                        # edit the set
                        updatedSet = self.editSet(aSet['name'], aSet['set'])

                        # save it
                        customPaths.updateSet(aSet['name'], updatedSet)

                    elif(menuOption == 1):
                        if(self.dialog.yesno(heading=utils.getString(30127), message=utils.getString(30128))):
                            # delete this path - subtract one because of "add" item
                            customPaths.deleteSet(exitCondition - 1)

    def copySimpleConfig(self):
        # disclaimer in case the user hit this on accident
        shouldContinue = self.dialog.yesno(heading=utils.getString(30139), message=utils.getString(30140) + "\n" + utils.getString(30141))

        if(shouldContinue):
            source = xbmcvfs.translatePath(os.path.join(utils.addon_dir(), 'resources', 'data', 'default_files.json'))
            dest = xbmcvfs.translatePath(os.path.join(utils.data_dir(), 'custom_paths.json'))

            xbmcvfs.copy(source, dest)

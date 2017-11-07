import xbmcgui
import resources.lib.utils as utils
from resources.lib.cronclasses import CronSchedule, CustomPathFile
dialog = xbmcgui.Dialog()

#show the disclaimer - do this every time
dialog.ok(utils.getString(30031),"",utils.getString(30032),utils.getString(30033))

def selectPath():
    path = {'expression':'0 */2 * * *'}
    
    #select path to scan
    path['path'] = dialog.browse(0,utils.getString(30023),'video')

    #create expression
    path['expression'] = dialog.input(utils.getString(30056),path['expression'])
    
    return path

def showMainScreen():
    exitCondition = ""
    customPaths = CustomPathFile()
    
    while(exitCondition != -1):
        #load the custom paths
        options = ['Add']
        
        for aPath in customPaths.getPaths():
            options.append(aPath['path'] + ' - ' + aPath['expression'])
            
        #show the gui
        exitCondition = dialog.select(utils.getString(30020),options)
        
        if(exitCondition >= 0):
            if(exitCondition == 0):
                path = selectPath()

                customPaths.addPath(path)
            else:
                #delete?
                if(dialog.yesno(heading=utils.getString(30021),line1=utils.getString(30022))):
                    #delete this path - subtract one because of "add" item
                    customPaths.deletePath(exitCondition -1)
            


showMainScreen()    

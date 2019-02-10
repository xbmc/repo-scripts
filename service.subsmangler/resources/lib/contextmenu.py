# This file includes code for SubsMangler's context menu functionality

import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import common

# check if .noautosubs extension flag or 'noautosubs' file should be set or cleared
def main():
    """check if .noautosubs extension flag or 'noautosubs' file should be set or cleared
    """

    # get the path and name of file clicked onto
    filepathname = xbmc.getInfoLabel('ListItem.FileNameAndPath')
    # get the path of file clicked onto
    filepath = xbmc.getInfoLabel('ListItem.Path')

    common.Log("Context menu invoked on: " + filepathname.encode('utf-8'), xbmc.LOGINFO)

    # check if noautosubs file exists
    # do nothing if clicked item is not a real file
    protocols = ("videodb", "plugin")
    if filepathname.lower().startswith(tuple(p + '://' for p in protocols)):
        common.Log("Source not supported. Ignoring it.", xbmc.LOGINFO)
        return

    # check if clicked item is a folder
    if xbmc.getCondVisibility('ListItem.IsFolder'):
        # clicked item is a folder
        # check if folder contains noautosubs file
        if (xbmcvfs.exists(os.path.join(filepathname, "noautosubs"))):
            common.Log("'noautosubs' file exists: " + os.path.join(filepathname, "noautosubs   Opening YesNoDialog.").encode('utf-8'), xbmc.LOGDEBUG)
            YesNoDialog = xbmcgui.Dialog().yesno("Subtitles Mangler", common.__addonlang__(32107).encode('utf-8'), line2=filepathname.encode('utf-8'), line3=common.__addonlang__(32104).encode('utf-8'), nolabel=common.__addonlang__(32042).encode('utf-8'), yeslabel=common.__addonlang__(32043).encode('utf-8'))
            # answering Yes deletes the file
            if YesNoDialog:
                common.Log("Answer is Yes. Deleting file: " + os.path.join(filepathname, "noautosubs").encode('utf-8'), xbmc.LOGDEBUG)
                # delete noautosubs file
                common.DeleteFile(os.path.join(filepathname, "noautosubs"))
            else:
                common.Log("Answer is No. Doing nothing.", xbmc.LOGDEBUG)

        else:
            common.Log("'noautosubs' file does not exist in: " + filepathname.encode('utf-8') + "   Opening YesNoDialog.", xbmc.LOGDEBUG)
            YesNoDialog = xbmcgui.Dialog().yesno("Subtitles Mangler", common.__addonlang__(32108).encode('utf-8'), line2=filepathname.encode('utf-8'), line3=common.__addonlang__(32106).encode('utf-8'), nolabel=common.__addonlang__(32042).encode('utf-8'), yeslabel=common.__addonlang__(32043).encode('utf-8'))
            # answering Yes creates the file
            if YesNoDialog:
                common.Log("Answer is Yes. Creating file: " + os.path.join(filepathname, "noautosubs").encode('utf-8'), xbmc.LOGDEBUG)
                # create .noautosubs file
                common.CreateNoAutoSubsFile(os.path.join(filepathname, "noautosubs"))
            else:
                common.Log("Answer is No. Doing nothing.", xbmc.LOGDEBUG)

    else:
        # clicked item is a file
        # check if folder contains .noautosubs file
        if (xbmcvfs.exists(os.path.join(filepath, "noautosubs"))):
            common.Log("'noautosubs' file exists: " + os.path.join(filepath, "noautosubs   Opening Ok dialog.").encode('utf-8'), xbmc.LOGDEBUG)
            xbmcgui.Dialog().ok("Subtitles Mangler", common.__addonlang__(32101).encode('utf-8'), line2=filepath.encode('utf-8'), line3=common.__addonlang__(32102).encode('utf-8'))
        else:
            common.Log("'noautosubs' file does not exist in: " + filepath.encode('utf-8'), xbmc.LOGDEBUG)
            # check if .noautosubs extension exists
            filebase, _fileext = os.path.splitext(filepathname)
            if (xbmcvfs.exists(filebase + ".noautosubs")):
                # extension flag is set for this file
                common.Log("'.noautosubs' file exists: " + filebase.encode('utf-8') + ".noautosubs   Opening YesNoDialog.", xbmc.LOGDEBUG)
                YesNoDialog = xbmcgui.Dialog().yesno("Subtitles Mangler", common.__addonlang__(32103).encode('utf-8'), line2=filepathname.encode('utf-8'), line3=common.__addonlang__(32104).encode('utf-8'), nolabel=common.__addonlang__(32042).encode('utf-8'), yeslabel=common.__addonlang__(32043).encode('utf-8'))
                # answering Yes clears the flag
                if YesNoDialog:
                    common.Log("Answer is Yes. Deleting file: " + filebase.encode('utf-8') + ".noautosubs", xbmc.LOGDEBUG)
                    # delete .noautosubs file
                    common.DeleteFile(filebase + ".noautosubs")
                else:
                    common.Log("Answer is No. Doing nothing.", xbmc.LOGDEBUG)

            else:
                # extension flag is not set for this file
                common.Log("'.noautosubs' file does not exist. Opening YesNoDialog.", xbmc.LOGDEBUG)
                YesNoDialog = xbmcgui.Dialog().yesno("Subtitles Mangler", common.__addonlang__(32105).encode('utf-8'), line2=filepathname.encode('utf-8'), line3=common.__addonlang__(32106).encode('utf-8'), nolabel=common.__addonlang__(32042).encode('utf-8'), yeslabel=common.__addonlang__(32043).encode('utf-8'))
                # answering Yes sets the flag
                if YesNoDialog:
                    common.Log("Answer is Yes. Creating file: " + filebase.encode('utf-8') + ".noautosubs", xbmc.LOGDEBUG)
                    # create .noautosubs file
                    common.CreateNoAutoSubsFile(filebase + ".noautosubs")
                else:
                    common.Log("Answer is No. Doing nothing.", xbmc.LOGDEBUG)



if __name__ == '__main__':
    main()
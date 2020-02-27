# -*- coding: utf-8 -*-
from resources.lib import kodiutils
from resources.lib import kodilogging
import mimetypes
import logging
import xbmcaddon
import xbmc
import sys
import os
import xbmcgui
import re
import xbmcvfs
import time
from contextlib import closing
from xbmcvfs import File
from subtitle import Subtitle
from syncwizard import SyncWizard
import copy

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString
logger = logging.getLogger(ADDON.getAddonInfo('id'))
backupfile = None

def select_line_subtitle(subtitlefile, start, end):
    start_index_found = False
    start_index, end_index = 0, 0
    if start:
        for index, line in enumerate(subtitlefile):
            if len(line) == 30 or len(line) == 31:
                if line[0] == "0" and line[17] == "0":
                    start_index = index - 1
                    start_index_found = True
            if start_index_found:
                if len(line) == 1 and line[0] == "\n":
                    end_index = index
                    break
                if len(line) == 2 and line[-1] == "\n" and line[0] == "\r":
                    end_index = index
                    break
        return start_index, end_index
    if end:
        for x in range(len(subtitlefile)-1,-1, -1):
            if len(subtitlefile[x]) == 30 or len(subtitlefile[x]) == 31:
                if subtitlefile[x][0] == "0" and subtitlefile[x][17] == "0":
                    start_index = x - 1
                    break
        end_index = len(subtitlefile)
    return start_index, end_index

def verify_timestring(timestring):
    try:
        h, m, se, ms = int(timestring[:2]), int(timestring[3:5]), int(timestring[6:8]), int(timestring[9:12])
        return True
    except:
        return False

def check_integrity(subtitlefile):
    whitelines = []
    for index in range(len(subtitlefile)):
        line = subtitlefile[index]
        if len(line) == 2 and line[-1] == "\n" and line[0] == "\r":
            whitelines.append(index)
    for x in range(len(whitelines)-1, -1, -1):
        if whitelines[x-1]+1 == whitelines[x]:
            del subtitlefile[whitelines[x]]
    subtitlefile.append("\n")
    subtitlefile.append("\n")
    problems = []
    lastposition = 0
    checker = re.compile("\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d")
    for index, line in enumerate(subtitlefile):
        if len(line) == 2 and line[-1] == "\n" and line[0] == "\r":
            flag = False
            for x in range(index, lastposition, -1):
                if checker.match(subtitlefile[x]):
                    flag = True
                    break
            if not flag:
                problems += [x for x in range(lastposition+1, index+1)]
            if not subtitlefile[x-1].strip().isdigit():
                problems.append(x-1)
                print(x-1)
            lastposition = index
    return subtitlefile, problems

def search_subtitles(subtitlefile, filename):
    searchstring = xbmcgui.Dialog().input(_(32023))
    dialog = xbmcgui.Dialog()
    results = []
    for index, lines in enumerate(subtitlefile):
        if searchstring in lines:
            results += [index-3, index-2, index-1, index, index+1]
    structured_results = [str(_(33032)) + str(x).zfill(4) + " | "
                                + subtitlefile[x] for x in sorted(set(results))]
    xbmcgui.Dialog().select(_(32011), structured_results)
    show_dialog(subtitlefile, filename)

def editing_menu(subtitlefile, filename):
    # Edit, DeleteFirst, DeleteLast, ManuallyScroll, Back
    secondmenuchoice = xbmcgui.Dialog().contextmenu(
                        [_(32001), _(32002), _(32003), _(32004), _(32005)])
    if secondmenuchoice == 0:
        subtitlefile = edit_specific_subtitle(subtitlefile, filename)
        editing_menu(subtitlefile, filename)
    if secondmenuchoice == 1:
        subtitlefile = delete_first_subtitle(subtitlefile)
        editing_menu(subtitlefile, filename)
    if secondmenuchoice == 2:
        subtitlefile = delete_last_subtitle(subtitlefile)
        editing_menu(subtitlefile, filename)
    if secondmenuchoice == 3:
        subtitlefile = manually_delete_subtitle(subtitlefile)
        editing_menu(subtitlefile, filename)
    if secondmenuchoice == 4:
        show_dialog(subtitlefile, filename)

def edit_specific_subtitle(subtitlefile, filename):
    line_index = xbmcgui.Dialog().select(_(32007), subtitlefile)
    if line_index == -1:
        editing_menu(subtitlefile, filename)
    #Edit line
    d = xbmcgui.Dialog().input(_(32001), defaultt=subtitlefile[line_index])
    subtitlefile[line_index] = d
    return subtitlefile

def delete_first_subtitle(subtitlefile):
    start_index, end_index = select_line_subtitle(subtitlefile, True, False)
    first_sub = "".join(subtitlefile[start_index:end_index])
    #Delete this subtitle?, Return, Delete
    ret = xbmcgui.Dialog().yesno(_(32006), first_sub,
                                  nolabel= _(32008), yeslabel= _(32009))
    if ret:
        del subtitlefile[start_index:end_index]
        return subtitlefile
    else:
        return subtitlefile

def delete_last_subtitle(subtitlefile):
    start_index, end_index = select_line_subtitle(subtitlefile, False, True)
    last_sub = "".join(subtitlefile[start_index:end_index])
    #Delete this subtitle?, Return, Delete
    ret = xbmcgui.Dialog().yesno(_(32006), last_sub,
                                  nolabel= _(32008), yeslabel= _(32009))
    if ret:
        del subtitlefile[start_index:end_index]
        return subtitlefile
    else:
        return subtitlefile

def manually_delete_subtitle(subtitlefile):
    #All Subtitles
    to_be_deleted = xbmcgui.Dialog().multiselect(_(32010), subtitlefile)
    if to_be_deleted:
        for index in to_be_deleted[::-1]:
            del subtitlefile[index]
    return subtitlefile

def decimal_timeline(timestring):
    decimal_timestring = (3600000 * int(timestring[:2]) + 60000
                    * int(timestring[3:5]) + 1000 * int(timestring[6:8]) + int(timestring[9:12]))
    return decimal_timestring

def create_new_factor2(new_start_timestring, new_end_timestring, old_starting_time="", old_ending_time=""):
    new_start_time = decimal_timeline(new_start_timestring)
    new_ending_value = decimal_timeline(new_end_timestring)
    old_factor = float(old_ending_time - old_starting_time)
    new_factor = float(new_ending_value - new_start_time)
    factor = new_factor / old_factor
    correction = old_starting_time * factor - old_starting_time
    return factor, correction

def check_timecode(subtitlefile, sync_subtitlefile, filename, moment):
    if subtitlefile:
        checked_subtitlefile = subtitlefile
    else:
        checked_subtitlefile = sync_subtitlefile
    needed_line = xbmcgui.Dialog().select(moment, checked_subtitlefile)
    if needed_line == -1:
        show_dialog(subtitlefile, filename)
    if verify_timestring(checked_subtitlefile[needed_line][:12]):
        needed_line_index = checked_subtitlefile[needed_line]
        return needed_line_index[:12], checked_subtitlefile[needed_line+1]
    else:
        xbmcgui.Dialog().ok(_(32091), _(32092))
        return check_timecode(subtitlefile, sync_subtitlefile, filename, moment)

def synchronize_with_other_subtitle(subtitlefile, filename, fail=False):
    if not fail:
        #Sublissimo, Long sync disclaimer, OK, _(32013)
        resp = xbmcgui.Dialog().yesno(_(31001), _(33000),
                        yeslabel=_(32012), nolabel= _(32013))
        if not resp:
            xbmcgui.Dialog().textviewer(_(32057), _(32058))
    #Select file to sync with
    sync_filename = xbmcgui.Dialog().browse(1, _(32015), 'video')
    if sync_filename == "":
        show_dialog(subtitlefile, filename)
    if sync_filename[-3:] != "srt":
        #Error, select .srt
        xbmcgui.Dialog().ok(_(32014), _(32016))
        synchronize_with_other_subtitle(subtitlefile, filename, True)
    try:
        syncf = xbmcvfs.File(sync_filename)
        syncflines = syncf.read().split("\n")
        sync_subtitlefile = [sentence+"\n" for sentence in syncflines]
    except:
        #Error, file not found
        xbmcgui.Dialog().ok(_(32014), _(32059))
        show_dialog(subtitlefile, filename)

    starting_line, start_textline  = check_timecode(None, sync_subtitlefile, filename, _(32063))
    xbmcgui.Dialog().ok( _(33065), starting_line + "\n" + start_textline)
    starting_line2, start_textline2  = check_timecode(subtitlefile, None, filename, _(32065))
    xbmcgui.Dialog().ok( _(33065), starting_line2 + "\n" + start_textline2)
    ending_line, end_textline = check_timecode(None, sync_subtitlefile, filename, _(32066))
    xbmcgui.Dialog().ok( _(33065), ending_line + "\n" + end_textline)
    ending_line2, end_textline2 = check_timecode(subtitlefile, None, filename, _(32067))
    xbmcgui.Dialog().ok( _(33065), ending_line2 + "\n" + end_textline2)

    old_starting_time = decimal_timeline(starting_line2)
    old_ending_time = decimal_timeline(ending_line2)
    new_starting_time = decimal_timeline(starting_line)
    movement = new_starting_time - old_starting_time

    factor, correction = create_new_factor2(starting_line[:12], ending_line[:12],
                                            old_starting_time, old_ending_time)
    current_sub2 = Subtitle(subtitlefile)
    subtitlefile3 = current_sub2.create_new_times(False, factor, correction)
    current_sub = Subtitle(subtitlefile3)
    subtitlefile2 = current_sub.move_subtitles(starting_line[:12], old_starting_time, old_ending_time)
    if subtitlefile2:
        #Succes, subs succes synced
        xbmcgui.Dialog().ok(_(32017), _(32050))
    return subtitlefile2

def move_subtitle(subtitlefile, filename, menuchoice=""):
    if not menuchoice:
        #move forwards, move backwards, give new time, back
        menuchoice = xbmcgui.Dialog().contextmenu([_(32051), _(32052), _(32053),_(32005)])
    if menuchoice == 0:
        try:
            #Move forwards by:
            timestring = xbmcgui.Dialog().input(_(32054))
            movement = decimal_timeline(timestring)
            current_moving_sub = Subtitle(subtitlefile)
            subtitlefile = current_moving_sub.create_new_times(movement, None, None)
            # Succes, subs moved forward by
            xbmcgui.Dialog().ok(_(32017), _(32070).format(timestring))
            show_dialog(subtitlefile, filename)
        except:
            # error, valid timecode
            xbmcgui.Dialog().ok(_(32014), _(32056))
            move_subtitle(subtitlefile, filename)
    if menuchoice == 1:
        try:
            # Move backwards by:
            timestring = xbmcgui.Dialog().input(_(32055))
            movement = decimal_timeline(timestring)
            current_moving_sub1 = Subtitle(subtitlefile)
            subtitlefile = current_moving_sub1.create_new_times(movement*-1, None, None)
            #Succes, subs moved back by
            xbmcgui.Dialog().ok(_(32017), _(32071).format(timestring))
            show_dialog(subtitlefile, filename)
        except:
            #error, valid timecode
            xbmcgui.Dialog().ok(_(32014), _(32056))
            move_subtitle(subtitlefile, filename)
    if menuchoice == 2:
        current_start_sub = Subtitle(subtitlefile)
        # timecode, write new timecode, for example
        xbmcgui.Dialog().ok(_(32068), _(32069))
        timestring = xbmcgui.Dialog().input(_(32029))
        subtitlefile = current_start_sub.move_subtitles(timestring)
        #Succes, First subs starts at
        xbmcgui.Dialog().ok(_(32017), _(32072).format(timestring))
        show_dialog(subtitlefile, filename)
        # except:
            # xbmcgui.Dialog().ok(_(32014), "Please enter valid timestring: HH:MM:SS:MSE")
            # move_subtitle(subtitlefile, filename)
    if menuchoice == 3 or menuchoice == -1:
        show_dialog(subtitlefile, filename)

def save_the_file(subtitlefile, filename):
    global backupfile
    #save w. edited, save current, save custom, back, exit w/o saving
    choice = xbmcgui.Dialog().contextmenu([_(32038), _(32039), _(32040),
                                           _(32005), _(32041)])
    if choice == -1 or choice == 3:
        show_dialog(subtitlefile, filename)
    if choice == 4:
        sys.exit()
    if choice == 0:
        new_file_name = filename[:-4] + "_edited.srt"
    if choice == 1:
        new_file_name = filename
    if choice == 2:
        # Give new filename
        new_file_name = xbmcgui.Dialog().input(_(32042), defaultt=filename)
    with closing(File(new_file_name, 'w')) as fo:
        fo.write("".join(subtitlefile))
    backupfile = copy.deepcopy(subtitlefile)
    if xbmcvfs.exists(new_file_name):
        # written to, to use select in kodi sub menu
        xbmcgui.Dialog().ok(_(32043), new_file_name + _(32044))
    else:
        #Error, File not written
        xbmcgui.Dialog().ok(_(32014), _(32045))
    show_dialog(subtitlefile, filename)

def exiting(subtitlefile=[], filename=""):
    global backupfile
    if backupfile != subtitlefile:
        # Warning, You might have unsaved progress, Exit anyway, Save
        ret = xbmcgui.Dialog().yesno(_(32046), _(32047),
                                      nolabel=_(32048), yeslabel=_(32049))
        if ret:
            save_the_file(subtitlefile, filename)
    sys.exit()

def stretch_subtitle(subtitlefile, filename):
    #Write new timestamp, for example
    xbmcgui.Dialog().ok(_(31001), _(32028))
    timestring = xbmcgui.Dialog().input(_(32029))
    try:
        current_sub = Subtitle(subtitlefile)
        subtitlefile = current_sub.create_new_factor(timestring)
    except:
        xbmcgui.Dialog().ok(_(31001), _(32028))
        show_dialog(subtitlefile, filename)
    # All subtitles
    xbmcgui.Dialog().multiselect(_(32010), subtitlefile)
    show_dialog(subtitlefile, filename)

def make_timelines_classical(decimal):
    hours = int(decimal / 3600000)
    restminutes = decimal % 3600000
    minutes = int(restminutes / 60000)
    restseconds = restminutes % 60000
    seconds = int(restseconds / 1000)
    milliseconds = int(restseconds % 1000)
    output = (str(hours).zfill(2) + ":" + str(minutes).zfill(2) + ":" +
              str(seconds).zfill(2) + "," + str(milliseconds).zfill(3))
    return output

def tryout(starting_time, ending_time, subtitlefile, filename):
    start = make_timelines_classical(starting_time*1000)
    end = make_timelines_classical(ending_time*1000)
    current_start_sub = Subtitle(subtitlefile)
    subtitlefile2 = current_start_sub.move_subtitles(start)
    # line_index = xbmcgui.Dialog().select("Result", subtitlefile2)
    current_sub = Subtitle(subtitlefile2)
    subtitlefile3 = current_sub.create_new_factor(end)
    # xbmcgui.Dialog().multiselect("All subtitles", subtitlefile3)
    if subtitlefile3:
        # Succes, Your subs starts at, your subs end at.
        xbmcgui.Dialog().ok(_(32017), _(32036) + start + "\n" +
                                      _(32037) + end)
    show_dialog(subtitlefile3, filename)

def retrieve_video(subtitlefile, filename):
    dirname = os.path.dirname(filename)
    location = xbmcgui.Dialog().browse(1, _(32020), 'files', '', False, False, dirname+"/")
    if location == dirname+"/":
        show_dialog(subtitlefile, filename)
    mimestart = mimetypes.guess_type(location)[0]
    if mimestart[:5] != 'video':
        xbmcgui.Dialog().ok(_(32014), _(32020))
        return retrieve_video(subtitlefile, filename)
    else:
        return location

def sync_with_video(subtitlefile, filename):
    #Name, long desc, Ok, More Info
    resp = xbmcgui.Dialog().yesno(_(31001), _(32060),
                                   yeslabel=_(32012), nolabel=_(32013))
    if not resp:
        # How to, long desc.
        xbmcgui.Dialog().textviewer(_(32061), _(32062))
    location = retrieve_video(subtitlefile, filename)
    xbmcPlayer = SyncWizard()
    xbmcPlayer.add(subtitlefile, filename)
    xbmcPlayer.play(location)
    xbmc.sleep(500)
    while xbmcPlayer.isPlaying():
        xbmc.sleep(500)

def check_integrity_menu(subtitlefile, filename):
    subtitlefile, problems = check_integrity(subtitlefile)
    if not problems:
        xbmcgui.Dialog().ok(_(32030), _(32031))
    else:
        report = []
        for x in problems:
            report += _(32032) + str(x) + " --> " + subtitlefile[int(x)]
        report = "".join(report)
        xbmcgui.Dialog().ok(_(32033), report)
    show_dialog(subtitlefile, filename)

def load_subtitle():
    global backupfile
    #Sublissimo, select sub, select sub
    xbmcgui.Dialog().ok(_(31001), _(32034))
    filename = xbmcgui.Dialog().browse(1, _(32035), 'video')
    if filename == "":
        sys.exit()
    if filename[-3:] != 'srt':
        # Error, only .srt files
        xbmcgui.Dialog().ok(_(32014), _(32026))
        sys.exit()
    try:
        f = xbmcvfs.File(filename)
        b = f.read().split("\n")
        subtitlefile = [sentence+"\n" for sentence in b]
        backupfile = copy.deepcopy(subtitlefile)
        return subtitlefile, filename
    except:
        # Error, file not found
        xbmcgui.Dialog().ok(_(32014), _(32027) + filename)
        sys.exit()

def show_dialog(subtitlefile="", filename=""):
    addon_name = ADDON.getAddonInfo('name')
    if not subtitlefile:
        subtitlefile, filename = load_subtitle()
    #Scroll, edit, move, stretch, syncwsub syncwvideo, search, check, save, quit
    options = [ _(31000), _(30001), _(31002), _(31003), _(31004), _(31005),
                _(31006), _(31007), _(31008), _(31009)]
    menuchoice = xbmcgui.Dialog().contextmenu(options)
    if menuchoice == 0:
        xbmcgui.Dialog().multiselect(_(32010), subtitlefile)
        show_dialog(subtitlefile, filename)
    if menuchoice == 1:
        editing_menu(subtitlefile, filename)
    if menuchoice == 2:
        move_subtitle(subtitlefile, filename)
    if menuchoice == 3:
        stretch_subtitle(subtitlefile, filename)
    if menuchoice == 4:
        subtitlefile = synchronize_with_other_subtitle(subtitlefile, filename)
        show_dialog(subtitlefile, filename)
    if menuchoice == 5:
        sync_with_video(subtitlefile, filename)
    if menuchoice == 6:
        search_subtitles(subtitlefile, filename)
    if menuchoice == 7:
        check_integrity_menu(subtitlefile, filename)
    if menuchoice == 8:
        save_the_file(subtitlefile, filename)
    if menuchoice == 9 or menuchoice == -1 :
        exiting(subtitlefile, filename)

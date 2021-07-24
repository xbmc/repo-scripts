# -*- coding: utf-8 -*-
import mimetypes
import logging
import xbmcaddon
import xbmcplugin
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
from sync_by_frame_rate import SyncWizardFrameRate
from play_along_file import PlayAlongFile
import copy

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString
logger = logging.getLogger(ADDON.getAddonInfo('id'))
backupfile = None
videodbfilename = None
videofilename = None
player_instances = []


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
            area = [x for x in [index-3, index-2, index-1, index, index+1] if x > 0 and x < len(subtitlefile)]
            results += area
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
    if secondmenuchoice == 4 or secondmenuchoice == -1:
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

def decimal_timeline_with_checker(timestring):
    try:
        decimal_timestring = (3600000 * int(timestring[:2]) + 60000
                    * int(timestring[3:5]) + 1000 * int(timestring[6:8]) + int(timestring[9:12]))
        return decimal_timestring
    except:
        return False

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
        syncf.close()
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
    current_sub2 = Subtitle(subtitlefile, filename)
    subtitlefile3 = current_sub2.create_new_times(False, factor, correction)
    current_sub = Subtitle(subtitlefile3, filename)
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
        #Move forwards by:
        timestring = xbmcgui.Dialog().input(_(32054))
        movement = decimal_timeline_with_checker(timestring)
        if movement:
            current_moving_sub = Subtitle(subtitlefile, filename)
            subtitlefile = current_moving_sub.create_new_times(movement, None, None)
            # Succes, subs moved forward by
            xbmcgui.Dialog().ok(_(32017), _(32070).format(timestring))
            show_dialog(subtitlefile, filename)
        else:
            # error, valid timecode
            xbmcgui.Dialog().ok(_(32014), _(32056))
            move_subtitle(subtitlefile, filename)
    if menuchoice == 1:
        # Move backwards by:
        timestring = xbmcgui.Dialog().input(_(32055))
        movement = decimal_timeline_with_checker(timestring)
        if movement:
            current_moving_sub1 = Subtitle(subtitlefile, filename)
            subtitlefile = current_moving_sub1.create_new_times(movement*-1, None, None)
            #Succes, subs moved back by
            xbmcgui.Dialog().ok(_(32017), _(32071).format(timestring))
            show_dialog(subtitlefile, filename)
        else:
            #error, valid timecode
            xbmcgui.Dialog().ok(_(32014), _(32056))
            move_subtitle(subtitlefile, filename)
    if menuchoice == 2:
        current_start_sub = Subtitle(subtitlefile, filename)
        # timecode, write new timecode, for example
        xbmcgui.Dialog().ok(_(32068), _(32069))
        timestring = xbmcgui.Dialog().input(_(32029))
        movement = decimal_timeline_with_checker(timestring)
        if movement:
            subtitlefile = current_start_sub.move_subtitles(timestring)
            #Succes, First subs starts at
            xbmcgui.Dialog().ok(_(32017), _(32072).format(timestring))
            show_dialog(subtitlefile, filename)
        else:
            xbmcgui.Dialog().ok(_(32014), _(32056))
            move_subtitle(subtitlefile, filename)
    if menuchoice == 3 or menuchoice == -1:
        show_dialog(subtitlefile, filename)

def save_the_file(subtitlefile, filename, playing=False):
    global backupfile
    #save w. edited, save current, save custom, back, exit w/o saving
    choice = xbmcgui.Dialog().contextmenu([_(32038), _(32039), _(32040),
                                           _(32005), _(32041)])
    if choice == -1 or choice == 3:
        show_dialog(subtitlefile, filename)
    if choice == 4:
        check_player_instances()
        sys.exit()
    if choice == 0:
        new_file_name = filename[:-4] + "_edited.srt"
    if choice == 1:
        new_file_name = filename[:-4] + ".srt"
    if choice == 2:
        # Give new filename
        new_file_name = xbmcgui.Dialog().input(_(32042), defaultt=filename[:-4] + ".srt")
    with closing(File(new_file_name, 'w')) as fo:
        fo.write("".join(subtitlefile))
    backupfile = copy.deepcopy(subtitlefile)
    if playing:
        xbmc.Player().setSubtitles(new_file_name)
        temp_file = filename[:-4] + "_temp.srt"
        if xbmcvfs.exists(temp_file):
            xbmcvfs.delete(temp_file)
        # succes, file saved to:
        xbmcgui.Dialog().ok(_(32017), _(32123) + str(new_file_name))
        xbmc.Player().pause()
        check_player_instances()
        sys.exit()
    if not playing:
        if xbmcvfs.exists(new_file_name):
            # written to, to use select in kodi sub menu
            xbmcgui.Dialog().ok(_(32043), new_file_name + _(32044))
        else:
            #Error, File not written
            xbmcgui.Dialog().ok(_(32014), _(32045))
        show_dialog(subtitlefile, filename)



def exiting(subtitlefile=[], filename=""):
    check_player_instances()
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
    movement = decimal_timeline_with_checker(timestring)
    if movement:
        current_sub = Subtitle(subtitlefile, filename)
        subtitlefile = current_sub.create_new_factor(timestring)
        xbmcgui.Dialog().ok(_(32017), _(33072).format(timestring))
        show_dialog(subtitlefile, filename)
    else:
        xbmcgui.Dialog().ok(_(32014), _(32056))
        stretch_subtitle_menu(subtitlefile, filename)

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

def sync_after_wizard(starting_time, ending_time, subtitlefile, filename):
    start = make_timelines_classical(starting_time*1000)
    end = make_timelines_classical(ending_time*1000)
    current_start_sub = Subtitle(subtitlefile, filename)
    subtitlefile2 = current_start_sub.move_subtitles(start)
    current_sub = Subtitle(subtitlefile2, filename)
    subtitlefile3 = current_sub.create_new_factor(end)
    if subtitlefile3:
        # Succes, Your subs starts at, your subs end at.
        xbmcgui.Dialog().ok(_(32017), _(32036) + start + "\n" +
                                      _(32037) + end)
    show_dialog(subtitlefile3, filename)

def retrieve_video(subtitlefile, filename):
    global videodbfilename, videofilename
    if videodbfilename == None and videofilename == None:
        choice = xbmcgui.Dialog().contextmenu([_(32093), _(32094), _(32095), _(32005)])
        if choice == 3 or choice == -1:
            show_dialog(subtitlefile, filename)
        pos_locations = ["videodb://movies/titles/", "videodb://tvshows/titles/", "videodb://"]
        location = xbmcgui.Dialog().browse(1, _(32020), 'video', '', False, False, pos_locations[choice])
        if location in pos_locations:
            show_dialog(subtitlefile, filename)
        videodbfilename = location

    else:
        if not videofilename:
            choice = xbmcgui.Dialog().contextmenu([_(32116) , _(32093), _(32094), _(32095), _(32005)])
        else:
            choice = xbmcgui.Dialog().contextmenu([_(35008) + os.path.basename(videofilename), _(32093), _(32094), _(32095), _(32005)])
        if choice == 4 or choice == -1:
            show_dialog(subtitlefile, filename)
        pos_locations = [videodbfilename, "videodb://movies/titles/", "videodb://tvshows/titles/", "videodb://"]
        if choice == 0:
            if not videofilename:
                location = videodbfilename
            else:
                location = videofilename
        else:
            location = xbmcgui.Dialog().browse(1, _(32020), 'video', '', False, False, pos_locations[choice])
        if location in pos_locations[1:]:
            show_dialog(subtitlefile, filename)
        videodbfilename = location
    return location

def sync_with_video(subtitlefile, filename):
    global player_instances
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
    player_instances.append(xbmcPlayer)
    xbmc.Monitor().waitForAbort()

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

def check_validity(subtitlefile):
    check = 0
    for line in subtitlefile:
        if len(line) == 30 or len(line) == 31:
            if line[0] == "0" and line[17] == "0":
                check += 1
    if check == 0:
        resp = xbmcgui.Dialog().yesno(_(32132), _(32132), yeslabel=_(32133), nolabel=_(32134))
        if resp:
            return True
        else:
            return False
    return True

def read_problematic_file_final(filename, backup):
    global backupfile
    xbmcgui.Dialog().ok(_(35017), _(35018))
    with closing(xbmcvfs.File(filename)) as fo:
        byte_string = bytes(fo.readBytes())
        text_string = byte_string.decode("utf-8", errors="replace")
    b = text_string.split("\n")
    subtitlefile = [sentence+"\n" for sentence in b]
    if backup:
        backupfile = copy.deepcopy(subtitlefile)
    return subtitlefile, filename

def read_problematic_file(filename, backup):
    global backupfile
    import chardet
    try:
        with closing(xbmcvfs.File(filename)) as fo:
            byte_string = bytes(fo.readBytes())
            result = chardet.detect(byte_string)
            char_set = result["encoding"]

        text_string = byte_string.decode(char_set)
        reencoded = text_string.encode("utf-8")
        lines = reencoded.split("\n")
        subtitlefile = [sentence+"\n" for sentence in lines]
        if backup:
            backupfile = copy.deepcopy(subtitlefile)
        xbmcgui.Dialog().multiselect(_(32010), subtitlefile)
        return subtitlefile, filename
    except:
        subtitlefile, filename = read_problematic_file_final(filename, backup)
        return subtitlefile, filename

def read_subtitle(filename, backup):
    global backupfile
    try:
        with closing(xbmcvfs.File(filename)) as fo:
            byte_string = bytes(fo.readBytes())
            text_string = byte_string.decode("utf-8")
            reencoded = text_string.encode("utf-8")
            lines = reencoded.split("\n")
            subtitlefile = [sentence+"\n" for sentence in lines]
            if backup:
                backupfile = copy.deepcopy(subtitlefile)

        return subtitlefile, filename
    except UnicodeDecodeError:
        subtitlefile, filename = read_problematic_file(filename, backup)
        return subtitlefile, filename
    except:
        # Error, file not found
        xbmcgui.Dialog().ok(_(32014), _(32027) + filename)
        sys.exit()

def load_subtitle(with_warning, filename=""):
    global backupfile
    #Sublissimo, select sub, select sub
    if with_warning:
        xbmcgui.Dialog().ok(_(31001), _(32034))
    if not filename:
        filename = xbmcgui.Dialog().browse(1, _(32035), 'video', ".srt|.sub")
    if filename == "":
        sys.exit()
    if filename[-3:] == 'sub':
        load_sub_subtitlefile(filename)
    if filename[-3:] != 'srt':
        # Error, only .srt files
        xbmcgui.Dialog().ok(_(32014), _(32026))
        load_subtitle(False)
    # try:
    subtitlefile, filename = read_subtitle(filename, True)
    if check_validity(subtitlefile):
        return subtitlefile, filename
    else:
        return load_subtitle(False)
    # except:
    #     # Error, file not found
    #     xbmcgui.Dialog().ok(_(32014), _(32027) + filename)
    #     sys.exit()

def synchronize_by_frame_rate(subtitlefile, filename):
    global player_instances
    location = retrieve_video(subtitlefile, filename)
    newplayer = SyncWizardFrameRate()
    newplayer.add(subtitlefile, filename)
    newplayer.play(location)
    newplayer.give_frame_rate(False)
    player_instances.append(newplayer)
    xbmc.Monitor().waitForAbort()

def play_along_file(subtitlefile, filename):
    global player_instances
    location = retrieve_video(subtitlefile, filename)
    play_along_file_player = PlayAlongFile()
    play_along_file_player.add(subtitlefile, filename)
    play_along_file_player.play(location)
    xbmc.sleep(500)
    play_along_file_player.activate_sub()
    player_instances.append(play_along_file_player)
    xbmc.Monitor().waitForAbort()

def stretch_by_providing_factor(subtitlefile, filename):
    try:
        # Provide Factor
        response = xbmcgui.Dialog().input(_(32117))
        new_factor = float(response)
    except:
        return stretch_by_providing_factor(subtitlefile, filename)
    cur_sub = Subtitle(subtitlefile, filename)
    old_starting_time, old_ending_time = cur_sub.make_timelines_decimal()
    new_timestamp = make_timelines_classical(new_factor * old_ending_time)
    start_timestamp = make_timelines_classical(old_starting_time)
    old_timestamp = make_timelines_classical(old_ending_time)
    # New Ending, Starting time, Old ending time, New Ending time, Ok, Return
    xbmcgui.Dialog().yesno(_(32107), _(34108) + str(start_timestamp) + "\n" +
                                  _(32109) + str(old_timestamp) + "\n" +
                                  _(32110) + str(new_timestamp) + "\n", yeslabel=_(32012), nolabel= _(32008))
    new_subtitlefile = cur_sub.create_new_factor(new_timestamp, old_starting_time, old_ending_time)
    show_dialog(new_subtitlefile, filename)




def stretch_subtitle_menu(subtitlefile, filename):
    # Synchronize by frame rate, Stretch by giving new end time, Stretch by providing factor, Back
    menuchoice = xbmcgui.Dialog().contextmenu([_(32119), _(32118), _(32005)])
    if menuchoice == 0:
        stretch_subtitle(subtitlefile, filename)
    if menuchoice == 1:
        stretch_by_providing_factor(subtitlefile, filename)
    if menuchoice == 2 or menuchoice == -1:
        show_dialog(subtitlefile, filename)

def check_valid_hexadecimal(hex_input):
    if len(hex_input) != 8:
        return False
    letters = ["A", "B", "C", "D", "E", "F"]
    for char in hex_input:
        if not char.isdigit():
            if char not in letters:
                return False
    return True

def filter_out_color(subtitlefile, filename, color_code=""):
    if not color_code:
        color_code = xbmcgui.Dialog().input(_(32141))
        if not color_code:
            advanced_options(subtitlefile, filename)
        if not check_valid_hexadecimal(color_code):
            xbmcgui.Dialog().ok(_(32014), _(32140))
            filter_out_color(subtitlefile, filename)
    new_subtitlefile = []
    for line in subtitlefile:
        if "<font color" in line:
            starts = [m.start() + len('<font color="#') for m in re.finditer('<font color="#', line)]
            ends = [m.start() for m in re.finditer('">', line)]
            for start, end in zip(starts, ends):
                line = line[:start] + color_code + line[end:]
            new_subtitlefile.append(line)
        else:
            new_subtitlefile.append(line)
    if color_code == "FFFFFFFF":
        xbmcgui.Dialog().ok(_(32017), _(32137))
    else:
        xbmcgui.Dialog().ok(_(32017), _(32142) + "#" + color_code)
    show_dialog(new_subtitlefile, filename)

def advanced_options(subtitlefile, filename):
    # Search, Check integrity, Back
    menuchoice = xbmcgui.Dialog().contextmenu([_(32138), _(32139), _(31006), _(31007), _(32005)])
    if menuchoice == 0:
        filter_out_color(subtitlefile, filename, "FFFFFFFF")
    if menuchoice == 1:
        filter_out_color(subtitlefile, filename)
    if menuchoice == 2:
        search_subtitles(subtitlefile, filename)
    if menuchoice == 3:
        check_integrity_menu(subtitlefile, filename)
    if menuchoice == 4 or menuchoice == -1:
        show_dialog(subtitlefile, filename)

# --------------------- SUB FILES-----------------------

def search_frame_rate(subtitlefile, filename):
    class SearchFrameRate(xbmc.Player):
        def __init__ (self):
            xbmc.Player.__init__(self)

        def get_frame_rate(self):
            self.frame_rate = xbmc.getInfoLabel('Player.Process(VideoFPS)')
            self.stop()
            return float(self.frame_rate)

    location = retrieve_video(subtitlefile, filename)
    newplayer = SearchFrameRate()
    newplayer.play(location)
    xbmc.sleep(500)
    frame_rate = newplayer.get_frame_rate()
    response = xbmcgui.Dialog().yesno(_(32106), _(32120) + str(frame_rate), yeslabel=_(32089), nolabel=_(32126))
    if response:
        create_new_sub(subtitlefile, filename, frame_rate)
    else:
        load_sub_subtitlefile(filename)
    xbmc.Monitor().waitForAbort()

def recreate_line(line, frame_rate, line_number):
    startline_index = line.find("{")
    midline_index = line.find("}{")
    endline_index = line.find("}", midline_index+1)
    start_time = line[startline_index+1:midline_index]
    end_time = line[midline_index+2:endline_index]
    srt_starttime = make_timelines_classical(int(start_time)/frame_rate*1000)
    srt_endtime = make_timelines_classical(int(end_time)/frame_rate*1000)
    txtlines = line[endline_index+1:len(line)].split("|")
    block = [str(line_number)] + [srt_starttime + " --> " + srt_endtime] + txtlines + [""]
    return [sentence+"\n" for sentence in block]

def load_sub_subtitlefile(filename="", subtitlefile=[]):
    if not subtitlefile:
        subtitlefile, not_important = read_subtitle(filename, False)
    check = 0
    for line in subtitlefile:
        if line[0] == "{" and "}{" in line:
            check += 1
    if check == 0:
        xbmcgui.Dialog().ok(_(32135), _(32136))
        show_dialog()
    options = ["23.976", "24", "25", "29.976", "30", _(32127), _(32104), _(32129)]
    menuchoice = xbmcgui.Dialog().select(_(32105), options)
    if menuchoice == 5:
        try:
            frame_rate = float(xbmcgui.Dialog().input(_(32127)))
            create_new_sub(subtitlefile, filename, frame_rate)
        except:
            load_sub_subtitlefile(filename, subtitlefile)
    if menuchoice == 6:
        search_frame_rate(subtitlefile, filename)
    if menuchoice == 7:
        response = xbmcgui.Dialog().yesno(_(32130), _(32131), yeslabel=_(32012), nolabel=_(32128))
        if response:
            load_sub_subtitlefile(filename, subtitlefile)
        else:
            load_subtitle(False)
    else:
        try:
            frame_rate = float(options[menuchoice])
        except:
            pass
        create_new_sub(subtitlefile, filename, frame_rate)

def create_new_sub(subtitlefile, filename, frame_rate):
    new_subtitlefile = []
    for line_number, line in enumerate(subtitlefile):
        if line.find("}{") != -1:
            new_subtitlefile += recreate_line(line, frame_rate, line_number+1)
    #xbmcgui.Dialog().multiselect("Sync was succesfull:", new_subtitlefile)
    if new_subtitlefile:
        show_dialog(new_subtitlefile, filename)
    else:
        xbmcgui.Dialog().ok(_(32014), _(32014))
        show_dialog()

# -------------END OF SUB FILES ---------------

def error_handling(subtitlefile, filename, error):
    # "Error", "The following error has occurred", "Return to Menu", "More Info"
    response = xbmcgui.Dialog().yesno(_(32014), _(35012) + "\n" + str(type(error))
                                                         + "\n" + str(error.args),
                                                         yeslabel=_(35011),
                                                         nolabel=_(32013))
    if response:
        show_dialog(subtitlefile, filename)
    else:
        xbmcgui.Dialog().textviewer(_(35013), _(35016))
        show_dialog(subtitlefile, filename)

def check_player_instances(filename=""):
    global player_instances
    if player_instances:
        for instance in player_instances:
            instance.proper_exit = True
    temp_file = filename[:-4] + "_temp.srt"
    if xbmcvfs.exists(temp_file):
        xbmcvfs.delete(temp_file)

def check_active_player():
    global videofilename
    if xbmc.Player().isPlayingVideo():
        current_subs = xbmc.Player().getAvailableSubtitleStreams()
        playingfile = xbmc.Player().getPlayingFile()
        if any(current_subs):
            active_sub_lang = xbmc.Player().getSubtitles()
            lang = xbmc.convertLanguage(active_sub_lang, xbmc.ISO_639_1)

            if not lang:
                filename = os.path.splitext(playingfile)[0] + ".srt"
            else:
                filename = os.path.splitext(playingfile)[0] + "." + lang + ".srt"
            if xbmcvfs.exists(filename):
                subtitlefile, filename = load_subtitle(False, filename)
                videofilename = playingfile
                if len(os.path.basename(playingfile)) < 50:
                    playbase = os.path.basename(playingfile)
                    subbase = os.path.basename(filename)
                else:
                    playbase = os.path.basename(playingfile)[:35] + "(...)" + os.path.basename(playingfile)[-10:]
                    subbase = os.path.basename(filename)[:35] + "(...)" + os.path.basename(filename)[-10:]
                result = xbmcgui.Dialog().yesno(_(31001), _(35003) + "\n"
                                + _(35006).ljust(11) + playbase + "\n"
                                + _(35007).ljust(11) + subbase
                                + "\n" + _(35004),
                                yeslabel=_(35000),
                                nolabel=_(35001))
                if not result:
                    xbmc.Player().stop()
                    show_dialog(subtitlefile, filename)
                else:
                    sys.exit()
        res = xbmcgui.Dialog().yesno(_(31001), _(35005) + "\n" + _(35004),
                            nolabel=_(35000), yeslabel=_(35002))
        if not res:
            sys.exit()
        playing_dir = os.path.dirname(playingfile) + "/"
        filename = xbmcgui.Dialog().browse(1, _(32035), 'files', ".srt|.sub", False, False, playing_dir)
        if filename == playing_dir:
            sys.exit()
        videofilename = playingfile
        subtitlefile, filename = load_subtitle(False, filename)
        xbmc.Player().stop()
        show_dialog(subtitlefile, filename)

    show_dialog()

def show_dialog(subtitlefile="", filename=""):
    if not subtitlefile:
        subtitlefile, filename = load_subtitle(True)
    check_player_instances(filename)
    #Scroll, edit, move, stretch, syncwsub, syncwvideo, playalong, advanced, save, quit
    options = [_(31000), _(30001), _(31002), _(31003), _(31004), _(31005),
               _(31010), _(31011), _(31013), _(31008), _(31009)]
    menuchoice = xbmcgui.Dialog().contextmenu(options)
    if menuchoice == 0:
        xbmcgui.Dialog().multiselect(_(32010), subtitlefile)
        show_dialog(subtitlefile, filename)
    if menuchoice == 1:
        editing_menu(subtitlefile, filename)
    if menuchoice == 2:
        move_subtitle(subtitlefile, filename)
    if menuchoice == 3:
        stretch_subtitle_menu(subtitlefile, filename)
    if menuchoice == 4:
        subtitlefile = synchronize_with_other_subtitle(subtitlefile, filename)
        show_dialog(subtitlefile, filename)
    if menuchoice == 5:
        sync_with_video(subtitlefile, filename)
    if menuchoice == 6:
        synchronize_by_frame_rate(subtitlefile, filename)
    if menuchoice == 7:
        play_along_file(subtitlefile, filename)
    if menuchoice == 8:
        advanced_options(subtitlefile, filename)
    if menuchoice == 9:
        save_the_file(subtitlefile, filename)
    if menuchoice == 10 or menuchoice == -1 :
        exiting(subtitlefile, filename)

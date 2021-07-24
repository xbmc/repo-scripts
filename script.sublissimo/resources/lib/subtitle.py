# -*- coding: utf-8 -*-
import script

class Subtitle(object):
    def __init__(self, subtitlefile, filename):
        self.subtitlefile = subtitlefile
        self.filename = filename
        self.timelines = []

    def make_timelines_decimal(self):
        for index, lines in enumerate(self.subtitlefile):
            if len(lines) == 31 or len(lines) == 30:
                if lines[0] == "0" and lines[17] == "0":
                    self.timelines.append(lines)
        try:
            starting_line = self.timelines[0]
            ending_line = self.timelines[-1]
            old_starting_time = (3600000 * int(starting_line[:2]) + 60000
                        * int(starting_line[3:5]) + 1000 * int(starting_line[6:8]) + int(starting_line[9:12]))
            old_ending_time = (3600000 * int(ending_line[:2]) + 60000
                        * int(ending_line[3:5]) + 1000 * int(ending_line[6:8]) + int(ending_line[9:12]))
            return old_starting_time, old_ending_time
        except Exception as e:
            script.error_handling(self.subtitlefile, self.filename, e)

    def rehash_time_string(self, timestring):
        hours = int(timestring[:2])
        minutes = int(timestring[3:5])
        seconds = int(timestring[6:8])
        milliseconds = int(timestring[9:12])
        return hours, minutes, seconds, milliseconds

    def create_new_factor(self, timestring, old_starting_time="", old_ending_time=""):
        if not old_starting_time:
            old_starting_time, old_ending_time = self.make_timelines_decimal()
        new_hours, new_minutes, new_seconds, new_milliseconds = self.rehash_time_string(timestring)
        old_factor = float(old_ending_time - old_starting_time)
        new_ending_value = new_hours * 3600000 + new_minutes * 60000 + new_seconds * 1000 + new_milliseconds
        new_factor = float(new_ending_value - old_starting_time)
        factor = new_factor / old_factor
        correction = old_starting_time * factor - old_starting_time
        newsubtitles = self.create_new_times(False, factor, correction)
        return newsubtitles

    def move_subtitles(self, timestring, old_starting_time="", old_ending_time=""):
        if not old_starting_time:
            old_starting_time, old_ending_time = self.make_timelines_decimal()
        new_hours, new_minutes, new_seconds, new_milliseconds = self.rehash_time_string(timestring)
        new_starting_time = new_hours * 3600000 + new_minutes * 60000 + new_seconds * 1000 + new_milliseconds
        movement = new_starting_time - old_starting_time
        newsubtitles = self.create_new_times(movement, False, False)
        return newsubtitles

    def create_new_times(self, movement, factor, correction):
        text_file = self.subtitlefile
        text_file.append("\n")
        text_file.append("\n")
        self.new_text_file = []
        for index, lines in enumerate(text_file):
            if len(lines) == 31 or len(lines) == 30:
                if lines[0] == "0" and lines[17] == "0":
                    numbers = text_file[index -1]
                    line_1 = text_file[index + 1]
                    line_2 = ""
                    if len(text_file[index + 2]) != 1:
                        line_2 = text_file[index + 2]
                    try:
                        starting_time = (3600000 * int(lines[:2]) + 60000
                            * int(lines[3:5]) + 1000 * int(lines[6:8]) + int(lines[9:12]))
                        ending_time = (3600000 * int(lines[17:19]) + 60000
                            * int(lines[20:22]) + 1000 * int(lines[23:25]) + int(lines[26:29]))
                    except Exception as e:
                        script.error_handling(self.subtitlefile, self.filename, e)
                    if not factor:
                        new_starting_time = starting_time + movement
                        new_ending_time = ending_time + movement
                    else:
                        new_starting_time = starting_time * factor - correction
                        new_ending_time = ending_time * factor - correction
                    self.new_text_file = self.write_output_to_file(new_starting_time, new_ending_time,
                        numbers, line_1, line_2)
        return self.new_text_file

    def make_timelines_classical(self, decimal):
        hours = int(decimal / 3600000)
        restminutes = decimal % 3600000
        minutes = int(restminutes / 60000)
        restseconds = restminutes % 60000
        seconds = int(restseconds / 1000)
        milliseconds = int(restseconds % 1000)
        output = (str(hours).zfill(2) + ":" + str(minutes).zfill(2) + ":" +
                  str(seconds).zfill(2) + "," + str(milliseconds).zfill(3))
        return output

    def write_output_to_file(self, new_starting_time, new_ending_time, numbers, line_1, line_2):
        self.new_text_file.append(numbers)
        output1 = self.make_timelines_classical(new_starting_time)
        output2 = self.make_timelines_classical(new_ending_time)
        self.new_text_file.append(output1 + " --> " + output2 + "\n")
        self.new_text_file.append(line_1)
        if line_2:
            self.new_text_file.append(line_2)
        self.new_text_file.append("\n")
        return self.new_text_file

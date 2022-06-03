import re
from contextlib import closing
import xbmcvfs

class Subtitle:
    def __init__(self, filename, subtitlelines, encodingfound):
        self.subtitlefile = []
        self.filename = filename
        self.subtitlelines = subtitlelines
        self.changed = False
        self.encodingfound = encodingfound
        self.videodbfilename = None
        self.skipped_lines = []
        self.videofilename = None
        self.set_times()

    def generate_problems_report(self):
        problems = []
        for index, problem in enumerate(self.skipped_lines):
            if problem and len(self.subtitlefile[index].strip()) > 2:
                problems.append(index)
        return self.encodingfound, problems

    def search_in_subtitle(self, search_string):
        founded = []
        for index, subtitleline in enumerate(self.subtitlelines):
            for textline in subtitleline.textlines:
                if search_string in textline:
                    founded.append(self.subtitlelines[index])
        return founded

    def change_html_color(self, new_color_code):
        for i, subtitleline in enumerate(self.subtitlelines):
            for j, line in enumerate(subtitleline.textlines):
                if "<font color" in line:
                    starts = [m.start() + len('<font color="#') for m in re.finditer('<font color="#', line)]
                    ends = [m.start() for m in re.finditer('">', line)]
                    for start, end in zip(starts, ends):
                        new_line = line[:start] + new_color_code + line[end:]
                        self.subtitlelines[i].textlines[j] = new_line

    def sync_chosen_lines_to_chosen_times(self, new_start=None, new_end=None, start_index=0, end_index=-1):
        currentfactor = self[end_index].startingtime - self[start_index].startingtime
        goalfactor = new_end - new_start
        factor = goalfactor / currentfactor
        correction = factor * 1 - 1
        self.stretch_subtitle(factor, correction)
        shift = new_start - self[start_index].startingtime
        self.shift_subtitle(shift)

    def sync_two_subtitles(self, other_sub, start_index=0, end_index=-1,
                                      start_index_other=0, end_index_other=-1):
        new_start = other_sub[start_index_other].startingtime
        new_end = other_sub[end_index_other].startingtime
        self.sync_chosen_lines_to_chosen_times(new_start, new_end, start_index, end_index)

    def __delitem__(self, position):
        self.changed = True
        del self.subtitlelines[position]
        self.set_times()

    def __getitem__(self, position):
        return self.subtitlelines[position]

    def __len__(self):
        return len(self.subtitlelines)

    def __iter__(self):
        self.index = -1
        return self

    def __str__(self):
        return "".join([str(line) for line in self.subtitlelines])

    def __next__(self):
        if self.index == len(self.subtitlelines)-1:
            raise StopIteration
        self.index = self.index + 1
        return str(self.subtitlelines[self.index])

    def easy_list_selector(self):
        subtitle_per_line = str(self).split("\n")
        lines = []
        for index, line in enumerate(self.subtitlelines):
            lines += len(line) * [index]
        return subtitle_per_line, lines

    def create_decimal_times(self, line):
        time = (3600000 * int(line[:2]) + 60000
            * int(line[3:5]) + 1000 * int(line[6:8]) + int(line[9:12]))
        return time

    def write_file(self, filename):
        result = "".join([str(line) for line in self.subtitlelines])
        with closing(xbmcvfs.File(filename, 'w')) as writer:
            writer.write(result)

    def write_temp_file(self):
        new_filename = self.filename[:-4] + "_temp.srt"
        result = "".join([str(line) for line in self.subtitlelines])
        with closing(xbmcvfs.File(new_filename, 'w')) as writer:
            writer.write(result)
        return new_filename

    def delete_temp_file(self):
        temp_file = self.filename[:-4] + "_temp.srt"
        if xbmcvfs.exists(temp_file):
            xbmcvfs.delete(temp_file)

    def change_text(self, index, new_text):
        self.changed = True
        self.subtitlelines[index].textlines = new_text.split("\n")

    def set_times(self):
        for index, line in enumerate(self.subtitlelines):
            self.subtitlelines[index].linenumber = index+1
        self.start = self.subtitlelines[0].startingtime
        self.end = self.subtitlelines[-1].startingtime
        self.length = self.end - self.start

    def shift_subtitle(self, milliseconds):
        self.changed = True
        for subtitleline in self.subtitlelines:
            subtitleline.startingtime += milliseconds
            subtitleline.endingtime += milliseconds
        self.set_times()

    def stretch_subtitle(self, factor, correction=0):
        self.changed = True
        for subtitleline in self.subtitlelines:
            subtitleline.startingtime *= factor
            subtitleline.startingtime -= correction
            subtitleline.endingtime *= factor
            subtitleline.endingtime -= correction
        self.set_times()

    def shift_to_new_start(self, new_starting_time_decimal):
        shift = new_starting_time_decimal - self.start
        self.shift_subtitle(shift)

    def stretch_to_new_end(self, new_ending_time_decimal):
        new_factor = float(new_ending_time_decimal - self.start)
        factor = new_factor / self.length
        correction = self.start * factor - self.start
        self.stretch_subtitle(factor, correction)

    def sync_to_times(self, new_starting_time, new_ending_time):
        new_ending_time_decimal = self.create_decimal_times(new_ending_time)
        new_starting_time_decimal = self.create_decimal_times(new_starting_time)
        self.shift_to_new_start(new_starting_time_decimal)
        self.stretch_to_new_end(new_ending_time_decimal)

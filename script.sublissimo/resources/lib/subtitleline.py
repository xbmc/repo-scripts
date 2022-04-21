from create_classical_times import create_classical_times

class SubtitleLine:
    def __init__(self):
        self.linenumber = None
        self.startingtime = None
        self.endingtime = None
        self.textlines = []

    def __len__(self):
        lines = [True for line in self.textlines if len(line) > 2]
        return len(lines) + 3

    def text(self):
        return "".join([line + "\n" if len(line) > 2 else line for line in self.textlines]).strip()

    def return_starting_time(self, factor=1):
        return create_classical_times(self.startingtime * factor)

    def __repr__(self):
        return "{0}\n{1} --> {2}\n{3}\n".format(
             self.linenumber,
             create_classical_times(self.startingtime),
             create_classical_times(self.endingtime),
             "".join([line + "\n" if len(line) > 2 else line for line in self.textlines]))

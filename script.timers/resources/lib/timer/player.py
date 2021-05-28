import xbmc


class Player(xbmc.Player):

    seektime = None

    def play(self, item):

        super().play(item)
        self.seektime = None

    def playWithSeekTime(self, item, seektime):

        super().play(item)
        self.seektime = seektime

    def onAVStarted(self):

        if self.seektime == None:
            pass

        elif self.getTotalTime() == 0:
            pass

        elif self.seektime < self.getTotalTime():
            self.seekTime(self.seektime)

        elif self.seektime > self.getTotalTime():
            pass

        self.seektime = None

import xbmc


class Player(xbmc.Player):

    def __init__(self) -> None:
        super().__init__()
        self._paused: bool = False

    def onPlayBackStarted(self) -> None:

        self._paused = False

    def onAVStarted(self) -> None:

        self._paused = False

    def onPlayBackStopped(self) -> None:

        self._paused = False

    def onPlayBackEnded(self) -> None:

        self._paused = False

    def onPlayBackError(self) -> None:

        self._paused = False

    def onPlayBackPaused(self) -> None:

        self._paused = True

    def onPlayBackResumed(self) -> None:

        self._paused = False

    def isPaused(self) -> bool:

        return self._paused

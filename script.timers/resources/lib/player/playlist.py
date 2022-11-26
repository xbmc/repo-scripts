import xbmc


class PlayList(xbmc.PlayList):

    def __init__(self, playList: int) -> None:
        super().__init__(playList)
        self.directUrl: str = None

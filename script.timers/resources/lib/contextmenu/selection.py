from resources.lib.timer.timer import (MEDIA_ACTION_START_STOP,
                                       SYSTEM_ACTION_NONE)


class Selection:

    path = None
    label = None
    timer = None
    activation = None
    startTime = None
    duration = None
    endTime = None
    systemAction = SYSTEM_ACTION_NONE
    mediaAction = MEDIA_ACTION_START_STOP
    repeat = False
    resume = False
    epg = False
    fade = False

#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

from enum import Enum

__Version__ = "1.0.0"

class MsgType(Enum):
    Request = 'Request'
    Response = 'Response'
    Notification = 'Notification'
    Message = 'Message'
    Error = 'Error'
    Login = 'Login'
    Logout = 'Logout'

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name



class OpStatus(Enum):
    Success=0
    GeneralFailure=1
    ItemDoesNotExist=30084
    KodiOpFailure=3
    ItemUpdateFailed=30083
    ItemAddedFailed=30085
    ItemRemovedFailed=30086
    ItemCancelledFailed=30087
    DuplicateItemError=30080
    InvalidAlarmTimeError=30082
    NoClientConnectedError=10
    StopVideoPlayerStopped=11
    ItemEnabled=12
    ItemDisabled=13
    VacationModeActive=30081
    ServerConnectionError=30088

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class NotificationAction(Enum):
    ItemUpdated = "ItemUpdated"
    ItemRemoved = 'ItemRemoved'
    ItemCancelled = 'ItemCancelled'
    ItemAdded = 'ItemAdded'
    VacationMode = 'VacationMode'
    PreRollTime = 'PreRollTime'
    ItemRetrieved = 'ItemRetrieved'
    ItemStateRetrieved = 'ItemStateRetrieved'
    ItemStateSet = 'ItemStateSet'
    ItemSuspended = 'ItemSuspended'
    ListCleared = 'ListCleared'

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class Cmd(Enum):
    AddPlayListItem = 'AddPlayListItem'
    RemovePlayListItem = 'RemovePlayListItem'
    RemoveAllPlayListItems = 'RemoveAllPlayListItems'
    GetChPlayListItems = 'GetChPlayListItems'
    GetPlayList = 'GetPlayList'
    GetPlayListItem = 'GetPlayListItem'
    UpdatePlayListItem = 'UpdatePlayListItem'
    PlayList = 'PlayList'
    GetChGroupList='GetChGroupList'
    GetChannelList='GetChannelList'
    SkipEvent='SkipEvent'
    SetVacationMode='SetVacationMode'
    GetVacationMode='GetVacationMode'
    Stop_Player='Stop Player'
    GetPreRollTime='GetPreRollTime'
    SetPreRollTime='SetPreRollTime'
    DisablePlayListItem='DisablePlayListItem'
    EnablePlayListItem='EnablePlayListItem'
    GetPlayListItemState='GetPlayListItemState'
    ClearPlayList='ClearPlayList'
    GetDailyStopCmdTime='GetDailyStopCmdTime'


    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


def xlateCmd2Notification(cmd):
    xlateTable = {Cmd.SkipEvent: NotificationAction.ItemUpdated,
                  Cmd.RemovePlayListItem: NotificationAction.ItemRemoved,
                  Cmd.UpdatePlayListItem: NotificationAction.ItemUpdated,
                  Cmd.AddPlayListItem: NotificationAction.ItemAdded,
                  Cmd.GetPlayList: NotificationAction.ItemRetrieved,
                  Cmd.GetPreRollTime:NotificationAction.ItemRetrieved,
                  Cmd.GetChGroupList:NotificationAction.ItemRetrieved,
                  Cmd.GetChannelList:NotificationAction.ItemRetrieved,
                  Cmd.GetPlayListItem:NotificationAction.ItemRetrieved,
                  Cmd.GetChPlayListItems:NotificationAction.ItemRetrieved,
                  Cmd.GetVacationMode:NotificationAction.ItemRetrieved,
                  Cmd.SetVacationMode: NotificationAction.VacationMode,
                  Cmd.GetPlayListItemState:NotificationAction.ItemStateRetrieved,
                  Cmd.DisablePlayListItem:NotificationAction.ItemUpdated,
                  Cmd.EnablePlayListItem:NotificationAction.ItemUpdated,
                  Cmd.ClearPlayList:NotificationAction.ListCleared}

    if cmd in xlateTable.keys():
        return xlateTable[cmd]
    else:
        raise Exception("Cannot Translate {}".format(cmd))



VACATIONMODE='vacationmode'
PREROLLTIME='preroll_time'
DAILYSTOPCOMMAND='dailystopcommand'
STOPCMD_ACTIVE='stopcmd_active'
DEBUGMODE='debugmode'
ACTIVATIONKEY='activationkey'
ALARMTIME='alarmtime'
COUNTDOWN_DURATION='countdown_duration'
CHANNELGROUP='channelgroup'
TRUE='true'
FALSE='false'
WRITEMODE='w'
READMODE='r'
WRITEBINARYMODE='rb'
READBINARYMODE='rb'
AUTOCLEANMODE='autocleanmode'


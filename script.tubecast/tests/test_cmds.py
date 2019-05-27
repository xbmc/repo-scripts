# -*- coding: utf-8 -*-
from resources.lib.tubecast.youtube.utils import parse_cmd

cmd_1 = '[[20,["remoteDisconnected",{"app":"android-phone-13.05.52","pairingType":"dial","capabilities":"atp,que,mus","ui":"true","clientName":"android","experiments":"","name":"MYPHONE","remoteControllerUrl":"ws://","id":"something","type":"REMOTE_CONTROL","device":"{\"app\":\"android-phone-13.05.52\",\"pairingType\":\"dial\",\"capabilities\":\"atp,que,mus\",\"clientName\":\"android\",\"experiments\":\"\",\"name\":\"MYPHONE\",\"remoteControllerUrl\":\"ws://\",\"id\":\"id\",\"type\":\"REMOTE_CONTROL\"}"}]]'
cmd_2 = '20,["remoteDisconnected",{"app":"android-phone-13.05.52","pairingType":"dial","capabilities":"atp,que,mus","ui":"true","clientName":"android","experiments":"","name":"MYPHONE","remoteControllerUrl":"ws://","id":"something","type":"REMOTE_CONTROL","device":"{\"app\":\"android-phone-13.05.52\",\"pairingType\":\"dial\",\"capabilities\":\"atp,que,mus\",\"clientName\":\"android\",\"experiments\":\"\",\"name\":\"MYPHONE\",\"remoteControllerUrl\":\"ws://\",\"id\":\"id\",\"type\":\"REMOTE_CONTROL\"}"}]]'


def test_cmd1():
    _, data = parse_cmd(cmd_1)
    assert data["name"] == "MYPHONE"


def test_cmd2():
    _, data = parse_cmd(cmd_2)
    assert data["name"] == "MYPHONE"

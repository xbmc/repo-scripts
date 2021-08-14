#! /usr/bin/python

######### Based upon: https://raw.githubusercontent.com/Quihico/handy.stuff/master/language.py
######### https://forum.kodi.tv/showthread.php?tid=268081&highlight=generate+.po+python+gettext
import traceback

_strings = {}

if __name__ == "__main__":

    import os
    import sys

    import polib

    print("PATH: {}".format(sys.path))
    print("executable: " + sys.executable)

    dirpath = os.getcwd()
    print("current directory is : " + dirpath)
    foldername = os.path.basename(dirpath)
    print("Directory name is : " + foldername)

    string_file = "..\\language\\resource.language.en_GB\\strings.po"
    print("input file: " + string_file)

    po = polib.pofile(string_file)

    try:
        import re, subprocess

        command = ["grep", "-hnr", "_([\'\"]", "..\\.."]
        print("grep command: {}".format(command))
        r = subprocess.check_output(command)

        print(r)

        strings = re.compile("_\([\"'](.*?)[\"']\)", re.IGNORECASE).findall(r)
        translated = [m.msgid.lower().replace("'", "\\'") for m in po]
        missing = set([s for s in strings if s.lower() not in translated])

        print("Missing:"+ str(missing))

        if missing:
            ids_range = list(range(30000, 35000))
            ids_reserved = [int(m.msgctxt[1:]) for m in po]
            ids_available = [x for x in ids_range if x not in ids_reserved]
            print("WARNING: adding missing translation for '%s'" % missing)
            for text in missing:
                id = ids_available.pop(0)
                entry = polib.POEntry(msgid=text, msgstr=u'', msgctxt="#{0}".format(id))
                po.append(entry)
            po.save(string_file)
    except Exception as e:
        print("Exception:")
        traceback.print_exc()
        content = []
    with open(__file__, "r") as me:
        content = me.readlines()
        content = content[:content.index("#GENERATED\n") + 1]
    with open(__file__, "w") as f:
        f.writelines(content)
        for m in po:
            line = "_strings['{0}'] = {1}\n".format(m.msgid.lower().replace("'", "\\'"),
                                                    m.msgctxt.replace("#", "").strip())
            f.write(line)
else:
    from . import STRDEBUG, ADDON, logger

    def get_string(t):
        string_id = _strings.get(t.lower())
        if not string_id:
            logger.debug("LANGUAGE: missing translation for '%s'" % t.lower())
            return t

        if STRDEBUG is True:
            return  "STR:{} {}".format(string_id,ADDON.getLocalizedString(string_id))
        return ADDON.getLocalizedString(string_id)
        # =======================================================================
        # elif id in range(30000, 31000) and ADDON_ID.startswith("plugin"): return ADDON.getLocalizedString(id)
        # elif id in range(31000, 32000) and ADDON_ID.startswith("skin"): return ADDON.getLocalizedString(id)
        # elif id in range(32000, 33000) and ADDON_ID.startswith("script"): return ADDON.getLocalizedString(id)
        # elif not id in range(30000, 33000): return ADDON.getLocalizedString(id)
        # =======================================================================
    # setattr(__builtin__, "_", get_string)

#GENERATED
_strings['video actions'] = 32100
_strings['audio actions'] = 32102
_strings['start/resume'] = 32201
_strings['pause'] = 32202
_strings['stop'] = 32203
_strings['scene name:'] = 32510
_strings['scene id'] = 32511
_strings['select...'] = 32512
_strings['bridge'] = 30500
_strings['discover hue bridge'] = 30501
_strings['bridge ip'] = 30502
_strings['bridge user'] = 30503
_strings['bridge serial'] = 30504
_strings['enable schedule (24-h format)'] = 30505
_strings['start time:'] = 30506
_strings['end time:'] = 30507
_strings['disable during daylight'] = 30508
_strings['activate during playback at sunset'] = 30509
_strings['general'] = 30510
_strings['schedule'] = 30511
_strings['scenes'] = 30512
_strings['start scene enabled'] = 30513
_strings['pause scene enabled'] = 30514
_strings['stop scene enabled'] = 30515
_strings['disable time check if any light already on'] = 30516
_strings['don\'t enable scene if any light is off'] = 30517
_strings['[b][i]warning: not supported on all hardware[/b][/i]'] = 30521
_strings['cpu & hue performance'] = 30522
_strings['ambilight'] = 30523
_strings['advanced'] = 32101
_strings['debug logs'] = 32102
_strings['separate debug log'] = 32105
_strings['initial flash'] = 5110
_strings['flash on settings reload'] = 5111
_strings['light selection'] = 6100
_strings['select lights'] = 6101
_strings['select hue group'] = 6102
_strings['group behavior'] = 6200
_strings['enabled'] = 30520
_strings['press connect button on hue bridge'] = 9001
_strings['create scene'] = 9007
_strings['delete scene'] = 9008
_strings['hue service'] = 30000
_strings['error: group not created'] = 30001
_strings['group deleted'] = 30003
_strings['check your bridge and network'] = 30004
_strings['hue connected'] = 30006
_strings['press link button on bridge'] = 30007
_strings['bridge not found'] = 30008
_strings['waiting for 90 seconds...'] = 30009
_strings['user not found'] = 30010
_strings['complete!'] = 30011
_strings['group created'] = 30012
_strings['cancelled'] = 30013
_strings['saving settings'] = 30014
_strings['select hue lights...'] = 30015
_strings['are you sure you want to delete this group: '] = 30016
_strings['found bridge: '] = 30017
_strings['discover bridge...'] = 30018
_strings['user found!'] = 30019
_strings['delete hue group'] = 30020
_strings['bridge connection failed'] = 30021
_strings['discovery started'] = 30022
_strings['bridge not configured'] = 30023
_strings['check hue bridge configuration'] = 30024
_strings['error: scene not created'] = 30025
_strings['scene created'] = 30026
_strings['are you sure you want to delete this scene: '] = 30027
_strings['delete hue scene'] = 30028
_strings['create a hue scene from current light state'] = 30029
_strings['enter scene name'] = 30030
_strings['transition time:'] = 30031
_strings['fade time must be saved as part of the scene.'] = 30032
_strings['{} secs.'] = 30033
_strings['cancel'] = 30034
_strings['lights:'] = 30035
_strings['scene name:'] = 30036
_strings['save'] = 30037
_strings['create hue scene'] = 30038
_strings['error: scene not created.'] = 30002
_strings['set a fade time in seconds, or set to 0 seconds for an instant transition.'] = 30039
_strings['scene deleted'] = 30040
_strings['you may now assign your scene to player actions.'] = 30041
_strings['fade time (seconds)'] = 30042
_strings['error'] = 30043
_strings['create new scene'] = 30044
_strings['scene successfully created!'] = 30045
_strings['adjust lights to desired state in the hue app to save as new scene.'] = 30046
_strings['connection lost. check settings. shutting down'] = 30047
_strings['connection lost. trying again in 2 minutes'] = 30048
_strings['scene name'] = 30049
_strings['n-upnp discovery...'] = 30050
_strings['upnp discovery...'] = 30051
_strings['searching for bridge...'] = 30005
_strings['invalid start or end time, schedule disabled'] = 30052
_strings['hue calls/sec (max 10): {}'] = 30053
_strings['est. hue calls/sec (max 10): {}'] = 30054
_strings['set brightness on start'] = 30056
_strings['force on'] = 30057
_strings['light names:'] = 30058
_strings['light gamut:'] = 30059
_strings['update interval (ms)'] = 30065
_strings['hue transition time (ms)'] = 30066
_strings['frame capture size'] = 30067
_strings['performance debug logging'] = 30068
_strings['minimum duration (minutes)'] = 30800
_strings['enable for movies'] = 30801
_strings['enable for tv episodes'] = 30802
_strings['enable for music videos'] = 30803
_strings['enable for other videos (discs)'] = 30804
_strings['enable for live tv'] = 30805
_strings['saturation'] = 30809
_strings['minimum brightness'] = 30810
_strings['maximum brightness'] = 30811
_strings['disable connection message'] = 30812
_strings['average image processing time:'] = 30813
_strings['on playback stop'] = 30814
_strings['resume light state'] = 30815
_strings['resume transition time (secs.)'] = 30816
_strings['only colour lights are supported'] = 30071
_strings['unsupported hue bridge'] = 30072
_strings['hue bridge v1 (round) is unsupported. hue bridge v2 (square) is required for certain features.'] = 30073
_strings['disabled'] = 30055
_strings['play'] = 30060
_strings['hue status: '] = 30061
_strings['settings'] = 30062
_strings['disabled by daylight'] = 30063
_strings['error: scene not found'] = 30064
_strings['the following error occurred:'] = 30080
_strings['automatically report this error?'] = 30081
_strings['no lights selected for ambilight.'] = 30069
_strings['ok'] = 30070
_strings['don\'t show again'] = 30074
_strings['hue bridge over capacity'] = 30075
_strings['network not ready'] = 30076
_strings['the hue bridge is over capacity. increase refresh rate or reduce the number of ambilights.'] = 30077
_strings['bridge not found[cr]check your bridge and network.'] = 30078
_strings['don\'t show again'] = 30079
_strings['press link button on bridge. waiting for 90 seconds...'] = 30082
_strings['unknown'] = 30083
_strings['user found![cr]saving settings...'] = 30084
_strings['adjust lights to desired state in the hue app to save as new scene.[cr]set a fade time in seconds, or set to 0 seconds for an instant transition.'] = 30085
_strings['user not found[cr]check your bridge and network.'] = 30086
_strings['scene successfully created![cr]you may now assign your scene to player actions.'] = 30087

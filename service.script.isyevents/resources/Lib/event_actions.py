# dictionary to translate actions
__act_names__ = {
    'Run': 'ProgramRun',
    'Run Then': 'ProgramRunThen',
    'Run Else': 'ProgramRunElse'}


def ParseDeviceSetting(isy, isy_events, name):
    enable = isy_events.getSetting(name + '_bool')
    addr = isy_events.getSetting(name)
    perc = int(float(isy_events.getSetting(name + '_perc')))

    if enable == 'true':
        if perc > 0:
            return lambda: isy.NodeOn(addr, val=perc * 255 / 100)
        else:
            return lambda: isy.NodeOff(addr)
    else:
        return None


def ParseProgramSetting(isy, isy_events, name):
    enable = isy_events.getSetting(name + '_bool')
    addr = isy_events.getSetting(name)
    act = isy_events.getSetting(name + '_act')
    action = __act_names__[act]

    if enable == 'true':
        fun = getattr(isy, action)
        return lambda: fun(addr)
    else:
        return None

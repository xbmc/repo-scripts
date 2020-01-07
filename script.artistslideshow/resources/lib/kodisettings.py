#v.0.0.1

def _get_setting( addon, setting_name, default, thetype="string" ):
    if thetype.lower() == "bool":
        if addon.getSetting( setting_name ).lower() == 'true':
            return True
        if addon.getSetting( setting_name ).lower() == 'false':
            return False
        return default
    if thetype.lower() == "int":
        try:
            return int( addon.getSetting( setting_name ) )
        except ValueError:
            return default
    if thetype.lower() == "number":
        try:
            return float( addon.getSetting( setting_name ) )
        except ValueError:
            return default
    else:
        setting = addon.getSetting( setting_name )
        if setting:
            return setting
        else:
            return default


def getSettingBool( addon, setting_name, default=False ):
    return _get_setting( addon, setting_name, default, 'bool' )


def getSettingInt( addon, setting_name, default=0 ):
    return _get_setting( addon, setting_name, default, 'int' )


def getSettingNumber( addon, setting_name, default=0.0 ):
    return _get_setting( addon, setting_name, default, 'number' )

def getSettingString( addon, setting_name, default='' ):
    return _get_setting( addon, setting_name, default, 'string' )

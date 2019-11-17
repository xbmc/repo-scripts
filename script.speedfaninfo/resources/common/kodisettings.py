#v.0.0.1

def _getsetting( addon, name, default, type="string" ):
    if type.lower() == "bool":
        try:
            thebool = addon.getSettingBool( name )
            if thebool == 0:
                return False
            elif thebool == 1:
                return True
            else:
                return thebool
        except TypeError:
            return default
        except AttributeError:
            if addon.getSetting( name ).lower() == 'true':
                return True
            if addon.getSetting( name ).lower() == 'false':
                return False
            return default
    if type.lower() == "int":
        try:
            return addon.getSettingInt( name )
        except TypeError:
            return default
        except AttributeError:
            try:
                return int( addon.getSetting( name ) )
            except:
                return default
    if type.lower() == "number":
        try:
            return addon.getSettingNumber( name )
        except TypeError:
            return default
        except AttributeError:
            try:
                return float( addon.getSetting( name ) )
            except:
                return default
    else:
        setting = addon.getSetting( name )
        if setting:
            return setting
        else:
            return default


def getSettingBool( addon, name, default=False ):
    return _getsetting( addon, name, default, 'bool' )


def getSettingInt( addon, name, default=0 ):
    return _getsetting( addon, name, default, 'int')


def getSettingNumber( addon, name, default=0.0 ):
    return _getsetting( addon, name, default, 'number')


def getSettingString( addon, name, default='' ):
    return _getsetting( addon, name, default, 'string')


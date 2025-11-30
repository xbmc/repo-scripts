from . import utils
from . import config

# Time
def time(unit, value):
	content = ''

	if unit == 'timeiso':
		data = utils.dt('isoloc', value)
	else:
		data = utils.dt('stamploc', value)

	# Hour
	if config.kodi.meri != '/':
		content += str(int(data.strftime('%I')))
	else:
		content += str(int(data.strftime('%H')))

	# Minute
	if unit.startswith('time'):
		content += data.strftime(':%M')

	# Meri
	if config.kodi.meri != '/':
		content += data.strftime('%p')

	return content

# Temperature
def tempconv(value, unit, kodi=False):
	if value is not False:
		value = float(value)

		if unit == '°F':
			v = value * 1.8 + 32
		elif unit == 'K':
			v = value + 273.15
		elif unit == '°Ré':
			v = value * 0.8
		elif unit == '°Ra':
			v = value * 1.8 + 491.67
		elif unit == '°Rø':
			v = value * 0.525 + 7.5
		elif unit == '°D':
			v = value / -0.667 + 150
		elif unit == '°N':
			v = value * 0.33
		else:
			v = value

		if config.addon.tempdp == '0' or kodi is True:
			return round(v)
		else:
			if config.addon.unitsep == ',':
				return str(round(v,int(config.addon.tempdp))).replace('.',',')
			else:
				return round(v,int(config.addon.tempdp))

	else:

		if unit == '°F':
			v = '°F'
		elif unit == 'K':
			v = 'K'
		elif unit == '°Ré':
			v = '°Ré'
		elif unit == '°Ra':
			v = '°Ra'
		elif unit == '°Rø':
			v = '°Rø'
		elif unit == '°D':
			v = '°D'
		elif unit == '°N':
			v = '°N'
		else:
			v = '°C'

		return v

def temp(value=False, kodi=False):

	if config.addon.temp == 'app' or kodi is True:
		return tempconv(value, config.kodi.temp, kodi)
	else:
		return tempconv(value, config.addon.temp)

# Speed
def beaufort(value):
	value = int(value)

	if (value < 1.0):
		v = '0'
	elif (value >= 1.0) and (value < 5.6):
		v = '1'
	elif (value >= 5.6) and (value < 12.0):
		v = '2'
	elif (value >= 12.0) and (value < 20.0):
		v = '3'
	elif (value >= 20.0) and (value < 29.0):
		v = '4'
	elif (value >= 29.0) and (value < 39.0):
		v = '5'
	elif (value >= 39.0) and (value < 50.0):
		v = '6'
	elif (value >= 50.0) and (value < 62.0):
		v = '7'
	elif (value >= 62.0) and (value < 75.0):
		v = '8'
	elif (value >= 75.0) and (value < 89.0):
		v = '9'
	elif (value >= 89.0) and (value < 103.0):
		v = '10'
	elif (value >= 103.0) and (value < 118.0):
		v = '11'
	elif (value >= 118.0):
		v = '12'
	else:
		v = ''

	return v

def speedconv(value, unit):
	if value is not False:
		value = float(value)

		if unit == 'mph':
			v = value / 1.609344
		elif unit == 'm/min':
			v = value * 16,667
		elif unit == 'm/s':
			v = value / 3.6
		elif unit == 'ft/h':
			v = value * 3281
		elif unit == 'ft/min':
			v = value * 54.681
		elif unit == 'ft/s':
			v = value / 1.0971
		elif unit == 'kts':
			v = value / 1.852
		elif unit == 'beaufort':
			v = beaufort(value)
		elif unit == 'inch/s':
			v = value * 10.936
		elif unit == 'yard/s':
			v = value / 3.292
		elif unit == 'Furlong/Fortnight':
			v = value * 1670
		else:
			v = value

		if config.addon.speeddp == '0':
			return round(v)
		else:
			if config.addon.unitsep == ',':
				return str(round(v,int(config.addon.speeddp))).replace('.',',')
			else:
				return round(v,int(config.addon.speeddp))

	else:

		if unit == 'mph':
			v = 'mph'
		elif unit == 'm/min':
			v = 'm/min'
		elif unit == 'm/s':
			v = 'm/s'
		elif unit == 'ft/h':
			v = 'ft/h'
		elif unit == 'ft/min':
			v = 'ft/min'
		elif unit == 'ft/s':
			v = 'ft/s'
		elif unit == 'kts':
			v = 'kts'
		elif unit == 'beaufort':
			v = 'beaufort'
		elif unit == 'inch/s':
			v = 'inch/s'
		elif unit == 'yard/s':
			v = 'yard/s'
		elif unit == 'Furlong/Fortnight':
			v = 'Furlong/Fortnight'
		else:
			v = 'km/h'

		return v

def speed(value=False, kodi=False):

	if config.addon.speed == 'app' or kodi is True:
		return speedconv(value, config.kodi.speed)
	else:
		return speedconv(value, config.addon.speed)

# Direction
def direction(deg):
	if deg >= 349 or deg <=  11:
		return utils.loc(71)
	elif deg >= 12 and deg <= 33:
		return utils.loc(72)
	elif deg >= 34 and deg <=  56:
		return utils.loc(73)
	elif deg >= 57 and deg <=  78:
		return utils.loc(74)
	elif deg >= 79 and deg <=  101:
		return utils.loc(75)
	elif deg >= 102 and deg <=  123:
		return utils.loc(76)
	elif deg >= 124 and deg <=  146:
		return utils.loc(77)
	elif deg >= 147 and deg <=  168:
		return utils.loc(78)
	elif deg >= 169 and deg <=  191:
		return utils.loc(79)
	elif deg >= 192 and deg <=  213:
		return utils.loc(80)
	elif deg >= 214 and deg <=  236:
		return utils.loc(81)
	elif deg >= 237 and deg <=  258:
		return utils.loc(82)
	elif deg >= 259 and deg <=  281:
		return utils.loc(83)
	elif deg >= 282 and deg <=  303:
		return utils.loc(84)
	elif deg >= 304 and deg <=  326:
		return utils.loc(85)
	elif deg >= 327 and deg <=  348:
		return utils.loc(86)

# Distance
def distanceconv(value, unit):
	if value is not False:
		value = float(value)

		if unit == 'km':
			v = value / 1000
		elif unit == 'mi':
			v = value / 1609
		else:
			v = value

		if config.addon.distancedp == '0':
			return round(v)
		else:
			if config.addon.unitsep == ',':
				return str(round(v,int(config.addon.distancedp))).replace('.',',')
			else:
				return round(v,int(config.addon.distancedp))

	else:

		if unit == 'km':
			v = 'km'
		elif unit == 'mi':
			v = 'mi'
		else:
			v = 'm'

		return v

def distance(value=False):
	return distanceconv(value, config.addon.distance)

# Precipitation
def precipconv(value, unit):
	if value is not False:
		value = float(value)

		if unit == 'in':
			v = value * 0.039
		else:
			v = value

		if config.addon.precipdp == '0':
			return round(v)
		else:
			if config.addon.unitsep == ',':
				return str(round(v,int(config.addon.precipdp))).replace('.',',')
			else:
				return round(v,int(config.addon.precipdp))

	else:

		if unit == 'in':
			v = 'in'
		else:
			v = 'mm'

		return v

def precip(value=False):
	return precipconv(value, config.addon.precip)

# Pressure
def pressureconv(value, unit):
	if value is not False:
		value = float(value)

		if unit == 'kPa':
			v = value * 0.1
		elif unit == 'mmHg':
			v = value * 0.7500637554
		elif unit == 'inHg':
			v = value * 0.02953
		elif unit == 'psi':
			v = value * 0.0145037738
		else:
			v = value

		if config.addon.pressuredp == '0':
			return round(v)
		else:
			if config.addon.unitsep == ',':
				return str(round(v,int(config.addon.pressuredp))).replace('.',',')
			else:
				return round(v,int(config.addon.pressuredp))

	else:

		if unit == 'kPa':
			v = 'kPa'
		elif unit == 'mmHg':
			v = 'mmHg'
		elif unit == 'inHg':
			v = 'inHg'
		elif unit == 'psi':
			v = 'psi'
		else:
			v = 'hPa'

		return v

def pressure(value=False):
	return pressureconv(value, config.addon.pressure)

# Decimal places
def dp(value, setting):
	value = float(value)

	if setting == '0':
		return round(value)
	else:
		if config.addon.unitsep == ',':
			return str(round(value, int(setting))).replace('.',',')
		else:
			return round(value, int(setting))

# Moonphase
def moonphase(deg):
	if deg == 358 or deg == 359 or deg == 0 or deg == 1 or deg == 2:
		return utils.locaddon(32440)
	elif deg >= 3 and deg <= 87:
		return utils.locaddon(32441)
	elif  deg == 88 or deg == 89 or deg == 90 or deg == 91 or deg == 92:
		return utils.locaddon(32442)
	elif deg >= 93 and deg <= 177:
		return utils.locaddon(32443)
	elif deg == 178 or deg == 179 or deg == 180 or deg == 181 or deg == 182:
		return utils.locaddon(32444)
	elif deg >= 183 and deg <= 267:
		return utils.locaddon(32445)
	elif deg == 268 or deg == 269 or deg == 270 or deg == 271 or deg == 272:
		return utils.locaddon(32446)
	elif deg >= 273 and deg <= 357:
		return utils.locaddon(32447)

def moonphaseimage(deg):
	if deg == 358 or deg == 359 or deg == 0 or deg == 1 or deg == 2:
		return '0.png'
	elif deg >= 3 and deg <= 87:
		return '1.png'
	elif  deg == 88 or deg == 89 or deg == 90 or deg == 91 or deg == 92:
		return '2.png'
	elif deg >= 93 and deg <= 177:
		return '3.png'
	elif deg == 178 or deg == 179 or deg == 180 or deg == 181 or deg == 182:
		return '4.png'
	elif deg >= 183 and deg <= 267:
		return '5.png'
	elif deg == 268 or deg == 269 or deg == 270 or deg == 271 or deg == 272:
		return '6.png'
	elif deg >= 273 and deg <= 357:
		return '7.png'


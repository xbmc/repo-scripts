import os

from . import weather
from . import config
from . import utils
from . import api

def Main():
	startup = True
	utils.log(f'Starting service ...')
	utils.log(config.addon_info, 3)

	# Geolocation
	if not utils.setting('geoip') and not utils.setting('loc1'):
		utils.setsetting('geoip', 'true')
		utils.setsetting('service', 'running')
		weather.Main('1', mode='geoip')
		weather.Main('1', mode='download')
		utils.setsetting('service', 'idle')

	# Service
	while not utils.monitor.abortRequested():
		utils.setsetting('service', 'running')

		# Init
		if utils.settingrpc('weather.addon') == 'weather.openmeteo':
			utils.log(f'Running service ...', 3)

			if not startup:
				config.init(cache=True)

			start   = utils.time.time()
			current = utils.settingrpc("weather.currentlocation")

			# Download
			for locid in range(1, config.addon.maxlocs):
				if utils.setting(f'loc{locid}'):
					weather.Main(str(locid), mode='download')

			# Update
			weather.Main(str(current), mode='update')
			utils.setsetting('service', 'idle')

			# Notification
			if startup or utils.lastupdate('alert_notification') >= utils.setting('alert_interval', 'int') * 60:
				utils.setupdate('alert_notification')

				# Queue
				for locid in range(1, config.addon.maxlocs):
					if utils.setting(f'loc{locid}') and utils.setting(f'loc{locid}alert', 'bool'):
						weather.Main(str(locid), mode='msgqueue')

				# Send
				weather.Main(str(current), mode='msgsend')

			# Finish
			utils.log(f'Finished ({round(utils.time.time() - start, 3)} sec)', 3)

		else:
			utils.log('Addon not enabled ...', 4)
			utils.setsetting('service', 'idle')

		# Sleep
		startup = False
		utils.monitor.waitForAbort(300)

	utils.log(f'Stopping service ...')
	api.s.close()

	# Workaround KODI issue (v0.9.5)
	try:
		utils.setsetting('service', 'stopped')
	except:
		pass


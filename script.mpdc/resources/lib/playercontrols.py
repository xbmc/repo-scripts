import xbmcgui
ctrls = {
	'Confluence':{
		'prev':['OSDPrevTrackNF.png','OSDPrevTrackFO.png'],
		'stop':['OSDStopNF.png','OSDStopFO.png'],
		'play':['OSDPauseNF.png','OSDPauseFO.png'],
		'pause':['OSDPlayNF.png','OSDPlayFO.png'],
		'next':['OSDNextTrackNF.png','OSDNextTrackFO.png'],
		'repeat':['OSDRepeatNF.png','OSDRepeatFO.png'],
		'repeat0':['OSDRepeatNF.png','OSDRepeatFO.png'],
		'repeat1':['OSDRepeatAllNF.png','OSDRepeatAllFO.png'],
		'random':['OSDRandomOffNF.png','OSDRandomOffFO.png'],
		'random0':['OSDRandomOffNF.png','OSDRandomOffFO.png'],
		'random1':['OSDRandomOnNF.png','OSDRandomOnFO.png'],
		'single':['SingleOffNF.png','SingleOffFO.png'],
		'single0':['SingleOffNF.png','SingleOffFO.png'],
		'single1':['SingleOnNF.png','SingleOnFO.png'],
		'consume':['ConsumeOffNF.png','ConsumeOffFO.png'],
		'consume0':['ConsumeOffNF.png','ConsumeOffFO.png'],
		'consume1':['ConsumeOnNF.png','ConsumeOnFO.png'],
		'outputs':['OSDAudioNF.png','OSDAudioFO.png']
	},
	'PM3.HD': {
		'prev':['PlayerControls-PrevNF.png','PlayerControls-PrevFO.png'],
		'stop':['PlayerControls-StopNF.png','PlayerControls-StopFO.png'],
		'play':['PlayerControls-PauseNF.png','PlayerControls-PauseFO.png'],
		'pause':['PlayerControls-PlayNF.png','PlayerControls-PlayFO.png'],
		'next':['PlayerControls-NextNF.png','PlayerControls-NextFO.png'],
		'repeat':['PlayerControls-RepeatNF.png','PlayerControls-RepeatFO.png'],
		'repeat0':['PlayerControls-RepeatNF.png','PlayerControls-RepeatFO.png'],
		'repeat1':['PlayerControls-RepeatAllNF.png','PlayerControls-RepeatAllFO.png'],
		'random':['PlayerControls-RandomNF.png','PlayerControls-RandomFO.png'],
		'random0':['PlayerControls-RandomNF.png','PlayerControls-RandomFO.png'],
		'random1':['PlayerControls-RandomOnNF.png','PlayerControls-RandomOnFO.png'],
		'single':['PlayerControls-RandomNF.png','PlayerControls-RandomFO.png'],
		'single0':['PlayerControls-RandomNF.png','PlayerControls-RandomFO.png'],
		'single1':['PlayerControls-RandomOnNF.png','PlayerControls-RandomOnFO.png'],
		'consume':['PlayerControls-RandomNF.png','PlayerControls-RandomFO.png'],
		'consume0':['PlayerControls-RandomNF.png','PlayerControls-RandomFO.png'],
		'consume1':['PlayerControls-RandomOnNF.png','PlayerControls-RandomOnFO.png']
	},
	'transparency':{
		'prev':['player-previous-nofocus.png','player-previous-focus.png'],
		'stop':['player-stop-nofocus.png','player-stop-focus.png'],
		'play':['player-pause-nofocus.png','player-pause-focus.png'],
		'pause':['player-play-nofocus.png','player-play-focus.png'],
		'next':['player-next-nofocus.png','player-next-focus.png'],
		'repeat':['player-repeat-nofocus.png','player-repeat-focus.png'],
		'repeat0':['player-repeat-nofocus.png','player-repeat-focus.png'],
		'repeat1':['player-repeatall-nofocus.png','player-repeatall-focus.png'],
		'random':['player-random-nofocus.png','player-random-focus.png'],
		'random0':['player-random-nofocus.png','player-random-focus.png'],
		'random1':['player-randomselected-nofocus.png','player-randomselected-focus.png'],
		'single':['player-repeat-nofocus.png','player-repeat-focus.png'],
		'single0':['player-repeat-nofocus.png','player-repeat-focus.png'],
		'single1':['player-repeatall-nofocus.png','player-repeatall-focus.png'],
		'consume':['player-repeat-nofocus.png','player-repeat-focus.png'],
		'consume0':['player-repeat-nofocus.png','player-repeat-focus.png'],
		'consume1':['player-repeatall-nofocus.png','player-repeatall-focus.png']
	}
}

pl_ctrl_types = ['random','repeat','single','consume']

class Controls(object):
	def __init__(self,theme):
		self._theme=theme
		if not theme in ctrls:
			raise Exception('Unexpected theme name %s'%theme)

	def _get_image(self,control):
		th = ctrls[self._theme]
		if not control in th:
			raise Exception('Unexpected control name or state %s'%control)
		return th[control]

	def _create_control(self,control):
		ctrl = xbmcgui.ListItem(label='')
		ctrl.setProperty('label',control)
		ctrl.setProperty('state','0')
		ctrl.setIconImage(self._get_image(control)[0])
		ctrl.setThumbnailImage(self._get_image(control)[1])
		return ctrl
	def _update_control(self,item,status):
		ctr
	def init_playback_controls(self,listview):
		listview.addItems([self._create_control('prev'),self._create_control('stop'),self._create_control('pause'),self._create_control('next')])

	def init_player_controls(self,listview,status):
		for key in pl_ctrl_types:
			if key in status:
				listview.addItem(self._create_control(key))
		listview.addItem(self._create_control('outputs'))

	def update_playback_controls(self,listview,status):
		item = listview.getListItem(2)
		state = status['state']
		item.setProperty('label',state)
		if state=='stop':
			img = self._get_image('pause')
			item.setProperty('label','pause')
		else:
			img = self._get_image(state)
		item.setIconImage(img[0])
		item.setThumbnailImage(img[1])
		
	def update_player_controls(self,listview,status):
		for i in range(0,listview.size()):
			item = listview.getListItem(i)
			name = item.getProperty('label')
			if name in pl_ctrl_types:
				img = self._get_image(name+status[name])
				item.setProperty('state',status[name])
				item.setIconImage(img[0])
				item.setThumbnailImage(img[1])
			
			
		

#	This file is part of PulseEqualizerGui for Kodi.
#
#	Copyright (C) 2021 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.
#
#

import subprocess

from time import sleep
from threading import Thread
from math import sin, pi
from array import array

from helper import SocketCom, handle, log, logerror

class SoundGen():
	def __init__(self, padb, pc):
		self.fs = 44100
		self.duration = 0.1
		self.player_proc = None

		self.playing = False
		self.stop = False

		self.pid = 0
		self.cur_eq = None
		self.cur_eq_index = None
		self.cur_eq_stream = None

		self.padb = padb
		self.pc = pc

	def end_server(self):
		self.on_tone_stop()
		self.on_pulseplayer_stop()

	def play_loop(self, freq, vol):
		log("soge: start play loop")
		if not self.player_proc: self.on_pulseplayer_start(None)

		self.playing = True
		self.stop = False

		n_sin = int(freq * self.duration)
		n_samp = self.fs / freq
		t_samp = round(n_samp * n_sin)

		dur = t_samp / self.fs

		samples = array('f',[])
		for i in range(t_samp):
			samples.append(float(sin(2 * i * pi / n_samp) * vol))

		self.player_proc.stdin.write(samples)
		self.player_proc.stdin.write(samples)

		while not self.stop:
			self.player_proc.stdin.write(samples)
			sleep(dur)

		self.stop = False
		self.playing = False

	def sweep_play_loop(self, count, channel, vol):
		if not self.player_proc:
			if not self.on_pulseplayer_start(channel): return False

		self.playing = True
		self.stop = False

		log("soge: sweep start")

		socket = SocketCom("sweep")
		sock_up = socket.is_server_running()
		if sock_up: log("soge: sweep server is up")

		sampleRate = float(self.cur_eq.sample_spec["rate"])
		chunk = int(sampleRate / 4)
		chunk_duration = float(0.25)

		#
		# prepare Sound
		#

		total_chunk = 20 * count
		cur_chunk = 0

		chunk_list = []
		pos = 0
		for c in range(20):
			base = c * chunk
			samples = array('f',[])
			for f in range(chunk):
				step = float((base + f)) / (sampleRate * 10)
				samples.append(float(sin( 2 * pos * pi) * vol))
				pos = pos + step
			chunk_list.append(samples)
		cur_chunk=0

		#
		# play Sound
		#

		for cnt in range(count):
			if sock_up: socket.send("play","sound",[count - cnt])
			c = 0

			for samples in chunk_list:
				if sock_up: socket.send("play","chunk",[c, 20, cur_chunk, total_chunk])
				self.player_proc.stdin.write(samples)

				if self.stop: break
				cur_chunk = cur_chunk + 1
				c = c + 1
				if cur_chunk > 2: sleep(chunk_duration)
			if self.stop: break

		sleep(4 * chunk_duration)

		log("soge: sweep has finished")
		self.stop = False
		self.playing = False
		if sock_up: socket.send("stop","sound")
		self.on_pulseplayer_stop()

	def on_pulseplayer_start(self,channel):
		try:
			sink = self.padb.chaineq_sink if self.padb.chaineq_sink is not None else self.padb.autoeq_sink
			if sink is None:
				log("soge: on_pulseplayer_start: no equalizer sink found")
				self.cur_eq_index = None
				return False

			try:
				self.cur_eq = sink
				self.cur_eq_index = sink.index
				self.cur_eq_stream = self.padb.stream_by_module[sink.owner_module].index
				self.cur_rate = sink.sample_spec["rate"]
			except Exception:
				self.cur_eq_index = None
				return False

			if self.player_proc: self.on_pulseplayer_stop()
			if channel is None: ch = []
			else: ch = ["--channel-map=%s" % channel]
			log("soge: start parec: rate=%s, channel=%s" %(self.cur_rate, repr(channel)))

			self.player_proc = subprocess.Popen(["parec","-p", "--rate=%d" % self.cur_rate, "--format=float32le", "--volume=65535","--latency-msec=250","--channels=1"]+ch,
				stdin=subprocess.PIPE, stdout=subprocess.PIPE)
			self.pid = self.player_proc.pid
			return True

		except Exception as e:
			if e.__class__.__name__ == "FileNotFoundError":
				logerror("soge: cannot find 'parec', please install 'pulseaudio-utils'")
			elif e.__class__.__name__ == "OSError" and e[0]==2:
				logerror("soge: cannot find 'parec', please install 'pulseaudio-utils'")
			else:
				handle(e)
			return False

	def on_pulseplayer_stop(self):
		if self.player_proc:
			self.player_proc.stdin.close()
			self.player_proc = None

	def on_sweep_play(self,count = 1,channel = None, vol = 1):
		log("soge: on_sweep_play")
		vol = vol * 0.58
		count = int(count)
		if self.playing: self.on_tone_stop()
		if count < 1: count = 1

		Thread(target=self.sweep_play_loop, args=(count, channel, vol)).start()

	def on_tone_start(self, freq, vol = 1):
		log("soge: on_tone_start")
		vol = vol * 0.58
		if self.playing: self.on_tone_stop()

		Thread(target=self.play_loop, args=(freq, vol)).start()

	def on_tone_stop(self):
		log("soge: on_tone_stop")
		self.stop = True
		while self.playing:	sleep(0.01)

	#
	# receive from pulseaudio
	#

	def on_sink_input_new(self,index):
		si = self.padb.sink_inputs[index]
		log("soge: on_sink_input_new %s"%index)
		if si.name == "parec" and si.proplist['application.process.id']==str(self.pid):
			log("pasp: parec stream found")
			if self.cur_eq_index is not None:
				# move parec stream to equalizer and then to output
				log("pasp: move stream parec -> %s -> %s" % (self.cur_eq.name, self.padb.output_sink.name))

				self.pc.move_sink_input(index , self.cur_eq_index)
				self.pc.move_sink_input(self.cur_eq_stream , self.padb.output_sink.index)


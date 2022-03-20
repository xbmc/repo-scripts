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
#   ----------
#   | socket |-- 
#   ----------  |   ---------    -----------    ------------------
#               --->| queue | -> | forward | -> | MessageCentral |
#   --------    |   ---------    -----------    ------------------
#   | pulse | --                       
#   --------
#
#   socket: messages coming from client, socket read is blocking, therefore has it's own thread
#   pulse:  messages coming from pulseaudio, palisten is blocking, therefore has it's own thread
#   queue: decouple incoming messages from their listening threads
#   forward: send messages to MessageCentral, send timeout message 100ms after last pulseaudio message 
#

import sys
import os
import time
import json
import pickle

import pulsectl

from threading import Thread

if sys.version_info[0] < 3:
	from Queue import Queue, Empty
else:
	from queue import Queue, Empty

from helper import *

from .pacentral import MessageCentral


class PulseInterfaceService():
	
	def __init__(self, gid = 0):
		self.service_owner = False
		self.running = False
		self.pulseloop = False
	
		self.gid = gid
		self.sock = SocketCom("server")

		self.q = Queue()
		self.mc = MessageCentral()

		#allow only one instance of the server
		if not self.sock.is_server_running():
			self.start_event_loop()
			self.service_owner = True
		else: 
			log("server alreay running, don't start")
	
	#start all message loops
	def start_event_loop(self):
		self.running = True
		Thread(target=self.message_forward).start()
		Thread(target=self.start_pulse_loop).start()
		self.sock.start_server(self.on_socket_message)

	#stop all message loops
	def stop_event_loop(self):
		if self.running:
			self.running = False
			self.pulseloop = True
			self.q.put(('exit','','', None))
			
			self.sock.stop_server()
			
			self.send_message_to_central('message','exit')
			self.pulse_event.close()


	#
	#	support functions
	#

	def handle(self, e):
		func_name = sys._getframe(1).f_code.co_name
		error_type = type(e)
		logerror("pulse_event_manager: %s %s %s" % (func_name, error_type, e.message))
	
	def send_message_to_central(self, target, func, param = '', conn = None):
		# create a new thread per message. So message_forward thread will not crash in case of message handling crash
		th = Thread(target=self.mc.on_message, args=(target, func, param, conn))
		th.start()
		th.join()
		if conn: conn.close()

	#
	#	message loops
	#
	
	def on_socket_message(self, conn, msg):
		try:
			func,target,args = pickle.loads(msg)
			log("receive from socket: %s" % repr([func,target,args]))
			
			if target == "service" and func == "stop" and args[0]== self.gid:
				log("stop_service received - stopping service")
				conn.close()
				self.stop_event_loop()
				
			
			self.q.put((target, func, args, conn))

		except Exception as e: handle(e)


	#messages from pulse audio
	def pulse_event_receive(self,event):
			if event.facility._value in ["server", "source", "source_output"]: return
			self.q.put((event.facility._value ,event.t._value, [event.index], None))

	#start message loop for pulse audio		
	def start_pulse_loop(self):
		log("start pulse loop")
		cnt = 1
		while True:
			try:
				self.pulse_event = pulsectl.Pulse('Event Manager')

				log("connected to pulse")
				cnt = 1

				self.pulse_event.event_mask_set('all')
				self.pulse_event.event_callback_set(self.pulse_event_receive)
				self.send_message_to_central('pulse','connect')
				self.pulse_event.event_listen()
			
			except pulsectl.PulseDisconnected:
					log("pulse disconnected")
					if not self.running: 
						self.pulseloop = False
						log("stop pulse loop")
						return
			except Exception as e: 
				if cnt > 0:
					handle(e)
					cnt = cnt - 1
				
			if not self.running: return
			
			time.sleep(0.5)
			
	#
	#	message forward
	#
	#	message from pulse may arrive to late/ quick for our message handling.
	#	therefore collect them and process them 100ms after the last message.
	
	def message_forward(self):
		log("start message_dispatch")

		timeout = None
		while True:
			try:
				try:
					target, func ,param, conn = self.q.get(timeout = timeout)
				
				except Empty:
					# we did not receive any message since 100 ms. Send this info to 
					# message collector. Message collector will then process the previouse
					# collected messages

					t = time.time()  

					self.send_message_to_central('pa','update')
					timeout = None

					log("pa_updated: time needed {:2f} ms".format((time.time()-t)*1000))
					continue
				except Exception as e: handle(e)
					
				
				if target == "exit": break
				
				if conn is None: timeout = 0.1   

				self.send_message_to_central(target, func, param, conn)
				
				self.q.task_done()
				
			except Exception as e: handle(e)


		log("stop message_dispatch")


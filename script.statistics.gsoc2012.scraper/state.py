class StateManager(object):
	def __init__(self):
		self.stack = list()
		self.active = None

	def switchTo(self, state):
		state.sm = self

		if self.active != None:
			self.active.close()
			self.stack.append(state)
		else:
			self.active = state

	def doModal(self):
		while self.active != None:
			self.active.doModal()
			self.active = None

			if len(self.stack) > 0:
				self.active = self.stack.pop(0)

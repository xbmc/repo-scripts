""" Compatibility class """

import sha
import md5 as md5_



class sha1:
	def __init__(self, var):
		self.var = var
	def hexdigest(self):
		return sha.new(self.var).hexdigest()

class md5:
	def __init__(self, var):
		self.var = var
	def hexdigest(self):
		return md5_.new(self.var).hexdigest()

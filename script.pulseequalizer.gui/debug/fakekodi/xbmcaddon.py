import os

class Addon():
	def __init__(self):
		pass

	def getAddonInfo(self,info):
		if info == 'path':
			return os.getcwd()

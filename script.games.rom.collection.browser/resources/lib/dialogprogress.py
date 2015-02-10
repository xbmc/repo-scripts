
import xbmcgui


class ProgressDialogGUI:
	
	def __init__(self):
		self.itemCount = 0
		self.dialog = xbmcgui.DialogProgress()				
			
	def writeMsg(self, line1, line2, line3, count=0):
		if (not count):
			self.dialog.create(line1)
		elif (count > 0 and self.itemCount != 0):
			percent = int(count * (float(100) / self.itemCount))			
			self.dialog.update(percent, line1, line2, line3)
			if (self.dialog.iscanceled()):
				return False
			else: 
				return True
		else:
			self.dialog.close()
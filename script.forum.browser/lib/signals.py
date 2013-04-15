import xbmc, xbmcaddon, os, filelock
from util import LOG, ERROR, getSettingExternal, setSettingExternal

DEBUG = False

SIGNAL_COUNTER = 0

SIGNAL_CACHE_PATH = os.path.join(xbmc.translatePath(xbmcaddon.Addon(id='script.forum.browser').getAddonInfo('profile')),'cache','signals')

class SignalHub(xbmc.Monitor): # @UndefinedVariable
	def __init__(self):
		self.currID = 0
		self.registry = {}
		self._lastSignal = ''
		clearSignals()
		xbmc.Monitor.__init__(self)  # @UndefinedVariable
		
	def registerReceiver(self,signal,registrant,callback):
		self.setRegistrantID(registrant)
		if DEBUG: LOG('SignalHub registering signal %s: [%s] %s' % (signal,registrant._receiverID,registrant.__class__.__name__))
		if signal in self.registry:
			self.registry[signal].append((registrant,callback))
		else:
			self.registry[signal] = [(registrant,callback)]
			
	def registerSelfReceiver(self,signal,registrant,callback):
		self.setRegistrantID(registrant)
		signal = signal + '.' + str(registrant._receiverID)
		return self.registerReceiver(signal, registrant, callback)
	
	def setRegistrantID(self,registrant):
		if not hasattr(registrant,'_receiverID'):
			registrant._receiverID = self.currID
			self.currID += 1
		
	def unRegister(self,signal,registrant):
		if signal and not signal in self.registry: return
		if signal:
			signals = [signal]
		else:
			signals = self.registry.keys()
			
		for signal in signals:
			i=0
			for reg, cb in self.registry[signal]:  # @UnusedVariable
				if reg._receiverID == registrant._receiverID:
					if DEBUG: LOG('SignalHub un-registering signal %s: [%s] %s' % (signal,registrant._receiverID,registrant.__class__.__name__))
					self.registry[signal].pop(i)
					break
				i+=1
				
	def unSelfRegister(self,signal,registrant):
		signal = signal + '.' + str(registrant._receiverID)
		return self.unRegister(signal, registrant)
	
	def validSignal(self):
		trigger = getSettingExternal('SignalHubSignal')
		if trigger == self._lastSignal: return False
		self._lastSignal = trigger
		return True
	
	def onSettingsChanged(self):
		if not self.validSignal(): return
		signals = getSignals()
		if not signals: return
		if DEBUG:
			import threading
			LOG('SignalHub: Thread: %s' % str(threading.currentThread().getName()))
			if len(signals) > 1: LOG('SignalHub: Multiple signals: %s' % len(signals))
			
		for signal in signals:
			if not ':' in signal: continue
			signal,data = signal.split(':',1)
			
			if not signal in self.registry: return
			for reg,cb in self.registry[signal]:  # @UnusedVariable
				if DEBUG: LOG('SignalHub: Callback in response to signal %s for [%s] %s (%s)' % (signal,reg._receiverID,reg.__class__.__name__,data))
				try:
					cb(signal,data)
				except:
					ERROR('SignalHub: Callback Error')
					continue
		
def clearSignals():
	f = open(SIGNAL_CACHE_PATH,'w')
	f.write('')
	f.close()
	
def getSignals():
	lock = filelock.FileLock(SIGNAL_CACHE_PATH, timeout=5,delay=0.1)
	lock.acquire()
	f = open(SIGNAL_CACHE_PATH,'r+')
	signals = f.read()
	f.truncate(0)
	f.close()
	if not signals: return []
	return signals.split('\n')
	lock.release()
	del lock

def addSignal(signal):
	signals = getSignals()
	signals.append(signal)
	
	lock = filelock.FileLock(SIGNAL_CACHE_PATH, timeout=5, delay=0.1)
	lock.acquire()
	f = open(SIGNAL_CACHE_PATH,'w')
	f.write('\n'.join(signals))
	f.close()
	lock.release()
	del lock
	
def sendSignal(signal,data=''):
	addSignal(signal + ':' + str(data))
	global SIGNAL_COUNTER
	setSettingExternal('SignalHubSignal',str(SIGNAL_COUNTER))
	SIGNAL_COUNTER+=1
	if DEBUG: LOG('SignalHub: Sending signal %s (%s)' % (signal,data))
	
def sendSelfSignal(sender,signal,data=''):
	if not hasattr(sender,'_receiverID'): return
	signal = signal + '.' + str(sender._receiverID)
	return sendSignal(signal,data)

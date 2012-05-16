import xbmc, xbmcgui, os
import socket

captureWidth = 132

try:
    if xbmc.CAPTURE_STATE_DONE:
        pass
except:
    sys.exit(1)

class CapturePlayer(xbmc.Player):

    def onPlayBackStarted(self):	
		capture = xbmc.RenderCapture()	
		captureHeight = captureWidth / capture.getAspectRatio()	
		capture.capture(int(captureWidth), int(captureHeight), xbmc.CAPTURE_FLAG_CONTINUOUS)		
		while self.isPlayingVideo() and not xbmc.abortRequested:
			capture.waitForCaptureStateChangeEvent(1000)
			if capture.getCaptureState() == xbmc.CAPTURE_STATE_DONE:
			
				pixelsMessage = []
				pixelsMessage.append('Image,')
				pixelsMessage.append('Width,%04d,'%(capture.getWidth()))
				pixelsMessage.append('Height,%04d,'%(capture.getHeight()))
				pixelsMessage.append('Format,%s,'%(capture.getImageFormat()))
				pixelsMessage.append(str(capture.getImage()))	
				pixelsMessage.append('\r\n')				
				
				udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				udpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
				udpSocket.sendto(''.join(pixelsMessage), ('127.0.0.1', 52101))
				udpSocket.close()
	
player = CapturePlayer()
while not xbmc.abortRequested:
    xbmc.sleep(1000)
player = None
'''
    Kodi video capturer for Hyperion

	Copyright (c) 2013-2016 Hyperion Team

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in
	all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
	THE SOFTWARE.
'''
import socket
import struct

#protobuf message includes
from message_pb2 import HyperionRequest
from message_pb2 import HyperionReply
from message_pb2 import ColorRequest
from message_pb2 import ImageRequest
from message_pb2 import ClearRequest

class Hyperion(object):
    '''Hyperion connection class
    
    A Hyperion object will connect to the Hyperion server and provide
    easy to use functions to send requests
    
    Note that the function will block until a reply has been received
    from the Hyperion server (or the call has timed out)
    '''
    
    def __init__(self, server, port):
        '''Constructor
        - server : server address of Hyperion
        - port   : port number of Hyperion
        '''
        # create a new socket
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.settimeout(2)

        # Connect socket to the provided server
        self.__socket.connect((server, port))

    def __del__(self):
        '''Destructor
        '''
        # close the socket
        self.__socket.close()

    def sendColor(self, color, priority, duration = -1):
        '''Send a static color to Hyperion
        - color    : integer value with the color as 0x00RRGGBB
        - priority : the priority channel to use
        - duration : duration the leds should be set
        ''' 
        # create the request
        request = HyperionRequest()
        request.command = HyperionRequest.COLOR
        colorRequest = request.Extensions[ColorRequest.colorRequest]
        colorRequest.rgbColor = color
        colorRequest.priority = priority
        colorRequest.duration = duration

        # send the message 
        self.__sendMessage(request)
        
    def sendImage(self, width, height, data, priority, duration = -1):
        '''Send an image to Hyperion
        - width    : width of the image
        - height   : height of the image
        - data     : image data (byte string containing 0xRRGGBB pixel values)
        - priority : the priority channel to use
        - duration : duration the leds should be set
        ''' 
        # create the request
        request = HyperionRequest()
        request.command = HyperionRequest.IMAGE
        imageRequest = request.Extensions[ImageRequest.imageRequest]
        imageRequest.imagewidth = width
        imageRequest.imageheight = height
        imageRequest.imagedata = str(data)
        imageRequest.priority = priority
        imageRequest.duration = duration

        # send the message 
        self.__sendMessage(request)
        
    def clear(self, priority):
        '''Clear the given priority channel
        - priority : the priority channel to clear
        '''
        # create the request
        request = HyperionRequest()
        request.command = HyperionRequest.CLEAR
        clearRequest = request.Extensions[ClearRequest.clearRequest]
        clearRequest.priority = priority

        # send the message 
        self.__sendMessage(request)
    
    def clearall(self):
        '''Clear all active priority channels
        '''
        # create the request
        request = HyperionRequest()
        request.command = HyperionRequest.CLEARALL

        # send the message 
        self.__sendMessage(request)
        
    def __sendMessage(self, message):
        '''Send the given proto message to Hyperion. A RuntimeError will 
        be raised if the reply contains an error
        - message : proto request to send
        '''
        #print "send message to Hyperion (%d):\n%s" % (len(message.SerializeToString()), message)

        # send message to Hyperion"
        binaryRequest = message.SerializeToString()
        binarySize = struct.pack(">I", len(binaryRequest))
        self.__socket.sendall(binarySize)
        self.__socket.sendall(binaryRequest);
        
        # receive a reply from Hyperion
        size = struct.unpack(">I", self.__socket.recv(4))[0]
        reply = HyperionReply()
        reply.ParseFromString(self.__socket.recv(size))
        
        # check the reply
        #print "Reply received:\n%s" % (reply)
        if not reply.success:
            raise RuntimeError("Hyperion server error: " + reply.error)
        
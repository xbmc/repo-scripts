import os


class Options:
	format = None
	
	frame_rate = None # the frame rate of a movie in fps.
	frame_height = None	# the height of the movie in pixels.
	frame_width = None	# the width of the movie in pixels.	
		
	video_bitrate = None # the bit rate of the video in bits per second.
	audio_bitrate = None # the audio bit rate of the media file in bits per second.
	audio_sample_rate = None # the audio sample rate of the media file in bits per second.
		
	video_codec = None # the name of the video codec used to encode this movie as a string.
	audio_codec = None # the name of the audio codec used to encode this movie as a string.
	
	def __repr__(self):
		return ' '.join(build_ffmpeg_args(self))


class FFMPEGArgsBulder:
	def __init__(self, input_filename, output_filename, options):
		self.input_filename = input_filename
		self.output_filename = output_filename
		self.options = options
		self.args = []
	
	def build_ffmpeg_args(self):
		options, args = self.options, self.args
		if not self.input_filename:
			assert False
		args += ['-y', '-i', self.input_filename]
		if not self.output_filename:
			return args
		if options:
			if options.video_codec:
				args += ['-acodec', options.video_codec]
			if options.video_codec:
				args += ['-vcodec', options.video_codec]
			if options.video_bitrate:
				args += ['-b', str(options.video_bitrate)]
			if options.audio_bitrate:
				args += ['-ab', str(options.audio_bitrate)]
			if options.frame_rate:
				args += ['-r', str(options.frame_rate)]
			if options.frame_width and options.frame_height:
				args += ['-s', '%sx%s' % (options.frame_width, options.frame_height)]
		args += [self.output_filename]
		return args
		
	
def build_ffmpeg_args(input_filename, output_filename=None, options=None):
	return FFMPEGArgsBulder(input_filename, output_filename, options).build_ffmpeg_args()

import logging
import re

log = logging.getLogger('mythbox.core')

class Metadata:
    duration = None # the duration of a movie or audio file in seconds.
    frame_count = None # the number of frames in a movie or audio file.
    frame_rate = None # the frame rate of a movie in fps.
    frame_height = None    # the height of the movie in pixels.
    frame_width = None    # the width of the movie in pixels.
    
    format = None # the pixel format of the movie.
    
    bit_rate = None # the bit rate of the video in bits per second.
    audio_sample_rate = None # the audio sample rate of the media file in bits per second.
    
    pixel_format = None    
    video_codec = None # the name of the video codec used to encode this movie as a string.
    audio_codec = None # the name of the audio codec used to encode this movie as a string.
    audio_channels = None # the number of audio channels in this movie as an integer.
    has_audio = None # boolean value indicating whether the movie has an audio stream.
    
    def __repr__(self):
        return str(self.__dict__)


class FFMPEGMetadataParser:
    # Input #0, flv, from 'foo.flv':
    INPUT_PATTERN = re.compile(r'^\s*Input #\d+,.*$')
    
    # Duration: 00:51:31.9, start: 0.000000, bitrate: 348 kb/s
    DURATION_PATTERN = re.compile(r'^\s*Duration: (.*?), start: (.*?), bitrate: (.*)$')
    
    # Stream #0.0: Audio: mp3, 44100 Hz, stereo
    AUDIO_STREAM_PATTERN = re.compile(r'^\s*Stream\s+#\d+\.\d+:\s+Audio(.*)$')
    
    # Stream #0.1: Video: vp6f, yuv420p, 368x288,  0.17 fps(r)
    #VIDEO_STREAM_PATTERN = re.compile(r'^\s*Stream\s+#\d+\.\d+:\s+Video(.*)$')
    
    # Stream #0.0[0x31]: Video: mpeg2video, yuv420p, 1280x720, 80000 kb/s, 59.94 fps(r)
    # Stream #0.0[0x1011]: Video: h264, yuv420p, 1280x720, 59.94 fps(r)
    # Stream #0.0[0x1011]: Video: h264, yuv420p, 1280x720 [PAR 1:1 DAR 16:9], 59.94 tbr, 90k tbn, 119.88 tbc
    # Stream #0.0[0x31]: Video: mpeg2video, yuv420p, 1280x720 [PAR 1:1 DAR 16:9], 65000 kb/s, 59.94 tbr, 90k tbn, 119.88 tbc
    # Stream #0.0[0x800]: Video: mpeg2video, yuv420p, 1920x1080 [PAR 1:1 DAR 16:9], 38810 kb/s, 29.97 fps, 29.97 tbr, 90k tbn, 59.94 tbc
    # Stream #0.0[0x31]: Video: mpeg2video, yuv420p, 1280x720 [PAR 1:1 DAR 16:9], 24000 kb/s, 81.76 fps, 59.94 tbr, 90k tbn, 119.88 tbc
    VIDEO_STREAM_PATTERN = re.compile(r'^\s*Stream\s+#\d+\.\d+.*:\s+Video(.*)$')
    
    def __init__(self, filelike):
        self.filelike = filelike
        self.raw_metadata_lines = []
        self.metadata = None
        
    def parse_duration(self, line):
        log.debug('parse_duration: %s' % line)
        metadata = self.metadata
        duration, start, bitrate = self.DURATION_PATTERN.match(line).groups()
        metadata.duration = duration
        metadata.start = start
        metadata.bitrate = bitrate
    
    def parse_audio_stream(self, line):
        log.debug('parse_audio_stream: %s' % line)
        metadata = self.metadata
        audio_codec, sample_rate = [each.strip() for each in self.AUDIO_STREAM_PATTERN.match(line).groups()[0].split(',')][:2]
        metadata.audio_codec = audio_codec
        metadata.sample_rate = sample_rate
        
    def parse_video_stream(self, line):
        log.debug('parse_video_stream: %s' % line)
        metadata = self.metadata
        video_tokens = self.VIDEO_STREAM_PATTERN.match(line).groups()[0].split(',')
        frame_rate2 = None
        
        if len(video_tokens) in (4, 6):
            video_codec, pixel_format, dimension, frame_rate = [each.strip() for each in video_tokens[:4]]
        elif len(video_tokens) in (5,):
            video_codec, pixel_format, dimension, bit_rate, frame_rate = [each.strip() for each in video_tokens[:5]]
        elif len(video_tokens) in (7,8,):
            video_codec, pixel_format, dimension, bit_rate, frame_rate, frame_rate2 = [each.strip() for each in video_tokens[:6]]
        else:
            raise Exception('Could not extract framerate from line with %d tokens: %s' % (len(video_tokens), line))
        
        metadata.video_codec = video_codec
        metadata.pixel_format = pixel_format
        metadata.dimension = dimension
        # jacked up ffmpeg in maverick keeps on changing output format
        if frame_rate and frame_rate2 and 'fps' in frame_rate and 'tbr' in frame_rate2:
            metadata.frame_rate = frame_rate2.split(' ')[0]
        elif frame_rate:
            metadata.frame_rate = frame_rate.split(' ')[0]  # extract first word
        
    def parse_input(self, line):
        log.debug('parse_input: %s' % line)
        metadata = Metadata()
        metadata.format = line.split(',')[1].strip()
        self.metadata = metadata
    
    def parse_line(self, line):
        match_any = True
        if self.INPUT_PATTERN.match(line):
            self.parse_input(line)
        elif self.DURATION_PATTERN.match(line):
            self.parse_duration(line)
        elif self.AUDIO_STREAM_PATTERN.match(line):
            self.parse_audio_stream(line)
        elif self.VIDEO_STREAM_PATTERN.match(line):
            self.parse_video_stream(line)
        else:
            match_any = False
        if match_any:
            self.raw_metadata_lines.append(line)
    
    def get_metadata(self):
        for line in self.filelike:
            self.parse_line(line.strip())
        return self.metadata


def parse_ffmpeg_metadata(filelike):
    return FFMPEGMetadataParser(filelike).get_metadata()

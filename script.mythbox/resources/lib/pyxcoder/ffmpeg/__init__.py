from subprocess import Popen
from subprocess import PIPE
from ffmpeg.options import Options
from ffmpeg.options import build_ffmpeg_args
from ffmpeg.metadata import parse_ffmpeg_metadata

import tempfile
import os

BUF_SIZE = 4096


class FFMPEG:
    
    def __init__(self, ffmpeg='ffmpeg', closeFDs=True, *args, **kwargs):
        self.ffmpeg = ffmpeg
        self.closeFDs = closeFDs
        self.windows = kwargs.has_key('windows') and kwargs['windows'] == True
        self.tempdir = kwargs.get('tempdir', tempfile.gettempdir())
        
    def get_metadata(self, input_filename):
        args = build_ffmpeg_args(input_filename)
        #
        # Nasty windows hack since Popen doesn't work in XBMC for Windows
        #
        if True:
            outfile = os.path.join(self.tempdir, os.path.basename(input_filename)) + '.out'
            
            # 
            # If output exists from a previous run, use it
            #
            if os.path.exists(outfile):
                print 'Using cached ffmpeg output for %s' % input_filename
            else:
                outfileQuoted = '"' + outfile + '"'
                print 'outfile = %s' % outfileQuoted
                #'start /B /WAIT /MIN ' +
                
                #print 'ffmpeg = %s' % self.ffmpeg
                #print 'input  = %s' % input_filename
                #print 'outfile = %s' % outfileQuoted
                
                if self.windows:
                    # Crappy windows needs extra set of quotes - see Issue 79
                    cmd = '"' + '"' + self.ffmpeg + '"' + ' -i ' + '"' + input_filename + '"' + ' 2>' + outfileQuoted + '"'
                else:
                    cmd = '"' + self.ffmpeg + '"' + ' -i ' + '"' + input_filename + '"' + ' 2>' + outfileQuoted
                
                print 'cmd = %s' % cmd
                result = os.system(cmd)
                print 'os.system = %s' % result
                    
            child_stderr = open(outfile)
        else:
            (child_stdout, child_stderr) = self.exec_ffmpeg(args)
        return parse_ffmpeg_metadata(child_stderr)
        
    def transcode(self, input_filename, output_filename, options=None):
        args = build_ffmpeg_args(input_filename, output_filename)
        self.exec_ffmpeg(args)
    
    def get_frame_as_jpeg(self, input_filename, output_filename, frame_number=1):
        args = ['-i', input_filename, '-ss', '00:00:00', '-vframes', '1', '-f', 'mjpeg', output_filename]
        print self.exec_ffmpeg(args)[1].read()
    
    def exec_ffmpeg(self, args):
        args = [self.ffmpeg] + args
        print ' '.join(args)
        p = Popen(args, shell=False, bufsize=BUF_SIZE, stderr=PIPE, stdout=PIPE, close_fds=self.closeFDs)
        p.wait()
        return (p.stdout, p.stderr)

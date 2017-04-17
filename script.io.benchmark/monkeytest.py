#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of I/O Benchmark.
#
# I/O Benchmark is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# I/O Benchmark is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with I/O Benchmark.  If not, see <http://www.gnu.org/licenses/>.

'''
Adapted from https://github.com/thodnev/MonkeyTest
I/O Benchmark -- test your hard drive read-write speed in Python
A simplistic script to show that such system programming
tasks are possible and convenient to be solved in Python

I haven't done any command-line arguments parsing, so
you should configure it using the constants below.

The file is being created, then Wrote with random data, randomly read
and deleted, so the script doesn't waste your drive

(!) Be sure, that the file you point to is not smthng
    you need, cause it'll be overWrote during test

Runs on both Python3 and 2, despite that I prefer 3
Has been tested on 3.5 and 2.7 under ArchLinux
'''

import os, sys
from random import shuffle

try:                    # if Python >= 3.3 use new high-res counter
    from time import perf_counter as time
except ImportError:     # else select highest available resolution counter
    if sys.platform[:3] == 'win':
        from time import clock as time
    else:
        from time import time

# change the constants below according to your needs
WRITE_MB       = 128    # total MBs Wrote during test
WRITE_BLOCK_KB = 1024   # KBs in each write block
READ_BLOCK_B   = 512    # bytes in each read block (high values may lead to
                        # invalid results because of system I/O scheduler        
                        # file must be at drive under test
 
def write_test(file, block_size, blocks_count, show_progress=None):
    '''
    Tests write speed by writing random blocks, at total quantity
    of blocks_count, each at size of block_size bytes to disk.
    Function returns a list of write times in sec of each block.
    '''
    f = os.open(file, os.O_CREAT|os.O_WRONLY, 0o777) # low-level I/O

    took = []
    for i in range(blocks_count): 
        if show_progress:    
            if (show_progress.iscanceled()) == True:
                return
            show_progress.update(int((i+1)*100/blocks_count),"Writing...",file)
        buff = os.urandom(block_size)
        start = time()
        os.write(f, buff)
        os.fsync(f)	# force write to disk
        t = time() - start
        took.append(t)
    os.close(f)
    return took

def read_test(file, block_size, blocks_count, show_progress=None):
    '''
    Performs read speed test by reading random offset blocks from
    file, at maximum of blocks_count, each at size of block_size
    bytes until the End Of File reached.
    Returns a list of read times in sec of each block.
    '''
    f = os.open(file, os.O_RDONLY, 0o777) # low-level I/O
    # generate random read positions
    offsets = list(range(0, blocks_count*block_size, block_size))
    shuffle(offsets)
    took = []
    for i, offset in enumerate(offsets, 1):
        if show_progress and i % int(WRITE_BLOCK_KB*1024/READ_BLOCK_B) == 0:    
            if (show_progress.iscanceled()) == True:
                return
            # read is faster than write, so try to equalize print period
            show_progress.update(int((i+1)*100/blocks_count),"Reading...",file)
        start = time()
        os.lseek(f, offset, os.SEEK_SET) # set position
        buff = os.read(f, block_size) # read from position
        t = time() - start
        if not buff: break # if EOF reached
        took.append(t)
    os.close(f)
    return took
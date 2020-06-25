# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements a class with methods related to the Chrome OS image"""

from __future__ import absolute_import, division, unicode_literals
import os
from struct import calcsize, unpack
from zipfile import ZipFile
from io import UnsupportedOperation

from ..kodiutils import exists, localize, log, mkdirs
from .. import config
from ..unicodes import compat_path


class ChromeOSImage:
    """
    The main class handling a Chrome OS image

    Information related to ext2 is sourced from here: https://www.nongnu.org/ext2-doc/ext2.html
    """

    def __init__(self, imgpath):
        """Prepares the image"""
        self.imgpath = imgpath
        self.bstream = self.get_bstream(imgpath)
        self.part_offset = None
        self.sb_dict = None
        self.blocksize = None
        self.blk_groups = None
        self.progress = None

    def gpt_header(self):
        """Returns the needed parts of the GPT header, can be easily expanded if necessary"""
        header_fmt = '<8s4sII4x4Q16sQ3I'
        header_size = calcsize(header_fmt)
        lba_size = config.CHROMEOS_BLOCK_SIZE  # assuming LBA size
        self.seek_stream(lba_size)

        # GPT Header entries: signature, revision, header_size, header_crc32, (reserved 4x skipped,) current_lba, backup_lba,
        #                     first_usable_lba, last_usable_lba, disk_guid, start_lba_part_entries, num_part_entries,
        #                     size_part_entry, crc32_part_entries
        _, _, _, _, _, _, _, _, _, start_lba_part_entries, num_part_entries, size_part_entry, _ = unpack(header_fmt, self.read_stream(header_size))

        return (start_lba_part_entries, num_part_entries, size_part_entry)

    def chromeos_offset(self):
        """Calculate the Chrome OS losetup start offset"""
        part_format = '<16s16sQQQ72s'
        entries_start, entries_num, entry_size = self.gpt_header()  # assuming partition table is GPT
        lba_size = config.CHROMEOS_BLOCK_SIZE  # assuming LBA size
        self.seek_stream(entries_start * lba_size)

        if not calcsize(part_format) == entry_size:
            log(4, 'Partition table entries are not 128 bytes long')
            return 0

        for index in range(1, entries_num + 1):  # pylint: disable=unused-variable
            # Entry: type_guid, unique_guid, first_lba, last_lba, attr_flags, part_name
            _, _, first_lba, _, _, part_name = unpack(part_format, self.read_stream(entry_size))
            part_name = part_name.decode('utf-16').strip('\x00')
            if part_name == 'ROOT-A':  # assuming partition name is ROOT-A
                offset = first_lba * lba_size
                break

        if not offset:
            log(4, 'Failed to calculate losetup offset.')
            return 0

        return offset

    def extract_file(self, filename, extract_path, progress):
        """Extracts the file from the image"""
        self.progress = progress

        self.progress.update(2, localize(30060))
        self.part_offset = self.chromeos_offset()
        self.sb_dict = self.superblock()
        self.blk_groups = self.block_groups()

        bin_filename = filename.encode('ascii')
        chunksize = 4 * 1024**2
        percent8 = 40
        self.progress.update(int(percent8 / 8), localize(30061))
        chunk1 = self.read_stream(chunksize)
        while True:
            chunk2 = self.read_stream(chunksize)
            if not chunk2:
                log(4, 'File {filename} not found in the ChromeOS image', filename=filename)
                return False

            chunk = chunk1 + chunk2
            if bin_filename in chunk:
                i_index_pos = chunk.index(bin_filename) - 8
                dir_dict = self.dir_entry(chunk[i_index_pos:i_index_pos + len(filename) + 8])
                if dir_dict['inode'] < self.sb_dict['s_inodes_count'] and dir_dict['name_len'] == len(filename):
                    break
            chunk1 = chunk2
            if percent8 < 240:
                percent8 += 1
                self.progress.update(int(percent8 / 8))

        self.progress.update(32, localize(30062))

        blk_group_num = (dir_dict['inode'] - 1) // self.sb_dict['s_inodes_per_group']
        blk_group = self.blk_groups[blk_group_num]
        i_index_in_group = (dir_dict['inode'] - 1) % self.sb_dict['s_inodes_per_group']

        inode_pos = self.part_offset + self.blocksize * blk_group['bg_inode_table'] + self.sb_dict['s_inode_size'] * i_index_in_group
        inode_dict, _ = self.inode_table(inode_pos)

        return self.write_file(inode_dict, os.path.join(extract_path, filename))

    def superblock(self):
        """Get relevant info from the superblock, assert it's an ext2 fs"""
        names = ('s_inodes_count', 's_blocks_count', 's_r_blocks_count', 's_free_blocks_count', 's_free_inodes_count', 's_first_data_block',
                 's_log_block_size', 's_log_frag_size', 's_blocks_per_group', 's_frags_per_group', 's_inodes_per_group', 's_mtime', 's_wtime',
                 's_mnt_count', 's_max_mnt_count', 's_magic', 's_state', 's_errors', 's_minor_rev_level', 's_lastcheck', 's_checkinterval',
                 's_creator_os', 's_rev_level', 's_def_resuid', 's_def_resgid', 's_first_ino', 's_inode_size', 's_block_group_nr',
                 's_feature_compat', 's_feature_incompat', 's_feature_ro_compat', 's_uuid', 's_volume_name', 's_last_mounted',
                 's_algorithm_usage_bitmap', 's_prealloc_block', 's_prealloc_dir_blocks')
        fmt = '<13I6H4I2HI2H3I16s16s64sI2B818x'
        fmt_len = calcsize(fmt)

        self.seek_stream(self.part_offset + 1024)  # superblock starts after 1024 byte
        pack = self.read_stream(fmt_len)
        sb_dict = dict(zip(names, unpack(fmt, pack)))

        sb_dict['s_magic'] = hex(sb_dict['s_magic'])
        assert sb_dict['s_magic'] == '0xef53'  # assuming/checking this is an ext2 fs

        block_groups_count1 = sb_dict['s_blocks_count'] / sb_dict['s_blocks_per_group']
        block_groups_count1 = int(block_groups_count1) if float(int(block_groups_count1)) == block_groups_count1 else int(block_groups_count1) + 1
        block_groups_count2 = sb_dict['s_inodes_count'] / sb_dict['s_inodes_per_group']
        block_groups_count2 = int(block_groups_count2) if float(int(block_groups_count2)) == block_groups_count2 else int(block_groups_count2) + 1
        assert block_groups_count1 == block_groups_count2
        sb_dict['block_groups_count'] = block_groups_count1

        self.blocksize = 1024 << sb_dict['s_log_block_size']

        return sb_dict

    def block_group(self):
        """Get info about a block group"""
        names = ('bg_block_bitmap', 'bg_inode_bitmap', 'bg_inode_table', 'bg_free_blocks_count', 'bg_free_inodes_count', 'bg_used_dirs_count', 'bg_pad')
        fmt = '<3I4H12x'
        fmt_len = calcsize(fmt)

        pack = self.read_stream(fmt_len)
        blk = unpack(fmt, pack)

        blk_dict = dict(zip(names, blk))

        return blk_dict

    def block_groups(self):
        """Get info about all block groups"""
        if self.blocksize == 1024:
            self.seek_stream(self.part_offset + 2 * self.blocksize)
        else:
            self.seek_stream(self.part_offset + self.blocksize)

        blk_groups = []
        for i in range(self.sb_dict['block_groups_count']):  # pylint: disable=unused-variable
            blk_group = self.block_group()
            blk_groups.append(blk_group)

        return blk_groups

    def inode_table(self, inode_pos):
        """Reads and returns an inode table and inode size"""
        names = ('i_mode', 'i_uid', 'i_size', 'i_atime', 'i_ctime', 'i_mtime', 'i_dtime', 'i_gid', 'i_links_count', 'i_blocks', 'i_flags',
                 'i_osd1', 'i_block0', 'i_block1', 'i_block2', 'i_block3', 'i_block4', 'i_block5', 'i_block6', 'i_block7', 'i_block8',
                 'i_block9', 'i_block10', 'i_block11', 'i_blocki', 'i_blockii', 'i_blockiii', 'i_generation', 'i_file_acl', 'i_dir_acl', 'i_faddr')
        fmt = '<2Hi4I2H3I15I4I12x'
        fmt_len = calcsize(fmt)
        inode_size = self.sb_dict['s_inode_size']

        self.seek_stream(inode_pos)
        pack = self.read_stream(fmt_len)
        inode = unpack(fmt, pack)

        inode_dict = dict(zip(names, inode))
        inode_dict['i_mode'] = hex(inode_dict['i_mode'])

        blocks = inode_dict['i_size'] / self.blocksize
        inode_dict['blocks'] = int(blocks) if float(int(blocks)) == blocks else int(blocks) + 1

        self.read_stream(inode_size - fmt_len)
        return inode_dict, inode_size

    @staticmethod
    def dir_entry(chunk):
        """Returns the directory entry found in chunk"""
        dir_names = ('inode', 'rec_len', 'name_len', 'file_type', 'name')
        dir_fmt = '<IHBB' + str(len(chunk) - 8) + 's'

        dir_dict = dict(zip(dir_names, unpack(dir_fmt, chunk)))

        return dir_dict

    def iblock_ids(self, blk_id, ids_to_read):
        """Reads the block indices/IDs from an indirect block"""
        seek_pos = self.part_offset + self.blocksize * blk_id
        self.seek_stream(seek_pos)
        fmt = '<' + str(int(self.blocksize / 4)) + 'I'
        ids = list(unpack(fmt, self.read_stream(self.blocksize)))
        ids_to_read -= len(ids)

        return ids, ids_to_read

    def iiblock_ids(self, blk_id, ids_to_read):
        """Reads the block indices/IDs from a doubly-indirect block"""
        seek_pos = self.part_offset + self.blocksize * blk_id
        self.seek_stream(seek_pos)
        fmt = '<' + str(int(self.blocksize / 4)) + 'I'
        iids = unpack(fmt, self.read_stream(self.blocksize))

        ids = []
        for iid in iids:
            if ids_to_read <= 0:
                break
            ind_block_ids, ids_to_read = self.iblock_ids(iid, ids_to_read)
            ids += ind_block_ids

        return ids, ids_to_read

    def seek_stream(self, seek_pos):
        """Move position of bstream to seek_pos"""
        try:
            self.bstream[0].seek(seek_pos)
            self.bstream[1] = seek_pos
            return

        except UnsupportedOperation:
            chunksize = 4 * 1024**2

            if seek_pos >= self.bstream[1]:
                while seek_pos - self.bstream[1] > chunksize:
                    self.read_stream(chunksize)
                self.read_stream(seek_pos - self.bstream[1])
                return

            self.bstream[0].close()
            self.bstream[1] = 0
            self.bstream = self.get_bstream(self.imgpath)

            while seek_pos - self.bstream[1] > chunksize:
                self.read_stream(chunksize)
            self.read_stream(seek_pos - self.bstream[1])

            return

    def read_stream(self, num_of_bytes):
        """Read and return a chunk of the bytestream"""
        self.bstream[1] += num_of_bytes

        return self.bstream[0].read(num_of_bytes)

    def get_block_ids(self, inode_dict):
        """Get all block indices/IDs of an inode"""
        ids_to_read = inode_dict['blocks']
        block_ids = [inode_dict['i_block' + str(i)] for i in range(12)]
        ids_to_read -= 12

        if not inode_dict['i_blocki'] == 0:
            iblocks, ids_to_read = self.iblock_ids(inode_dict['i_blocki'], ids_to_read)
            block_ids += iblocks
        if not inode_dict['i_blockii'] == 0:
            iiblocks, ids_to_read = self.iiblock_ids(inode_dict['i_blockii'], ids_to_read)
            block_ids += iiblocks

        return block_ids[:inode_dict['blocks']]

    def read_file(self, block_ids):
        """Read blocks specified by IDs into a dict"""
        block_dict = {}
        for block_id in block_ids:
            percent = int(35 + 60 * block_ids.index(block_id) / len(block_ids))
            self.progress.update(percent, localize(30048))
            seek_pos = self.part_offset + self.blocksize * block_id
            self.seek_stream(seek_pos)
            block_dict[block_id] = self.read_stream(self.blocksize)

        return block_dict

    @staticmethod
    def write_file_chunk(opened_file, chunk, bytes_to_write):
        """Writes bytes to file in chunks"""
        if len(chunk) > bytes_to_write:
            opened_file.write(chunk[:bytes_to_write])
            return 0

        opened_file.write(chunk)
        return bytes_to_write - len(chunk)

    def write_file(self, inode_dict, filepath):
        """Writes file specified by its inode to filepath"""
        bytes_to_write = inode_dict['i_size']
        block_ids = self.get_block_ids(inode_dict)

        block_ids_sorted = block_ids[:]
        block_ids_sorted.sort()
        block_dict = self.read_file(block_ids_sorted)

        write_dir = os.path.join(os.path.dirname(filepath), '')
        if not exists(write_dir):
            mkdirs(write_dir)

        with open(compat_path(filepath), 'wb') as opened_file:
            for block_id in block_ids:
                bytes_to_write = self.write_file_chunk(opened_file, block_dict[block_id], bytes_to_write)
                if bytes_to_write == 0:
                    return True

        return False

    @staticmethod
    def get_bstream(imgpath):
        """Get a bytestream of the image"""
        if imgpath.endswith('.zip'):
            bstream = ZipFile(compat_path(imgpath), 'r').open(os.path.basename(imgpath).strip('.zip'), 'r')
        else:
            bstream = open(compat_path(imgpath), 'rb')

        return [bstream, 0]

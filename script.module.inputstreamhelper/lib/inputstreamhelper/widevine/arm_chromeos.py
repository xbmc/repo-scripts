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


class ChromeOSError(Exception):
    """Custom Exception if something fails during extraction from ChromeOSImage"""


class ChromeOSImage:
    """
    The main class handling a Chrome OS image

    Information related to ext2 is sourced from here: https://www.nongnu.org/ext2-doc/ext2.html
    """

    def __init__(self, imgpath, progress=None):
        """Prepares the image"""
        self.progress = progress
        if self.progress:
            self.progress.update(2, localize(30060))
        self.imgpath = imgpath
        self.bstream = self._get_bstream(imgpath)
        self.part_offset = self.chromeos_offset()
        self.blocksize = None
        self.sb_dict = self._superblock()
        self.blk_groups = self._block_groups()

    def _gpt_header(self):
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
        entries_start, entries_num, entry_size = self._gpt_header()  # assuming partition table is GPT
        lba_size = config.CHROMEOS_BLOCK_SIZE  # assuming LBA size
        self.seek_stream(entries_start * lba_size)

        if not calcsize(part_format) == entry_size:
            raise ChromeOSError('Partition table entries are not 128 bytes long')

        for _ in range(1, entries_num + 1):
            # Entry: type_guid, unique_guid, first_lba, last_lba, attr_flags, part_name
            _, _, first_lba, _, _, part_name = unpack(part_format, self.read_stream(entry_size))
            part_name = part_name.decode('utf-16').strip('\x00')
            if part_name == 'ROOT-A':  # assuming partition name is ROOT-A
                offset = first_lba * lba_size
                break

        if not offset:
            raise ChromeOSError('Failed to calculate losetup offset.')

        return offset

    def _find_file_in_chunk(self, bfname, chunk):
        """
        Checks if the filename is found in the given chunk.
        Then makes some plausibility checks, to see if it is in fact a proper dentry.

        returns the dentry if found, else False.
        """

        if bfname in chunk:
            i_index_pos = chunk.index(bfname) - 8  # the filename is the last element of the dentry, the elements before are 8 bytes total
            file_entry = self.dir_entry(chunk[i_index_pos:i_index_pos + len(bfname) + 8])  # 8 because see above
            if file_entry['inode'] < self.sb_dict['s_inodes_count'] and file_entry['name_len'] == len(bfname):
                return file_entry

            log(0, 'Found filename, but checks did not pass:')
            log(0, 'inode number: {inode} < {count}, name_len: {name_len} == {len_fname}'.format(inode=file_entry['inode'],
                                                                                                 count=self.sb_dict['s_inodes_count'],
                                                                                                 name_len=file_entry['name_len'],
                                                                                                 len_fname=len(bfname)))
        return False

    def _find_file_naive(self, fname):
        """
        Finds a file by basically searching for the filename as bytes in the bytestream.
        Searches through the whole image only once, making it fast, but may be unreliable at times.

        Returns a directory entry.
        """

        fname_alt = fname + '#new'  # Sometimes the filename has "#new" at the end
        bfname = fname.encode('ascii')
        bfname_alt = fname_alt.encode('ascii')
        chunksize = 4 * 1024**2
        chunk1 = self.read_stream(chunksize)
        while True:
            chunk2 = self.read_stream(chunksize)
            if not chunk2:
                raise ChromeOSError('File {fname} not found in the ChromeOS image'.format(fname=fname))

            chunk = chunk1 + chunk2

            file_entry = self._find_file_in_chunk(bfname, chunk)
            if file_entry:
                break

            file_entry = self._find_file_in_chunk(bfname_alt, chunk)
            if file_entry:
                break

            chunk1 = chunk2

        return file_entry

    def _find_file_properly(self, filename, path_to_file=("opt", "google", "chrome", "WidevineCdm", "_platform_specific", "cros_arm")):
        """
        Finds a file at a given path, or searches upwards if not found.

        Assumes the path is roughly correct, else it might take long.
        It also might take long for ZIP files, since it might have to jump back and forth while traversing down the given path.

        Returns a directory entry.
        """
        root_inode_pos = self._calc_inode_pos(2)
        root_inode_dict = self._inode_table(root_inode_pos)
        root_dir_entries = self.dir_entries(self.read_file(self._get_block_ids(root_inode_dict)))

        dentries = root_dir_entries
        try:
            for dir_name in path_to_file:
                inode_dict = self._inode_table(self._calc_inode_pos(dentries[dir_name]["inode"]))
                dentries = self.dir_entries(self.read_file(self._get_block_ids(inode_dict)))

        except KeyError:
            log(0, "Path to {filename} does not exist: {path}".format(filename=filename, path=path_to_file))
            return self.find_file(filename, path_to_file[:-1])

        file_entry = self._find_file_in_dir(filename, dentries)
        if file_entry:
            return file_entry

        log(0, "{filename} not found in path: {path}".format(filename=filename, path=path_to_file))
        if path_to_file:
            return self.find_file(filename, path_to_file[:-1])

        return None

    def _find_file_in_dir(self, filename, dentries):
        """
        Finds a file in a directory or recursively in its subdirectories.
        Can take long for deep searches.

        Returns the first result as a directory entry.
        """
        try:
            return dentries[filename]
        except KeyError:
            for dentry in dentries:
                if dentry in (".", "..") or not dentries[dentry]["file_type"] == 2:  # makes sure it's not recursive and checks if a directory
                    continue

                inode_dict = self._inode_table(self._calc_inode_pos(dentries[dentry]["inode"]))
                subdentries = self.dir_entries(self.read_file(self._get_block_ids(inode_dict)))

                file_entry = self._find_file_in_dir(filename, subdentries)
                if file_entry:
                    return file_entry

            return None

    def find_file(self, filename, path_to_file=None):
        """
        Finds a file. Supplying a path could take longer for ZIP files!

        Returns a directory entry.
        """

        if path_to_file:
            return self._find_file_properly(filename, path_to_file)

        try:
            return self._find_file_naive(filename)
        except ChromeOSError:
            if self.progress:
                self.progress.update(5, localize(30071))  # Could not find file, doing proper search
            return self._find_file_properly(filename)

    def _calc_inode_pos(self, inode_num):
        """Calculate the byte position of an inode from its index"""
        blk_group_num = (inode_num - 1) // self.sb_dict['s_inodes_per_group']
        blk_group = self.blk_groups[blk_group_num]
        i_index_in_group = (inode_num - 1) % self.sb_dict['s_inodes_per_group']

        return self.part_offset + self.blocksize * blk_group['bg_inode_table'] + self.sb_dict['s_inode_size'] * i_index_in_group

    def _superblock(self):
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
        sb_dict = dict(list(zip(names, unpack(fmt, pack))))

        sb_dict['s_magic'] = hex(sb_dict['s_magic'])
        if not sb_dict['s_magic'] == '0xef53':  # assuming/checking this is an ext2 fs
            raise ChromeOSError("Filesystem is not ext2!")

        block_groups_count1 = sb_dict['s_blocks_count'] / sb_dict['s_blocks_per_group']
        block_groups_count1 = int(block_groups_count1) if float(int(block_groups_count1)) == block_groups_count1 else int(block_groups_count1) + 1
        block_groups_count2 = sb_dict['s_inodes_count'] / sb_dict['s_inodes_per_group']
        block_groups_count2 = int(block_groups_count2) if float(int(block_groups_count2)) == block_groups_count2 else int(block_groups_count2) + 1
        if block_groups_count1 != block_groups_count2:
            raise ChromeOSError("Calculated 2 different numbers of block groups!")

        sb_dict['block_groups_count'] = block_groups_count1

        self.blocksize = 1024 << sb_dict['s_log_block_size']

        return sb_dict

    def _block_group(self):
        """Get info about a block group. Expects stream to be at the right position already."""
        names = ('bg_block_bitmap', 'bg_inode_bitmap', 'bg_inode_table', 'bg_free_blocks_count', 'bg_free_inodes_count', 'bg_used_dirs_count', 'bg_pad')
        fmt = '<3I4H12x'
        fmt_len = calcsize(fmt)

        pack = self.read_stream(fmt_len)
        blk = unpack(fmt, pack)

        blk_dict = dict(list(zip(names, blk)))

        return blk_dict

    def _block_groups(self):
        """Get info about all block groups"""
        if self.blocksize == 1024:
            self.seek_stream(self.part_offset + 2 * self.blocksize)
        else:
            self.seek_stream(self.part_offset + self.blocksize)

        blk_groups = []
        for _ in range(self.sb_dict['block_groups_count']):
            blk_group = self._block_group()
            blk_groups.append(blk_group)

        return blk_groups

    def _inode_table(self, inode_pos):
        """Reads and returns an inode table entry and its size"""
        names = ('i_mode', 'i_uid', 'i_size', 'i_atime', 'i_ctime', 'i_mtime', 'i_dtime', 'i_gid', 'i_links_count', 'i_blocks', 'i_flags',
                 'i_osd1', 'i_block0', 'i_block1', 'i_block2', 'i_block3', 'i_block4', 'i_block5', 'i_block6', 'i_block7', 'i_block8',
                 'i_block9', 'i_block10', 'i_block11', 'i_blocki', 'i_blockii', 'i_blockiii', 'i_generation', 'i_file_acl', 'i_dir_acl', 'i_faddr')
        fmt = '<2Hi4I2H3I15I4I12x'
        fmt_len = calcsize(fmt)
        inode_size = self.sb_dict['s_inode_size']

        self.seek_stream(inode_pos)
        pack = self.read_stream(fmt_len)
        inode = unpack(fmt, pack)

        inode_dict = dict(list(zip(names, inode)))
        inode_dict['i_mode'] = hex(inode_dict['i_mode'])

        blocks = inode_dict['i_size'] / self.blocksize
        inode_dict['blocks'] = int(blocks) if float(int(blocks)) == blocks else int(blocks) + 1

        self.read_stream(inode_size - fmt_len)  # move to end of entry
        return inode_dict

    @staticmethod
    def dir_entry(chunk):
        """Returns the directory entry found in chunk as dict."""
        dir_names = ('inode', 'rec_len', 'name_len', 'file_type', 'name')
        dir_fmt = '<IHBB' + str(len(chunk) - 8) + 's'

        entry = dict(list(zip(dir_names, unpack(dir_fmt, chunk))))
        entry["name"] = entry["name"][:entry["name_len"]]

        return entry

    def dir_entries(self, dir_file):
        """Returns all directory entries of a directory file as dict of dicts with name as key"""
        dirs = {}
        while dir_file:
            dir_entry = self.dir_entry(dir_file)
            dir_file = dir_file[dir_entry["rec_len"]:]
            if dir_entry['inode'] == 0:
                continue

            name = dir_entry["name"].decode()
            dirs[name] = dir_entry

        return dirs

    def _iblock_ids(self, blk_id, ids_to_read):
        """Reads the block indices/IDs from an indirect block"""
        seek_pos = self.part_offset + self.blocksize * blk_id
        self.seek_stream(seek_pos)
        fmt = '<' + str(int(self.blocksize / 4)) + 'I'
        ids = list(unpack(fmt, self.read_stream(self.blocksize)))
        ids_to_read -= len(ids)

        return ids, ids_to_read

    def _iiblock_ids(self, blk_id, ids_to_read):
        """Reads the block indices/IDs from a doubly-indirect block"""
        seek_pos = self.part_offset + self.blocksize * blk_id
        self.seek_stream(seek_pos)
        fmt = '<' + str(int(self.blocksize / 4)) + 'I'
        iids = unpack(fmt, self.read_stream(self.blocksize))

        ids = []
        for iid in iids:
            if ids_to_read <= 0:
                break
            ind_block_ids, ids_to_read = self._iblock_ids(iid, ids_to_read)
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
            self.bstream = self._get_bstream(self.imgpath)

            while seek_pos - self.bstream[1] > chunksize:
                self.read_stream(chunksize)
            self.read_stream(seek_pos - self.bstream[1])

            return

    def read_stream(self, num_of_bytes):
        """Read and return a chunk of the bytestream"""
        self.bstream[1] += num_of_bytes

        return self.bstream[0].read(num_of_bytes)

    def _get_block_ids(self, inode_dict):
        """Get all block indices/IDs of an inode"""
        if not inode_dict['i_blockiii'] == 0:
            raise ChromeOSError("Triply indirect blocks detected, but not implemented!")

        ids_to_read = inode_dict['blocks']
        block_ids = [inode_dict['i_block' + str(i)] for i in range(12)]
        ids_to_read -= 12

        if not inode_dict['i_blocki'] == 0:
            iblocks, ids_to_read = self._iblock_ids(inode_dict['i_blocki'], ids_to_read)
            block_ids += iblocks
        if not inode_dict['i_blockii'] == 0:
            iiblocks, ids_to_read = self._iiblock_ids(inode_dict['i_blockii'], ids_to_read)
            block_ids += iiblocks

        return block_ids[:inode_dict['blocks']]

    def _read_file_dict(self, block_ids):
        """Reads blocks specified by IDs into a dict with IDs as key"""
        block_dict = {}
        for block_id in block_ids:
            if self.progress:
                percent = int(35 + 60 * block_ids.index(block_id) / len(block_ids))
                self.progress.update(percent, localize(30048))
            seek_pos = self.part_offset + self.blocksize * block_id
            self.seek_stream(seek_pos)
            block_dict[block_id] = self.read_stream(self.blocksize)

        return block_dict

    def read_file(self, block_ids):
        """Reads a file (can be directory or anything ext2 considers a file) as one binary string"""
        block_ids_sorted = sorted(block_ids)
        block_dict = self._read_file_dict(block_ids_sorted)

        file_str = b''
        for block_id in block_ids:
            file_str += block_dict[block_id]

        return file_str

    def write_file(self, inode_dict, filepath):
        """Writes file specified by its inode to filepath"""
        bytes_to_write = inode_dict['i_size']
        block_ids = self._get_block_ids(inode_dict)
        bin_file = self.read_file(block_ids)[:bytes_to_write]

        write_dir = os.path.join(os.path.dirname(filepath), '')
        if not exists(write_dir):
            mkdirs(write_dir)

        with open(compat_path(filepath), 'wb') as opened_file:
            opened_file.write(bin_file)

    @staticmethod
    def _get_bstream(imgpath):
        """Get a bytestream of the image"""
        if imgpath.endswith('.zip'):
            bstream = ZipFile(compat_path(imgpath), 'r').open(os.path.basename(imgpath).strip('.zip'), 'r')  # pylint: disable=consider-using-with
        else:
            bstream = open(compat_path(imgpath), 'rb')  # pylint: disable=consider-using-with

        return [bstream, 0]

    def extract_file(self, filename, extract_path):
        """Extracts the file from the image"""

        try:
            if self.progress:
                self.progress.update(5, localize(30061))
            file_entry = self.find_file(filename)

            if self.progress:
                self.progress.update(32, localize(30062))
            inode_pos = self._calc_inode_pos(file_entry["inode"])
            inode_dict = self._inode_table(inode_pos)

            self.write_file(inode_dict, os.path.join(extract_path, filename))

            return True

        except ChromeOSError as error:
            log(4, "Extracting {filename} failed with {error}!".format(filename=filename, error=error))
            return False

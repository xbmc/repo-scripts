import os
from random import uniform

import xbmcvfs
from resources.lib.player.mediatype import PICTURE
from resources.lib.utils import vfs_utils


def get_good_matching_random_folder(path: str, wanted_amount: int) -> 'tuple[str,bool]':

    def _scan_dirs_with_filecount(path: str, wanted_amount: int) -> 'list[str,int]':

        def _scan(path: str) -> 'tuple[int, list[str,int]]':

            dirs, files = xbmcvfs.listdir(path)
            files = [
                f for f in files if vfs_utils.get_media_type(f) == PICTURE]

            result = list()
            files_count = len(files)

            for d in dirs:
                sub_count, subs = _scan(os.path.join(path, d))
                files_count += sub_count
                if sub_count * 2 >= wanted_amount:
                    result.extend(subs)

            result.append((path, files_count))
            return files_count, result

        return _scan(path)[1]

    scale = 0
    choices = list()
    dirs_with_filecount = _scan_dirs_with_filecount(path, wanted_amount)
    for dir_with_filecount in dirs_with_filecount:
        if dir_with_filecount[1] > wanted_amount:
            match_factor = wanted_amount / dir_with_filecount[1]
        else:
            match_factor = dir_with_filecount[1] / wanted_amount

        choices.append(
            (match_factor, dir_with_filecount[0], dir_with_filecount[1], dir_with_filecount[1] > wanted_amount))

        scale += match_factor

    pick = uniform(0, scale)
    current = 0
    for t in choices:
        current += t[0]
        if current > pick:
            return t[1], t[3]

    return path, True

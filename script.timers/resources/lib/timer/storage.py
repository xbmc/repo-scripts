import json
import os
import random
import time

import xbmc
import xbmcaddon
import xbmcvfs
from resources.lib.timer.timer import Timer


def _get_storage_path() -> str:

    addon = xbmcaddon.Addon()
    profile_path = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    return os.path.join(profile_path, "timers.json")


def _aquire_lock() -> str:

    lock_path = "%s.lck" % _get_storage_path()
    lock = str(int(time.time()))

    with xbmcvfs.File(lock_path, "w") as file:
        file.write(lock)

    return lock


def release_lock() -> None:

    lock_file = "%s.lck" % _get_storage_path()
    if xbmcvfs.exists(lock_file):
        xbmcvfs.rmdir(lock_file, force=True)


def _wait_for_unlock() -> None:

    lock_path = "%s.lck" % _get_storage_path()

    wait = 5
    while xbmcvfs.exists(lock_path) and wait > 0:

        xbmc.sleep(100 + int(random.random() * 100))
        wait -= 1

    if wait == 0:
        xbmc.log("%s is locked. Unlock now with small risk of data loss." %
                 _get_storage_path(), xbmc.LOGWARNING)
        release_lock()


def _load_from_storage() -> 'list[dict]':

    _wait_for_unlock()

    storage_path = _get_storage_path()
    _storage = list()
    if xbmcvfs.exists(storage_path):
        with xbmcvfs.File(storage_path, "r") as file:
            try:
                _storage.extend(json.load(file))
            except:
                # this should normally not be a problem, but it fails when running unit tests
                xbmc.log("Can't read timers from storage.", xbmc.LOGWARNING)

    return _storage


def _save_to_storage(storage: 'list[dict]') -> None:

    storage.sort(key=lambda item: item["id"])
    storage_path = _get_storage_path()

    _wait_for_unlock()
    try:
        lock = _aquire_lock()
        tmp = "%s.%s" % (storage_path, lock)
        old = "%s.old" % storage_path
        with xbmcvfs.File(tmp, "w") as file:
            json.dump(obj=storage, fp=file, indent=2, sort_keys=True)

        if xbmcvfs.exists(old):
            xbmcvfs.delete(old)

        xbmcvfs.rename(storage_path, old)
        xbmcvfs.rename(tmp, storage_path)

    finally:
        release_lock()


def load_timers_from_storage() -> 'list[Timer]':

    timers = list()
    storage = _load_from_storage()
    for item in storage:
        timers.append(_init_timer_from_item(item))

    return timers


def load_timer_from_storage(id: int) -> Timer:

    storage = _load_from_storage()
    for item in storage:
        if item["id"] == id:
            return _init_timer_from_item(item)

    return None


def _init_timer_from_item(item: dict) -> Timer:

    timer = Timer(item["id"])
    timer.label = item["label"]
    timer.system_action = item["system_action"]
    timer.media_action = item["media_action"]
    timer.fade = item["fade"]
    timer.vol_min = item["vol_min"]
    timer.vol_max = item["vol_max"]
    timer.path = item["path"]
    timer.media_type = item["media_type"]
    timer.repeat = item["repeat"]
    timer.shuffle = item["shuffle"]
    timer.resume = item["resume"]

    item["days"].sort()
    timer.days = item["days"]

    timer.start = item["start"]
    timer.end_type = item["end_type"]
    timer.end = item["end"]
    timer.duration = item["duration"]

    timer.notify = item["notify"]

    timer.return_vol = None
    timer.active = False

    timer.compute()

    return timer


def _find_item_index(storage: 'list[dict]', id: int) -> int:

    for i, item in enumerate(storage):
        if item["id"] == id:
            return i

    return -1


def save_timer(timer: Timer) -> None:

    timer.compute()

    item = {
        "days": timer.days,
        "duration": timer.duration,
        "end": timer.end,
        "end_type": timer.end_type,
        "fade": timer.fade,
        "id": timer.id,
        "label": timer.label,
        "media_action": timer.media_action,
        "media_type": timer.media_type,
        "notify": timer.notify,
        "path": timer.path,
        "repeat": timer.repeat,
        "resume": timer.resume,
        "shuffle": timer.shuffle,
        "start": timer.start,
        "system_action": timer.system_action,
        "vol_min": timer.vol_min,
        "vol_max": timer.vol_max
    }

    storage = _load_from_storage()
    idx = _find_item_index(storage, timer.id)
    if idx == -1:
        storage.append(item)
    else:
        storage[idx] = item

    _save_to_storage(storage)


def delete_timer(timer_id: int) -> None:

    storage = _load_from_storage()
    idx = _find_item_index(storage, timer_id)
    if idx >= 0:
        storage.pop(idx)
        _save_to_storage(storage=storage)


def get_scheduled_timers() -> 'list[Timer]':

    timers = load_timers_from_storage()
    scheduled_timers = list([timer for timer in timers if timer.days])
    scheduled_timers.sort(key=lambda timer: (timer.days, timer.start,
                                             timer.media_action, timer.system_action))
    return scheduled_timers


def get_next_id() -> int:

    storage = _load_from_storage()

    next_id = 0
    if storage:
        next_id = max(storage, key=lambda item: item["id"])["id"] + 1

    return next_id

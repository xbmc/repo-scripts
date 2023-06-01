import time


def get_timestamp(timestamp=None, set_int=False):
    if not timestamp:
        return
    now = time.time()
    tmp = timestamp
    if set_int:
        now = int(now)
        tmp = int(tmp)
    if now > tmp:
        return
    return timestamp


def set_timestamp(wait_time=60, set_int=False):
    timestamp = time.time() + wait_time
    return int(timestamp) if set_int else timestamp

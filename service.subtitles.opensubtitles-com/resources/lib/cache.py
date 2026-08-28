import base64
import gzip
import json
import uuid
from time import time, sleep
import xbmcgui
from resources.lib.utilities import log

# How long an index-lock holder may be presumed alive without renewing its
# lease. Mutations hold the lock for milliseconds; a long-running Clear
# Cache renews via _heartbeat() well inside this window, so anything older
# really is a crashed invocation's leftover and gets stolen.
_LOCK_STALE_SECONDS = 5.0


class Cache(object):
    """Caches Python values as gzip-compressed JSON in Kodi window properties."""

    def __init__(self, key_prefix=""):
        self.key_prefix = key_prefix
        self._win = xbmcgui.Window(10000)
        self._index_key = f"{key_prefix}:__index__" if key_prefix else "__cache_index__"
        self._lock_key = self._index_key + ":__lock__"

    def _with_index_lock(self, mutate, verify=None):
        """Runs mutate() holding a cross-invocation mutex on the index.

        Window properties offer no compare-and-swap, so a bare read-modify-write
        lets two overlapping invocations drop each other's keys no matter how
        often each verifies - a slower writer that read first can overwrite a
        faster writer AFTER its verification passed. Individual property reads
        and writes ARE atomic though, which is enough for a token spinlock:
        write your token, read back, and only the writer whose token survived
        proceeds - the loser retries. A lock left behind by a crashed
        invocation is stolen after _LOCK_STALE_SECONDS, so with mutations
        holding the lock for ~1ms, acquisition within the deadline is certain
        short of pathological livelock. Even then nothing is overwritten
        blindly: the fallback re-runs mutate() - which re-reads the live index
        - until verify() confirms the update landed.
        """
        token = uuid.uuid4().hex
        try:
            deadline = time() + 8.0
            while time() < deadline:
                current = self._win.getProperty(self._lock_key)
                if current:
                    try:
                        held_since = float(current.split(":", 1)[1])
                    except (IndexError, ValueError):
                        held_since = 0.0
                    if time() - held_since < _LOCK_STALE_SECONDS:
                        sleep(0.002)
                        continue
                self._win.setProperty(self._lock_key, f"{token}:{time()}")
                sleep(0.001)  # let a colliding writer's set land before we re-read
                if not self._win.getProperty(self._lock_key).startswith(token):
                    continue
                self._held_token = token
                try:
                    mutate()
                finally:
                    self._held_token = None
                    # release only OUR lock: if we stalled past the stale
                    # window and someone stole it, clearing would hand a
                    # third invocation a free pass into the mutation
                    if self._win.getProperty(self._lock_key).startswith(token):
                        self._win.clearProperty(self._lock_key)
                # Two writers CAN both confirm their token inside the settle
                # gap - hard mutual exclusion is impossible with only atomic
                # reads/writes. What makes that harmless: mutate() is a MERGE
                # of live state, and we verify AFTER release. A lost update
                # fails verification and the whole acquire-merge cycle runs
                # again, converging with the concurrent writer's state kept.
                if verify is None or verify():
                    return
        except Exception:
            pass
        # Livelock fallback: merge-with-verification, never a single blind
        # write - each pass re-reads the live index, so an update lost to a
        # concurrent writer is re-applied instead of silently dropped.
        try:
            for _ in range(5):
                mutate()
                if verify is None or verify():
                    return
        except Exception:
            pass

    def _heartbeat(self):
        """Renews the lock lease mid-mutation.

        A mutation that outlives _LOCK_STALE_SECONDS (a Clear Cache over a
        huge index) would otherwise look crashed and get stolen while still
        writing - long loops call this periodically to stay leased."""
        token = getattr(self, "_held_token", None)
        try:
            if token and self._win.getProperty(self._lock_key).startswith(token):
                self._win.setProperty(self._lock_key, f"{token}:{time()}")
        except Exception:
            pass

    def _add_to_index(self, key):
        def mutate():
            raw = self._win.getProperty(self._index_key)
            keys = set(json.loads(raw)) if raw else set()
            keys.add(key)
            self._win.setProperty(self._index_key, json.dumps(sorted(keys)))

        def verify():
            raw = self._win.getProperty(self._index_key)
            return key in (set(json.loads(raw)) if raw else set())

        self._with_index_lock(mutate, verify)

    def set(self, key, value, expires=60 * 60 * 24 * 7):
        log(__name__, f"caching {key}")
        full_key = f"{self.key_prefix}:{key}" if self.key_prefix else key
        expires_at = expires + time()

        raw_json = json.dumps(dict(value=value, expires=expires_at)).encode("utf-8")
        compressed = gzip.compress(raw_json)
        b64_str = base64.b64encode(compressed).decode("ascii")

        # Property write and index registration under ONE lock hold: written
        # separately, a Clear Cache landing between them deleted the fresh
        # value and the delayed index add then registered a dead key. Under
        # the lock, publication is atomic relative to clear() - the entry
        # either fully survives a concurrent clear or was never published.
        def mutate():
            self._win.setProperty(full_key, f"gz:{b64_str}")
            raw = self._win.getProperty(self._index_key)
            keys = set(json.loads(raw)) if raw else set()
            keys.add(full_key)
            self._win.setProperty(self._index_key, json.dumps(sorted(keys)))

        def verify():
            raw = self._win.getProperty(self._index_key)
            return (bool(self._win.getProperty(full_key))
                    and full_key in (set(json.loads(raw)) if raw else set()))

        self._with_index_lock(mutate, verify)

    def get(self, key, default=None):
        log(__name__, f"got request for {key} from cache")
        result = default
        full_key = f"{self.key_prefix}:{key}" if self.key_prefix else key

        prop_val = self._win.getProperty(full_key)
        if prop_val:
            try:
                if prop_val.startswith("gz:"):
                    compressed = base64.b64decode(prop_val[3:])
                    raw_json = gzip.decompress(compressed).decode("utf-8")
                    cache_data = json.loads(raw_json)
                else:
                    # Discard legacy uncompressed cache or attempt fallback
                    cache_data = json.loads(prop_val)

                if cache_data.get("expires", 0) > time():
                    result = cache_data["value"]
                    log(__name__, f"got {key} from cache")
            except Exception:
                pass

        return result

    def get_stats(self):
        """Returns (active_item_count, total_compressed_bytes) of valid cached items."""
        count = 0
        total_bytes = 0
        try:
            raw = self._win.getProperty(self._index_key)
            if raw:
                keys = json.loads(raw)
                for k in keys:
                    val = self._win.getProperty(k)
                    if val:
                        try:
                            if val.startswith("gz:"):
                                compressed = base64.b64decode(val[3:])
                                raw_json = gzip.decompress(compressed).decode("utf-8")
                                data = json.loads(raw_json)
                            else:
                                data = json.loads(val)

                            if data.get("expires", 0) > time():
                                count += 1
                                total_bytes += len(val.encode("ascii"))
                        except Exception:
                            pass
        except Exception:
            pass
        return count, total_bytes

    def clear(self):
        """Clears all cached properties from memory and returns (cleared_count, cleared_bytes)."""
        count, total_bytes = self.get_stats()
        try:
            # Snapshot, property deletion and index rewrite all happen in ONE
            # lock hold: deleting properties before taking the lock let a
            # writer re-cache a key in the gap, after which the index rewrite
            # dropped the key while its (new) property survived - orphaned
            # from statistics and future clears. Under the lock a concurrent
            # set() can at worst re-add its key to the index right after us,
            # and that entry is consistent with its property.
            state = {"cleared": set()}

            def mutate():
                raw = self._win.getProperty(self._index_key)
                cleared = set(json.loads(raw)) if raw else set()
                state["cleared"] |= cleared
                for i, k in enumerate(cleared):
                    if i % 200 == 0:
                        self._heartbeat()   # keep the lease during huge clears
                    self._win.clearProperty(k)
                cur_raw = self._win.getProperty(self._index_key)
                remaining = (set(json.loads(cur_raw)) if cur_raw else set()) - state["cleared"]
                if remaining:
                    self._win.setProperty(self._index_key, json.dumps(sorted(remaining)))
                else:
                    self._win.clearProperty(self._index_key)

            def verify():
                cur = self._win.getProperty(self._index_key)
                live = set(json.loads(cur)) if cur else set()
                return not (live & state["cleared"])

            self._with_index_lock(mutate, verify)
        except Exception:
            pass
        return count, total_bytes


def get_total_cache_stats():
    """Returns (total_count, total_bytes, formatted_str) across all cache prefixes."""
    total_count = 0
    total_bytes = 0
    for prefix in ("os_com", "OpenSubtitles", "os_library", ""):
        c = Cache(prefix)
        cnt, b = c.get_stats()
        total_count += cnt
        total_bytes += b

    kb = round(total_bytes / 1024, 1)
    formatted = f"{total_count} items ({kb} KB)"
    return total_count, total_bytes, formatted


def sync_cache_stats_setting():
    """Updates the cache_stats setting in add-on configuration."""
    try:
        import xbmcaddon
        addon = xbmcaddon.Addon("service.subtitles.opensubtitles-com")
        _, _, formatted = get_total_cache_stats()
        addon.setSetting("cache_stats", formatted)
        return formatted
    except Exception:
        return None

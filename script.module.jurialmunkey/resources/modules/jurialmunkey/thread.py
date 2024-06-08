from xbmc import Monitor
from threading import Thread


class ParallelThread():
    thread_max = 0  # 0 is unlimited

    def __init__(self, items, func, *args, **kwargs):
        """ ContextManager for running parallel threads alongside another function
        with ParallelThread(items, func, *args, **kwargs) as pt:
            pass
            item_queue = pt.queue
        item_queue[x]  # to get returned items
        """
        self._mon = Monitor()
        thread_max = self.thread_max or len(items)
        self.queue = [None] * len(items)
        self._pool = [None] * thread_max
        self._exit = False

        threading_enabled = True
        for x, i in enumerate(items):
            if threading_enabled:
                n = x
                while n >= thread_max and not self._mon.abortRequested():  # Hit our thread limit so look for a spare spot in the queue
                    for y, j in enumerate(self._pool):
                        if j.is_alive():
                            continue
                        n = y
                        break
                    if n >= thread_max:
                        self._mon.waitForAbort(0.025)
                try:
                    self._pool[n] = Thread(target=self._threadwrapper, args=[x, i, func, *args], kwargs=kwargs)
                    self._pool[n].start()
                except IndexError:
                    self.kodi_log(f'ParallelThread: INDEX {n} OUT OF RANGE {thread_max}', 1)
                except RuntimeError as exc:
                    self.kodi_log(f'ParallelThread: RUNTIME ERROR: UNABLE TO SPAWN {n} THREAD {thread_max}\nREDUCE MAX THREAD COUNT\n{exc}', 1)
                    threading_enabled = False
            if not threading_enabled:  # Execute rest of queue in series if threading disabled due to RuntimeError
                self._threadwrapper(x, i, func, *args, **kwargs)

    def _threadwrapper(self, x, i, func, *args, **kwargs):
        self.queue[x] = func(i, *args, **kwargs)

    @staticmethod
    def kodi_log(msg, level=0):
        from jurialmunkey.logger import Logger
        Logger('[script.module.jurialmunkey]\n').kodi_log(msg, level)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        for i in self._pool:
            if self._exit or self._mon.abortRequested():
                break
            try:
                i.join()
            except AttributeError:  # is None
                pass

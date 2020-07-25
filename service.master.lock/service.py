from resources.lib.lockmonitor import LockMonitor

mon = LockMonitor()
while not mon.abortRequested():
    mon.waitForAbort(1)

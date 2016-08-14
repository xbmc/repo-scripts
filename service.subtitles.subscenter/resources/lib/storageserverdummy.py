'''
     StorageServer override.
     Version: 1.0
'''


class StorageServer:
    storage = {}

    def __init__(self, table, timeout=24):
        return None

    def cacheFunction(self, funct=False, *args):
        return funct(*args)

    def set(self, name, data):
        self.storage[name] = data
        return ""

    def get(self, name):
        if name in self.storage.keys():
            return self.storage[name]
        return ""

    def setMulti(self, name, data):
        return ""

    def getMulti(self, name, items):
        return ""

    def lock(self, name):
        return False

    def unlock(self, name):
        return False

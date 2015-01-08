class MockBaseClass(object):

    def __init__(self):
        super(MockBaseClass, self).__init__()
        self.called = {}

    def _increase_called(self, name, args=None):
        if name in self.called:
            self.called[name].append(args)
        else:
            self.called[name] = [args]

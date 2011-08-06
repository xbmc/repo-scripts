import types
from string import ascii_uppercase

class MockClass(object):
    '''This is a base class used for stubbing out a class. It 
    always returns a callable and will never raiase an AttributeError.
    '''
    def __getattr__(self, name):
        def mock_method(*args, **kwargs):
            return self
        return mock_method
        

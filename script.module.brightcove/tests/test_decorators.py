#from unittest import TestCase
#from brightcove.decorators import accepts, requires, api_command

#class TestAccepts(TestCase):
    #def setUp(self):
        #@accepts('foo')
        #def bar(**kwargs):
            #return kwargs['foo']
        #self.bar = bar

    #def test_valid_arg(self):
        #self.assertEquals(self.bar(foo='foo'), 'foo')

    #def test_invalid_arg(self):
        #self.assertRaises(AssertionError, self.bar, baz='baz')
    
    #def test_mixed_args(self):
        #self.assertRaises(AssertionError, self.bar, baz='baz', foo='foo')

    #def test_no_kwargs(self):
        #self.assertRaises(TypeError, self.bar, 'foo')

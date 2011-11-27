from unittest import TestCase
from brightcove.core import APIObjectMeta, Field, DateTimeField, ListField, get_item
from operator import attrgetter
from datetime import datetime

class TestFunctions(TestCase):
    def setUp(self):
        class Bar(object):
            def __init__(self, bar=None, baz=None):
                self.bar = bar
                self.baz = baz
        self.Bar = Bar

    def test_get_item_dict(self):
        kwargs = {u'bar': 'bar', u'baz': 'baz'}
        item = get_item(kwargs, self.Bar)
        self.assertEqual(item.bar, 'bar')
        self.assertEqual(item.baz, 'baz')

    #def test_get_item_list(self):
        #args = [('bar', 'baz')]
        #item = get_item(args, self.Bar)
        #self.assertEqual(item.bar, 'bar')
        #self.assertEqual(item.baz, 'baz')

        




class TestField(TestCase):
    def setUp(self):
        self.field = Field('help')

    def test_init(self):
        self.assertEqual(self.field.help, 'help')

    def test_to_python(self):
        self.assertEqual(self.field.to_python('alpha'), 'alpha')
        self.assertEqual(self.field.to_python(True), True)
        self.assertEqual(self.field.to_python(42), 42)

    def test_from_python(self):
        self.assertEqual(self.field.from_python('alpha'), 'alpha')
        self.assertEqual(self.field.from_python(True), True)
        self.assertEqual(self.field.from_python(42), 42)

class TestDateTimeField(TestCase):
    def test_to_python(self):
        ts = '1320283529000'
        isoformat = '2011-11-02T21:25:29'

        dtf = DateTimeField()
        dt = dtf.to_python(ts)
        self.assertEqual(dt.isoformat(), isoformat)

    def test_from_python(self):
        ts = 1320283529
        long_ts = '1320283529000'
        dt = datetime.fromtimestamp(ts)

        dtf = DateTimeField()
        self.assertEqual(dtf.from_python(dt), long_ts)


class TestListField(TestCase):
    def setUp(self):
        class A(object):
            def __init__(self, value):
                self.value = value

            def __eq__(self, other):
                return self.value == other.value

            def from_python(self):
                return self.value

        self.A = A
        self.lf = ListField(self.A, help='help')

    def test_init(self):
        self.assertEqual(self.lf.item_cls, self.A)
        self.assertEqual(self.lf.help, 'help')
        
    def test_to_python(self):
        before = ['alpha', 'bravo', 'charlie']
        after = self.lf.to_python(before)
        self.assertEqual([self.A('alpha'), self.A('bravo'), self.A('charlie')], after)

    def test_from_python(self):
        before = [self.A('alpha'), self.A('bravo')]
        after = ['alpha', 'bravo']
        self.assertEqual(self.lf.from_python(before), after)
        

class TestAPIObjectMeta(TestCase):
    def setUp(self):
        class Bar(object):
            __metaclass__ = APIObjectMeta
            _fields = ['alpha', 'bravo', 'charlie']
        self.Bar = Bar

    def test_cls_creation(self):
        class Foo(object):
            __metaclass__ = APIObjectMeta
            _fields = ['bar', 'baz']
        self.assertEqual(Foo.bar, None)
        self.assertEqual(Foo.baz, None)
        self.assertEqual(Foo._meta.keys(), ['bar', 'baz'])
        self.assertEqual(isinstance(Foo._meta['bar'], Field), True)
        self.assertEqual(isinstance(Foo._meta['baz'], Field), True)
        self.assertRaises(AttributeError, attrgetter('_fields'), Foo)

    def test_cls_constructor(self):
        bar = self.Bar(alpha='alpha', bravo='bravo', charlie='charlie')
        self.assertEqual(bar.alpha, 'alpha')
        self.assertEqual(bar.bravo, 'bravo')
        self.assertEqual(bar.charlie, 'charlie')
        
    def test_nonspecified_args(self):
        bar = self.Bar(delta='delta')
        self.assertEqual(bar.delta, 'delta')

    def test_non_kwargs(self):
        self.assertRaises(TypeError, attrgetter('Bar'), self, 'alpha')

import sys
from lib.xpath.exceptions import *
import lib.xpath.exceptions
import lib.xpath.expr
import lib.xpath.parser
import lib.xpath.yappsrt
xpath = sys.modules[__name__]

__all__ = ['find', 'findnode', 'findvalue', 'XPathContext', 'XPath']
__all__.extend((x for x in dir(xpath.exceptions) if not x.startswith('_')))

def api(f):
    """Decorator for functions and methods that are part of the external
    module API and that can throw XPathError exceptions.

    The call stack for these exceptions can be very large, and not very
    interesting to the user.  This decorator rethrows XPathErrors to
    trim the stack.

    """
    def api_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except XPathError, e:
            raise e
    api_function.__name__ = f.__name__
    api_function.__doc__ = f.__doc__
    return api_function

class XPathContext(object):
    def __init__(self, document=None, **kwargs):
        self.default_namespace = None
        self.namespaces = {}
        self.variables = {}

        if document is not None:
            if document.nodeType != document.DOCUMENT_NODE:
                document = document.ownerDocument
            if document.documentElement is not None:
                attrs = document.documentElement.attributes
                for attr in (attrs.item(i) for i in xrange(attrs.length)):
                    if attr.name == 'xmlns':
                        self.default_namespace = attr.value
                    elif attr.name.startswith('xmlns:'):
                        self.namespaces[attr.name[6:]] = attr.value

        self.update(**kwargs)

    def clone(self):
        dup = XPathContext()
        dup.default_namespace = self.default_namespace
        dup.namespaces.update(self.namespaces)
        dup.variables.update(self.variables)
        return dup

    def update(self, default_namespace=None, namespaces=None,
                  variables=None, **kwargs):
        if default_namespace is not None:
            self.default_namespace = default_namespace
        if namespaces is not None:
            self.namespaces = namespaces
        if variables is not None:
            self.variables = variables
        self.variables.update(kwargs)

    @api
    def find(self, expr, node, **kwargs):
        return xpath.find(expr, node, context=self, **kwargs)

    @api
    def findnode(self, expr, node, **kwargs):
        return xpath.findnode(expr, node, context=self, **kwargs)

    @api
    def findvalue(self, expr, node, **kwargs):
        return xpath.findvalue(expr, node, context=self, **kwargs)

    @api
    def findvalues(self, expr, node, **kwargs):
        return xpath.findvalues(expr, node, context=self, **kwargs)

class XPath():
    _max_cache = 100
    _cache = {}

    def __init__(self, expr):
        """Init docs.
        """
        try:
            parser = xpath.parser.XPath(xpath.parser.XPathScanner(str(expr)))
            self.expr = parser.XPath()
        except xpath.yappsrt.SyntaxError, e:
            raise XPathParseError(str(expr), e.pos, e.msg)

    @classmethod
    def get(cls, s):
        if isinstance(s, cls):
            return s
        try:
            return cls._cache[s]
        except KeyError:
            if len(cls._cache) > cls._max_cache:
                cls._cache.clear()
            expr = cls(s)
            cls._cache[s] = expr
            return expr

    @api
    def find(self, node, context=None, **kwargs):
        if context is None:
            context = XPathContext(node, **kwargs)
        elif kwargs:
            context = context.clone()
            context.update(**kwargs)
        return self.expr.evaluate(node, 1, 1, context)

    @api
    def findnode(self, node, context=None, **kwargs):
        result = self.find(node, context, **kwargs)
        if not xpath.expr.nodesetp(result):
            raise XPathTypeError("expression is not a node-set")
        if len(result) == 0:
            return None
        return result[0]

    @api
    def findvalue(self, node, context=None, **kwargs):
        result = self.find(node, context, **kwargs)
        if xpath.expr.nodesetp(result):
            if len(result) == 0:
                return None
            result = xpath.expr.string(result)
        return result

    @api
    def findvalues(self, node, context=None, **kwargs):
        result = self.find(node, context, **kwargs)
        if not xpath.expr.nodesetp(result):
            raise XPathTypeError("expression is not a node-set")
        return [xpath.expr.string_value(x) for x in result]

    def __repr__(self):
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__name__,
                              repr(str(self.expr)))

    def __str__(self):
        return str(self.expr)

@api
def find(expr, node, **kwargs):
    return XPath.get(expr).find(node, **kwargs)

@api
def findnode(expr, node, **kwargs):
    return XPath.get(expr).findnode(node, **kwargs)

@api
def findvalue(expr, node, **kwargs):
    return XPath.get(expr).findvalue(node, **kwargs)

@api
def findvalues(expr, node, **kwargs):
    return XPath.get(expr).findvalues(node, **kwargs)

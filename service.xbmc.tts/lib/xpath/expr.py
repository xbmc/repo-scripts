from __future__ import division
from itertools import *
import math
import operator
import re
import xml.dom
import weakref

import sys

from exceptions import *


#
# Data model functions.
#

def string_value(node):
    """Compute the string-value of a node."""
    if (node.nodeType == node.DOCUMENT_NODE or
        node.nodeType == node.ELEMENT_NODE):
        s = u''
        for n in axes['descendant'](node):
            if n.nodeType == n.TEXT_NODE:
                s += n.data
        return s

    elif node.nodeType == node.ATTRIBUTE_NODE:
        return node.value

    elif (node.nodeType == node.PROCESSING_INSTRUCTION_NODE or
          node.nodeType == node.COMMENT_NODE or
          node.nodeType == node.TEXT_NODE):
        return node.data

def document_order(node):
    """Compute a document order value for the node.
    
    cmp(document_order(a), document_order(b)) will return -1, 0, or 1 if
    a is before, identical to, or after b in the document respectively.

    We represent document order as a list of sibling indexes.  That is,
    the third child of the document node has an order of [2].  The first
    child of that node has an order of [2,0].

    Attributes have a sibling index of -1 (coming before all children of
    their node) and are further ordered by name--e.g., [2,0,-1,'href'].

    """

    # Attributes: parent-order + [-1, attribute-name]
    if node.nodeType == node.ATTRIBUTE_NODE:
        order = document_order(node.ownerElement)
        order.extend((-1, node.name))
        return order

    # The document root (hopefully): []
    if node.parentNode is None:
        return []

    # Determine which child this is of its parent.
    sibpos = 0
    sib = node
    while sib.previousSibling is not None:
        sibpos += 1
        sib = sib.previousSibling

    # Order: parent-order + [sibling-position]
    order = document_order(node.parentNode)
    order.append(sibpos)
    return order

#
# Type functions, operating on the various XPath types.
#
# Internally, we use the following representations:
#       nodeset - list of DOM tree nodes in document order
#       string  - str or unicode
#       boolean - bool
#       number  - int or float
#

def nodeset(v):
    """Convert a value to a nodeset."""
    if not nodesetp(v):
        raise XPathTypeError, "value is not a node-set"
    return v

def nodesetp(v):
    """Return true iff 'v' is a node-set."""
    if isinstance(v, list):
        return True

def string(v):
    """Convert a value to a string."""
    if nodesetp(v):
        if not v:
            return u''
        return string_value(v[0])
    elif numberp(v):
        if v == float('inf'):
            return u'Infinity'
        elif v == float('-inf'):
            return u'-Infinity'
        elif int(v) == v and v <= 0xffffffff:
            v = int(v)
        elif str(v) == 'nan':
            return u'NaN'
        return unicode(v)
    elif booleanp(v):
        return u'true' if v else u'false'
    return v

def stringp(v):
    """Return true iff 'v' is a string."""
    return isinstance(v, basestring)

def boolean(v):
    """Convert a value to a boolean."""
    if nodesetp(v):
        return len(v) > 0
    elif numberp(v):
        if v == 0 or v != v:
            return False
        return True
    elif stringp(v):
        return v != ''
    return v

def booleanp(v):
    """Return true iff 'v' is a boolean."""
    return isinstance(v, bool)

def number(v):
    """Convert a value to a number."""
    if nodesetp(v):
        v = string(v)
    try:
        return float(v)
    except ValueError:
        return float('NaN')

def numberp(v):
    """Return true iff 'v' is a number."""
    return (not(isinstance(v, bool)) and
            (isinstance(v, int) or isinstance(v, float)))

class Expr(object):
    """Abstract base class for XPath expressions."""

    def evaluate(self, node, pos, size, context):
        """Evaluate the expression.

        The context node, context position, and context size are passed as
        arguments.

        Returns an XPath value: a nodeset, string, boolean, or number.

        """

class BinaryOperatorExpr(Expr):
    """Base class for all binary operators."""

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def evaluate(self, node, pos, size, context):
        # Subclasses either override evaluate() or implement operate().
        return self.operate(self.left.evaluate(node, pos, size, context),
                            self.right.evaluate(node, pos, size, context))

    def __str__(self):
        return '(%s %s %s)' % (self.left, self.op, self.right)

class AndExpr(BinaryOperatorExpr):
    """<x> and <y>"""

    def evaluate(self, node, pos, size, context):
        # Note that XPath boolean operations short-circuit.
        return (boolean(self.left.evaluate(node, pos, size, context) and
                boolean(self.right.evaluate(node, pos, size, context))))

class OrExpr(BinaryOperatorExpr):
    """<x> or <y>"""

    def evaluate(self, node, pos, size, context):
        # Note that XPath boolean operations short-circuit.
        return (boolean(self.left.evaluate(node, pos, size, context) or
                boolean(self.right.evaluate(node, pos, size, context))))

class EqualityExpr(BinaryOperatorExpr):
    """<x> = <y>, <x> != <y>, etc."""

    operators = {
        '='  : operator.eq,
        '!=' : operator.ne,
        '<=' : operator.le,
        '<'  : operator.lt,
        '>=' : operator.ge,
        '>'  : operator.gt,
    }

    def operate(self, a, b):
        if nodesetp(a):
            for node in a:
                if self.operate(string_value(node), b):
                    return True
            return False

        if nodesetp(b):
            for node in b:
                if self.operate(a, string_value(node)):
                    return True
            return False

        if self.op in ('=', '!='):
            if booleanp(a) or booleanp(b):
                convert = boolean
            elif numberp(a) or numberp(b):
                convert = number
            else:
                convert = string
        else:
            convert = number

        a, b = convert(a), convert(b)
        return self.operators[self.op](a, b)

def divop(x, y):
    try:
        return x / y
    except ZeroDivisionError:
        if x == 0 and y == 0:
            return float('nan')
        if x < 0:
            return float('-inf')
        return float('inf')

class ArithmeticalExpr(BinaryOperatorExpr):
    """<x> + <y>, <x> - <y>, etc."""

    # Note that we must use math.fmod for the correct modulo semantics.
    operators = {
        '+'   : operator.add,
        '-'   : operator.sub,
        '*'   : operator.mul,
        'div' : divop,
        'mod' : math.fmod
    }

    def operate(self, a, b):
        return self.operators[self.op](number(a), number(b))

class UnionExpr(BinaryOperatorExpr):
    """<x> | <y>"""

    def operate(self, a, b):
        if not nodesetp(a) or not nodesetp(b):
            raise XPathTypeError("union operand is not a node-set")

        # Need to sort the result to preserve document order.
        return sorted(set(chain(a, b)), key=document_order)

class NegationExpr(Expr):
    """- <x>"""

    def __init__(self, expr):
        self.expr = expr

    def evaluate(self, node, pos, size, context):
        return -number(self.expr.evaluate(node, pos, size, context))

    def __str__(self):
        return '(-%s)' % self.expr

class LiteralExpr(Expr):
    """Literals--either numbers or strings."""

    def __init__(self, literal):
        self.literal = literal

    def evaluate(self, node, pos, size, context):
        return self.literal

    def __str__(self):
        if stringp(self.literal):
            if "'" in self.literal:
                return '"%s"' % self.literal
            else:
                return "'%s'" % self.literal
        return string(self.literal)

class VariableReference(Expr):
    """Variable references."""

    def __init__(self, prefix, name):
        self.prefix = prefix
        self.name = name

    def evaluate(self, node, pos, size, context):
        try:
            if self.prefix is not None:
                try:
                    namespaceURI = context.namespaces[self.prefix]
                except KeyError:
                    raise XPathUnknownPrefixError(self.prefix)
                return context.variables[(namespaceURI, self.name)]
            else:
                return context.variables[self.name]
        except KeyError:
            raise XPathUnknownVariableError(str(self))

    def __str__(self):
        if self.prefix is None:
            return '$%s' % self.name
        else:
            return '$%s:%s' % (self.prefix, self.name)

class Function(Expr):
    """Functions."""

    def __init__(self, name, args):
        self.name = name
        self.args = args
        self.evaluate = getattr(self, 'f_%s' % name.replace('-', '_'), None)
        if self.evaluate is None:
            raise XPathUnknownFunctionError, 'unknown function "%s()"' % name

        if len(self.args) < self.evaluate.minargs:
            raise XPathTypeError, 'too few arguments for "%s()"' % name
        if (self.evaluate.maxargs is not None and
            len(self.args) > self.evaluate.maxargs):
            raise XPathTypeError, 'too many arguments for "%s()"' % name

    #
    # XPath functions are implemented by methods of the Function class.
    #
    # A method implementing an XPath function is decorated with the function
    # decorator, and receives the evaluated function arguments as positional
    # parameters.
    #

    def function(minargs, maxargs, implicit=False, first=False, convert=None):
        """Function decorator.

        minargs -- Minimum number of arguments taken by the function.
        maxargs -- Maximum number of arguments taken by the function.
        implicit -- True for functions which operate on a nodeset consisting
                    of the current context node when passed no argument.
                    (e.g., string() and number().)
        convert -- When non-None, a function used to filter function arguments.
        """
        def decorator(f):
            def new_f(self, node, pos, size, context):
                if implicit and len(self.args) == 0:
                    args = [[node]]
                else:
                    args = [x.evaluate(node, pos, size, context)
                            for x in self.args]
                if first:
                    args[0] = nodeset(args[0])
                    if len(args[0]) > 0:
                        args[0] = args[0][0]
                    else:
                        args[0] = None
                if convert is not None:
                    args = [convert(x) for x in args]
                return f(self, node, pos, size, context, *args)

            new_f.minargs = minargs
            new_f.maxargs = maxargs
            new_f.__name__ = f.__name__
            new_f.__doc__ = f.__doc__
            return new_f
        return decorator

    # Node Set Functions

    @function(0, 0)
    def f_last(self, node, pos, size, context):
        return size

    @function(0, 0)
    def f_position(self, node, pos, size, context):
        return pos

    @function(1, 1, convert=nodeset)
    def f_count(self, node, pos, size, context, nodes):
        return len(nodes)

    @function(1, 1)
    def f_id(self, node, pos, size, context, arg):
        if nodesetp(arg):
            ids = (string_value(x) for x in arg)
        else:
            ids = [string(arg)]
        if node.nodeType != node.DOCUMENT_NODE:
            node = node.ownerDocument
        return list(filter(None, (node.getElementById(id) for id in ids)))

    @function(0, 1, implicit=True, first=True)
    def f_local_name(self, node, pos, size, context, argnode):
        if argnode is None:
            return ''
        if (argnode.nodeType == argnode.ELEMENT_NODE or
            argnode.nodeType == argnode.ATTRIBUTE_NODE):
            return argnode.localName
        elif argnode.nodeType == argnode.PROCESSING_INSTRUCTION_NODE:
            return argnode.target
        return ''

    @function(0, 1, implicit=True, first=True)
    def f_namespace_uri(self, node, pos, size, context, argnode):
        if argnode is None:
            return ''
        return argnode.namespaceURI

    @function(0, 1, implicit=True, first=True)
    def f_name(self, node, pos, size, context, argnode):
        if argnode is None:
            return ''
        if argnode.nodeType == argnode.ELEMENT_NODE:
            return argnode.tagName
        elif argnode.nodeType == argnode.ATTRIBUTE_NODE:
            return argnode.name
        elif argnode.nodeType == argnode.PROCESSING_INSTRUCTION_NODE:
            return argnode.target
        return ''

    # String Functions

    @function(0, 1, implicit=True, convert=string)
    def f_string(self, node, pos, size, context, arg):
        return arg

    @function(2, None, convert=string)
    def f_concat(self, node, pos, size, context, *args):
        return ''.join((x for x in args))

    @function(2, 2, convert=string)
    def f_starts_with(self, node, pos, size, context, a, b):
        return a.startswith(b)

    @function(2, 2, convert=string)
    def f_contains(self, node, pos, size, context, a, b):
        return b in a

    @function(2, 2, convert=string)
    def f_substring_before(self, node, pos, size, context, a, b):
        try:
            return a[0:a.index(b)]
        except ValueError:
            return ''

    @function(2, 2, convert=string)
    def f_substring_after(self, node, pos, size, context, a, b):
        try:
            return a[a.index(b)+len(b):]
        except ValueError:
            return ''

    @function(2, 3)
    def f_substring(self, node, pos, size, context, s, start, count=None):
        s = string(s)
        start = round(number(start))
        if start != start:
            # Catch NaN
            return ''

        if count is None:
            end = len(s) + 1
        else:
            end = start + round(number(count))
            if end != end:
                # Catch NaN
                return ''
            if end > len(s):
                end = len(s)+1

        if start < 1:
            start = 1
        if start > len(s):
            return ''
        if end <= start:
            return ''
        return s[int(start)-1:int(end)-1]

    @function(0, 1, implicit=True, convert=string)
    def f_string_length(self, node, pos, size, context, s):
        return len(s)

    @function(0, 1, implicit=True, convert=string)
    def f_normalize_space(self, node, pos, size, context, s):
        return re.sub(r'\s+', ' ', s.strip())

    @function(3, 3, convert=lambda x: unicode(string(x)))
    def f_translate(self, node, pos, size, context, s, source, target):
        # str.translate() and unicode.translate() are completely different.
        # The translate() arguments are coerced to unicode.
        table = {}
        for schar, tchar in izip(source, target):
            schar = ord(schar)
            if schar not in table:
                table[schar] = tchar
        if len(source) > len(target):
            for schar in source[len(target):]:
                schar = ord(schar)
                if schar not in table:
                    table[schar] = None
        return s.translate(table)

    # Boolean functions

    @function(1, 1, convert=boolean)
    def f_boolean(self, node, pos, size, context, b):
        return b

    @function(1, 1, convert=boolean)
    def f_not(self, node, pos, size, context, b):
        return not b

    @function(0, 0)
    def f_true(self, node, pos, size, context):
        return True

    @function(0, 0)
    def f_false(self, node, pos, size, context):
        return False

    @function(1, 1, convert=string)
    def f_lang(self, node, pos, size, context, s):
        s = s.lower()
        for n in axes['ancestor-or-self'](node):
            if n.nodeType == n.ELEMENT_NODE and n.hasAttribute('xml:lang'):
                lang = n.getAttribute('xml:lang').lower()
                if s == lang or lang.startswith(s + u'-'):
                    return True
                break
        return False

    # Number functions

    @function(0, 1, implicit=True, convert=number)
    def f_number(self, node, pos, size, context, n):
        return n

    @function(1, 1, convert=nodeset)
    def f_sum(self, node, pos, size, context, nodes):
        return sum((number(string_value(x)) for x in nodes))

    @function(1, 1, convert=number)
    def f_floor(self, node, pos, size, context, n):
        return math.floor(n)

    @function(1, 1, convert=number)
    def f_ceiling(self, node, pos, size, context, n):
        return math.ceil(n)

    @function(1, 1, convert=number)
    def f_round(self, node, pos, size, context, n):
        # XXX round(-0.0) should be -0.0, not 0.0.
        # XXX round(-1.5) should be -1.0, not -2.0.
        return round(n)

    def __str__(self):
        return '%s(%s)' % (self.name, ', '.join((str(x) for x in self.args)))

#
# XPath axes.
#

# Dictionary of all axis functions.
axes = {}

def axisfn(reverse=False, principal_node_type=xml.dom.Node.ELEMENT_NODE):
    """Axis function decorator.

    An axis function will take a node as an argument and return a sequence
    over the nodes along an XPath axis.  Axis functions have two extra
    attributes indicating the axis direction and principal node type.
    """
    def decorate(f):
        f.__name__ = f.__name__.replace('_', '-')
        f.reverse = reverse
        f.principal_node_type = principal_node_type
        return f
    return decorate

def make_axes():
    """Define functions to walk each of the possible XPath axes."""

    @axisfn()
    def child(node):
        return node.childNodes

    @axisfn()
    def descendant(node):
        for child in node.childNodes:
            for node in descendant_or_self(child):
                yield node

    @axisfn()
    def parent(node):
        if node.parentNode is not None:
            yield node.parentNode

    @axisfn(reverse=True)
    def ancestor(node):
        while node.parentNode is not None:
            node = node.parentNode
            yield node

    @axisfn()
    def following_sibling(node):
        while node.nextSibling is not None:
            node = node.nextSibling
            yield node

    @axisfn(reverse=True)
    def preceding_sibling(node):
        while node.previousSibling is not None:
            node = node.previousSibling
            yield node

    @axisfn()
    def following(node):
        while node is not None:
            while node.nextSibling is not None:
                node = node.nextSibling
                for n in descendant_or_self(node):
                    yield n
            node = node.parentNode

    @axisfn(reverse=True)
    def preceding(node):
        while node is not None:
            while node.previousSibling is not None:
                node = node.previousSibling
                # Could be more efficient here.
                for n in reversed(list(descendant_or_self(node))):
                    yield n
            node = node.parentNode

    @axisfn(principal_node_type=xml.dom.Node.ATTRIBUTE_NODE)
    def attribute(node):
        if node.attributes is not None:
            return (node.attributes.item(i)
                    for i in xrange(node.attributes.length))
        return ()

    @axisfn()
    def namespace(node):
        raise XPathNotImplementedError("namespace axis is not implemented")

    @axisfn()
    def self(node):
        yield node

    @axisfn()
    def descendant_or_self(node):
        yield node
        for child in node.childNodes:
            for node in descendant_or_self(child):
                yield node

    @axisfn(reverse=True)
    def ancestor_or_self(node):
        return chain([node], ancestor(node))

    # Place each axis function defined here into the 'axes' dict.
    for axis in locals().values():
        axes[axis.__name__] = axis

make_axes()

def merge_into_nodeset(target, source):
    """Place all the nodes from the source node-set into the target
    node-set, preserving document order.  Both node-sets must be in
    document order to begin with.

    """
    if len(target) == 0:
        target.extend(source)
        return

    source = [n for n in source if n not in target]
    if len(source) == 0:
        return

    # If the last node in the target set comes before the first node in the
    # source set, then we can just concatenate the sets.  Otherwise, we
    # will need to sort.  (We could also check to see if the last node in
    # the source set comes before the first node in the target set, but this
    # situation is very unlikely in practice.)
    if document_order(target[-1]) < document_order(source[0]):
        target.extend(source)
    else:
        target.extend(source)
        target.sort(key=document_order)

class AbsolutePathExpr(Expr):
    """Absolute location paths."""

    def __init__(self, path):
        self.path = path

    def evaluate(self, node, pos, size, context):
        if node.nodeType != node.DOCUMENT_NODE:
            node = node.ownerDocument
        if self.path is None:
            return [node]
        return self.path.evaluate(node, 1, 1, context)

    def __str__(self):
        return '/%s' % (self.path or '')

class PathExpr(Expr):
    """Location path expressions."""

    def __init__(self, steps):
        self.steps = steps

    def evaluate(self, node, pos, size, context):
        # The first step in the path is evaluated in the current context.
        # If this is the only step in the path, the return value is
        # unimportant.  If there are other steps, however, it must be a
        # node-set.
        result = self.steps[0].evaluate(node, pos, size, context)
        if len(self.steps) > 1 and not nodesetp(result):
            raise XPathTypeError("path step is not a node-set")

        # Subsequent steps are evaluated for each node in the node-set
        # resulting from the previous step.
        for step in self.steps[1:]:
            aggregate = []
            for i in xrange(len(result)):
                nodes = step.evaluate(result[i], i+1, len(result), context)
                if not nodesetp(nodes):
                    raise XPathTypeError("path step is not a node-set")
                merge_into_nodeset(aggregate, nodes)
            result = aggregate

        return result

    def __str__(self):
        return '/'.join((str(s) for s in self.steps))

class PredicateList(Expr):
    """A list of predicates.
    
    Predicates are handled as an expression wrapping the expression
    filtered by the predicates.

    """
    def __init__(self, expr, predicates, axis='child'):
        self.predicates = predicates
        self.expr = expr
        self.axis = axes[axis]

    def evaluate(self, node, pos, size, context):
        result = self.expr.evaluate(node, pos, size, context)
        if not nodesetp(result):
            raise XPathTypeError("predicate input is not a node-set")

        if self.axis.reverse:
            result.reverse()

        for pred in self.predicates:
            match = []
            for i, node in izip(count(1), result):
                r = pred.evaluate(node, i, len(result), context)

                # If a predicate evaluates to a number, select the node
                # with that position.  Otherwise, select nodes for which
                # the boolean value of the predicate is true.
                if numberp(r):
                    if r == i:
                        match.append(node)
                elif boolean(r):
                    match.append(node)
            result = match

        if self.axis.reverse:
            result.reverse()

        return result

    def __str__(self):
        s = str(self.expr)
        if '/' in s:
            s = '(%s)' % s
        return s + ''.join(('[%s]' % x for x in self.predicates))

class AxisStep(Expr):
    """One step in a location path expression."""

    def __init__(self, axis, test=None, predicates=None):
        if test is None:
            test = AnyKindTest()
        self.axis = axes[axis]
        self.test = test

    def evaluate(self, node, pos, size, context):
        match = []
        for n in self.axis(node):
            if self.test.match(n, self.axis, context):
                match.append(n)

        if self.axis.reverse:
            match.reverse()

        return match

    def __str__(self):
        return '%s::%s' % (self.axis.__name__, self.test)

#
# Node tests.
#

class Test(object):
    """Abstract base class for node tests."""

    def match(self, node, axis, context):
        """Return True if 'node' matches the test along 'axis'."""

class NameTest(object):
    def __init__(self, prefix, localpart):
        self.prefix = prefix
        self.localName = localpart
        if self.prefix == None and self.localName == '*':
            self.prefix = '*'

    def match(self, node, axis, context):
        if node.nodeType != axis.principal_node_type:
            return False

        if self.prefix != '*':
            namespaceURI = None
            if self.prefix is not None:
                try:
                    namespaceURI = context.namespaces[self.prefix]
                except KeyError:
                    raise XPathUnknownPrefixError(self.prefix)
            elif axis.principal_node_type == node.ELEMENT_NODE:
                namespaceURI = context.default_namespace
            if namespaceURI != node.namespaceURI:
                return False
        if self.localName != '*':
            if self.localName != node.localName:
                return False
        return True

    def __str__(self):
        if self.prefix is not None:
            return '%s:%s' % (self.prefix, self.localName)
        else:
            return self.localName

class PITest(object):
    def __init__(self, name=None):
        self.name = name

    def match(self, node, axis, context):
        return (node.nodeType == node.PROCESSING_INSTRUCTION_NODE and
                (self.name is None or node.target == self.name))

    def __str__(self):
        if self.name is None:
            name = ''
        elif "'" in self.name:
            name = '"%s"' % self.name
        else:
            name = "'%s'" % self.name
        return 'processing-instruction(%s)' % name

class CommentTest(object):
    def match(self, node, axis, context):
        return node.nodeType == node.COMMENT_NODE

    def __str__(self):
        return 'comment()'

class TextTest(object):
    def match(self, node, axis, context):
        return node.nodeType == node.TEXT_NODE

    def __str__(self):
        return 'text()'

class AnyKindTest(object):
    def match(self, node, axis, context):
        return True

    def __str__(self):
        return 'node()'

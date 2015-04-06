
class XPathError(Exception):
    """Base exception class used for all XPath exceptions."""

class XPathNotImplementedError(XPathError):
    """Raised when an XPath expression contains a feature of XPath which
    has not been implemented.

    """

class XPathParseError(XPathError):
    """Raised when an XPath expression could not be parsed."""

    def __init__(self, expr, pos, message):
        XPathError.__init__(self)
        self.expr = expr
        self.pos = pos
        self.message = message

    def __str__(self):
        return ("Syntax error:\n" +
                self.expr.replace("\n", " ") + "\n" +
                ("-" * self.pos) + "^")

class XPathTypeError(XPathError):
    """Raised when an XPath expression is found to contain a type error.
    For example, the expression "string()/node()" contains a type error
    because the "string()" function does not return a node-set.

    """

class XPathUnknownFunctionError(XPathError):
    """Raised when an XPath expression contains a function that has no
    binding in the expression context.

    """

class XPathUnknownPrefixError(XPathError):
    """Raised when an XPath expression contains a QName with a namespace
    prefix that has no corresponding namespace declaration in the expression
    context.

    """

class XPathUnknownVariableError(XPathError):
    """Raised when an XPath expression contains a variable that has no
    binding in the expression context.

    """

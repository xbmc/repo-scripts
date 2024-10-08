from . import filters
from . import nodes
from . import loaders
from . import errors
from . import compiler

from .template import Template


# Library version.
__version__ = "3.3.0"


# Assign a template-loading callable here to enable the {% include %} and {% extends %} tags.
# The callable should accept a single string argument and either return an instance of the
# corresponding Template class or raise a TemplateLoadError exception.
loader = None

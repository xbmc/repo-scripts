"""Wrapper for Python 2.4 (which also works with 2.3) decimal datatype

You can find the 2.3 decimal module described in the PEP for it
here:
	http://www.python.org/peps/pep-0327.html

This is a floating-point decimal data-type, not the "fixedpoint" module.
"""
from basictypes import basic_types
try:
	import decimal
except ImportError, err:
	decimal = None

if decimal:
	class DecimalDT( basic_types.Numeric_DT ):
		"""Numeric data-type descriptor for the new standard Decimal type"""
		dataType = "decimal"
		baseType = decimal.Decimal
	basic_types.registry.registerDT( decimal.Decimal, DecimalDT )
	

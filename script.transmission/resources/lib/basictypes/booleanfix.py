"""Hack to provide Python 2.3-style boolean operation in 2.2
"""
try:
	if str(True) != 'True':
		# Python 2.2.3 has True, but it's just 1 and 0 refs...
		raise NameError
	True = True
	False = False
	bool = bool
except NameError:
	class bool(int):
		def __new__(cls, val=0):
			# This constructor always returns an existing instance
			if val:
				return True
			else:
				return False

		def __repr__(self):
			if self:
				return "True"
			else:
				return "False"

		__str__ = __repr__

		def __and__(self, other):
			if isinstance(other, bool):
				return bool(int(self) & int(other))
			else:
				return int.__and__(self, other)

		__rand__ = __and__

		def __or__(self, other):
			if isinstance(other, bool):
				return bool(int(self) | int(other))
			else:
				return int.__or__(self, other)

		__ror__ = __or__

		def __xor__(self, other):
			if isinstance(other, bool):
				return bool(int(self) ^ int(other))
			else:
				return int.__xor__(self, other)

		__rxor__ = __xor__

	# Bootstrap truth values through sheer willpower
	False = int.__new__(bool, 0==1)
	True = int.__new__(bool, 1==1)

	def install():
		"""Install the enhanced bool, True and False in __builtin__"""
		import __builtin__
		__builtin__.True = True
		__builtin__.False = False
		__builtin__.bool = bool
	#install()

if __name__ == "__main__":
	assert True == 1
	assert False == 0
	

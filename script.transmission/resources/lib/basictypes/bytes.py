"""Simple class providing formatting of byte values (gigabytes, megabytes, etceteras)"""
from basictypes import basic_types


class Bytes( long ):
	"""Special data-type for byte values"""
	KILOBYTES = 1024.0
	MEGABYTES = KILOBYTES*1024
	GIGABYTES = MEGABYTES*1024
	TERABYTES = GIGABYTES*1024

	displayNames = [
		(TERABYTES, 'TB'),
		(GIGABYTES, 'GB'),
		(MEGABYTES, 'MB'),
		(KILOBYTES, 'KB'),
		(0, 'B'),
	]
	
	def coerce( cls, value ):
		"""Coerce the value to byte value"""
		if isinstance( value, cls ):
			return value
		elif isinstance( value, (str,unicode)):
			value = value.strip().upper()
			for multiplier,name in cls.displayNames:
				if value.endswith( name ):
					value = (value[:-len(name)]).strip()
					try:
						return cls( long( value ) * multiplier )
					except ValueError, err:
						try:
							return cls( long(float(value)*multiplier))
						except ValueError, err:
							raise ValueError(
								"""Unable to coerce to a Bytes type, invalid numeric component: %r"""%(
									value,
								)
							)
			# had no recognised suffix, try to convert directly with long
		# numeric or string with right format will succeed,
		# everything else will go boom
		result = cls( value )
		return result
	coerce = classmethod( coerce )
	def format( cls, value, multiplier=None, asBits=False ):
		"""Format as a string which is back-coercable

		multiplier -- pass in the appropriate multiplier for
			the value (i.e. request 'KB' to get back as kilobytes,
			default (None) indicates that the nearest should
			be used
		asBits -- if True, format a Byte value as bits, suitable
			for display in a "bandwidth" setting, as distinct
			from a simple measure of bytes.
		"""
		if value < 0:
			value = abs(value)
			neg = '-'
		else:
			neg = ""
		if asBits:
			value = value * 8
		for threshold, name in cls.displayNames:
			if value >= threshold:
				if threshold:
					value = value/threshold
					value = '%3.1f'%(value,)
				if asBits:
					name = name[:-1] + name[-1].lower()
				return '%s%s %s'%( neg, value, name)
		raise RuntimeError( """A value %r both > 0 and < 0 was encountered?"""%(value,))
	format = classmethod( format )
	
# backwards compatibility
Bytes_DT = Bytes

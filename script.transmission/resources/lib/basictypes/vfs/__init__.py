"""URL manipulation and object-oriented class hierarchy"""


def path( value, target = None, force=0 ):
	"""Convert value to the target path-type

	XXX this becomes a hook-point for creating
	virtual file-systems, with force true requiring
	the particular target and false allowing
	substitutes
	"""
	if target is None:
		from basictypes.vfs import filepath
		target = filepath.FilePath
	if not isinstance( value, target ):
		value = target( value )
	return value


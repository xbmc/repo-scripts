"""Mapping from core types/classes to stand-in DataTypeDefinitions"""
REGISTRY = {
}

def registerDT( base, DT ):
	"""Register a DataTypeDefinition for a given base-class"""
	REGISTRY[ base ] = DT

def getDT( base ):
	"""Return the appropriate DT for the given base-class

	This looks up the base in the registry, returning
	either a registered stand-alone data-type-definition
	or the base itself.
	"""
	return REGISTRY.get( base, base )

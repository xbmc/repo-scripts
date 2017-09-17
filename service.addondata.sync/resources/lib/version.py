class Comparable:
    """ 
    Base Class for a simple comparison class. A derived class only needs to
    implement an __lt__(self, other) method. All the other required methods are
    implemented by this Comparable class and are based on the __lt__ method.
    
    """

    def __init__(self):
        pass

    def __eq__(self, other):
        """ Test two objects 'for Equality'
        
        Arguments:
        other : Object - The other object.
        
        Returns:
        True or False
        
        """

        if other is None:
            return False

        return not self < other and not other < self

    def __ne__(self, other):
        """ Test two objects 'for non-equality'  
        
        Arguments:
        other : Object - The other object.
        
        Returns:
        True or False
        
        """

        return not self.__eq__(other)

    def __gt__(self, other):
        """ Test two objects for 'greater than'
        
        Arguments:
        other : Object - The other object.
        
        Returns:
        True or False
        
        """

        return other < self

    def __ge__(self, other):
        """ Test two objects for 'greater or equal than'  
        
        Arguments:
        other : Object - The other object.
        
        Returns:
        True or False
        
        """

        return not self < other

    def __le__(self, other):
        """ Test two objects for 'less than or equal'
        
        Arguments:
        other : Object - The other object.
        
        Returns:
        True or False
        
        """

        return not other < self


class Version(Comparable):
    """ Class representing a version number """

    def __init__(self, version=None, major=None, minor=None, build=None, revision=None, build_type=None):
        """ Initialises a new version number

        Keyword arguments:
        version  : String  - Version string
        major    : Integer - The Major build number
        minor    : Integer - The Minor build number
        revision : Integer - The Revision number
        build    : Integer - The Build number
        buildType: String  - None, Alpha, Beta etc

        """

        Comparable.__init__(self)

        if version is None and major is None and minor is None and revision is None and build is None:
            raise ValueError("Either a version string or a set of version numbers should be provided.")

        if version and not (major is None and minor is None and revision is None and build is None):
            raise ValueError("Only a complete version or a set of version numbers should be provided, not both.")

        if major is None and not (minor is None and revision is None and build is None):
            raise ValueError("A Major version must be provided if a minor, revision or build is provided.")

        if minor is None and not (revision is None and build is None):
            raise ValueError("A Minor version must be provided if a revision or build is provided.")

        if build is None and revision is not None:
            raise ValueError("A build number must be provided if a revision is provided.")

        self.major = major
        self.minor = minor
        self.revision = revision
        self.build = build
        if build_type is not None:
            self.buildType = build_type.lower()
        else:
            self.buildType = None

        if version:
            self.__extract_version(version)

    def equal_builds(self, other):
        """ Checks if two versions have the same version up until the revision 
        part of the version 
        
        Arguments:
        other : Version - The version to compare with.
        
        Returns:
        True or False
        
        """

        if other is None:
            return False

        return self.major == other.major and self.minor == other.minor and self.build == other.build

    def __extract_version(self, version):
        """ Extracts the Major, Minor, Revision and Build number from a version string
        
        Arguments:
        version : String - The version string
        
        """

        if "~" in version:
            version, self.buildType = version.split("~")

        split = str(version).split('.')
        if len(split) > 0:
            self.major = int(split[0])
        if len(split) > 1:
            self.minor = int(split[1])
        if len(split) > 2:
            self.build = int(split[2])
        if len(split) > 3:
            self.revision = int(split[3])

    @staticmethod
    def __none_is_zero(value):
        """ Returns 0 if a value is None. This is needed for comparison. As None
        should be interpreted as Zero. 
        
        Arguments: 
        value : Integer - The value to check for None
        
        """

        if value is None:
            return 0
        return int(value)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        """ String representation """

        if self.major is None:
            return "None"

        if self.buildType:
            if self.minor is None:
                return "%s~%s" % (self.major, self.buildType)
            elif self.build is None:
                return "%s.%s~%s" % (self.major, self.minor, self.buildType)
            elif self.revision is None:
                return "%s.%s.%s~%s" % (self.major, self.minor, self.build, self.buildType)
            else:
                return "%s.%s.%s.%s~%s" % (self.major, self.minor, self.build, self.revision, self.buildType)
        else:
            if self.minor is None:
                return str(self.major)
            elif self.build is None:
                return "%s.%s" % (self.major, self.minor)
            elif self.revision is None:
                return "%s.%s.%s" % (self.major, self.minor, self.build)
            else:
                return "%s.%s.%s.%s" % (self.major, self.minor, self.build, self.revision)

    def __lt__(self, other):
        """ Tests two versions for 'Lower Then'
        
        Arguments:
        other : Version - The version to compare with.
        
        Returns:
        True or False

        """

        version_types = ["alpha", "beta"]

        if not self.__none_is_zero(self.major) == self.__none_is_zero(other.major):
            return self.__none_is_zero(self.major) < self.__none_is_zero(other.major)

        if not self.__none_is_zero(self.minor) == self.__none_is_zero(other.minor):
            return self.__none_is_zero(self.minor) < self.__none_is_zero(other.minor)

        if not self.__none_is_zero(self.build) == self.__none_is_zero(other.build):
            return self.__none_is_zero(self.build) < self.__none_is_zero(other.build)

        if not self.__none_is_zero(self.revision) == self.__none_is_zero(other.revision):
            return self.__none_is_zero(self.revision) < self.__none_is_zero(other.revision)

        if self.buildType is None and other.buildType is None:
            # they are the same
            return False

        if self.buildType is None and other.buildType is not None:
            # one has beta/alpha, the other None, so the other is larger
            return False

        if self.buildType is not None and other.buildType is None:
            return True

        # we have 2 build types
        self_build_name = self.buildType.rstrip("0123456789")
        self_build_name_number = self.buildType.lstrip("".join(version_types))
        other_build_name = other.buildType.rstrip("0123456789")
        other_build_name_number = other.buildType.lstrip("".join(version_types))

        if self_build_name == other_build_name:
            return self_build_name_number < other_build_name_number

        return version_types.index(self_build_name) < version_types.index(other_build_name)

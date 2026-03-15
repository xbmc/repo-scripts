# -*- coding: utf-8 -*-
# Copyright (c) 2015,2018 Fredrik Eriksson <git@wb9.se>
# This file is covered by the BSD-3-Clause license, read LICENSE for details.

class ProjectorError(Exception):
    """Exception for failures in projector communication"""
    pass

class InvalidCommandError(Exception):
    """Exception for invalid input"""
    pass

class ConfigurationError(Exception):
    """Exception for invalid configuration"""
    pass

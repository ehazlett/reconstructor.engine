#!/usr/bin/env python
#
#  packagehelper.py 
#        Package helper class that downloads and resolves packages for alternate disc
#
#    Copyright (C) 2010  Lumentica
#       http://www.lumentica.com
#       info@lumentica.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import re

class DebHelper(object):
    """Resolves and downloads .deb packages"""
    def __init__(self, target_dir=''):
        self.targetdir = target_dir
        
    def add_package(self, package_name=''):
        """Adds a package to the target repository"""
        raise RuntimeError, "Not yet implemented."
        
    def remove_package(self, package_name=''):
        """Removes a package from the target repository"""
        raise RuntimeError, "Not yet implemented."
        
    def resolve_dependencies(self, package_name=''):
        """Resolves and downloads package dependencies"""
        raise RuntimeError, "Not yet implemented."
        
    def list_packages(self):
        """Lists all packages in target repository"""
        raise RuntimeError, "Not yet implemented."
        




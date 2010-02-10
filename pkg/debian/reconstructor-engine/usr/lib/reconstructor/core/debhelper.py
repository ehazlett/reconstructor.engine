#!/usr/bin/env python
#
#  packagehelper.py  (c) Reconstructor Team, 2008
#        Package helper class that downloads and resolves packages for alternate disc
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

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
        




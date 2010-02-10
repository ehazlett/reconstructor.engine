#!/usr/bin/env python
#
#  engine.py  (c) Reconstructor Team, 2008
#    Config module (misc ConfigParser routines)
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

################################################################################
# This class is a wrapper for ConfigParser. Eventually settings.py
# will be phased out as this will handle it much better once complete.
################################################################################
#
# TODO: replace print with logging code
#       Use SafeConfigParser instead of the regular
#       Exception handling
#       get(), set() functions
#       cleanup imports if need be
#
################################################################################

import os
import sys
from gettext import gettext as _
import re
import ConfigParser

#[Section]
#Option=Value

#config = ConfigParser.ConfigParser()
#fname = open("configparser.txt","r")
#config.readfp(fname)
#fname.close()
#print config.get("Test", "Value")
#config.set("Test", "Value", "NewValue")
#print config.get("Test", "Value")
#fname = open("configparser.txt","w")
#config.write(fname)
#fname.close()


class ConfigTools:
    # Constructor
    def __init__(self, ifile=None, ofile=None, debug=False):
        if debug == True:
            print "DEBUG: ConfigTools __init__"

        #create the config object
        self.config  = ConfigParser.ConfigParser()
        self.infile  = ifile
        self.outfile = ofile
        self.debug = debug

    # Read a Config File
    def readfp(self, ifile=None):
        self.config = ConfigParser.ConfigParser()
        if ofile != None:
            fname = open(ifile,"r")
        else:
            fname = open(self.infile,"r")
        self.config.readfp(fname)
        fname.close()

    # Write a Config File
    def write(self, ofile=None):
        if ofile != None:
            fname = open(ofile,"w")
        else:
            fname = open(self.outfile,"w")
        self.config.write(fname)
        fname.close()

    # Print value to the terminal
    def printValue(self, section, option):
        print self.config.get(section, option)


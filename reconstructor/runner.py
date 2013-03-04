#!/usr/bin/env python
# Copyright (c) 2013 Evan Hazlett
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from optparse import OptionParser
import logging
import os
import sys
import tempfile
from distro import Ubuntu

LOG_FILE='reconstructor.log'
LOG_CONFIG=logging.basicConfig(level=logging.DEBUG, # always log debug to file
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d-%Y %H:%M:%S',
                    filename=LOG_FILE,
                    filemode='w')

logging.config=LOG_CONFIG
console = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)-5s %(name)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def main():
    log = logging.getLogger('reconstructor.cli')

    parser = OptionParser()
    parser.add_option('--name', dest='name', default='Reconstructor Live CD',
        help='Distribution Name')
    parser.add_option('--hostname', dest='hostname', default='live',
        help='Distribution Hostname')
    parser.add_option('--arch', dest='arch', default='i386',
        help='Distribution Architecture (i.e. i386, amd64)')
    parser.add_option('--codename', dest='codename', default=None,
        help='Distribution Codename (i.e. precise)')
    parser.add_option('--output-file', dest='output_file', default=None,
        help='Output file')
    parser.add_option('--url', dest='url', default='http://reconstructor.org',
        help='Distribution URL')
    parser.add_option('--debug', dest='debug', action='store_true',
        default=False, help='Show debug')
    parser.add_option('--packages', dest='packages',
        default='',
        help='Comma separated list of additional packages to install')
    parser.add_option('--work-dir', dest='work_dir',
        default=tempfile.mkdtemp())
    parser.add_option('--skip-cleanup', dest='skip_cleanup', action='store_true',
        default=False, help='Skip removing work directory')
    # parse
    opts, args = parser.parse_args()
    # set log level
    level = logging.INFO
    if opts.debug:
        level = logging.DEBUG
    log.setLevel(level)
    console.setLevel(level)
    # check args
    if not opts.codename:
        log.error('You must specify a codename')
        sys.exit(1)
    if not opts.output_file:
        log.error('You must specify an output file')
        sys.exit(1)
    # select distro
    distros = {
        'precise': Ubuntu(**vars(opts)),
    }
    # run
    distros[opts.codename].run()
if __name__=='__main__':
    main()


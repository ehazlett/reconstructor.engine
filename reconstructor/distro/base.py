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
import os
import tempfile
import logging
import shutil
from subprocess import Popen, PIPE, STDOUT, call
import sys

class BaseDistro(object):
    """
    Core distro class

    """
    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger('distro.base')
        self._name = kwargs.get('name', 'Reconstructor Live CD')
        self._arch = kwargs.get('arch', 'i386')
        self._codename = kwargs.get('codename')
        self._hostname = kwargs.get('hostname', 'live')
        self._live_user = kwargs.get('live_user', 'liveuser')
        self._url = kwargs.get('url', 'http://reconstructor.org')
        self._work_dir = kwargs.get('work_dir', tempfile.mkdtemp())
        self._chroot_dir = os.path.join(self._work_dir, 'chroot')
        self._iso_dir = os.path.join(self._work_dir, 'iso')
        self._skip_cleanup = kwargs.get('skip_cleanup', False)
        self._packages = kwargs.get('packages', '').split(',')
        self._output_file = kwargs.get('output_file')

    def _run_command(self, cmd):
        """
        Runs a command from the host machine

        :param cmd: Command to run

        """
        out = call(cmd, shell=True)
        return out

    def _run_chroot_command(self, cmd):
        """
        Runs a command inside the chroot environment

        :param cmd: Command to run

        """
        chroot_cmd = "chroot {0} /bin/bash -c \"{1}\"".format(
            self._chroot_dir, cmd)
        out = call(chroot_cmd, shell=True)
        return out

    def _init(self):
        if not os.path.exists(self._chroot_dir):
            os.makedirs(self._chroot_dir)
        if not os.path.exists(self._iso_dir):
            os.makedirs(self._iso_dir)

    def setup(self):
        """
        Override this for initial setup

        """
        raise NotImplementedError

    def build(self):
        """
        Override this for building the distribution

        """
        raise NotImplementedError

    def add_packages(self, packages=[]):
        """
        Override this for adding packages

        """
        raise NotImplementedError

    def run_chroot_script(self):
        """
        Override this for running scripts in the chroot environment

        """
        raise NotImplementedError

    def teardown(self):
        """
        Override this for environment teardown
        """
        pass

    def cleanup(self):
        """
        Override this for cleaning up

        """
        self.log.info('Cleaning up...')
        if os.path.exists(self._work_dir):
            self.log.debug('Removing work dir: {0}'.format(self._work_dir))
            shutil.rmtree(self._work_dir)

    def run(self):
        self._init()
        self.setup()
        self.teardown()
        self.build()
        if not self._skip_cleanup:
            self.cleanup()
        else:
            self.log.info('Skipping cleanup ; work directory is {0}'.format(
                self._work_dir))

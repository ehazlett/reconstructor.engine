#!/usr/bin/env python
import os
from base import BaseDistro
import logging
from subprocess import Popen, PIPE

class Debian(BaseDistro):
    def __init__(self, version='squeeze', arch='i386', username='debian', packages=[],\
        name='DebianCustom'):
        super(Debian, self).__init__()
        self._log = logging.getLogger('debian')
        self._name = name
        self._version = version
        self._arch = arch
        self._username = username
        self._packages = packages
    
    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def arch(self):
        return self._arch

    @property
    def username(self):
        return self._username

    @property
    def packages(self):
        return self._packages

    def build(self):
        self._log.debug('build')
        cmd = "cd {0} && ".format(self._build_dir)
        cmd += "lb config --debian-installer true --debian-installer-gui true "
        cmd += "-a {0} ".format(self._arch)
        cmd += "-d {0} ".format(self._version)
        cmd += "--iso-application \"{0}\" ".format(self._copyright)
        cmd += "--iso-volume \"{0}\" ".format(self._name)
        cmd += "--mode debian "
        cmd += "-m http://localhost:3142/apt-cacher/ftp.us.debian.org/debian "
        cmd += "--username {0} ".format(self._username)
        cmd += "--packages \"{0}\" ".format(' '.join(self._packages))
        self._log.debug(cmd)
        self._run_command(cmd)
        # build
        cmd = "cd {0} && ".format(self._build_dir)
        cmd += "lb build"
        self._run_command(cmd)
        iso_file = os.path.join(self._build_dir, 'binary.iso')
        if os.path.exists(iso_file):
            os.rename(iso_file, os.path.join(os.getcwd(), '{0}-{1}.iso'.format(self._name, self._arch)))




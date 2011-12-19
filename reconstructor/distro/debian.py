#!/usr/bin/env python
import os
from base import BaseDistro
import logging
import tarfile
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue, Empty
import time
try:
    import simplejson as json
except ImportError:
    import json
from reconstructor.buildserver import BuildLogHandler

class Debian(BaseDistro):
    def __init__(self, project=None, version='squeeze', arch='i386', username='debian', packages=[],\
        name='DebianCustom', apt_cacher_host=None, mirror=None, extra_log_handler=None, **kwargs):
        super(Debian, self).__init__()
        self._log = logging.getLogger('debian')
        if extra_log_handler:
            extra_log_handler.setLevel(logging.DEBUG)
            self._log.addHandler(extra_log_handler)
        if 'build_uuid' in kwargs:
            blh = BuildLogHandler(build_uuid=kwargs['build_uuid'])
            self._log.addHandler(blh)
        self._project = project
        self._name = name
        self._version = version
        self._arch = arch
        self._username = username
        self._packages = packages
        if apt_cacher_host and apt_cacher_host != '':
            self._apt_cacher_host = apt_cacher_host
        else:
            self._apt_cacher_host = None
        if mirror and mirror != '':
            self._mirror = mirror
        else:
            self._mirror = 'http://ftp.us.debian.org/debian'
        # load project if needed
        if self._project:
            self._load_project()
    
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

    def _run(self, cmds=None, cwd=None):
        """
        This run method will stream the output of the command

        """
        if not cmds:
            return False
        if cwd:
            os.chdir(cwd)
        p = Popen(cmds, stdout=PIPE, bufsize=1, close_fds=False)
        out = p.stdout
        while True:
            o = out.readline()
            if o != '':
                self._log.debug(o.replace('\n', ''))
            else:
                break

    def _load_project(self):
        if not os.path.exists(self._project):
            self._log.error('Unable to find project file {0}'.format(self._project))
            return None
        self._log.debug('Extracting project {0}'.format(self._project))
        tf = tarfile.open(self._project)
        tf.extractall(self._build_dir)
        prj = json.loads(open(os.path.join(self._build_dir, 'project.json'), 'r').read())
        self._name = prj['name']
        self._arch = prj['arch']
        self._version = prj['distro']['codename']
        self._packages = [x['name'] for x in prj['packages']]

    def _config(self):
        self._log.info('Configuring...')
        cmd = "cd {0} && ".format(self._build_dir)
        cmd += "lb config "
        cmd += "-a {0} ".format(self._arch)
        cmd += "-d {0} ".format(self._version)
        cmd += "--debian-installer live "
        #cmd += "--debian-installer-gui true "
        cmd += "--iso-application \"{0}\" ".format(self._copyright)
        cmd += "--iso-volume \"{0}\" ".format(self._name)
        cmd += "--archive-areas \"main contrib non-free\" "
        cmd += "--debian-installer-distribution {0} ".format(self._version)
        #cmd += "--debian-installer-distribution daily "
        cmd += "--mode debian "
        if self._apt_cacher_host:
            if self._mirror.find('//') > -1:
                self._mirror = self._mirror.split('//')[-1]
            cmd += "-m http://{0}/apt-cacher/{1} ".format(self._apt_cacher_host, self._mirror)
        else:
            cmd += "-m {0} ".format(self._mirror)
        cmd += "--username {0} ".format(self._username)
        cmd += "--packages \"{0}\" ".format(' '.join(self._packages))
        #self._log.debug(cmd)
        self._run_command(cmd)

    def _bootstrap(self):
        self._log.info('Running bootstrap...')
        #cmd = "cd {0} && ".format(self._build_dir)
        cmds = ['lb', 'bootstrap']
        #self._run_command(cmd)
        self._run(cmds, self._build_dir)

    def _chroot(self):
        self._log.info('Running chroot...')
        #cmd = "cd {0} && ".format(self._build_dir)
        #cmd += "lb chroot"
        #self._run_command(cmd)
        cmds = ['lb', 'chroot']
        self._run(cmds, self._build_dir)
    
    def _build_iso(self):
        self._log.info('Running binary...')
        #cmd = "cd {0} && ".format(self._build_dir)
        #cmd += "lb binary"
        #self._run_command(cmd)
        cmds = ['lb', 'binary']
        self._run(cmds, self._build_dir)
        if os.path.exists(os.path.join(self._build_dir, 'binary.iso')):
            iso_file = os.path.join(self._build_dir, 'binary.iso')
        elif os.path.exists(os.path.join(self._build_dir, 'binary-amd64.iso')):
            iso_file = os.path.join(self._build_dir, 'binary-amd64.iso')
        elif os.path.exists(os.path.join(self._build_dir, 'binary-hybrid.iso')):
            iso_file = os.path.join(self._build_dir, 'binary-hybrid.iso')
        else:
            iso_file = None
        if iso_file and os.path.exists(iso_file):
            os.rename(iso_file, os.path.join(os.getcwd(), '{0}-{1}.iso'.format(self._name, self._arch)))

    def build(self):
        # config
        self._config()
        # bootstrap
        self._bootstrap()
        # chroot
        self._chroot()
        # binary
        self._build_iso()
        self._log.info('Build complete')


